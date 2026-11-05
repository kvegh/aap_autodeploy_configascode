"""Prove exact native guest ownership, idempotence and rollback without a live VM."""

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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

    def test_rollback_refuses_concurrent_policy_and_preserves_old_bytes_on_apply_error(self):
        request, state = fixture()
        request['operation'] = 'rollback'
        with self.assertRaises(ValueError):
            runtime.plan(request, state)
        state['policy'] = deepcopy(request['transition']['desired_policy'])
        self.assertEqual(runtime.plan(request, state)['desired_policy'], request['transition']['previous_policy'])
        self.exercise_reconcile(fail_apply=True)

    def test_runtime_check_and_apply_are_idempotent_and_touch_only_existing_isolation(self):
        self.exercise_reconcile(check_mode=True)
        self.exercise_reconcile()

    def exercise_reconcile(self, check_mode=False, fail_apply=False):
        request, state = fixture()
        request['check_mode'] = check_mode
        with tempfile.TemporaryDirectory(prefix='guest-release-runtime-') as directory:
            root = Path(directory)
            config = root / 'replacement-isolation.json'
            original = json.dumps(state['policy']).encode()
            config.write_bytes(original)
            config.chmod(0o600)
            helper = root / 'isolation-helper'
            helper.write_text("TABLE='hactar_recovery'\ndef validate_configuration(value):return value\ndef policy(value):return []\n")
            calls, applied = [], []
            def command(arguments, data=None):
                calls.append((arguments, data))
                if arguments[-1] == 'apply':
                    applied.append(json.loads(config.read_text()))
                    if fail_apply and len(applied) == 1:
                        raise ValueError('synthetic failed nft application')
                return subprocess.CompletedProcess(arguments, 0, '', '')
            with patch.object(runtime.base, 'DIRECTORY', root), patch.object(runtime.base, 'CONFIG', config), \
                    patch.object(runtime.base, 'HELPER', helper), patch.object(runtime.base, 'probe', return_value=state), \
                    patch.object(runtime.base, 'command', side_effect=command):
                if fail_apply:
                    with self.assertRaises(ValueError):
                        runtime.reconcile(request)
                    self.assertEqual(config.read_bytes(), original)
                    self.assertEqual(applied[-1], state['policy'])
                else:
                    result = runtime.reconcile(request)
                    self.assertEqual(result['applied'], not check_mode)
                    self.assertEqual(config.read_bytes() == original, check_mode)
                    if check_mode:
                        self.assertEqual(applied, [])
                    else:
                        self.assertEqual(json.loads(config.read_text()), request['transition']['desired_policy'])
                        state['policy'] = deepcopy(request['transition']['desired_policy'])
                        self.assertFalse(runtime.reconcile(request)['changed'])
            self.assertTrue(any(args[:2] == ['/usr/sbin/nft', '--check'] for args, _ in calls))
            self.assertFalse(any('firewall-cmd' in args or 'destroy' in args for args, _ in calls))

    def test_native_dynamic_role_loads_existing_action_without_a_wrapper(self):
        with tempfile.TemporaryDirectory(prefix='guest-release-role-load-') as directory:
            root = Path(directory)
            play = root / 'fixture.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'recovery_release_guest': {}, 'recovery_release_hypervisor': {},
                         'recovery_release_trust_file': '/tmp/synthetic-trust'},
                'tasks': [{'ansible.builtin.include_role': {
                    'name': str(ROOT / 'roles/recovery_guest_release')}}]}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                       ANSIBLE_HOME=str(root / 'home'), ANSIBLE_NOCOLOR='1')
            for key in ('CAC_GIT_TOKEN', 'AAP_CAC_SOURCE_TOKEN', 'AAP_CAC_SOURCE_URL'):
                env.pop(key, None)
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play), '--check'],
                env=env, cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Preflight the source job', result.stdout)
            self.assertNotIn('couldn\'t resolve module', result.stdout + result.stderr)
            self.assertNotIn('No module named', result.stdout + result.stderr)
            self.assertNotIn('Allocate protected temporary', result.stdout)

    def test_native_role_rolls_back_unpublished_change_and_keeps_durable_release(self):
        for durable in (False, True):
            with self.subTest(durable=durable):
                self.native_role_failure(durable)

    def test_native_role_skips_rollback_after_failed_empty_runtime_result(self):
        self.native_role_failure(False, runtime_failure=True)

    def test_native_http_role_uses_exact_bootstrap_mode_and_durable_rollback_rules(self):
        for durable in (False, True):
            with self.subTest(durable=durable):
                self.native_role_failure(durable, operation='guest_bootstrap_http')

    def native_role_failure(self, durable, runtime_failure=False, operation='release_guest'):
        request, _ = fixture()
        if operation == 'guest_bootstrap_http':
            request['transition']['desired_policy'] = deepcopy(request['transition']['previous_policy'])
            request['transition']['desired_policy']['http_clients'] = deepcopy(request['transition']['previous_policy']['https_clients'])
        with tempfile.TemporaryDirectory(prefix='guest-release-role-rollback-') as directory:
            root = Path(directory)
            source = root / 'source'
            role = source / 'roles/recovery_guest_release'
            (role / 'tasks').mkdir(parents=True)
            (role / 'action_plugins').mkdir()
            (source / 'src').mkdir()
            for name in ('aap_hypervisor_access.py', 'aap_guest_release.py'):
                (source / 'src' / name).write_text((ROOT / 'src' / name).read_text())
            trace = root / 'operations.jsonl'
            stub = root / 'runtime.py'
            stub.write_text("import json,pathlib,sys\nrequest=json.load(sys.stdin)\n"
                "request['_runtime_directory']=str(pathlib.Path(sys.argv[1]).parent)\n"
                "with pathlib.Path(" + repr(str(trace)) + ").open('a') as f:f.write(json.dumps(request)+'\\n')\n"
                + ("raise SystemExit(1)\n" if runtime_failure else "print(json.dumps({'changed':True,'applied':True}))\n"))
            (role / 'action_plugins/aap_publish_instance_keys.py').write_text(
                "from ansible.plugins.action import ActionBase\n"
                "class ActionModule(ActionBase):\n"
                " def run(self,tmp=None,task_vars=None):\n"
                "  assert self._task.args['operation']==task_vars['fixture_operation']\n"
                "  if self._task.args['phase']=='plan':return {'changed':False,'transition':task_vars['fixture_transition']}\n"
                "  return {'failed':True,'msg':'Synthetic publication failure','durable_policy_published':task_vars['fixture_durable']}\n")
            tasks = yaml.safe_load((ROOT / 'roles/recovery_guest_release/tasks/main.yml').read_text())
            def localize(values):
                for task in values:
                    task['no_log'] = False  # Synthetic fixture data only; production task defaults remain protected.
                    if 'delegate_to' in task:
                        task.update(delegate_to='localhost', become=False)
                        task['vars'] = {'ansible_connection': 'local'}
                    if 'ansible.builtin.command' in task:
                        actual_path = task['ansible.builtin.command']['argv'][1]
                        task['ansible.builtin.command']['argv'] = [sys.executable, str(stub), actual_path]
                    if 'ansible.builtin.copy' in task:
                        task['ansible.builtin.copy'].pop('owner', None)
                        task['ansible.builtin.copy'].pop('group', None)
                    for key in ('block', 'rescue', 'always'):
                        if key in task:
                            localize(task[key])
            localize(tasks)
            planned_tasks = yaml.safe_load((ROOT / 'roles/recovery_guest_release/tasks/plan.yml').read_text())
            localize(planned_tasks)
            (role / 'tasks/plan.yml').write_text(yaml.safe_dump(planned_tasks, sort_keys=False))
            (role / 'tasks/main.yml').write_text(yaml.safe_dump(tasks, sort_keys=False))
            play = root / 'fixture.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'recovery_release_guest': request['guest'], 'recovery_release_hypervisor': request['hypervisor'],
                         'recovery_release_operation': operation, 'fixture_operation': operation,
                         'recovery_release_trust_file': '/tmp/synthetic-trust', 'fixture_durable': durable,
                         'fixture_transition': request['transition']},
                'tasks': [{'ansible.builtin.include_role': {'name': str(role)}}]}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                       ANSIBLE_HOME=str(root / 'home'), ANSIBLE_NOCOLOR='1')
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                env=env, cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Stop after an incomplete guest release publication', result.stdout)
            self.assertNotIn('Expecting value', result.stdout + result.stderr)
            self.assertTrue(trace.exists(), result.stdout + result.stderr)
            operations = [json.loads(line) for line in trace.read_text().splitlines()]
            self.assertEqual([row['operation'] for row in operations],
                             ['apply'] if durable or runtime_failure else ['apply', 'rollback'])
            self.assertEqual(operations[0]['transition'], request['transition'])
            self.assertTrue(all(row['mode'] == ('bootstrap_http' if operation == 'guest_bootstrap_http' else 'release') for row in operations))
            # Native tempfile/copy/file tasks must remove their actual staging directory on failure.
            self.assertFalse(Path(operations[0]['_runtime_directory']).exists())


if __name__ == '__main__':
    unittest.main()
