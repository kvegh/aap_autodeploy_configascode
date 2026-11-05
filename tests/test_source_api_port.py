"""Prove exact SSH pin matching survives Controller's native API wire types."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

import yaml
from test_guest_release import fixture, Source, keys

ROOT = Path(__file__).resolve().parents[1]


def source_port(source, pin, value):
    for row in source.hosts.values():
        values = keys.inventory_variables(row)
        if values.get('ansible_host') == pin['address']:
            values['ansible_port'] = value
            row['variables'] = json.dumps(values)


class SourceApiPortTests(unittest.TestCase):
    def test_actual_uri_native_serialization_preserves_exact_port_and_other_identity_guards(self):
        for native in (False, True):
            with self.subTest(native=native):
                self.run_native(native)

    def run_native(self, native):
        captured = []

        class Controller(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_PATCH(self):
                if self.headers.get('Authorization') != 'Bearer synthetic-controller-token':
                    self.send_error(403)
                    return
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                captured.append(yaml.safe_load(body['variables']))
                raw = json.dumps(body).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Controller)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix='source-api-native-port-') as directory:
                root = Path(directory)
                play = root / 'wire.yml'
                tasks = []
                for encoded in ('ansible_port: "{{ declared_port }}"\n', '{{ {"ansible_port": declared_port} | to_json }}'):
                    tasks.append({'name': 'Send an actual Controller variables wire representation',
                        'ansible.builtin.uri': {
                            'url': 'http://127.0.0.1:%s/api/controller/v2/hosts/10/' % server.server_port,
                            'method': 'PATCH', 'headers': {'Authorization': 'Bearer synthetic-controller-token'},
                            'body_format': 'json', 'body': {'variables': encoded}, 'status_code': 200}})
                play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                    'vars': {'declared_port': 2222}, 'tasks': tasks}], sort_keys=False))
                result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                    cwd=ROOT, text=True, capture_output=True, timeout=45,
                    env=dict(os.environ, ANSIBLE_HOME=str(root/'home'), ANSIBLE_LOCAL_TEMP=str(root/'local'),
                        ANSIBLE_REMOTE_TEMP=str(root/'remote'), ANSIBLE_JINJA2_NATIVE=str(native).lower()))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(captured, [{'ansible_port': '2222'}, {'ansible_port': 2222}])
                for current in captured:
                    for access in ('bootstrap_https', 'release'):
                        guest, pin, main, shared, hactar, _ = fixture(new=True)
                        source = Source(main, shared, hactar)
                        source_port(source, pin, current['ansible_port'])
                        before = json.dumps(source.hosts, sort_keys=True)
                        context = keys.guest_release_context(main, shared, guest, pin, access=access)
                        self.assertTrue(keys.source_guest_release_operations(source, shared, main, hactar, context))
                        self.assertEqual(json.dumps(source.hosts, sort_keys=True), before)
                        self.assertEqual(source.calls, [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_noncanonical_or_different_api_ports_refuse_before_any_write(self):
        for value in (True, False, None, 0, -1, 65536, 2222.0, '', '02222', '+2222', '-2222', ' 2222',
                      '2222 ', '2222\n', '２２２２', '2_222', '0', '65536', 2223, '2223'):
            with self.subTest(value=value):
                guest, pin, main, shared, hactar, _ = fixture(new=True)
                source = Source(main, shared, hactar)
                source_port(source, pin, value)
                context = keys.guest_release_context(main, shared, guest, pin, access='bootstrap_https')
                with self.assertRaises(keys.StoreError):
                    keys.source_guest_release_operations(source, shared, main, hactar, context)
                self.assertEqual(source.calls, [])

    def test_only_live_port_wire_text_is_normalized_and_bounds_remain_exact(self):
        for value in (1, 65535, '1', '65535'):
            self.assertEqual(keys.canonical_api_port(value), int(value))
        guest, pin, main, shared, hactar, _ = fixture(new=True)
        source = Source(main, shared, hactar)
        source_port(source, pin, str(pin['port']))
        for row in source.hosts.values():
            values = keys.inventory_variables(row)
            if values.get('ansible_host') == pin['address']:
                values['machine_id'] = '0' * 32
                row['variables'] = json.dumps(values)
        context = keys.guest_release_context(main, shared, guest, pin)
        with self.assertRaises(keys.StoreError):
            keys.source_guest_release_operations(source, shared, main, hactar, context)
        self.assertEqual(source.calls, [])


if __name__ == '__main__':
    unittest.main()
