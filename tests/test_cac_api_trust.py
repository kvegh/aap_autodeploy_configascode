"""Exercise importer trust against a local TLS API without real credentials."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
import yaml
from ansible.template import trust_as_template

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('trust_fixture_yaml', ROOT / 'src/cac_yaml.py')
codec = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(codec)
CANARY = 'synthetic-import-bearer-must-stay-hidden'


class ImportTrustTests(unittest.TestCase):
    def test_existing_ca_is_scoped_preserves_defaults_and_refuses_bad_trust(self):
        self.assertTrue(shutil.which('openssl'), 'OpenSSL is required for the local TLS fixture')
        source = codec.load_repository_yaml((ROOT / 'tasks/cac-api-auth.yml').read_text())
        trust = next(t for t in source if t['name'] == 'Supplement job-local API trust with the existing injected CA')
        request = next(t for t in source if 'ansible.builtin.uri' in t)
        report = next(t for t in source if t['name'] == 'Require authenticated HTTPS and report only a safe failure category')
        importer = codec.load_repository_yaml((ROOT / 'deploy-cac-project.yml').read_text())[0]
        environment = next(t for t in importer['pre_tasks'] if 'environment' in t)['environment']
        with tempfile.TemporaryDirectory(prefix='cac-import-trust-') as temporary:
            root = Path(temporary)
            def certificate(name, san):
                cert, key = root / (name + '.pem'), root / (name + '.key')
                subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                                '-keyout', str(key), '-out', str(cert), '-days', '1',
                                '-subj', '/CN=Synthetic import fixture', '-addext', san],
                               check=True, capture_output=True)
                return cert, key
            cert, key = certificate('trusted', 'subjectAltName=IP:127.0.0.1')
            unrelated, unused = certificate('unrelated', 'subjectAltName=DNS:unrelated.example.invalid')
            malformed = root / 'malformed.pem'
            malformed.write_text(CANARY + '\n')
            seen = []
            class API(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass
                def do_GET(self):
                    seen.append(self.path)
                    code = 200 if self.headers.get('Authorization') == 'Bearer ' + CANARY else 401
                    self.send_response(code)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{}')
            server = ThreadingHTTPServer(('127.0.0.1', 0), API)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(cert), str(key))
            server.socket = context.wrap_socket(server.socket, server_side=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            cases = [('trusted', cert, False, '127.0.0.1', True),
                     ('missing', None, False, '127.0.0.1', False),
                     ('unrelated', unrelated, False, '127.0.0.1', False),
                     ('malformed', malformed, True, '127.0.0.1', False),
                     ('preserve-default', unrelated, True, '127.0.0.1', True),
                     ('wrong-host', cert, False, 'localhost', False)]
            try:
                for name, supplemental, default_trust, hostname, success in cases:
                    with self.subTest(case=name):
                        seen.clear()
                        runroot = root / name
                        runroot.mkdir()
                        workspace = runroot / 'private'
                        workspace.mkdir(mode=0o700)
                        protected = runroot / 'protected.json'
                        protected.write_text(json.dumps({'cac_api_auth': {'hostname':
                            f'https://{hostname}:{server.server_port}', 'token': CANARY},
                            'cac_workspace': {'path': str(workspace)}}))
                        protected.chmod(0o600)
                        module_probe = deepcopy(request)
                        module_probe['name'] = 'Verify inherited module trust without a per-request CA'
                        module_probe['ansible.builtin.uri'].pop('ca_path')
                        module_probe.pop('failed_when')
                        module_probe['ansible.builtin.uri']['url'] = trust_as_template('{{ cac_api_auth.hostname }}/module-probe')
                        unscoped = deepcopy(module_probe)
                        unscoped['name'] = 'Observe unchanged trust outside the import block'
                        unscoped['failed_when'] = False
                        unscoped['register'] = 'outside_probe'
                        checks = [{'ansible.builtin.stat': {'path': trust_as_template('{{ cac_api_ca_path }}')},
                                   'register': 'trust_stat', 'when': 'cac_api_ca_path is defined'},
                                  {'ansible.builtin.assert': {'that': "trust_stat.stat.mode == '0600'"},
                                   'when': 'cac_api_ca_path is defined'}]
                        fixture = runroot / 'fixture.yml'
                        fixture.write_text(yaml.dump([{'hosts': 'localhost', 'connection': 'local',
                            'gather_facts': False, 'vars_files': [str(protected)], 'tasks': [
                                {'block': [deepcopy(trust), deepcopy(request), deepcopy(report), module_probe, *checks],
                                 'environment': environment,
                                 'always': [{'ansible.builtin.file': {'path': trust_as_template('{{ cac_workspace.path }}'),
                                                                     'state': 'absent'}}]},
                                unscoped,
                                {'ansible.builtin.assert': {'that':
                                    'outside_probe.status == 200' if default_trust else 'outside_probe.status != 200'},
                                 'no_log': True}]}], Dumper=codec.VaultDumper, sort_keys=False))
                        env = {k: v for k, v in os.environ.items()
                               if not k.startswith(('AAP_', 'TOWER_', 'CONTROLLER_'))
                               and k not in ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE')}
                        env.update(ANSIBLE_NOCOLOR='1', ANSIBLE_LOCAL_TEMP=str(runroot / 'local'),
                                   ANSIBLE_REMOTE_TEMP=str(runroot / 'remote'))
                        if supplemental:
                            env['AAP_CAC_SOURCE_CA_FILE'] = str(supplemental)
                        if default_trust:
                            env['SSL_CERT_FILE'] = str(cert)
                        result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-vvv',
                            '-i', 'localhost,', str(fixture)], cwd=runroot, env=env,
                            capture_output=True, text=True, timeout=90)
                        output = result.stdout + result.stderr
                        self.assertNotIn(CANARY, output)
                        self.assertEqual(result.returncode == 0, success, output)
                        self.assertFalse(workspace.exists(), 'Private CA workspace was not cleaned')
                        if success:
                            self.assertIn('/api/gateway/v1/me/', seen)
                            self.assertIn('/module-probe', seen)
                        else:
                            self.assertEqual(seen, [], 'Untrusted peer received HTTP credentials')
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
