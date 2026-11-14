"""Run the selector's real tasks with synthetic controller job primitives only."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest

from ansible.parsing.vault import VaultLib, VaultSecret
import yaml


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'synthetic-selector-vault-password'
ERROR = 'synthetic-selector-observer-error-canary'
ARGUMENT_SECRET = 'synthetic-selector-invocation-secret-canary'
TOKEN = 'synthetic-selector-token-canary'
CHILD = 412
PREVIOUS_CHILD = 411


class SelectedImportObserverTests(unittest.TestCase):
    def test_launch_once_publishes_identity_before_wait_and_preserves_final_checks(self):
        self.run_case('success')

    def test_failed_wait_retains_identity_and_encrypts_original_error(self):
        self.run_case('wait-failure')

    def test_failed_launch_cannot_reuse_previous_step_identity(self):
        self.run_case('launch-failure')

    def test_wait_cannot_substitute_another_successful_child(self):
        self.run_case('wrong-child')

    def test_successful_child_cannot_bypass_credential_readback(self):
        self.run_case('wrong-credentials')

    def test_native_module_success_accepts_returned_messages(self):
        self.run_case('module-success')

    def test_real_module_failure_messages_remain_encrypted(self):
        for operation in ('launch', 'wait'):
            with self.subTest(operation=operation):
                self.run_case(operation + '-module-failure')

    def test_raw_failure_flag_cannot_be_lost_even_with_a_success_shaped_result(self):
        for operation in ('launch', 'wait'):
            with self.subTest(operation=operation):
                self.run_case(operation + '-flag-only-failure')

    def test_malformed_results_cannot_continue(self):
        for behavior in ('launch-missing-id', 'wait-missing-id', 'wait-wrong-type', 'wait-unsuccessful',
                         'wait-retained-exception', 'wait-nonzero-rc'):
            with self.subTest(behavior=behavior):
                self.run_case(behavior)

    def test_raised_transport_errors_fail_closed(self):
        for operation in ('launch', 'wait'):
            with self.subTest(operation=operation):
                self.run_case(operation + '-transport-failure')

    def run_case(self, behavior):
        requests = []

        class CredentialReadback(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.path, self.headers.get('Authorization')))
                identities = [1, 2, 3] if behavior != 'wrong-credentials' else [1, 2, 99]
                body = json.dumps({'next': None, 'results': [{'id': value} for value in identities]}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        # The real uri module reads a synthetic local HTTP endpoint; no AAP or
        # infrastructure connection is made, and no other Ansible task is mocked.
        with ThreadingHTTPServer(('127.0.0.1', 0), CredentialReadback) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.execute_fixture(behavior, server.server_port, requests)
            finally:
                server.shutdown()
                thread.join()

    def execute_fixture(self, behavior, port, requests):
        with tempfile.TemporaryDirectory(prefix='selector-observer-') as directory:
            root = Path(directory)
            secret = VaultSecret(PASSWORD.encode())
            vault = VaultLib([('cac', secret)])
            capture = root / 'workspace/repository/cac/base_CaC_vault.yml'
            capture.parent.mkdir(parents=True)
            capture.write_bytes(vault.encrypt(b'synthetic: true\n', secret=secret, vault_id='cac'))
            password_file = root / 'password'
            password_file.write_text(PASSWORD)
            password_file.chmod(0o600)
            events = root / 'events.jsonl'
            receipt = root / 'stats.json'
            collection = root / 'collections/ansible_collections/ansible/controller/plugins'
            actions = collection / 'action'
            modules = collection / 'modules'
            actions.mkdir(parents=True)
            modules.mkdir()
            library = root / 'library'
            library.mkdir()
            (library / 'synthetic_job_primitive.py').write_text('''#!/usr/bin/python
import json
from ansible.module_utils.basic import AnsibleModule
module=AnsibleModule(argument_spec={'operation':{'type':'str'},'behavior':{'type':'str'},'error':{'type':'str'},'argument_secret':{'type':'str'}})
p=module.params
if p['behavior'].endswith('module-failure'):
 module.fail_json(msg=p['error'],detail={'nested':{'reason':'original-observer-detail','module_args':{'password':p['argument_secret']}}},module_stdout=json.dumps({'msg':'wrapped-error','invocation':{'password':p['argument_secret']}}))
module.exit_json(changed=p['operation']=='launch',id=CHILD,status='pending' if p['operation']=='launch' else 'successful',msg='Synthetic successfully observed job.')
'''.replace('CHILD', str(CHILD)))
            # Only these two external primitives are replaced. All surrounding
            # includes, assertions, rescue, Vault action and stats run in Ansible.
            stub = '''import json
from pathlib import Path
from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
class ActionModule(ActionBase):
 _requires_connection=False
 def run(self,tmp=None,task_vars=None):
  result=super().run(tmp,task_vars)
  operation=OPERATION
  with Path(task_vars['synthetic_events']).open('a') as stream:
   stream.write(json.dumps({'event':operation,'args':dict(self._task.args),'environment':self._task.environment})+'\\n')
  behavior=task_vars['synthetic_behavior']
  if behavior == 'module-success' or behavior == operation+'-module-failure':
   return self._execute_module(module_name='synthetic_job_primitive',module_args={'operation':operation,'behavior':behavior,'error':task_vars['synthetic_error'],'argument_secret':task_vars['synthetic_argument_secret']},task_vars=task_vars)
  if behavior == operation+'-transport-failure':
   raise AnsibleActionFail('Synthetic external transport failed.',result={'stderr':task_vars['synthetic_error']})
  if behavior == operation+'-failure':
   result.update(failed=True,msg=task_vars['synthetic_error'],detail={'nested':{'reason':'original-observer-detail','module_args':{'password':task_vars['synthetic_argument_secret']}}},invocation={'module_args':{'password':task_vars['synthetic_argument_secret']}},module_stdout=json.dumps({'msg':'wrapped-error','invocation':{'password':task_vars['synthetic_argument_secret']}}))
  else:
   result.update(changed=operation=='launch',id=CHILD+1 if behavior=='wrong-child' and operation=='wait' else CHILD,status='pending' if operation=='launch' else 'successful')
   if behavior == operation+'-flag-only-failure':
    result['failed']=True
   if behavior == operation+'-missing-id':
    result.pop('id')
   if behavior == 'wait-wrong-type' and operation=='wait':
    result['id']=str(CHILD)
   if behavior == 'wait-unsuccessful' and operation=='wait':
    result['status']='failed'
   if behavior == 'wait-retained-exception' and operation=='wait':
    result.update(failed=False,exception=task_vars['synthetic_error'])
   if behavior == 'wait-nonzero-rc' and operation=='wait':
    result.update(failed=False,rc=17)
  return result
'''.replace('CHILD', str(CHILD))
            for operation in ('launch', 'wait'):
                (actions / ('job_' + operation + '.py')).write_text(stub.replace('OPERATION', repr(operation)))
                (modules / ('job_' + operation + '.py')).write_text('# Synthetic action-boundary fixture only.\n')
            callbacks = root / 'callback_plugins'
            callbacks.mkdir()
            (callbacks / 'selector_receipt.py').write_text('''import json
from pathlib import Path
from ansible.plugins.callback import CallbackBase
class CallbackModule(CallbackBase):
 CALLBACK_VERSION=2.0
 CALLBACK_TYPE='aggregate'
 CALLBACK_NAME='selector_receipt'
 CALLBACK_NEEDS_ENABLED=True
 def v2_runner_on_ok(self,result):
  if result._task.action=='ansible.builtin.set_stats':
   with Path(EVENTS).open('a') as stream:
    stream.write(json.dumps({'event':'stats','data':result._task.args['data']},default=str)+'\\n')
 def v2_playbook_on_stats(self,stats):
  Path(RECEIPT).write_text(json.dumps(stats.custom,default=str))
'''.replace('EVENTS', repr(str(events))).replace('RECEIPT', repr(str(receipt))))
            organization = 'Synthetic organization'
            credentials = [
                {'id': 1, 'name': 'Synthetic Git', 'kind': 'cloud'},
                {'id': 2, 'name': 'Synthetic Vault', 'kind': 'vault', 'inputs': {'vault_id': 'cac'}},
                {'id': 3, 'name': 'AAP API/MCP Auth Token Store', 'kind': 'cloud', 'credential_type': 46,
                 'summary_fields': {'credential_type': {'name': 'Pseudo Instance Key Store'}}},
            ]
            for credential in credentials:
                credential.setdefault('summary_fields', {})['organization'] = {'name': organization}
            origin = 'http://127.0.0.1:' + str(port)
            variables = {
                'cac_workspace': {'path': str(root / 'workspace')},
                'synthetic_events': str(events), 'synthetic_behavior': behavior,
                'synthetic_error': ERROR, 'synthetic_argument_secret': ARGUMENT_SECRET,
                'aap_selected_importer': {'json': {'results': [{'id': 88}]}, 'item': {
                    'name': 'Synthetic importer', 'playbook': 'deploy-cac-project.yml',
                    'project_id': 'assistant-team', 'repository': 'https://git.example.invalid/config.git'}},
                'aap_selected_importer_key': 'synthetic-selection',
                'aap_selected_saved_credentials': credentials,
                'cac_use_case_selector': {'importer_credentials': {'Synthetic importer': [c['name'] for c in credentials]}},
                'aap_selected_api_credentials': [credentials[-1]],
                'aap_selected_target_auth': {'hostname': 'https://target.example.invalid'},
                'aap_selected_source_auth': {'hostname': origin, 'token': TOKEN},
                'aap_selected_setup_plan': {'organization': organization},
                'aap_selected_route_credentials': {'results': []},
                'aap_instance_route': {'hypervisor': {'machine_credential_name': 'Synthetic Machine'}},
                'aap_instance_key': 'synthetic-target', 'aap_selected_importer_extra': {},
                'aap_validate_certs': True, 'aap_seed_ca_path': '',
                # Simulate the previous successful loop iteration explicitly.
                'aap_selected_import_job': {'id': PREVIOUS_CHILD, 'status': 'successful'},
                'aap_selected_import_wait': {'id': PREVIOUS_CHILD, 'status': 'successful'},
                'aap_selected_setup_results': [],
            }
            tasks = [{'ansible.builtin.include_tasks': str(ROOT / 'tasks/selected-use-case-import.yml')},
                     {'name': 'Verify final successful selector result', 'ansible.builtin.assert': {'that': [
                         'aap_selected_setup_results == ' + repr([{'selection': 'synthetic-selection', 'job_id': CHILD, 'status': 'successful'}])
                     ]}, 'no_log': True}]
            play = root / 'play.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                                            'vars': variables, 'tasks': tasks}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_HOME=str(root / 'home'), ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                       ANSIBLE_REMOTE_TEMP=str(root / 'remote'), ANSIBLE_ACTION_PLUGINS=str(ROOT / 'action_plugins'),
                       ANSIBLE_FILTER_PLUGINS=str(ROOT / 'filter_plugins'), ANSIBLE_COLLECTIONS_PATH=str(root / 'collections'),
                       ANSIBLE_LIBRARY=str(library),
                       ANSIBLE_CALLBACK_PLUGINS=str(callbacks), ANSIBLE_CALLBACKS_ENABLED='selector_receipt',
                       ANSIBLE_NOCOLOR='1')
            process = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                                      '--vault-id', 'cac@' + str(password_file), str(play)],
                                     cwd=ROOT, env=env, text=True, capture_output=True, timeout=35)
            console = process.stdout + process.stderr
            successful = behavior in ('success', 'module-success')
            self.assertEqual(process.returncode == 0, successful, console)
            for canary in (PASSWORD, ERROR, ARGUMENT_SECRET, TOKEN):
                self.assertNotIn(canary, console)
            observed = [json.loads(line) for line in events.read_text().splitlines()]
            launches = [event for event in observed if event['event'] == 'launch']
            self.assertEqual(len(launches), 1)
            launch = launches[0]['args']
            self.assertEqual(launch, {'job_template': '88', 'extra_vars': {'aap_instance_key': 'synthetic-target', 'debug_logging': 'false'},
                                     'credentials': ['1', '2', '3'], 'wait': False, 'controller_host': origin,
                                     'controller_oauthtoken': TOKEN, 'validate_certs': True})
            values = json.loads(receipt.read_text()).get('_run', {})
            if behavior.startswith('launch-'):
                self.assertEqual([event['event'] for event in observed], ['launch', 'stats'])
                expected_id = CHILD if behavior == 'launch-flag-only-failure' else None
                self.assertEqual(values['aap_selected_configuration_job']['job_id'], expected_id)
                self.assertFalse(requests)
            else:
                self.assertEqual([event['event'] for event in observed[:3]], ['launch', 'stats', 'wait'])
                self.assertEqual(observed[1]['data']['aap_selected_configuration_job'],
                                 {'selection': 'synthetic-selection', 'job_id': CHILD, 'status': 'pending'})
                wait = observed[2]['args']
                self.assertEqual(wait, {'job_id': CHILD, 'job_type': 'jobs', 'interval': 10, 'timeout': 10800,
                                       'controller_host': origin, 'controller_oauthtoken': TOKEN, 'validate_certs': True})
                self.assertEqual(launches[0]['environment'], observed[2]['environment'])
                self.assertEqual(values['aap_selected_configuration_job']['job_id'], CHILD)
            if successful or behavior == 'wrong-credentials':
                self.assertEqual(requests, [('/api/controller/v2/jobs/' + str(CHILD) + '/credentials/?page_size=200', 'Bearer ' + TOKEN)])
                self.assertNotIn('aap_selected_configuration_failure_vault', values)
                return
            self.assertFalse(requests)
            sealed = values['aap_selected_configuration_failure_vault']
            self.assertTrue(sealed.startswith('$ANSIBLE_VAULT;1.2;AES256;cac\n'))
            decoded = json.loads(vault.decrypt(sealed))
            self.assertEqual(decoded['stage'], 'selected_configuration_job')
            self.assertEqual(decoded['configuration_job'], {'id': expected_id if behavior.startswith('launch-') else CHILD,
                                                          'selection': 'synthetic-selection'})
            primitive = decoded['launch'] if behavior.startswith('launch-') else decoded['observation']
            if behavior in ('launch-failure', 'wait-failure', 'launch-module-failure', 'wait-module-failure'):
                self.assertEqual(primitive['msg'], ERROR)
                self.assertEqual(primitive['detail']['nested']['reason'], 'original-observer-detail')
            if behavior.endswith('transport-failure'):
                self.assertEqual(decoded['original_failure']['stderr'], ERROR)
            if behavior.startswith('launch-'):
                self.assertEqual(decoded['observation'], {})
            protected = json.dumps(decoded)
            for excluded in ('invocation', 'module_args', ARGUMENT_SECRET, PASSWORD, TOKEN):
                self.assertNotIn(excluded, protected)


if __name__ == '__main__':
    unittest.main()
