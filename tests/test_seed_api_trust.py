"""Exercise real source authentication, launch/wait and cleanup over private TLS."""

import base64
import copy
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
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible") and shutil.which("openssl"),
                     "requires installed Ansible, PyYAML and OpenSSL")
class SeedApiTrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
        if not any((Path(path) / "ansible_collections/ansible/controller").is_dir() for path in paths if path):
            raise unittest.SkipTest("requires installed ansible.controller")
        cls.directory = tempfile.TemporaryDirectory(prefix="seed-api-trust-")
        cls.root = Path(cls.directory.name)
        cls.certificate = cls.root / "synthetic-ca.pem"
        key = cls.root / "synthetic-key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                        "-keyout", str(key), "-out", str(cls.certificate), "-days", "1",
                        "-subj", "/CN=Synthetic fixture authority",
                        "-addext", "subjectAltName=IP:127.0.0.1"],
                       check=True, capture_output=True)
        cls.requests = []

        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, code, data):
                cls.requests.append((self.command, urlsplit(self.path).path))
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("X-API-Product-Version", "4.8.11")
                self.end_headers()
                if code != 204:
                    self.wfile.write(json.dumps(data).encode())

            def do_GET(self):
                path = urlsplit(self.path).path.rstrip("/")
                job = {"id": 7, "name": "Synthetic configuration importer",
                       "related": {"launch": "/api/controller/v2/job_templates/7/launch/"},
                       "ask_variables_on_launch": False, "survey_enabled": True}
                if path.endswith("/job_templates/7"):
                    data = job
                elif path.endswith("/job_templates"):
                    data = {"count": 1, "results": [job], "next": None, "previous": None}
                elif path.endswith("/jobs/99"):
                    data = {"id": 99, "status": "successful", "failed": False,
                            "finished": "2000-01-01T00:00:00Z", "elapsed": 0}
                elif path.endswith("/instances"):
                    data = {"count": 1, "results": [{"uuid": "synthetic-seed"}], "next": None}
                elif path.endswith("/credentials"):
                    data = {"count": 0, "results": [], "next": None}
                else:
                    data = {}
                self.respond(200, data)

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                path = urlsplit(self.path).path.rstrip("/")
                if path.endswith("/tokens"):
                    expected = base64.b64encode(b"synthetic-seed-user:synthetic-seed-password").decode()
                    if self.headers.get("Authorization") != "Basic " + expected:
                        return self.respond(401, {})
                    return self.respond(201, {"id": 42, "token": "synthetic-seed-token"})
                if path.endswith("/job_templates/7/launch"):
                    return self.respond(201, {"id": 99, "status": "pending",
                                             "url": "/api/controller/v2/jobs/99/"})
                self.respond(404, {})

            def do_DELETE(self):
                self.respond(204, {})

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), API)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(cls.certificate), str(key))
        cls.server.socket = context.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.directory.cleanup()

    def run_source_tasks(self, *, ca=True, hostname="127.0.0.1", seed_login=True):
        self.requests.clear()
        source = yaml.safe_load((ROOT / "deploy-selected-use-cases.yml").read_text())[0]
        block = source["tasks"][0]["block"]
        names = ["Require explicit seed credentials separately from target base",
                 "Authenticate only the seed controller for importer orchestration",
                 "Read the seed controller's current instance identities"]
        tasks = [copy.deepcopy(next(task for task in block if task["name"] == name)) for name in names]
        tasks[1]["ansible.builtin.include_tasks"] = str(ROOT / "tasks/gateway-base-login.yml")
        importer = yaml.safe_load((ROOT / "tasks/selected-use-case-import.yml").read_text())
        tasks.extend(copy.deepcopy(importer[1:3]))
        tasks.extend([
            {"name": "Source module environment must not change default trust",
             "ansible.builtin.uri": {"url": "{{ aap_seed_hostname }}/untrusted-default-probe",
                                     "validate_certs": True},
             "failed_when": False, "register": "default_trust_probe", "no_log": True},
            {"name": "Keep target credentials and default trust independent",
             "ansible.builtin.assert": {"that": [
                 "aap_password == 'synthetic-target-password'",
                 "default_trust_probe.status | default(-1) != 200",
                 "aap_selected_import_job.status == 'successful'",
                 "aap_selected_completed_credentials.json.count == 0"]}, "no_log": True},
            {"name": "Remove temporary seed authentication",
             "ansible.builtin.include_tasks": str(ROOT / "tasks/private-config-cleanup.yml"),
             "vars": {"aap_hostname": "{{ aap_seed_hostname }}",
                      "cac_cleanup_ca_path": "{{ aap_seed_ca_path }}"}},
        ])
        variables = {
            "aap_seed_hostname": f"https://{hostname}:{self.server.server_port}",
            "aap_seed_ca_path": str(self.certificate) if ca else "",
            "aap_validate_certs": True, "aap_username": "synthetic-target-user",
            "aap_password": "synthetic-target-password", "aap_instance_key": "synthetic-target",
            "cac_use_case_selector": {"seed_username": "synthetic-seed-user",
                                       "seed_password": "synthetic-seed-password"} if seed_login else {},
            "aap_selected_importer": {"json": {"results": [{"id": 7}]},
                                      "item": {"repository": "https://git.example.invalid/test/config.git"}},
            "aap_selected_importer_extra": {}, "aap_selected_launch_credential_ids": [],
        }
        with tempfile.TemporaryDirectory(dir=self.root, prefix="run-") as directory:
            path = Path(directory)
            config = path / "ansible.cfg"
            config.write_text("[defaults]\nstdout_callback=default\nretry_files_enabled=False\n")
            play = path / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local",
                                            "gather_facts": False, "vars": variables,
                                            "tasks": tasks}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                       ANSIBLE_LOCAL_TEMP=str(path / "local"), ANSIBLE_REMOTE_TEMP=str(path / "remote"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                    cwd=path, env=env, capture_output=True, text=True, timeout=90)
            output = result.stdout + result.stderr
            for secret in ["synthetic-seed-password", "synthetic-target-password", "synthetic-seed-token"]:
                self.assertNotIn(secret, output)
            return result, output

    def test_scoped_ca_supports_authentication_real_launch_wait_and_cleanup(self):
        result, output = self.run_source_tasks()
        self.assertEqual(result.returncode, 0, output)
        self.assertIn(("POST", "/api/controller/v2/job_templates/7/launch/"), self.requests)
        self.assertIn(("GET", "/api/controller/v2/jobs/99/"), self.requests)
        self.assertIn(("DELETE", "/api/gateway/v1/tokens/42/"), self.requests)
        self.assertNotIn(("GET", "/untrusted-default-probe"), self.requests)

    def test_missing_ca_refuses_private_source_before_any_http(self):
        result, output = self.run_source_tasks(ca=False)
        self.assertNotEqual(result.returncode, 0, output)
        self.assertEqual(self.requests, [])

    def test_wrong_hostname_is_refused_even_with_the_trusted_ca(self):
        result, output = self.run_source_tasks(hostname="localhost")
        self.assertNotEqual(result.returncode, 0, output)
        self.assertEqual(self.requests, [])

    def test_target_password_is_not_a_fallback_for_missing_seed_login(self):
        result, output = self.run_source_tasks(seed_login=False)
        self.assertNotEqual(result.returncode, 0, output)
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
