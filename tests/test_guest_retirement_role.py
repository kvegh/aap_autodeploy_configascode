"""Exercise two native retirement phases and cleanup without a VM or network."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

from test_guest_retirement_runtime import fixture, runtime

ROOT = Path(__file__).resolve().parents[1]


class GenericRetirementRoleTests(unittest.TestCase):
    def test_native_role_loads_existing_action_and_stops_before_hypervisor_without_credentials(self):
        path = ROOT / 'roles/recovery_guest_retire/action_plugins/aap_publish_instance_keys.py'
        self.assertTrue(path.is_symlink())
        self.assertEqual(path.resolve(), ROOT / 'action_plugins/aap_publish_instance_keys.py')
        request, _ = fixture()
        with tempfile.TemporaryDirectory(prefix='retire-role-loading-') as directory:
            root = Path(directory)
            play = root / 'fixture.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'recovery_retire_phase': 'plan', 'recovery_retire_guest_name': request['guest_name'],
                         'recovery_retire_hypervisor': request['hypervisor']},
                'tasks': [{'ansible.builtin.include_role': {'name': str(ROOT / 'roles/recovery_guest_retire')}}]}]))
            environment = dict(os.environ, ANSIBLE_HOME=str(root / 'home'), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                               ANSIBLE_REMOTE_TEMP=str(root / 'remote'))
            for name in ['CAC_GIT_TOKEN', 'AAP_CAC_SOURCE_URL', 'AAP_CAC_SOURCE_TOKEN']:
                environment.pop(name, None)
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play), '--check'],
                cwd=ROOT, env=environment, text=True, capture_output=True, timeout=45)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Preflight canonical and source ownership', result.stdout)
            self.assertNotIn("couldn't resolve module", result.stdout + result.stderr)
            self.assertNotIn('No module named', result.stdout + result.stderr)
            self.assertNotIn('Allocate private controller trust', result.stdout)

    def test_native_two_phases_gate_publication_and_remove_every_temporary_file(self):
        for native in (False, True):
            for behavior in ('success', 'unpublished', 'durable', 'runtime-failure', 'deletion-failure'):
                with self.subTest(native=native, behavior=behavior):
                    self.run_role(native, behavior)

    def run_role(self, native, behavior):
        request, _ = fixture()
        with tempfile.TemporaryDirectory(prefix='retire-native-phases-') as directory:
            root = Path(directory)
            source = root / 'source'
            role = source / 'roles/recovery_guest_retire'
            (role / 'tasks').mkdir(parents=True)
            (role / 'tasks/plan.yml').write_text((ROOT / 'roles/recovery_guest_retire/tasks/plan.yml').read_text())
            (role / 'action_plugins').mkdir()
            (source / 'src').mkdir()
            for name in ('aap_guest_release.py', 'aap_hypervisor_access.py'):
                (source / 'src' / name).write_text((ROOT / 'src' / name).read_text())
            trace, api_trace = root / 'native.jsonl', root / 'api.jsonl'
            marker = root / 'physical-deletion-verified'
            stub = root / 'native.py'
            stub.write_text("import json,pathlib,sys\nr=json.load(sys.stdin)\n"
                "r['_directory']=str(pathlib.Path(sys.argv[1]).parent)\n"
                "r['_trust']=sys.argv[2]\n"
                "with pathlib.Path(" + repr(str(trace)) + ").open('a') as f:f.write(json.dumps(r)+'\\n')\n"
                "if r['operation']=='retire_apply':\n"
                " assert pathlib.Path(" + repr(str(marker)) + ").exists()\n"
                + (" raise SystemExit(1)\n" if behavior == 'runtime-failure' else '')
                + "print(json.dumps({'changed':r['operation']!='retire_plan','retirement_verified':True,"
                  "'domain_present':r['operation']=='retire_plan','disks_absent':r['operation']!='retire_plan',"
                  "'already_absent':False,'dynamic_lease_cache':{'rows':0,'expired':0,'unexpired':0}}))\n")
            (role / 'action_plugins/aap_publish_instance_keys.py').write_text(
                "from ansible.plugins.action import ActionBase\nimport json,pathlib\n"
                "class ActionModule(ActionBase):\n"
                " def run(self,tmp=None,task_vars=None):\n"
                "  phase=self._task.args['phase']\n"
                "  with pathlib.Path(" + repr(str(api_trace)) + ").open('a') as f:f.write(json.dumps(phase)+'\\n')\n"
                "  if phase=='plan':return {'changed':False,'guest':task_vars['fixture_guest'],"
                "'transition':task_vars['fixture_transition'],'records_absent':False}\n"
                + ("  return {'changed':True,'published':True,'durable_policy_published':True}\n" if behavior == 'success' else
                   "  return {'failed':True,'msg':'Synthetic publication interruption','durable_policy_published':" + repr(behavior == 'durable') + "}\n"))
            tasks = deepcopy(yaml.safe_load((ROOT / 'roles/recovery_guest_retire/tasks/main.yml').read_text()))
            def localize(items):
                for task in items:
                    task['no_log'] = False  # Synthetic fixture only; published role stays protected.
                    if 'delegate_to' in task:
                        task.update(delegate_to='localhost', become=False)
                        task['vars'] = {'ansible_connection': 'local'}
                    if 'ansible.builtin.copy' in task:
                        task['ansible.builtin.copy'].pop('owner', None)
                        task['ansible.builtin.copy'].pop('group', None)
                    if 'ansible.builtin.command' in task:
                        actual = task['ansible.builtin.command']['argv'][1]
                        task['ansible.builtin.command']['argv'] = [sys.executable, str(stub), actual,
                            '{{ __recovery_retire_trust.path }}']
                    for key in ('block', 'rescue', 'always'):
                        if key in task: localize(task[key])
            localize(tasks)
            (role / 'tasks/main.yml').write_text(yaml.safe_dump(tasks, sort_keys=False))
            play = root / 'fixture.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': dict({'recovery_retire_guest_name': request['guest_name'], 'recovery_retire_hypervisor': request['hypervisor'],
                         'fixture_guest': request['guest'], 'fixture_transition': request['transition']},
                         **({'recovery_retire_guest_kind': 'windows'} if request.get('guest_kind') == 'windows' else {})),
                'tasks': [
                    {'name': 'Plan exact native retirement', 'ansible.builtin.include_role': {'name': str(role)},
                     'vars': {'recovery_retire_phase': 'plan'}},
                    {'name': 'Refuse a simulated physical deletion failure', 'ansible.builtin.assert': {
                        'that': [behavior != 'deletion-failure']}},
                    {'name': 'Simulate separately verified domain and disk deletion', 'ansible.builtin.file': {
                        'path': str(marker), 'state': 'touch', 'mode': '0600'}},
                    {'name': 'Publish only after physical deletion', 'ansible.builtin.include_role': {'name': str(role)},
                     'vars': {'recovery_retire_phase': 'publish'}},
                ]}], sort_keys=False))
            environment = dict(os.environ, ANSIBLE_HOME=str(root / 'home'), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                ANSIBLE_REMOTE_TEMP=str(root / 'remote'), ANSIBLE_JINJA2_NATIVE=str(native).lower(), ANSIBLE_NOCOLOR='1')
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                cwd=ROOT, env=environment, text=True, capture_output=True, timeout=60)
            self.assertEqual(result.returncode == 0, behavior == 'success', result.stdout + result.stderr)
            operations = [json.loads(line) for line in trace.read_text().splitlines()]
            expected = ['retire_plan'] if behavior == 'deletion-failure' else ['retire_plan', 'retire_apply']
            if behavior == 'unpublished': expected.append('retire_rollback')
            self.assertEqual([row['operation'] for row in operations], expected, result.stdout + result.stderr)
            self.assertTrue(all(row.get('guest_kind') == request.get('guest_kind') for row in operations))
            phases = [json.loads(line) for line in api_trace.read_text().splitlines()]
            self.assertEqual(phases, ['plan'] if behavior in ('deletion-failure', 'runtime-failure') else ['plan', 'publish'])
            self.assertTrue(all(not Path(row['_directory']).exists() for row in operations))
            self.assertTrue(all(not Path(row['_trust']).exists() for row in operations))
            self.assertNotIn('Expecting value', result.stdout + result.stderr)

    def test_native_source_plan_can_choose_existing_windows_cleanup_without_touching_hypervisor(self):
        request, _ = fixture()
        with tempfile.TemporaryDirectory(prefix='retire-source-plan-') as directory:
            root = Path(directory)
            role = root / 'roles/recovery_guest_retire'
            (role / 'tasks').mkdir(parents=True)
            (role / 'action_plugins').mkdir()
            (role / 'tasks/plan.yml').write_text((ROOT / 'roles/recovery_guest_retire/tasks/plan.yml').read_text())
            (role / 'action_plugins/aap_publish_instance_keys.py').write_text(
                'from ansible.plugins.action import ActionBase\n'
                'class ActionModule(ActionBase):\n'
                ' def run(self,tmp=None,task_vars=None):\n'
                "  assert self._task.args['guest_kind']=='windows' and self._task.args['phase']=='plan'\n"
                "  return {'changed':False,'guest':None,'records_absent':True,'transition':task_vars['fixture_transition']}\n")
            play = root / 'fixture.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'gather_facts': False,
                'vars': {'recovery_retire_phase': 'plan', 'recovery_retire_guest_name': request['guest_name'],
                         'recovery_retire_hypervisor': request['hypervisor'], 'recovery_retire_guest_kind': 'windows',
                         'fixture_transition': request['transition']},
                'tasks': [{'ansible.builtin.include_role': {'name': str(role), 'tasks_from': 'plan'}},
                          {'ansible.builtin.assert': {'that': ['recovery_guest_retire_plan.records_absent',
                                                            'recovery_guest_retire_plan.guest is none']}}]}]))
            for native in (False, True):
                env = dict(os.environ, ANSIBLE_HOME=str(root / 'home'), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                           ANSIBLE_JINJA2_NATIVE=str(native).lower())
                result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                    cwd=root, env=env, text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('Allocate private controller trust', result.stdout)


if __name__ == '__main__':
    unittest.main()
