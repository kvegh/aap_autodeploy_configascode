"""Exercise real source authentication, launch/wait and cleanup over private TLS."""

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
        cls.unrelated_certificate = cls.root / "synthetic-unrelated-ca.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                        "-keyout", str(cls.root / "unrelated-key.pem"), "-out", str(cls.unrelated_certificate),
                        "-days", "1", "-subj", "/CN=Unrelated synthetic fixture authority"],
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
                if self.headers.get("Authorization") != "Bearer synthetic-seed-token":
                    return self.respond(401, {})
                job = {"id": 7, "name": "Synthetic configuration importer",
                       "related": {"launch": "/api/controller/v2/job_templates/7/launch/"},
                       "ask_variables_on_launch": False, "survey_enabled": True}
                if path.endswith("/job_templates/7"):
                    data = job
                elif path.endswith("/job_templates"):
                    data = {"count": 1, "results": [job], "next": None, "previous": None}
                elif path.endswith("/jobs/81"):
                    data = {"id": 81, "status": "running", "job_template": cls.source_template,
                            "scm_revision": "fixture-revision"}
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
                if path.endswith("/job_templates/7/launch"):
                    if self.headers.get("Authorization") != "Bearer synthetic-seed-token":
                        return self.respond(401, {})
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

    def run_source_tasks(self, *, ca=True, hostname="127.0.0.1", source_token=True, source_template=90,
                         default_trust=False, unrelated_extra=False, malformed_extra=False, native="true"):
        self.requests.clear()
        type(self).source_template = source_template
        source = yaml.safe_load((ROOT / "deploy-selected-use-cases.yml").read_text())[0]
        block = source["tasks"][0]["block"]
        names = ["Require the existing source API credential and running job identity",
                 "Bind orchestration to the API credential of the AAP running this job",
                 "Supplement the execution environment's trust with the existing source CA",
                 "Read this running job through its source API credential",
                 "Require the credential to identify the actual running source job"]
        tasks = [copy.deepcopy(next(task for task in block if task["name"] == name)) for name in names]
        tasks.append(copy.deepcopy(next(task for task in block if task["name"] ==
                                       "Read the seed controller's current instance identities")))
        importer = yaml.safe_load((ROOT / "tasks/selected-use-case-import.yml").read_text())
        tasks.extend(copy.deepcopy([
            next(task for task in importer if "ansible.controller.job_launch" in task),
            next(task for task in importer if task.get("name") ==
                 "Read the completed job's actual credential associations"),
        ]))
        tasks.extend([
            {"name": "Source module environment must not change default trust",
             "ansible.builtin.uri": {"url": "{{ aap_selected_source_auth.hostname }}/untrusted-default-probe",
                                     "validate_certs": True},
             "failed_when": False, "register": "default_trust_probe", "no_log": True},
            {"name": "Keep target credentials and default trust independent",
             "ansible.builtin.assert": {"that": [
                 "aap_password == 'synthetic-target-password'",
                 "default_trust_probe.status | default(-1) != 200",
                 "aap_selected_import_job.status == 'successful'",
                 "aap_selected_completed_credentials.json.count == 0"]}, "no_log": True},
        ])
        variables = {
            "awx_job_id": 81, "awx_job_template_id": 90, "awx_project_revision": "fixture-revision",
            "aap_seed_ca_path": str(self.unrelated_certificate if unrelated_extra else self.certificate) if ca else "",
            "aap_validate_certs": True, "aap_username": "synthetic-target-user",
            "aap_password": "synthetic-target-password", "aap_instance_key": "synthetic-target",
            "aap_selected_importer": {"json": {"results": [{"id": 7}]},
                                      "item": {"repository": "https://git.example.invalid/test/config.git",
                                               "playbook": "deploy-cac-project.yml"}},
            "aap_selected_importer_extra": {}, "aap_selected_launch_credential_ids": [],
        }
        with tempfile.TemporaryDirectory(dir=self.root, prefix="run-") as directory:
            path = Path(directory)
            if malformed_extra:
                malformed = path / "malformed-source-ca.pem"
                malformed.write_text("synthetic malformed trust input\n")
                variables["aap_seed_ca_path"] = str(malformed)
            config = path / "ansible.cfg"
            config.write_text("[defaults]\nstdout_callback=default\nretry_files_enabled=False\n")
            workspace_record = path / "workspace-path.txt"
            # Retain the allocated path even when the first authenticated request fails.
            source_trust = next(task for task in tasks if task["name"] == names[2])
            source_trust["block"].insert(1, {"name": "Remember only the fixture workspace path", "no_log": True,
                "ansible.builtin.copy": {"dest": str(workspace_record), "mode": "0600",
                                        "content": "{{ cac_workspace.path }}"}})
            source_trust["block"].extend([
                {"ansible.builtin.stat": {"path": "{{ aap_seed_ca_path }}"}, "register": "fixture_trust_stat"},
                {"ansible.builtin.assert": {"that": ["fixture_trust_stat.stat.mode == '0600'"]}},
            ])
            checkout = yaml.safe_load((ROOT / "tasks/private-config-checkout.yml").read_text())
            tasks[3:3] = [copy.deepcopy(task) for task in checkout if task["name"] in (
                "Create a private temporary configuration workspace", "Use the newly allocated configuration workspace")]
            play = path / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local",
                                            "gather_facts": False, "vars": variables,
                                            "tasks": [{"block": tasks,
                                                "always": copy.deepcopy(source["tasks"][0]["always"])}]}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                       AAP_CAC_SOURCE_URL=f"https://{hostname}:{self.server.server_port}",
                       AAP_CAC_SOURCE_TOKEN="synthetic-seed-token" if source_token else "",
                       ANSIBLE_JINJA2_NATIVE=native,
                       ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"),
                       ANSIBLE_LOCAL_TEMP=str(path / "local"), ANSIBLE_REMOTE_TEMP=str(path / "remote"))
            if default_trust:
                env["SSL_CERT_FILE"] = str(self.certificate)
            else:
                env.pop("SSL_CERT_FILE", None)
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                    cwd=path, env=env, capture_output=True, text=True, timeout=90)
            output = result.stdout + result.stderr
            for secret in ["synthetic-seed-password", "synthetic-target-password", "synthetic-seed-token"]:
                self.assertNotIn(secret, output)
            if workspace_record.exists():
                self.assertFalse(Path(workspace_record.read_text()).exists(), "Private source trust workspace leaked.")
            return result, output

    def test_scoped_ca_supports_authentication_real_launch_wait_and_cleanup(self):
        for native in ("false", "true"):
            with self.subTest(native=native):
                result, output = self.run_source_tasks(native=native)
                self.assertEqual(result.returncode, 0, output)
                self.assertIn(("POST", "/api/controller/v2/job_templates/7/launch/"), self.requests)
                self.assertIn(("GET", "/api/controller/v2/jobs/99/"), self.requests)
                self.assertIn(("GET", "/api/controller/v2/jobs/81/"), self.requests)
                self.assertFalse(any(method == "DELETE" or "/tokens" in path for method, path in self.requests))
                self.assertNotIn(("GET", "/untrusted-default-probe"), self.requests)

    def test_unrelated_extra_ca_preserves_default_runtime_trust_for_uri_and_sdk(self):
        for native in ("false", "true"):
            with self.subTest(native=native):
                result, output = self.run_source_tasks(default_trust=True, unrelated_extra=True, native=native)
                self.assertEqual(result.returncode, 0, output)
                self.assertIn(("POST", "/api/controller/v2/job_templates/7/launch/"), self.requests)
                self.assertIn(("GET", "/untrusted-default-probe"), self.requests)

    def test_unrelated_extra_ca_still_refuses_untrusted_source_and_cleans_workspace(self):
        for native in ("false", "true"):
            with self.subTest(native=native):
                result, output = self.run_source_tasks(unrelated_extra=True, native=native)
                self.assertNotEqual(result.returncode, 0, output)
                self.assertEqual(self.requests, [])

    def test_malformed_extra_ca_is_refused_even_when_default_trust_accepts_source(self):
        for native in ("false", "true"):
            with self.subTest(native=native):
                result, output = self.run_source_tasks(default_trust=True, malformed_extra=True, native=native)
                self.assertNotEqual(result.returncode, 0, output)
                self.assertEqual(self.requests, [])

    def test_missing_ca_refuses_private_source_before_any_http(self):
        for native in ("false", "true"):
            with self.subTest(native=native):
                result, output = self.run_source_tasks(ca=False, native=native)
                self.assertNotEqual(result.returncode, 0, output)
                self.assertEqual(self.requests, [])

    def test_wrong_hostname_is_refused_even_with_the_trusted_ca(self):
        for native in ("false", "true"):
            with self.subTest(native=native):
                result, output = self.run_source_tasks(hostname="localhost", native=native)
                self.assertNotEqual(result.returncode, 0, output)
                self.assertEqual(self.requests, [])

    def test_target_password_is_not_a_fallback_for_missing_source_token(self):
        for native in ("false", "true"):
            with self.subTest(native=native):
                result, output = self.run_source_tasks(source_token=False, native=native)
                self.assertNotEqual(result.returncode, 0, output)
                self.assertEqual(self.requests, [])

    def test_wrong_source_job_identity_refuses_orchestration_before_launch(self):
        for native in ("false", "true"):
            with self.subTest(native=native):
                result, output = self.run_source_tasks(source_template=91, native=native)
                self.assertNotEqual(result.returncode, 0, output)
                self.assertEqual(self.requests, [("GET", "/api/controller/v2/jobs/81/")])


if __name__ == "__main__":
    unittest.main()
