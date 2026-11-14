"""Exercise real Ansible failure reporting without revealing protected results."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml
from ansible.template import trust_as_template

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('auth_result_yaml', ROOT / 'src/cac_yaml.py')
codec = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(codec)
CANARY = 'synthetic-protected-auth-result-must-stay-hidden'


class AuthenticationResultTests(unittest.TestCase):
    def test_http_tls_dns_and_network_results_keep_their_details_hidden(self):
        source = codec.load_repository_yaml((ROOT / 'tasks/cac-api-auth.yml').read_text())
        request = next(task for task in source if 'ansible.builtin.uri' in task)
        self.assertTrue(request['no_log'])
        self.assertTrue(request['ansible.builtin.uri']['validate_certs'])
        self.assertEqual(request['ansible.builtin.uri']['follow_redirects'], 'none')
        report = next(task for task in source if task.get('name') ==
                      'Require authenticated HTTPS and report only a safe failure category')
        cases = [
            ({'status': 200, 'msg': CANARY}, None),
            ({'status': 401, 'msg': CANARY, 'content': CANARY}, 'API authorization rejected'),
            ({'status': 403, 'msg': CANARY, 'authorization': CANARY}, 'API authorization rejected'),
            ({'status': -1, 'msg': 'SSL certificate verify failed ' + CANARY}, 'TLS certificate validation'),
            ({'status': -1, 'msg': 'Temporary failure in name resolution ' + CANARY}, 'DNS resolution'),
            ({'status': -1, 'msg': 'Connection refused ' + CANARY}, 'network connection'),
            ({'status': -1, 'msg': 'The read operation timed out ' + CANARY}, 'connection timeout'),
            ({'status': 302, 'msg': CANARY}, 'request failed'),
            ({'msg': CANARY}, 'request failed'),
        ]
        tasks = []
        for index, (result, category) in enumerate(cases):
            tasks.append({'name': 'Supply a protected synthetic request result',
                          'ansible.builtin.set_fact': {'cac_bearer_probe': trust_as_template('{{ fixture_auth_results[' + str(index) + '] }}')},
                          'no_log': True})
            task = deepcopy(report)
            task.update(register='fixture_report', ignore_errors=True)
            tasks.append(task)
            conditions = ['fixture_report is succeeded'] if category is None else [
                'fixture_report is failed', repr(category) + ' in fixture_report.msg']
            tasks.append({'name': 'Verify the safe result without printing protected input',
                          'ansible.builtin.assert': {'that': conditions, 'quiet': True}})
        with tempfile.TemporaryDirectory(prefix='cac-auth-report-fixture-') as temporary:
            directory = Path(temporary)
            protected = directory / 'synthetic-results.json'
            protected.write_text(json.dumps({'fixture_auth_results': [result for result, unused in cases]}))
            protected.chmod(0o600)
            fixture = directory / 'fixture.yml'
            fixture.write_text(yaml.dump([{'hosts': 'localhost', 'connection': 'local',
                                           'gather_facts': False, 'vars_files': [str(protected)], 'tasks': tasks}],
                                          Dumper=codec.VaultDumper, sort_keys=False))
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(('AAP_', 'TOWER_', 'CONTROLLER_'))}
            environment.update(ANSIBLE_NOCOLOR='1', ANSIBLE_DISPLAY_ARGS_TO_STDOUT='true',
                               ANSIBLE_LOCAL_TEMP=str(directory / 'local'),
                               ANSIBLE_REMOTE_TEMP=str(directory / 'remote'))
            run = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-vvv',
                                  '-i', 'localhost,', str(fixture)], cwd=ROOT, env=environment,
                                 text=True, capture_output=True, timeout=60)
            output = run.stdout + run.stderr
            self.assertNotIn(CANARY, output)
            self.assertEqual(run.returncode, 0, output)
            for unused, category in cases:
                if category is not None:
                    self.assertIn(category, output)


if __name__ == '__main__':
    unittest.main()
