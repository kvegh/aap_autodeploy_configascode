"""Retire only proven same-version guest grants and exercise native rollback tasks."""
import copy
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.errors import AnsibleFilterError

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("decommission_guest_access", ROOT / "filter_plugins/aap_decommission.py")
RETIRE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RETIRE)


def fixture():
    pin = {"address": "192.0.2.10", "public_ip": "192.0.2.10", "port": 2222,
           "user": "automation", "machine_id": "1" * 32,
           "host_keys": ["ssh-ed25519 AAAA"], "isolation_bridges": ["vmbr0"],
           "isolation_dns_bridges": ["vmbr0"]}
    route = {"vm_name": "aap27-test-7", "vm_ip": "192.168.70.10", "hypervisor": pin,
             "aap_hostname": "https://aap27.v07.example.invalid", "guest_host_keys": ["ssh-ed25519 AAAA"]}
    metadata = {"zabbix": {"uuid": "11111111-2222-3333-4444-555555555555", "address": "192.168.70.20",
                           "mac": "52:54:00:12:34:57", "network": "isolated",
                           "disk": "/opt/vms/zabbix-v07.disk.qcow2", "verified": True}}
    selected = RETIRE.resources(route, "example.invalid", "/opt/vms", metadata)
    clients = [{"bridge": "vmbr0", "ipv4": route["vm_ip"], "mac": "52:54:00:12:34:56",
                "destinations": [pin["address"]], "ports": [2222]},
               {"bridge": "vmbr0", "ipv4": "192.168.70.20", "mac": "52:54:00:12:34:57",
                "destinations": ["192.168.70.1"], "ports": [443]},
               {"bridge": "vmbr0", "ipv4": "192.168.70.30", "mac": "52:54:00:12:34:58",
                "destinations": ["192.168.70.1"], "ports": [443]}]
    policy = {"bridges": ["vmbr0"], "dns_bridges": ["vmbr0"], "guest_host_clients": clients,
              "https_clients": [{key: client[key] for key in ("bridge", "ipv4", "mac")}
                                for client in (clients[0], clients[2])], "protected_ipv4": ["198.51.100.20"]}
    xmls = {}
    for domain, client in zip(selected["domains"][:2], clients):
        uuid = metadata["zabbix"]["uuid"] if not domain["primary"] else "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        xmls[domain["name"]] = ('<domain><name>%s</name><uuid>%s</uuid><devices>'
            '<disk device="disk"><source file="%s"/></disk><interface type="network">'
            '<mac address="%s"/><source network="isolated"/></interface></devices></domain>'
            % (domain["name"], uuid, domain["disk"], client["mac"]))
    networks = {"isolated": '<network><name>isolated</name><bridge name="vmbr0"/></network>'}
    return policy, selected, route, metadata, xmls, networks


class GuestAccessRetirementTests(unittest.TestCase):
    def test_missing_source_guest_checks_both_disk_variants_before_any_vm_operation(self):
        for orphan in (False, True):
            with self.subTest(orphan=orphan), tempfile.TemporaryDirectory(prefix="missing-related-disk-") as temporary:
                directory = Path(temporary)
                tasks = yaml.safe_load((ROOT / "tasks/decommission-related-check.yml").read_text())
                for task in tasks:
                    if task.get("name") == "Inspect both bounded related disk variants before any deletion":
                        task["loop"] = [path.replace('/opt/vms/', str(directory) + '/') for path in task["loop"]]
                if orphan:
                    (directory / "zabbix-v07.qcow2").write_text("synthetic unrecorded image")
                play = directory / "play.yml"
                play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "become": False,
                    "gather_facts": False, "vars": {"aap_related_guest": {"name": "zabbix-v07",
                        "disk": str(directory / "zabbix-v07.disk.qcow2"), "uuid": None},
                        "aap_retirement_domains": {"stdout_lines": []}}, "tasks": tasks}], sort_keys=False))
                config = directory / "ansible.cfg"
                config.write_text("[defaults]\n")
                env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_LOCAL_TEMP=str(directory / "local"),
                           ANSIBLE_REMOTE_TEMP=str(directory / "remote"))
                result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play), "--check"],
                    env=env, text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 2 if orphan else 0, result.stdout + result.stderr)
                self.assertNotIn('"cmd": ["virsh"', result.stdout)
                if orphan:
                    self.assertEqual((directory / "zabbix-v07.qcow2").read_text(), "synthetic unrecorded image")

    def test_selected_identities_are_removed_from_both_lists_without_other_changes(self):
        inputs = fixture()
        original = copy.deepcopy(inputs)
        plan = RETIRE.guest_access_plan(*inputs)
        self.assertEqual(inputs, original)
        self.assertTrue(plan["changed"])
        self.assertEqual(len(plan["identities"]), 2)
        self.assertEqual(plan["desired_policy"]["guest_host_clients"], [inputs[0]["guest_host_clients"][2]])
        self.assertEqual(plan["desired_policy"]["https_clients"], [inputs[0]["https_clients"][1]])
        self.assertEqual(plan["desired_policy"]["protected_ipv4"], inputs[0]["protected_ipv4"])
        self.assertEqual(len(plan["rich_rules_to_remove"]), 2)
        self.assertIn('port port="2222"', " ".join(plan["rich_rules_to_remove"]))
        self.assertTrue(all('destination address=' in rule and 'priority="0"' in rule
                            for rule in plan["rich_rules_to_remove"]))

    def test_last_clients_remove_optional_pair_and_default_is_idempotent(self):
        inputs = list(fixture())
        inputs[0]["guest_host_clients"].pop()
        inputs[0]["https_clients"].pop()
        plan = RETIRE.guest_access_plan(*inputs)
        self.assertEqual(plan["desired_policy"], {"bridges": ["vmbr0"], "dns_bridges": ["vmbr0"]})
        inputs[0] = plan["desired_policy"]
        again = RETIRE.guest_access_plan(*inputs)
        self.assertFalse(again["changed"])
        self.assertEqual(again["rich_rules_to_remove"], [])

    def test_primary_recorded_uuid_mac_and_bridge_are_additional_mandatory_proofs(self):
        for field, value in (("uuid", "00000000-0000-0000-0000-000000000000"),
                             ("mac", "52:54:00:12:34:99"), ("bridge", "other0"),
                             ("address", "192.168.70.99")):
            inputs = list(fixture())
            inputs[3]["aap"] = {"uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "disk": inputs[1]["disk"], "mac": "52:54:00:12:34:56", "bridge": "vmbr0",
                "address": inputs[2]["vm_ip"], "network": "isolated", "verified": True}
            inputs[3]["aap"][field] = value
            with self.subTest(field=field), self.assertRaises(AnsibleFilterError):
                RETIRE.guest_access_plan(*inputs)

    def test_recorded_absent_guest_identity_can_retire_its_stale_grants(self):
        inputs = list(fixture())
        inputs[4].pop("zabbix-v07")
        plan = RETIRE.guest_access_plan(*inputs)
        self.assertEqual(len(plan["rich_rules_to_remove"]), 2)
        inputs[3]["zabbix"].pop("mac")
        with self.assertRaises(AnsibleFilterError):
            RETIRE.guest_access_plan(*inputs)

    def test_absent_legacy_primary_with_remaining_grants_refuses_an_invented_identity(self):
        inputs = list(fixture())
        inputs[4].pop("aap27-test-7")
        with self.assertRaises(AnsibleFilterError):
            RETIRE.guest_access_plan(*inputs)

    def test_mismatched_live_ip_mac_bridge_disk_uuid_or_foreign_domain_refuse(self):
        for kind in ("ip", "mac", "bridge", "disk", "uuid", "foreign", "extra_interface", "extra_policy"):
            inputs = list(fixture())
            if kind == "ip": inputs[2]["vm_ip"] = "192.168.70.90"
            if kind == "mac": inputs[4]["aap27-test-7"] = inputs[4]["aap27-test-7"].replace("12:34:56", "12:34:99")
            if kind == "bridge": inputs[5]["isolated"] = inputs[5]["isolated"].replace("vmbr0", "foreign0")
            if kind == "disk": inputs[4]["aap27-test-7"] = inputs[4]["aap27-test-7"].replace("/opt/vms/", "/other/")
            if kind == "uuid": inputs[4]["zabbix-v07"] = inputs[4]["zabbix-v07"].replace("11111111-", "00000000-")
            if kind == "foreign": inputs[1]["domains"][1]["name"] = "zabbix-v08"
            if kind == "extra_interface": inputs[4]["aap27-test-7"] = inputs[4]["aap27-test-7"].replace("</devices>", '<interface type="bridge"/></devices>')
            if kind == "extra_policy": inputs[0]["unknown"] = True
            with self.subTest(kind=kind), self.assertRaises(AnsibleFilterError):
                RETIRE.guest_access_plan(*inputs)

    def test_only_recorded_network_names_are_resolved(self):
        inputs = fixture()
        self.assertEqual(RETIRE.guest_networks(inputs[4], inputs[3]), ["isolated"])
        with self.assertRaises(AnsibleFilterError):
            RETIRE.guest_networks({}, {"aap": {"network": "--all"}})

    def test_retry_accepts_only_canonical_or_exact_proven_retirement_policy(self):
        inputs = fixture()
        first = RETIRE.guest_access_plan(*inputs)
        retry = RETIRE.guest_access_plan(*inputs, actual_policy=first["desired_policy"])
        self.assertTrue(retry["changed"])
        self.assertFalse(retry["requires_local_update"])
        self.assertEqual(retry["rich_rules_to_remove"], first["rich_rules_to_remove"])
        self.assertEqual(retry["previous_policy"], inputs[0])
        for field in ("guest_host_clients", "https_clients"):
            invalid = copy.deepcopy(first["desired_policy"])
            invalid[field] = []
            with self.subTest(field=field), self.assertRaises(AnsibleFilterError):
                RETIRE.guest_access_plan(*inputs, actual_policy=invalid)

    def test_real_ansible_preflight_plan_preserves_canonical_handoff_on_a_retry(self):
        inputs = fixture()
        expected = RETIRE.guest_access_plan(*inputs)
        tasks = yaml.safe_load((ROOT / "tasks/decommission-guest-access.yml").read_text())[1]["block"]
        selected = [task for task in tasks if task["name"] in (
            "Plan removal of only verified selected guest identities",
            "Expose the protected policy handoff for canonical source retirement")]
        with tempfile.TemporaryDirectory(prefix="decommission-plan-typing-") as temporary:
            directory = Path(temporary)
            variables = {"aap_hypervisor_pin": inputs[2]["hypervisor"],
                "aap_hypervisor_isolation_https_clients": inputs[0]["https_clients"],
                "aap_hypervisor_isolation_protected_ipv4": inputs[0]["protected_ipv4"],
                "aap_hypervisor_isolation_host_clients": inputs[0]["guest_host_clients"],
                "aap_retirement": inputs[1], "aap_instance_route": inputs[2], "aap_instance_resources": inputs[3],
                "aap_decommission_guest_xmls": inputs[4], "aap_decommission_guest_network_xmls": inputs[5],
                "aap_decommission_isolation_capture": {"content": base64.b64encode(json.dumps(expected["desired_policy"]).encode()).decode()}}
            play = directory / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "become": False,
                "gather_facts": False, "vars": variables, "tasks": selected + [{"ansible.builtin.assert": {"that": [
                    "aap_decommission_isolation_retirement is mapping",
                    "aap_decommission_guest_access_plan.changed",
                    "aap_decommission_guest_access_plan.requires_local_update",
                    "aap_decommission_isolation_retirement.previous_policy.guest_host_clients | length == 3",
                    "aap_decommission_isolation_retirement.desired_policy.guest_host_clients | length == 1"]}}]}], sort_keys=False))
            config = directory / "ansible.cfg"
            config.write_text("[defaults]\n")
            env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"),
                       ANSIBLE_LOCAL_TEMP=str(directory / "local"), ANSIBLE_REMOTE_TEMP=str(directory / "remote"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                    env=env, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_teardown_order_proves_permissions_before_shutdown_and_cleanup_before_undefine(self):
        play = yaml.safe_load((ROOT / "destroy-test-aap.yml").read_text())[0]
        preflight = next(index for index, task in enumerate(play["pre_tasks"])
                         if task.get("ansible.builtin.include_tasks") == "tasks/decommission-guest-access.yml")
        end = next(index for index, task in enumerate(play["pre_tasks"]) if "ansible.builtin.meta" in task)
        self.assertLess(preflight, end)
        tasks = play["tasks"]
        stopped = next(index for index, task in enumerate(tasks)
                       if "aap_decommission_selected_guests_stopped" in task.get("ansible.builtin.set_fact", {}))
        cleanup = next(index for index, task in enumerate(tasks)
                       if task.get("ansible.builtin.include_tasks") == "tasks/decommission-guest-access.yml")
        undefine = next(index for index, task in enumerate(tasks)
                        if "undefine" in task.get("ansible.builtin.command", {}).get("argv", []))
        self.assertLess(stopped, cleanup)
        self.assertLess(cleanup, undefine)
        self.assertEqual(tasks[undefine]["loop"], "{{ aap_retirement.domains }}")
        self.assertIn("aap_publish_instance_keys", tasks[-2])

    def test_shared_identity_preserves_ordinary_policy_checks_and_strict_decommission_path(self):
        identity = yaml.safe_load((ROOT / "tasks/aap-hypervisor-identity.yml").read_text())
        pin = yaml.safe_load((ROOT / "tasks/aap-hypervisor-pin.yml").read_text())
        self.assertEqual(pin[0]["ansible.builtin.include_tasks"], "aap-hypervisor-identity.yml")
        self.assertIn("aap_hypervisor_isolation_host_clients", pin[1]["ansible.builtin.set_fact"]["aap_isolation_pin_policy"])
        self.assertEqual(pin[2]["block"][1]["ansible.builtin.include_tasks"], "aap-isolation-observe.yml")
        self.assertEqual(pin[2]["always"][0]["ansible.builtin.include_tasks"], "aap-isolation-finish.yml")
        self.assertEqual(pin[3]["loop"], ["is-active", "is-enabled"])
        connection = next(task["ansible.builtin.set_fact"] for task in identity if "ansible.builtin.set_fact" in task)
        self.assertTrue(connection["ansible_host_key_checking"])
        self.assertIn("StrictHostKeyChecking=yes", connection["ansible_ssh_common_args"])
        self.assertEqual(identity[-1]["ansible.builtin.command"]["argv"], ["cat", "/etc/machine-id"])
        self.assertIn("aap_hypervisor_pin.machine_id", identity[-1]["failed_when"])
        play = yaml.safe_load((ROOT / "destroy-test-aap.yml").read_text())[0]
        self.assertEqual(play["pre_tasks"][2]["ansible.builtin.include_tasks"], "tasks/aap-hypervisor-identity.yml")

    def run_apply(self, fail=False, check=False, applications=False, no_delete=False):
        inputs = fixture()
        app_clients = []
        app_owners = []
        selected_app_clients = []
        if applications:
            selected_app_clients = [copy.deepcopy(inputs[0]['guest_host_clients'][1])]
            inputs[0]['guest_host_clients'].pop(1)
            other = {'bridge': 'vmbr0', 'ipv4': '192.168.70.99', 'mac': '52:54:00:00:00:99',
                     'destinations': ['192.168.70.1'], 'ports': [443]}
            app_clients = selected_app_clients + [other]
            guest = dict(inputs[3]['zabbix'], vm_name='zabbix-v07', instance_name=inputs[2]['vm_name'])
            app_owners = [{'guest': guest, 'clients': selected_app_clients},
                          {'guest': dict(guest, instance_name='aap27-test-8', vm_name='zabbix-v08',
                                         uuid='88888888-2222-3333-4444-555555555555',
                                         disk='/opt/vms/zabbix-v08.disk.qcow2', address=other['ipv4'], mac=other['mac']), 'clients': [other]}]
        plan = RETIRE.guest_access_plan(*inputs)
        effective_previous = copy.deepcopy(plan['previous_policy'])
        effective_previous['guest_host_clients'] += app_clients
        effective_desired = copy.deepcopy(plan['desired_policy'])
        effective_desired['guest_host_clients'] += [row for row in app_clients if row not in selected_app_clients]
        def rich_rule(row):
            return ('rule family="ipv4" priority="0" source address="%s/32" destination address="%s/32" '
                    'port port="%s" protocol="tcp" accept' % (row['ipv4'], row['destinations'][0], row['ports'][0]))
        application_rules = [rich_rule(row) for row in app_clients]
        remaining_app_rules = [rich_rule(row) for row in app_clients if row not in selected_app_clients]
        with tempfile.TemporaryDirectory(prefix='retire-native-ansible-') as temporary:
            directory = Path(temporary)
            policy = directory/'hactar-recovery.nft'
            policy.write_text(json.dumps(effective_previous))
            native = directory/'firewalld-fixture.json'
            original_native = {'runtime':plan['rich_rules_to_remove']+application_rules+['unrelated'],
                               'permanent':plan['rich_rules_to_remove']+application_rules+['unrelated']}
            native.write_text(json.dumps(original_native))
            events = directory/'events.jsonl'
            (directory/'action_plugins').mkdir()
            (directory/'action_plugins/fixture_firewall.py').write_text(
                'import json,pathlib\nfrom ansible.plugins.action import ActionBase\n'
                'class ActionModule(ActionBase):\n'
                ' def run(self,tmp=None,task_vars=None):\n'
                '  path=pathlib.Path('+repr(str(native))+');state=json.loads(path.read_text())\n'
                '  for item in self._templar.template(task_vars["firewall"]):\n'
                '   if task_vars["fixture_no_delete"] and item["state"]=="disabled":continue\n'
                '   rules=item["rich_rule"] if isinstance(item["rich_rule"],list) else [item["rich_rule"]]\n'
                '   for kind in ("runtime","permanent"):\n'
                '    if not item[kind]:continue\n'
                '    for rule in rules:\n'
                '     if item["state"]=="disabled" and rule in state[kind]:state[kind].remove(rule)\n'
                '     elif item["state"]=="enabled" and rule not in state[kind]:state[kind].append(rule)\n'
                '  path.write_text(json.dumps(state))\n'
                '  return {"changed":True}\n')
            collection=directory/'collections/ansible_collections/redhat/rhel_system_roles/roles/firewall/tasks'
            collection.mkdir(parents=True)
            (collection/'main.yml').write_text(yaml.safe_dump([
                {'name':'Exercise exact certified-role inputs in isolated fixture','ansible.legacy.fixture_firewall':{}}]))
            hactar=directory/'hactar/playbooks/tasks'
            hactar.mkdir(parents=True)
            (hactar/'replacement-isolation-apply.yml').write_text(yaml.safe_dump([
                {'name':'Record complete nft policy candidate','ansible.builtin.lineinfile':{
                    'path':str(events),'create':True,'mode':'0600','line':'{{ hactar_isolation_policy | to_json }}'}},
                {'name':'Refuse injected native apply failure','ansible.builtin.assert':{'that':
                    "not fixture_fail or hactar_isolation_policy == fixture_previous"}},
                {'name':'Apply native nft fixture policy','ansible.builtin.copy':{'dest':str(policy),
                    'content':'{{ hactar_isolation_policy | to_json }}','mode':'0600'}}]))
            for name,data in {
                'aap-isolation-prepare.yml':[{'name':'Prepare synthetic locked native transaction','ansible.builtin.set_fact':{
                    'aap_isolation_lock_acquired':False,'aap_isolation_source_workspace':{},
                    'hactar_firewall_source_root':str(directory/'hactar')}}],
                'decommission-network-readback.yml':[{'name':'Retain synthetic actual network definitions','ansible.builtin.set_fact':{
                    'aap_decommission_guest_network_xmls':{name:{'persistent':xml,'current':xml} for name,xml in inputs[5].items()}}}]
            }.items():
                (directory/name).write_text(yaml.safe_dump(data,sort_keys=False))
            (directory/'aap-isolation-observe.yml').write_text((ROOT/'tasks/aap-isolation-observe.yml').read_text())
            (directory/'decommission-aiops-access.yml').write_text((ROOT/'tasks/decommission-aiops-access.yml').read_text())
            (hactar/'replacement-isolation-validate.yml').write_text(yaml.safe_dump([
                {'name':'Validate synthetic complete native policy','ansible.builtin.assert':{'that':'hactar_isolation_policy is mapping'}}]))
            (hactar/'replacement-isolation-readback.yml').write_text(yaml.safe_dump([
                {'name':'Read synthetic native policy','ansible.builtin.slurp':{'src':str(policy)},'register':'fixture_native'},
                {'name':'Compare complete native policy','ansible.builtin.set_fact':{'__hactar_isolation_matches':
                    '{{ (fixture_native.content | b64decode | from_json) == hactar_isolation_policy }}'}}]))
            (directory/'aap-isolation-finish.yml').write_text((ROOT/'tasks/aap-isolation-finish.yml').read_text())
            firewall=directory/'firewall-cmd'
            firewall.write_text('#!/usr/bin/env python3\nimport json,pathlib,sys\n'
                'state=json.loads(pathlib.Path('+repr(str(native))+').read_text())\n'
                'kind="permanent" if "--permanent" in sys.argv else "runtime"\n'
                'rule=next(x.split("=",1)[1] for x in sys.argv if x.startswith("--query-rich-rule="))\n'
                'raise SystemExit(0 if rule in state[kind] else 1)\n')
            firewall.chmod(0o700)
            tasks=yaml.safe_load((ROOT/'tasks/decommission-guest-access.yml').read_text())
            def adapt(rows):
                for task in rows:
                    command=task.get('ansible.builtin.command',{})
                    if command.get('argv',[None])[0]=='firewall-cmd':command['argv'][0]=str(firewall)
                    for section in ('block','rescue','always'):adapt(task.get(section,[]))
            adapt(tasks)
            variables={'aap_decommission_guest_access_phase':'apply','aap_decommission_selected_guests_stopped':True,
                'aap_decommission_guest_network_names':list(inputs[5]),
                'aap_instance_route':inputs[2], 'aap_retirement':inputs[1], 'aap_decommission_guest_xmls':inputs[4],
                'aap_decommission_app_clients':selected_app_clients, 'aap_isolation_app_clients':app_clients,
                'aap_isolation_app_owners':app_owners,
                'aap_decommission_reservations':RETIRE.reservation_plan(
                    {name:{'persistent':xml,'current':xml} for name,xml in inputs[5].items()},inputs[2],inputs[3]),
                'aap_decommission_isolation_retirement':{key:plan[key] for key in ('previous_policy','desired_policy','identities')},
                'aap_decommission_guest_access_plan':plan,'fixture_fail':fail,'fixture_previous':effective_previous,'fixture_no_delete':no_delete}
            play=directory/'play.yml'
            play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','become':False,
                'gather_facts':False,'vars':variables,'tasks':tasks}],sort_keys=False))
            config=directory/'ansible.cfg';config.write_text('[defaults]\n')
            env=dict(os.environ,ANSIBLE_CONFIG=str(config),ANSIBLE_FILTER_PLUGINS=str(ROOT/'filter_plugins'),
                ANSIBLE_ACTION_PLUGINS=str(directory/'action_plugins'),ANSIBLE_COLLECTIONS_PATH=str(directory/'collections'),
                ANSIBLE_LOCAL_TEMP=str(directory/'local'),ANSIBLE_REMOTE_TEMP=str(directory/'remote'))
            command=[sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)]
            if check:command.append('--check')
            result=subprocess.run(command,env=env,text=True,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,2 if fail or check or no_delete else 0,result.stdout+result.stderr)
            self.assertEqual(json.loads(policy.read_text()),effective_previous if fail or check or no_delete else effective_desired)
            result_rules=json.loads(native.read_text())
            for kind in ('runtime','permanent'):
                self.assertEqual(set(result_rules[kind]),set(original_native[kind]) if fail or check or no_delete else set(remaining_app_rules+['unrelated']))
            if check:self.assertFalse(events.exists())

    def test_native_ansible_removes_only_exact_rules_and_applies_complete_cac(self):
        self.run_apply()

    def test_native_ansible_failure_restores_prior_cac_and_exact_rich_rule_states(self):
        self.run_apply(fail=True)

    def test_selected_app_rules_are_removed_before_owner_retirement_and_other_instance_survives(self):
        self.run_apply(applications=True)

    def test_failed_selected_app_cleanup_restores_exact_states_and_retains_owner_records(self):
        self.run_apply(fail=True, applications=True)

    def test_absence_check_stops_retirement_if_a_native_rule_was_not_removed(self):
        self.run_apply(applications=True, no_delete=True)

    def test_check_mode_refuses_permission_removal_without_native_writes(self):
        self.run_apply(check=True)


if __name__ == '__main__':
    unittest.main()
