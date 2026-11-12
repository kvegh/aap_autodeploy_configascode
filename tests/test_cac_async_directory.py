"""Exercise native async launch, real CoP polling and exact-job cleanup offline.

The legacy-default case requires the actual Core 2.20 runner image, whose
process home and configured local connection user differ. No HOME, user,
image, credentials or service settings are changed by this fixture.
"""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.release import __version__ as CORE_VERSION


ROOT = Path(__file__).resolve().parents[1]


def setup_tasks(entrypoint='base'):
    filename = '04-aap-config.yml' if entrypoint == 'base' else 'deploy-cac-project.yml'
    play = yaml.safe_load((ROOT / filename).read_text())[0]
    scope_name = ('Retrieve and load the encrypted shared configuration' if entrypoint == 'base'
                  else "Authenticate, load and import only this project's reviewed definitions")
    scope = next(task for task in play['pre_tasks'] if task.get('name') == scope_name)
    base = scope['block']
    bind = next(task for task in base if 'aap_configuration_async_dir' in task.get('ansible.builtin.set_fact', {}))
    create = next(task for task in base if task.get('ansible.builtin.file', {}).get('path') ==
                  '{{ aap_configuration_async_dir }}')
    boundary = ('Create base organizations before their PAH credentials' if entrypoint == 'base'
                else "Authenticate through the selected target's verified API from this execution environment")
    first_role = next(i for i, task in enumerate(base) if task.get('name') == boundary)
    if base.index(bind) >= base.index(create) or base.index(create) >= first_role:
        raise AssertionError('Bind and protect the shared async directory before the first configuration role.')
    if entrypoint == 'importer':
        allocated = next(i for i, task in enumerate(play['pre_tasks']) if task.get('register') == 'cac_workspace')
        if allocated >= play['pre_tasks'].index(scope) or not scope.get('always'):
            raise AssertionError('Allocate the importer workspace before binding its owned async directory.')
    return deepcopy([bind, create])


class CacAsyncDirectoryTests(unittest.TestCase):
    def test_real_private_workspace_setup_survives_native_launch_poll_and_cleanup(self):
        self.run_case(True)

    def test_real_importer_setup_keeps_owned_path_after_capture_vars_are_loaded(self):
        self.run_case(True, 'importer')

    @unittest.skipUnless(CORE_VERSION.startswith('2.20.') and Path('/runner').is_dir(),
                         'legacy home divergence requires the actual Core 2.20 runner image')
    def test_legacy_default_misses_the_same_job_that_the_launch_actually_completed(self):
        self.run_case(False)

    def run_case(self, fixed, entrypoint='base'):
        with tempfile.TemporaryDirectory(prefix='cac-async-directory-') as directory:
            root = Path(directory)
            workspace = root / 'workspace'
            workspace.mkdir(mode=0o700)
            output = root / 'proof.json'
            setup = setup_tasks(entrypoint) if fixed else []
            if entrypoint == 'importer':
                captured = root / 'synthetic-capture.yml'
                captured.write_text('aap_configuration_async_dir: null\n')
                # The real importer loads its capture after workspace setup.
                # Its data must not override the play-owned set_fact binding.
                setup.append({'ansible.builtin.include_vars': {'file': str(captured)}})
            launch = {'name': 'Launch one harmless native local async module',
                      'ansible.builtin.command': {'argv': [sys.executable, '-c', 'print("native-async-completed")']},
                      'async': 30, 'poll': 0, 'register': 'fixture_launch', 'changed_when': False, 'no_log': True}
            poll = {'name': 'Poll through the actual installed CoP status role',
                    'ansible.builtin.include_role': {'name': 'infra.aap_configuration.collect_async_status'},
                    'vars': {'cas_secure_logging': True, 'cas_async_delay': 1, 'cas_async_retries': 10,
                        'cas_job_async_results_item': "{{ fixture_launch | combine({'ansible_loop_var': 'fixture_item', 'fixture_item': {'name': 'Synthetic'}}) }}",
                        'cas_register_subvar': 'synthetic', 'cas_error_list_var_name': 'synthetic_errors',
                        'cas_object_label': 'Poll the synthetic native async result'}}
            tasks = [*setup, {'name': 'Keep the CoP launch status and cleanup variable scope intact',
                'vars': {'ansible_async_dir': '{{ aap_configuration_async_dir }}'},
                'block': [launch, poll],
                'rescue': [{'ansible.builtin.set_fact': {'fixture_failed': True,
                            'fixture_outer_error': '{{ ansible_failed_result | default({}) }}'}, 'no_log': True}],
                'always': [
                    {'name': 'Clean up through the same normal CoP async directory',
                     'ansible.builtin.async_status': {'jid': '{{ fixture_launch.ansible_job_id }}', 'mode': 'cleanup'},
                     'register': 'fixture_cleanup', 'ignore_errors': True, 'no_log': True,
                     'when': 'fixture_launch.ansible_job_id is defined'},
                    # An old default can miss its job file while the real module
                    # has completed. Follow that original job at its acknowledged
                    # absolute path; never cancel or launch a replacement.
                    {'name': 'Verify the original module at its exact acknowledged result path when defaults disagree',
                     'ansible.builtin.async_status': {'jid': '{{ fixture_launch.ansible_job_id }}'},
                     'vars': {'ansible_async_dir': '{{ fixture_launch.results_file | dirname }}'},
                     'register': 'fixture_recovered', 'until': 'fixture_recovered.finished', 'retries': 10, 'delay': 1,
                     'no_log': True, 'when': 'fixture_cleanup is failed'},
                    {'name': 'Remove only the completed original fixture job result after verifying it',
                     'ansible.builtin.async_status': {'jid': '{{ fixture_launch.ansible_job_id }}', 'mode': 'cleanup'},
                     'vars': {'ansible_async_dir': '{{ fixture_launch.results_file | dirname }}'},
                     'when': 'fixture_cleanup is failed', 'no_log': True},
                ]},
                {'name': 'Inspect the private directory mode without exposing job results',
                 'ansible.builtin.stat': {'path': '{{ aap_configuration_async_dir }}'}, 'register': 'fixture_dir',
                 'when': fixed, 'no_log': True},
                {'name': 'Retain only private synthetic launch status and cleanup proof',
                 'ansible.builtin.copy': {'dest': str(output), 'mode': '0600', 'decrypt': False,
                    'content': "{{ {'failed': fixture_failed, 'launch': fixture_launch, 'status': __cas_job_async_result | default({}), 'cleanup': fixture_cleanup, 'recovered': fixture_recovered | default({}), 'outer_error': fixture_outer_error | default({}), 'directory': aap_configuration_async_dir, 'mode': fixture_dir.stat.mode | default('')} | to_json }}"}, 'no_log': True}]
            play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'cac_workspace': {'path': str(workspace)}, 'fixture_failed': False,
                         'aap_configuration_async_dir': None, 'aap_configuration_collect_logs': False,
                         'ansible_python_interpreter': sys.executable},
                'tasks': tasks}]
            file = root / 'play.yml'
            file.write_text(yaml.safe_dump(play, sort_keys=False))
            env = dict(os.environ, ANSIBLE_HOME=str(root / 'home'), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                       ANSIBLE_REMOTE_TEMP=str(root / 'remote'), ANSIBLE_NOCOLOR='1')
            run = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(file)],
                                 cwd=root, env=env, capture_output=True, text=True, timeout=45)
            console = run.stdout + run.stderr
            if "the role 'infra.aap_configuration.collect_async_status' was not found" in console:
                self.skipTest('requires the existing installed infra.aap_configuration collection')
            self.assertEqual(run.returncode, 0, console)
            data = json.loads(output.read_text())
            self.assertIn('ansible_job_id', data['launch'], 'The real native async module must actually start.')
            self.assertIn('ansible_job_id', data['status'], str(data['outer_error'].get('msg', 'No native CoP result')) + '\n' + console)
            self.assertEqual(data['launch']['ansible_job_id'], data['status']['ansible_job_id'])
            if fixed:
                self.assertFalse(data['failed'])
                self.assertTrue(data['status']['finished'])
                self.assertEqual(data['status']['stdout'].strip(), 'native-async-completed')
                self.assertEqual(data['directory'], str(workspace / 'async'))
                self.assertEqual(data['mode'], '0700')
                self.assertEqual(Path(data['launch']['results_file']).parent, workspace / 'async')
                self.assertEqual(Path(data['status']['results_file']).parent, workspace / 'async')
                self.assertEqual(Path(data['cleanup']['erased']).parent, workspace / 'async')
                self.assertFalse(Path(data['launch']['results_file']).exists())
            else:
                self.assertTrue(data['failed'], 'The actual runner must reproduce the old home-resolution failure.')
                self.assertEqual(data['status']['msg'], 'could not find job')
                self.assertNotEqual(Path(data['launch']['results_file']).parent, Path(data['status']['results_file']).parent)
                self.assertTrue(data['recovered']['finished'])
                self.assertEqual(data['recovered']['stdout'].strip(), 'native-async-completed')


if __name__ == '__main__':
    unittest.main()
