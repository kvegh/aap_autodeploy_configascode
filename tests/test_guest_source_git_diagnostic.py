"""Exercise the actual source Git rescue without API, SSH or Git requests."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ansible.parsing.vault import VaultLib, VaultSecret
import yaml

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'synthetic-source-git-cac-key'
ERROR = 'synthetic-private-source-git-error'
ARGUMENT = 'synthetic-invocation-credential'


class GuestSourceGitDiagnosticTests(unittest.TestCase):
    def test_success_does_not_publish_diagnostic_or_change_completion(self):
        self.run_case('success')

    def test_failure_retains_encrypted_copy_and_requested_visible_error(self):
        self.run_case('failure')

    def test_missing_cac_key_never_uses_environment_key_or_prevents_outer_cleanup(self):
        self.run_case('missing-cac')

    def run_case(self, behavior):
        path = ROOT / 'tasks/aap-isolation-app-read.yml'
        if not path.exists():
            path = ROOT / 'tasks/aap-isolation-app-permissions.yml'
        tasks = yaml.safe_load(path.read_text())
        block = deepcopy(next(task for task in tasks if task.get('name') ==
            'Read the central bootstrap and retain protected failures before rollback'))
        git = block['block'][0]
        self.assertEqual(git['ansible.builtin.git']['version'], 'main')
        self.assertFalse(git['no_log'])
        self.assertEqual(git['environment']['GIT_CONFIG_VALUE_2'], 'true')
        git.pop('ansible.builtin.git')
        git.pop('environment')
        git['ansible.builtin.command'] = {
            'argv': [sys.executable, '-c',
                'import json,sys; x=json.load(sys.stdin); sys.stderr.write(x["error"]); sys.exit(' +
                ('0' if behavior == 'success' else '1') + ')'],
            'stdin': '{{ synthetic_private_git_inputs | to_json }}'}
        with tempfile.TemporaryDirectory(prefix='source-git-diagnostic-') as directory:
            root = Path(directory)
            password = root / 'password'
            password.write_text(PASSWORD)
            password.chmod(0o600)
            receipt = root / 'receipt.json'
            callback = root / 'callbacks'
            callback.mkdir()
            (callback / 'source_git_receipt.py').write_text('''import json
from pathlib import Path
from ansible.plugins.callback import CallbackBase
class CallbackModule(CallbackBase):
 CALLBACK_VERSION=2.0
 CALLBACK_TYPE='aggregate'
 CALLBACK_NAME='source_git_receipt'
 CALLBACK_NEEDS_ENABLED=True
 def v2_playbook_on_stats(self,stats):
  target=Path(RECEIPT); target.write_text(json.dumps(stats.custom,default=str)); target.chmod(0o600)
'''.replace('RECEIPT', repr(str(receipt))))
            rollback = root / 'outer-rescue'
            cleanup = root / 'outer-cleanup'
            play = root / 'play.yml'
            play.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'aap_isolation_source_workspace': {'path': '/tmp/aap-hactar-source-synthetic'},
                         'synthetic_private_git_inputs': {'error': ERROR, 'credential': ARGUMENT}},
                'tasks': [{'block': [block],
                    'rescue': [{'name': 'Observe that normal outer rollback is reached',
                        'ansible.builtin.copy': {'dest': str(rollback), 'content': 'reached', 'mode': '0600'}},
                        {'name': 'Retain the original deployment failure',
                         'ansible.builtin.fail': {'msg': 'The original source Git operation failed.'}}],
                    'always': [{'name': 'Observe that normal outer cleanup is reached',
                        'ansible.builtin.copy': {'dest': str(cleanup), 'content': 'reached', 'mode': '0600'}}]}]}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_HOME=str(root / 'home'),
                       ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                       ANSIBLE_ACTION_PLUGINS=str(ROOT / 'action_plugins'),
                       ANSIBLE_CALLBACK_PLUGINS=str(callback), ANSIBLE_CALLBACKS_ENABLED='source_git_receipt',
                       ANSIBLE_NOCOLOR='1')
            label = 'env' if behavior == 'missing-cac' else 'cac'
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                '--vault-id', label + '@' + str(password), str(play)],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=35)
            console = result.stdout + result.stderr
            self.assertEqual(result.returncode == 0, behavior == 'success', console)
            self.assertEqual(ERROR in console, behavior != 'success', console)
            for value in (PASSWORD, ARGUMENT):
                self.assertNotIn(value, console)
            self.assertTrue(cleanup.exists(), console)
            self.assertEqual(rollback.exists(), behavior != 'success', console)
            values = json.loads(receipt.read_text()).get('_run', {})
            key = 'aap_guest_source_git_failure_vault'
            if behavior != 'failure':
                self.assertNotIn(key, values)
                if behavior == 'missing-cac':
                    self.assertIn('normal rollback and cleanup continue', console)
                return
            sealed = values[key]
            self.assertTrue(sealed.startswith('$ANSIBLE_VAULT;1.2;AES256;cac\n'))
            vault = VaultLib([('cac', VaultSecret(PASSWORD.encode()))])
            decoded = json.loads(vault.decrypt(sealed))
            self.assertEqual(decoded['stage'], 'guest_source_git')
            self.assertEqual(decoded['original_failure']['stderr'], ERROR)
            self.assertNotIn(ARGUMENT, json.dumps(decoded))
            self.assertNotIn('invocation', json.dumps(decoded))
            self.assertNotIn('module_args', json.dumps(decoded))


if __name__ == '__main__':
    unittest.main()
