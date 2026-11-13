"""Prove exact native guest ownership, idempotence and rollback without a live VM."""

from copy import deepcopy
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import errno
import fcntl
from importlib.util import module_from_spec, spec_from_file_location
import io
import json
import os
from pathlib import Path
import subprocess
import runpy
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
spec = spec_from_file_location('guest_release_runtime', ROOT / 'src/aap_guest_release.py')
runtime = module_from_spec(spec)
spec.loader.exec_module(runtime)


def fixture():
    pin = {'address': '192.0.2.10', 'public_ip': '192.0.2.10', 'machine_id': '1' * 32,
           'isolation_bridges': ['virbr0'], 'isolation_dns_bridges': ['virbr0']}
    guest = {'vm_name': 'fixture-v07', 'uuid': '01234567-89ab-cdef-0123-456789abcdef',
             'disk': '/opt/vms/fixture-v07.disk.qcow2', 'network': 'isolated', 'bridge': 'virbr0',
             'address': '192.168.10.5', 'mac': '52:54:00:00:00:07', 'host_keys': ['ssh-ed25519 AAAA'],
             'machine_id': '2' * 32, 'hypervisor_machine_id': pin['machine_id'],
             'source_image_sha256': 'a' * 64, 'verified': True}
    description = dict(schema_version=1, deployment_type='generic-recovery', **{
        key: guest[key] for key in ('vm_name', 'uuid', 'hypervisor_machine_id', 'source_image_sha256', 'host_keys')})
    domain = ('<domain><name>{name}</name><uuid>{uuid}</uuid><description>{description}</description>'
              '<devices><disk device="disk"><source file="{disk}"/></disk>'
              '<interface type="network"><mac address="{mac}"/><source network="isolated"/></interface>'
              '</devices></domain>').format(name=guest['vm_name'], uuid=guest['uuid'],
                  description=escape(json.dumps(description)), disk=guest['disk'], mac=guest['mac'])
    before = {'bridges': ['virbr0'], 'dns_bridges': ['virbr0'], 'protected_ipv4': ['198.51.100.5'],
              'https_clients': [{'bridge': 'virbr0', 'ipv4': guest['address'], 'mac': guest['mac']}]}
    desired = deepcopy(before)
    desired['released_clients'] = deepcopy(before['https_clients'])
    request = {'operation': 'apply', 'guest': guest, 'hypervisor': pin,
               'transition': {'previous_policy': before, 'desired_policy': desired}, 'check_mode': False}
    state = {'machine_id': pin['machine_id'], 'policy': deepcopy(before), 'autostart': [],
             'domains': {guest['vm_name']: {'persistent': domain, 'current': domain}},
             'networks': {'isolated': '<network><name>isolated</name><bridge name="virbr0"/></network>'},
             'leases': guest['mac'] + ' ipv4 ' + guest['address'] + '/24'}
    return request, state


class RuntimeReleaseTests(unittest.TestCase):
    def test_native_domain_and_dhcp_proof_accepts_only_exact_one_guest(self):
        request, state = fixture()
        self.assertTrue(runtime.plan(request, state)['changed'])
        state['policy'] = deepcopy(request['transition']['desired_policy'])
        self.assertFalse(runtime.plan(request, state)['changed'])

    def test_config_only_provenance_is_valid_and_both_live_ownership_and_present_metadata_remain_checked(self):
        request, state = fixture()
        live = ET.fromstring(state['domains'][request['guest']['vm_name']]['current'])
        live.remove(live.find('description'))
        state['domains'][request['guest']['vm_name']]['current'] = ET.tostring(live, encoding='unicode')
        self.assertTrue(runtime.plan(request, state)['changed'])
        for variant in ('missing-persistent', 'foreign-live-metadata', 'foreign-live-uuid',
                        'missing-live-state', 'missing-persistent-state'):
            with self.subTest(variant=variant):
                changed = deepcopy(state)
                if variant == 'missing-persistent':
                    changed['domains'][request['guest']['vm_name']]['persistent'] = ET.tostring(live, encoding='unicode')
                elif variant == 'foreign-live-metadata':
                    description = ET.SubElement(live, 'description')
                    description.text = '{}'
                    changed['domains'][request['guest']['vm_name']]['current'] = ET.tostring(live, encoding='unicode')
                    live.remove(description)
                elif variant == 'foreign-live-uuid':
                    forged = deepcopy(live)
                    forged.find('uuid').text = 'foreign'
                    changed['domains'][request['guest']['vm_name']]['current'] = ET.tostring(forged, encoding='unicode')
                else:
                    key = 'current' if variant == 'missing-live-state' else 'persistent'
                    del changed['domains'][request['guest']['vm_name']][key]
                with self.assertRaises(ValueError):
                    runtime.plan(request, changed)

    def test_forged_machine_vm_network_and_saved_provenance_stop_release(self):
        for key, value in [('machine_id', '3' * 32), ('uuid', 'foreign'), ('disk', '/foreign'),
                           ('mac', '52:54:00:ff:ff:ff'), ('source_image_sha256', 'b' * 64),
                           ('host_keys', ['ssh-ed25519 BBBB']), ('verified', False)]:
            with self.subTest(key=key):
                request, state = fixture()
                if key == 'machine_id':
                    state[key] = value
                else:
                    request['guest'][key] = value
                with self.assertRaises(ValueError):
                    runtime.plan(request, state)

    def test_production_denial_other_clients_and_concurrent_policy_are_preserved(self):
        for variant in ('production', 'other-client', 'drift', 'autostart', 'duplicate-owner'):
            with self.subTest(variant=variant):
                request, state = fixture()
                if variant == 'production':
                    request['transition']['desired_policy']['protected_ipv4'] = []
                elif variant == 'other-client':
                    request['transition']['desired_policy']['released_clients'].append(
                        {'bridge': 'virbr0', 'ipv4': '192.168.10.6', 'mac': '52:54:00:00:00:08'})
                elif variant == 'drift':
                    state['policy']['extra'] = True
                elif variant == 'autostart':
                    state['autostart'] = ['foreign']
                else:
                    state['domains']['foreign'] = {'current': next(iter(state['domains'].values()))['current'].replace(
                        '<name>fixture-v07</name>', '<name>foreign</name>')}
                with self.assertRaises(ValueError):
                    runtime.plan(request, state)

    def test_rollback_refuses_concurrent_policy_and_keeps_all_native_provenance_checks(self):
        request, state = fixture()
        request['operation'] = 'rollback'
        with self.assertRaises(ValueError):
            runtime.plan(request, state)
        state['policy'] = deepcopy(request['transition']['desired_policy'])
        self.assertEqual(runtime.plan(request, state)['desired_policy'], request['transition']['previous_policy'])

    def test_resource_cli_never_mutates_firewall_or_writes_managed_policy(self):
        request, state = fixture()
        with patch.object(runtime.base, 'probe', return_value=state) as probe, \
             patch.object(runtime.base, 'command') as command:
            original = deepcopy(state)
            result = runtime.reconcile(request)
            self.assertFalse(result['applied'])
            self.assertEqual(probe.call_args.args[1], request['transition']['previous_policy'])
            self.assertEqual(state, original)
            command.assert_not_called()

    def test_actual_cli_sanitizes_resource_errors_without_retry_or_secret_output(self):
        request, _ = fixture()
        stream = io.StringIO()
        with patch.object(runtime.base, 'probe', side_effect=ValueError('secret-canary')) as probe, \
             patch('sys.stdin', io.StringIO(json.dumps(request))), redirect_stdout(stream), redirect_stderr(stream):
            with self.assertRaises(SystemExit) as stopped:
                runpy.run_path(str(ROOT / 'src/aap_guest_release.py'), run_name='__main__')
        self.assertEqual(stopped.exception.code, 1)
        self.assertEqual(probe.call_count, 1)
        self.assertNotIn('secret-canary', stream.getvalue())
        self.assertIn('Protected guest resource verification failed.', stream.getvalue())

    def test_native_policy_transaction_rolls_back_failed_publication_and_preserves_durable_state(self):
        for durable in (False, True):
            self.native_role_failure(durable)

    def test_native_policy_transaction_keeps_failed_empty_resource_result_protected(self):
        self.native_role_failure(False, resource_failure=True)

    def test_native_mkdir_contention_is_bounded_and_never_breaks_another_lock(self):
        self.native_role_failure(False, busy=True)

    def test_native_mkdir_waits_for_transient_contention_then_releases_its_own_lock(self):
        self.native_role_failure(False, contended=True)

    def test_native_mkdir_extended_budget_waits_for_a_longer_transaction(self):
        self.native_role_failure(False, contended=True, release_delay=15, lock_retries=25)

    def test_native_mkdir_rejects_invalid_retry_budgets_before_resource_changes(self):
        for value in (True, -1, 1801, '25'):
            with self.subTest(value=value):
                self.native_role_failure(False, lock_retries=value, invalid_retries=True)

    def test_application_permissions_remain_native_only_through_failed_base_publication(self):
        app = [{'bridge': 'virbr0', 'ipv4': '192.168.10.17', 'mac': '52:54:00:00:00:17',
                'destinations': ['192.168.10.1'], 'ports': [443]}]
        self.native_role_failure(False, app_clients=app)

    def native_role_failure(self, durable, resource_failure=False, busy=False, contended=False,
                            app_clients=None, release_delay=2.5, lock_retries=None, invalid_retries=False):
        request, _ = fixture()
        with tempfile.TemporaryDirectory(prefix='guest-release-native-') as directory:
            root = Path(directory)
            source = root / 'source'
            role = source / 'roles/recovery_guest_release'
            (role / 'tasks').mkdir(parents=True)
            (role / 'action_plugins').mkdir()
            (source / 'tasks').mkdir()
            (source / 'src').mkdir()
            native_tasks = root / 'hactar/playbooks/tasks'
            native_tasks.mkdir(parents=True)
            trace = root / 'resource-calls.jsonl'
            native = root / 'hactar-recovery.nft'
            native.write_text(json.dumps(request['transition']['previous_policy']))
            lock = root / 'policy.lock'
            for name in ('aap_hypervisor_access.py', 'aap_guest_release.py'):
                (source / 'src' / name).write_text((ROOT / 'src' / name).read_text())
            stub = root / 'resource.py'
            stub.write_text('import json,pathlib,sys\nrequest=json.load(sys.stdin)\n'
                'with pathlib.Path(' + repr(str(trace)) + ').open("a") as f:f.write(json.dumps({"operation":request["operation"],"runtime":sys.argv[1]})+"\\n")\n'
                + ('print("secret-resource-canary",file=sys.stderr)\nraise SystemExit(1)\n' if resource_failure else
                   'print(json.dumps({"changed":True,"applied":False}))\n'))
            (role / 'action_plugins/aap_publish_instance_keys.py').write_text(
                'from ansible.plugins.action import ActionBase\n'
                'class ActionModule(ActionBase):\n'
                ' def run(self,tmp=None,task_vars=None):\n'
                '  if self._task.args["phase"]=="plan":return {"changed":False,"transition":task_vars["fixture_transition"]}\n'
                '  assert self._task.args["transition"]==task_vars["fixture_transition"], "Base publication received application data"\n'
                '  return {"failed":True,"msg":"Synthetic publication failure","durable_policy_published":task_vars["fixture_durable"]}\n')
            (native_tasks / 'replacement-isolation-validate.yml').write_text(yaml.safe_dump([
                {'name':'Validate synthetic CaC input','ansible.builtin.assert':{'that':'hactar_isolation_policy is mapping'}}]))
            (native_tasks / 'replacement-isolation-readback.yml').write_text(yaml.safe_dump([
                {'name':'Read synthetic native nft file','ansible.builtin.slurp':{'src':str(native)},'register':'fixture_native'},
                {'name':'Compare complete synthetic nft state','ansible.builtin.set_fact':{'__hactar_isolation_matches':
                    '{{ (fixture_native.content | b64decode | from_json) == hactar_isolation_policy }}'}}]))
            (native_tasks / 'replacement-isolation-apply.yml').write_text(yaml.safe_dump([
                {'name':'Apply complete synthetic nft state','ansible.builtin.copy':{'dest':str(native),
                 'content':'{{ hactar_isolation_policy | to_json }}','mode':'0600'}}]))
            def localize(tasks):
                for task in tasks:
                    if 'delegate_to' in task:
                        task.update(delegate_to='localhost',become=False)
                    if 'vars' in task and 'ansible_connection' in task['vars']:
                        task['vars']={'ansible_connection':'local'}
                    if 'ansible.builtin.copy' in task:
                        task['ansible.builtin.copy'].pop('owner',None)
                        task['ansible.builtin.copy'].pop('group',None)
                    if 'ansible.builtin.command' in task:
                        args=task['ansible.builtin.command']['argv']
                        if args[0]=='python3':task['ansible.builtin.command']['argv']=[sys.executable,str(stub),args[1]]
                        else:task['ansible.builtin.command']['argv']=[str(lock) if value=='/run/hactar-recovery-policy.lock' else value for value in args]
                    for section in ('block','rescue','always'):
                        if section in task:localize(task[section])
            for name in ('main.yml','plan.yml'):
                tasks=yaml.safe_load((ROOT / 'roles/recovery_guest_release/tasks' / name).read_text())
                localize(tasks)
                (role / 'tasks' / name).write_text(yaml.safe_dump(tasks,sort_keys=False))
            actual_prepare=yaml.safe_load((ROOT / 'tasks/aap-isolation-prepare.yml').read_text())
            prepare=[{'name':'Initialize isolated native transaction fixture','ansible.builtin.set_fact':{
                'aap_isolation_lock_acquired':False,'aap_isolation_source_workspace':{},'aap_isolation_app_clients':app_clients or [],
                'hactar_firewall_source_root':str(root/'hactar')}}]
            prepare += [task for task in actual_prepare if task['name'].startswith(
                ('Require a bounded native policy lock', 'Acquire the approved', 'Retain this invocation'))]
            localize(prepare)
            (source / 'tasks/aap-isolation-prepare.yml').write_text(yaml.safe_dump(prepare,sort_keys=False))
            for name in ('aap-isolation-observe.yml','aap-isolation-finish.yml'):
                tasks=yaml.safe_load((ROOT/'tasks'/name).read_text());localize(tasks)
                (source/'tasks'/name).write_text(yaml.safe_dump(tasks,sort_keys=False))
            if busy or contended:
                lock.mkdir()
            thread=None
            if contended:
                def release_competitor():
                    time.sleep(release_delay)
                    lock.rmdir()
                thread=threading.Thread(target=release_competitor)
                thread.start()
            play=root/'play.yml'
            extra_vars = {} if lock_retries is None else {'aap_isolation_lock_retries': lock_retries}
            play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                'vars':{'recovery_release_guest':request['guest'],'recovery_release_hypervisor':request['hypervisor'],
                        'recovery_release_trust_file':'/tmp/synthetic-trust','fixture_durable':durable,
                        'fixture_transition':request['transition'], **extra_vars},
                'tasks':[{'ansible.builtin.include_role':{'name':str(role)}}]}],sort_keys=False))
            env=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(root/'local'),ANSIBLE_REMOTE_TEMP=str(root/'remote'),
                     ANSIBLE_HOME=str(root/'home'),ANSIBLE_NOCOLOR='1')
            started=time.monotonic()
            result=subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)],
                cwd=ROOT,env=env,text=True,capture_output=True,timeout=45)
            if thread:thread.join(timeout=max(5, release_delay + 2))
            self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertNotIn('secret-resource-canary',result.stdout+result.stderr)
            if invalid_retries:
                self.assertFalse(trace.exists(), result.stdout + result.stderr)
                self.assertFalse(lock.exists(), result.stdout + result.stderr)
                self.assertEqual(json.loads(native.read_text()), request['transition']['previous_policy'])
            elif busy:
                self.assertFalse(trace.exists(),result.stdout+result.stderr)
                self.assertTrue(lock.is_dir())
                self.assertGreaterEqual(time.monotonic()-started,5)
                self.assertLess(time.monotonic()-started,25)
                self.assertEqual(json.loads(native.read_text()),request['transition']['previous_policy'])
            else:
                self.assertTrue(trace.exists(),result.stdout+result.stderr)
                self.assertFalse(lock.exists(),result.stdout+result.stderr)
                operations=[json.loads(row) for row in trace.read_text().splitlines()]
                self.assertEqual([row['operation'] for row in operations],['apply'])
                self.assertFalse(Path(operations[0]['runtime']).parent.exists())
                expected='desired_policy' if durable and not resource_failure else 'previous_policy'
                expected_policy = deepcopy(request['transition'][expected])
                if app_clients and not resource_failure:
                    expected_policy['guest_host_clients'] = app_clients
                self.assertEqual(json.loads(native.read_text()),expected_policy,result.stdout+result.stderr)
                self.assertIn('Stop after incomplete guest verification or publication',result.stdout)


if __name__ == '__main__':
    unittest.main()
