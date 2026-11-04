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
                    "not aap_decommission_guest_access_plan.requires_local_update",
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
        self.assertEqual(pin[1]["ansible.builtin.command"]["argv"], ["/usr/local/sbin/hactar-recovery-isolation", "check"])
        self.assertIn("aap_hypervisor_isolation_host_clients", pin[1]["ansible.builtin.command"]["stdin"])
        self.assertEqual(pin[2]["loop"], ["is-active", "is-enabled"])
        connection = next(task["ansible.builtin.set_fact"] for task in identity if "ansible.builtin.set_fact" in task)
        self.assertTrue(connection["ansible_host_key_checking"])
        self.assertIn("StrictHostKeyChecking=yes", connection["ansible_ssh_common_args"])
        self.assertEqual(identity[-1]["ansible.builtin.command"]["argv"], ["cat", "/etc/machine-id"])
        self.assertIn("aap_hypervisor_pin.machine_id", identity[-1]["failed_when"])
        play = yaml.safe_load((ROOT / "destroy-test-aap.yml").read_text())[0]
        self.assertEqual(play["pre_tasks"][2]["ansible.builtin.include_tasks"], "tasks/aap-hypervisor-identity.yml")

    def test_actual_preflight_check_mode_reads_verified_transition_without_host_writes(self):
        inputs = fixture()
        plan = RETIRE.guest_access_plan(*inputs)
        with tempfile.TemporaryDirectory(prefix="decommission-check-preflight-") as temporary:
            directory = Path(temporary)
            policy = directory / "policy.json"
            before = json.dumps(plan["desired_policy"])
            policy.write_text(before)
            policy.chmod(0o600)
            events = directory / "events.jsonl"
            helper = directory / "isolation"
            helper.write_text("#!/usr/bin/env python3\nimport json,pathlib,sys\n" +
                "p=pathlib.Path(%r);log=pathlib.Path(%r)\n" % (str(policy), str(events)) +
                "with log.open('a') as f: f.write(json.dumps(sys.argv[1:])+chr(10))\n" +
                "assert sys.argv[1:] == ['check']\nassert json.load(sys.stdin)==json.loads(p.read_text())\n")
            helper.chmod(0o700)
            for executable in ("virsh", "systemctl", "firewall-cmd"):
                stub = directory / executable
                stub.write_text("#!/usr/bin/env python3\nimport json,pathlib,sys\n" +
                    "log=pathlib.Path(%r)\n" % str(events) +
                    "with log.open('a') as f: f.write(json.dumps(sys.argv)+chr(10))\n" +
                    "xmls=%r\nnetworks=%r\n" % (inputs[4], inputs[5]) +
                    "if 'dumpxml' in sys.argv: print(xmls[sys.argv[-1]])\n" +
                    "elif 'net-dumpxml' in sys.argv: print(networks[sys.argv[-1]])\n" +
                    "elif pathlib.Path(sys.argv[0]).name=='systemctl': assert sys.argv[1] in ('is-active','is-enabled')\n" +
                    "else: assert any(x.startswith('--query-rich-rule=') for x in sys.argv)\n")
                stub.chmod(0o700)
            tasks = yaml.safe_load((ROOT / "tasks/decommission-guest-access.yml").read_text())
            for task in tasks[1]["block"]:
                if "ansible.builtin.stat" in task:
                    task["ansible.builtin.stat"]["path"] = str(policy)
                if "ansible.builtin.slurp" in task:
                    task["ansible.builtin.slurp"]["src"] = str(policy)
                if task["name"] == "Require the existing root-owned regular isolation file":
                    # A user-owned disposable fixture substitutes only the owner assertion.
                    task["ansible.builtin.assert"]["that"] = [value.replace(".uid == 0", ".uid == %s" % os.getuid())
                                                               for value in task["ansible.builtin.assert"]["that"]]
                command = task.get("ansible.builtin.command", {})
                if command.get("argv", [None])[0] == "/usr/local/sbin/hactar-recovery-isolation":
                    command["argv"][0] = str(helper)
                elif command.get("argv", [None])[0] in ("virsh", "systemctl", "firewall-cmd"):
                    command["argv"][0] = str(directory / command["argv"][0])
            variables = {"aap_decommission_guest_access_phase": "preflight",
                "aap_hypervisor_pin": inputs[2]["hypervisor"], "aap_instance_route": inputs[2],
                "aap_instance_resources": inputs[3], "aap_retirement": inputs[1],
                "aap_retirement_domains": {"stdout_lines": list(inputs[4])},
                "aap_hypervisor_isolation_https_clients": inputs[0]["https_clients"],
                "aap_hypervisor_isolation_protected_ipv4": inputs[0]["protected_ipv4"],
                "aap_hypervisor_isolation_host_clients": inputs[0]["guest_host_clients"]}
            play = directory / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "become": False,
                "gather_facts": False, "vars": variables, "tasks": tasks + [{"ansible.builtin.assert": {"that": [
                    "aap_decommission_isolation_retirement is mapping",
                    "not aap_decommission_guest_access_plan.requires_local_update",
                    "aap_decommission_guest_access_plan.rich_rules_to_remove | length == 2"]}}]}], sort_keys=False))
            config = directory / "ansible.cfg"
            config.write_text("[defaults]\n")
            env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"),
                       ANSIBLE_LOCAL_TEMP=str(directory / "local"), ANSIBLE_REMOTE_TEMP=str(directory / "remote"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play), "--check"],
                                    env=env, text=True, capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(policy.read_text(), before)
            recorded = [json.loads(line) for line in events.read_text().splitlines()]
            self.assertTrue(recorded)
            self.assertFalse(any("apply" in event or any(str(part).startswith('--remove-rich-rule=')
                                                       for part in event) for event in recorded))

    def run_apply(self, fail=False, check=False):
        inputs = fixture()
        plan = RETIRE.guest_access_plan(*inputs)
        with tempfile.TemporaryDirectory(prefix="retire-guest-access-") as temporary:
            directory = Path(temporary)
            policy = directory / "policy.json"
            policy.write_text(json.dumps(plan["previous_policy"]))
            native = directory / "native.json"
            native.write_text(json.dumps({"runtime": plan["rich_rules_to_remove"] + ["unrelated"],
                                          "permanent": plan["rich_rules_to_remove"] + ["unrelated"]}))
            events = directory / "events.jsonl"
            helper = directory / "isolation"
            helper.write_text("#!/usr/bin/env python3\n" +
                "import json,pathlib,sys\n" +
                "p=pathlib.Path(%r); log=pathlib.Path(%r)\n" % (str(policy), str(events)) +
                "value=json.loads(p.read_text()); action=sys.argv[1]\n" +
                "with log.open('a') as f: f.write(json.dumps([action,value])+chr(10))\n" +
                "if action=='check':\n value_from_stdin=json.load(sys.stdin)\n sys.exit(0 if value_from_stdin==value else 9)\n" +
                ("if len(value.get('guest_host_clients',[]))==1: sys.exit(7)\n" if fail else "") +
                "print('changed')\n")
            helper.chmod(0o700)
            firewall = directory / "firewall-cmd"
            firewall.write_text("#!/usr/bin/env python3\nimport json,pathlib,sys\n" +
                "p=pathlib.Path(%r); log=pathlib.Path(%r)\n" % (str(native), str(events)) +
                "data=json.loads(p.read_text()); key='permanent' if '--permanent' in sys.argv else 'runtime'\n" +
                "argument=next(x for x in sys.argv if x.startswith(('--query-rich-rule=','--remove-rich-rule=')))\n" +
                "action,rule=argument.split('=',1)\n" +
                "with log.open('a') as f: f.write(json.dumps([action,key,rule])+chr(10))\n" +
                "if action=='--query-rich-rule': sys.exit(0 if rule in data[key] else 1)\n" +
                "data[key].remove(rule);p.write_text(json.dumps(data))\n")
            firewall.chmod(0o700)
            tasks = yaml.safe_load((ROOT / "tasks/decommission-guest-access.yml").read_text())

            def adapt(rows):
                for task in rows:
                    command = task.get("ansible.builtin.command", {})
                    if command.get("argv", [None])[0] == "/usr/local/sbin/hactar-recovery-isolation":
                        command["argv"][0] = str(helper)
                    if command.get("argv", [None])[0] == "firewall-cmd":
                        command["argv"][0] = str(firewall)
                    if "ansible.builtin.copy" in task:
                        task["ansible.builtin.copy"].update(dest=str(policy), owner=str(os.getuid()), group=str(os.getgid()))
                    for field in ("block", "rescue", "always"):
                        adapt(task.get(field, []))
            adapt(tasks)
            play = directory / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "become": False,
                "gather_facts": False, "vars": {"aap_decommission_guest_access_phase": "apply",
                    "aap_decommission_selected_guests_stopped": True,
                    "aap_decommission_isolation_retirement": {key: plan[key] for key in ("previous_policy", "desired_policy", "identities")},
                    "aap_decommission_guest_access_plan": plan}, "tasks": tasks}], sort_keys=False))
            config = directory / "ansible.cfg"
            config.write_text("[defaults]\nretry_files_enabled=false\n")
            environment = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                               ANSIBLE_LOCAL_TEMP=str(directory / "local"), ANSIBLE_REMOTE_TEMP=str(directory / "remote"))
            command = [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)]
            if check:
                command.append("--check")
            result = subprocess.run(command,
                                    env=environment, text=True, capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 2 if fail or check else 0, result.stdout + result.stderr)
            if check:
                self.assertFalse(events.exists())
                self.assertEqual(json.loads(policy.read_text()), plan["previous_policy"])
                self.assertTrue(all(len(rules) == 3 for rules in json.loads(native.read_text()).values()))
                return
            self.assertEqual(json.loads(policy.read_text()), plan["previous_policy"] if fail else plan["desired_policy"])
            self.assertEqual(json.loads(native.read_text()), {"runtime": ["unrelated"], "permanent": ["unrelated"]})
            recorded = [json.loads(line) for line in events.read_text().splitlines()]
            self.assertEqual(recorded[0][0], "check")
            self.assertEqual(recorded[-1][0], "check")
            if fail:
                self.assertEqual(recorded[-1][1], plan["previous_policy"])
                self.assertIn("selected guests remain stopped", result.stdout)
            else:
                self.assertEqual(recorded[-1][1], plan["desired_policy"])

    def test_real_ansible_tasks_remove_only_exact_native_rules_then_apply_and_check(self):
        self.run_apply()

    def test_failed_apply_restores_previous_file_and_policy_without_reenabling_native_grants(self):
        self.run_apply(fail=True)

    def test_check_mode_refuses_mutating_phase_without_native_or_policy_writes(self):
        self.run_apply(check=True)


if __name__ == "__main__":
    unittest.main()
