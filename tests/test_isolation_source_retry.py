"""Exercise the pinned source read's native retry and pre-mutation SHA guard."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
REVISION = 'a' * 40
TOKEN = 'synthetic-isolation-reader-token-canary'
STDOUT = 'synthetic-isolation-git-stdout-canary'
STDERR = 'synthetic-isolation-git-stderr-canary'


class IsolationSourceRetryTests(unittest.TestCase):
    def test_interrupted_read_retries_once_then_accepts_only_the_exact_revision(self):
        self.run_case('fail-once', expected_attempts=2, succeeds=True)

    def test_persistent_read_failure_stops_after_three_attempts_before_mutation(self):
        self.run_case('persistent-failure', expected_attempts=3, succeeds=False)

    def test_successful_read_of_wrong_revision_stops_before_mutation(self):
        self.run_case('wrong-revision', expected_attempts=1, succeeds=False)

    def test_ordinary_success_reads_once(self):
        self.run_case('success', expected_attempts=1, succeeds=True)

    def run_case(self, behavior, expected_attempts, succeeds):
        actual = yaml.safe_load((ROOT / 'tasks/aap-isolation-prepare.yml').read_text())
        start = next(index for index, task in enumerate(actual) if 'ansible.builtin.git' in task)
        guard = next(index for index, task in enumerate(actual)
                     if task.get('name') == 'Require the exact requested source revision')
        tasks = deepcopy(actual[start:guard + 1])
        # Replace only the external Git result boundary. Native task keywords,
        # the intervening source binding and the real exact-SHA assertion run.
        tasks[0]['synthetic_git_read'] = tasks[0].pop('ansible.builtin.git')
        with tempfile.TemporaryDirectory(prefix='isolation-source-retry-') as directory:
            root = Path(directory)
            trace = root / 'read-attempts.jsonl'
            marker = root / 'mutation-marker'
            plugins = root / 'action_plugins'
            plugins.mkdir()
            (plugins / 'synthetic_git_read.py').write_text('''import json
from pathlib import Path
from ansible.plugins.action import ActionBase
class ActionModule(ActionBase):
 _requires_connection=False
 def run(self,tmp=None,task_vars=None):
  result=super().run(tmp,task_vars)
  trace=Path(TRACE)
  attempt=len(trace.read_text().splitlines())+1 if trace.exists() else 1
  with trace.open('a') as stream:
   stream.write(json.dumps({'attempt':attempt,'args':dict(self._task.args)})+'\\n')
  behavior=task_vars['synthetic_behavior']
  if behavior=='persistent-failure' or (behavior=='fail-once' and attempt==1):
   result.update(failed=True,msg='Synthetic source transfer interrupted.',stdout=task_vars['synthetic_stdout'],stderr=task_vars['synthetic_stderr'],detail={'credential':task_vars['hactar_source_git_token']},invocation={'module_args':{'password':task_vars['hactar_source_git_token']}})
  else:
   result.update(changed=True,after='b'*40 if behavior=='wrong-revision' else self._task.args['version'])
  return result
'''.replace('TRACE', repr(str(trace))))
            tasks += [{'name': 'Represent the first policy or VM mutation only after the source guard',
                       'ansible.builtin.copy': {'dest': str(marker), 'content': 'guard passed\n', 'mode': '0600'}}]
            variables = root / 'variables.yml'
            variables.write_text(yaml.safe_dump({
                'aap_isolation_source_workspace': {'path': str(root / 'workspace')},
                'aap_hactar_source_revision': REVISION, 'hactar_source_git_token': TOKEN,
                'ansible_python_interpreter': sys.executable, 'synthetic_behavior': behavior,
                'synthetic_stdout': STDOUT, 'synthetic_stderr': STDERR,
            }, sort_keys=False))
            play = root / 'play.yml'
            play.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars_files': [str(variables)],
                'tasks': tasks,
            }], sort_keys=False))
            config = root / 'ansible.cfg'
            config.write_text('[defaults]\n')
            env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_HOME=str(root / 'home'),
                       ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                       ANSIBLE_ACTION_PLUGINS=str(plugins), ANSIBLE_NOCOLOR='1')
            process = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                                     cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
            console = process.stdout + process.stderr
            self.assertEqual(process.returncode == 0, succeeds, console)
            self.assertEqual(marker.exists(), succeeds, console)
            for canary in (TOKEN, STDOUT, STDERR):
                self.assertNotIn(canary, console)
            observed = [json.loads(line) for line in trace.read_text().splitlines()]
            self.assertEqual(len(observed), expected_attempts)
            self.assertEqual([entry['attempt'] for entry in observed], list(range(1, expected_attempts + 1)))
            # Every retry receives the same actual task inputs and exact pin;
            # neither a failed transfer nor the wrong SHA can broaden the read.
            for entry in observed:
                self.assertEqual(entry['args'], {
                    'repo': actual[start]['ansible.builtin.git']['repo'],
                    'dest': str(root / 'workspace/repository'), 'version': REVISION,
                    'recursive': False, 'update': False,
                })


if __name__ == '__main__':
    unittest.main()
