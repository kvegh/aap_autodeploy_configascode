"""Exercise the actual organization rescue without API or SSH operations."""

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
PASSWORD = 'synthetic-cac-diagnostic-password'
CANARIES = ('synthetic-status-error-canary', 'synthetic-cleanup-error-canary',
            'synthetic-invocation-password-canary', 'synthetic-module-args-canary')


class EncryptedOrganizationDiagnosticTests(unittest.TestCase):
    def test_success_does_not_publish_diagnostics_or_change_role_inputs(self):
        self.run_case('success')

    def test_original_async_and_cleanup_errors_are_recoverable_only_from_ciphertext(self):
        self.run_case('failure')
        self.run_case('cleanup')

    def test_environment_key_cannot_replace_the_required_cac_key(self):
        self.run_case('missing-cac')

    def run_case(self, behavior):
        actual = yaml.safe_load((ROOT / '04-aap-config.yml').read_text())[0]
        base = next(task['block'] for task in actual['pre_tasks']
                    if task.get('name') == 'Retrieve and load the encrypted shared configuration')
        block = deepcopy(next(task for task in base if task.get('name') ==
                              'Create base organizations before their PAH credentials'))
        role = block['block'][0]
        self.assertEqual(role['ansible.builtin.include_role']['name'], 'infra.aap_configuration.gateway_organizations')
        self.assertEqual(role['vars'], {'aap_organizations': '{{ aap_organizations_base }}',
                                        'assign_galaxy_credentials_to_org': False})
        with tempfile.TemporaryDirectory(prefix='cac-encrypted-diagnostic-') as directory:
            root = Path(directory)
            secret = VaultSecret(PASSWORD.encode())
            vault = VaultLib([('cac', secret)])
            capture = root / 'workspace/repository/cac/base_CaC_vault.yml'
            capture.parent.mkdir(parents=True)
            capture.write_bytes(vault.encrypt(b'synthetic: true\n', secret=secret, vault_id='cac'))
            password_file = root / 'password'
            password_file.write_text(PASSWORD)
            password_file.chmod(0o600)
            receipt = root / 'native-stats.json'
            callbacks = root / 'callback_plugins'
            callbacks.mkdir()
            (callbacks / 'diagnostic_receipt.py').write_text('''import json,os
from pathlib import Path
from ansible.plugins.callback import CallbackBase
class CallbackModule(CallbackBase):
 CALLBACK_VERSION=2.0
 CALLBACK_TYPE='aggregate'
 CALLBACK_NAME='diagnostic_receipt'
 CALLBACK_NEEDS_ENABLED=True
 def v2_playbook_on_stats(self,stats):
  target=Path(RECEIPT)
  target.write_text(json.dumps(stats.custom,default=str));target.chmod(0o600)
'''.replace('RECEIPT', repr(str(receipt))))
            simulated = [{'name': 'Verify unchanged organization role inputs', 'ansible.builtin.assert': {
                'that': ["aap_organizations == [{'name': 'Synthetic'}]", 'not assign_galaxy_credentials_to_org']}, 'no_log': True}]
            if behavior != 'success':
                simulated += [{'name': 'Simulate the original protected async result', 'ansible.builtin.set_fact': {
                    '__cas_job_async_result': {'failed': True, 'finished': True,
                        'msg': CANARIES[0], 'ansible_job_id': 'j123.456',
                        'invocation': {'password': CANARIES[2]},
                        'detail': {'nested': {'reason': 'nested-error', 'module_args': {'password': CANARIES[3]}}},
                        'module_stdout': json.dumps({'msg': 'wrapped-error', 'invocation': {'password': CANARIES[2]}})},
                    '__organizations_job_async': {'results': [{'ansible_job_id': 'j123.456',
                        'results_file': '/synthetic/async/j123.456', 'started': True,
                        '__controller_organizations_item': {'password': CANARIES[2]}}]}}, 'no_log': True},
                    {'name': 'Keep normal role failure behavior', 'block': [
                        {'name': 'Fail at the original organization boundary', 'ansible.builtin.command': {
                            'argv': [sys.executable, '-c', 'import sys; sys.stderr.write(sys.stdin.read()); sys.exit(1)'],
                            'stdin': '{{ synthetic_failure_canaries[0] }}'}, 'no_log': True}],
                     'always': [{'name': 'Simulate a subsequent protected async cleanup failure',
                        'ansible.builtin.command': {
                            'argv': [sys.executable, '-c', 'import sys; sys.stderr.write(sys.stdin.read()); sys.exit(1)'],
                            'stdin': '{{ synthetic_failure_canaries[1] }}'}, 'no_log': True,
                        'when': behavior == 'cleanup'}]}]
            role.pop('ansible.builtin.include_role')
            stub = root / 'organization-role.yml'
            stub.write_text(yaml.safe_dump(simulated, sort_keys=False))
            role['ansible.builtin.include_tasks'] = str(stub)
            play = root / 'play.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': {'cac_workspace': {'path': str(root / 'workspace')},
                         'synthetic_failure_canaries': list(CANARIES),
                         'aap_organizations_base': [{'name': 'Synthetic'}]},
                'tasks': [block, {'name': 'Prove successful role completion continues normally',
                    'ansible.builtin.assert': {'that': ['true']}}]}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_HOME=str(root / 'home'), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                       ANSIBLE_REMOTE_TEMP=str(root / 'remote'), ANSIBLE_ACTION_PLUGINS=str(ROOT / 'action_plugins'),
                       ANSIBLE_CALLBACK_PLUGINS=str(callbacks), ANSIBLE_CALLBACKS_ENABLED='diagnostic_receipt',
                       ANSIBLE_NOCOLOR='1')
            label = 'env' if behavior == 'missing-cac' else 'cac'
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                '--vault-id', label + '@' + str(password_file), str(play)],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=35)
            console = result.stdout + result.stderr
            self.assertEqual(result.returncode == 0, behavior == 'success', console)
            for canary in (*CANARIES, PASSWORD):
                self.assertNotIn(canary, console)
            custom = json.loads(receipt.read_text())
            values = custom.get('_run', {})
            if behavior in ('success', 'missing-cac'):
                self.assertNotIn('aap_base_organization_failure_vault', values)
                if behavior == 'missing-cac':
                    self.assertNotIn('Stop base configuration after its protected organization failure', console)
                return
            sealed = values['aap_base_organization_failure_vault']
            self.assertTrue(sealed.startswith('$ANSIBLE_VAULT;1.2;AES256;cac\n'))
            decoded = json.loads(vault.decrypt(sealed))
            self.assertEqual(decoded['async_status']['msg'], CANARIES[0])
            self.assertEqual(decoded['original_failure']['stderr'].strip(), CANARIES[1] if behavior == 'cleanup' else CANARIES[0])
            self.assertEqual(decoded['controller_launches'], [{'ansible_job_id': 'j123.456',
                'results_file': '/synthetic/async/j123.456', 'started': True}])
            text = json.dumps(decoded)
            self.assertNotIn('invocation', text)
            self.assertNotIn('module_args', text)
            self.assertNotIn(CANARIES[2], text)
            self.assertNotIn(CANARIES[3], text)


if __name__ == '__main__':
    unittest.main()
