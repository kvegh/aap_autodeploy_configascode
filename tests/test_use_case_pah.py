"""Run real PAH preparation tasks against an isolated API, including failures."""

import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
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
PULP = "/api/galaxy/pulp/api/v3/"
REMOTE = PULP + "remotes/ansible/collection/11111111-1111-1111-1111-111111111111/"
REPOSITORY = PULP + "repositories/ansible/ansible/22222222-2222-2222-2222-222222222222/"
POLICY_TASK = PULP + "tasks/33333333-3333-3333-3333-333333333333/"
SYNC_TASK = PULP + "tasks/44444444-4444-4444-4444-444444444444/"
SECRET = "synthetic-pah-management-secret"


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires installed Ansible and PyYAML")
class UseCasePahTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        roots = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
        if not any((Path(root) / "ansible_collections/ansible/hub").is_dir() for root in roots if root):
            raise unittest.SkipTest("requires installed ansible.hub")
        cls.state = {}

        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, status, body):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def do_GET(self):
                path = urlsplit(self.path).path
                if path == "/api/":
                    return self.respond(200, {"apis": {"galaxy": "/api/galaxy/"}})
                if path == "/api/galaxy/":
                    return self.respond(200, {"server_version": "4.12.0"})
                if path.endswith("/auth/login/"):
                    return self.respond(200, {})
                if path == REMOTE:
                    return self.respond(200, cls.state["remote"])
                if path == PULP + "remotes/ansible/collection/":
                    return self.respond(200, {"count": 1, "results": [cls.state["remote"]], "next": None})
                if path == PULP + "repositories/ansible/ansible/":
                    return self.respond(200, {"count": 1, "results": [{"name": "rh-certified", "pulp_href": REPOSITORY}], "next": None})
                if path == POLICY_TASK:
                    cls.state["policy_observed"] = True
                    return self.respond(200, {"state": "failed" if cls.state["fail_policy"] else "completed",
                                               "error": None, "pulp_href": POLICY_TASK})
                if path == SYNC_TASK:
                    failure = cls.state["fail_second_sync"] and len(cls.state["syncs"]) == 2
                    return self.respond(200, {"state": "failed" if failure else "completed", "pulp_href": SYNC_TASK,
                                               "error": {"description": "Synthetic,sync failed,test", "traceback": "fixture"} if failure else None})
                if "/collections/index/" in path:
                    parts = path.strip("/").split("/")
                    index = parts.index("index")
                    name = parts[index + 1] + "." + parts[index + 2]
                    version = parts[index + 4]
                    return self.respond(200 if (name, version) in cls.state["available"] else 404, {})
                self.respond(404, {"path": path})

            def do_PATCH(self):
                path = urlsplit(self.path).path
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if path != REMOTE:
                    return self.respond(404, {})
                if "sync_highest_versions" in body:
                    cls.state["remote"].update(body)
                    return self.respond(202, {"task": POLICY_TASK})
                if not cls.state["policy_observed"]:
                    return self.respond(409, {"detail": "The policy task must finish before updating requirements"})
                cls.state["remote"].update(body)
                self.respond(200, cls.state["remote"])

            def do_POST(self):
                path = urlsplit(self.path).path
                if path.endswith("/auth/logout/"):
                    return self.respond(200, {})
                if path != REPOSITORY + "sync/":
                    return self.respond(404, {})
                batch = yaml.safe_load(cls.state["remote"]["requirements_file"])["collections"]
                if len({entry["name"] for entry in batch}) != len(batch):
                    return self.respond(400, {"detail": "Duplicate names would discard an explicitly pinned version"})
                cls.state["syncs"].append(copy.deepcopy(batch))
                if not (cls.state["fail_second_sync"] and len(cls.state["syncs"]) == 2):
                    cls.state["available"].update((entry["name"], entry["version"]) for entry in batch)
                self.respond(202, {"task": SYNC_TASK})

            def do_DELETE(self):
                if self.path != "/api/gateway/v1/tokens/99/":
                    return self.respond(404, {})
                cls.state["tokens_revoked"].append(99)
                self.respond(204, {})

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), API)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.target = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.entries = [{"name": "example.roles", "version": "1.2.3"},
                        {"name": "example.roles", "version": "2.4.0"},
                        {"name": "example.windows", "version": "3.1.0"}]
        self.state.clear()
        self.state.update(remote={"name": "rh-certified", "url": "https://upstream.example.invalid/api/",
                                  "pulp_href": REMOTE, "tls_validation": True, "requirements_file": "collections: []\n",
                                  "sync_highest_versions": 0}, syncs=[], available={("unrelated.existing", "1.0.0")},
                          fail_policy=False, fail_second_sync=False, policy_observed=False, tokens_revoked=[])

    def run_tasks(self):
        with tempfile.TemporaryDirectory(prefix="use-case-pah-test-") as directory:
            root = Path(directory)
            workspace = root / "private"
            workspace.mkdir(mode=0o700)
            variables = {"aap_hostname": self.target, "aap_token": SECRET, "aap_validate_certs": True,
                         "debug_logging": True, "cac_workspace": {"path": str(workspace)},
                         "cac_gateway_token": {"json": {"id": 99, "token": SECRET}},
                         "cac_required_repository": {"name": "rh-certified", "collections": self.entries}}
            fixture = root / "play.yml"
            fixture.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                                               "vars": variables, "tasks": [{"block": [
                                                   {"ansible.builtin.include_tasks": {"file": str(ROOT / "tasks/use-case-pah-repository.yml"),
                                                                                       "apply": {"no_log": True}}}],
                                                   "always": [{"ansible.builtin.include_tasks": str(ROOT / "tasks/private-config-cleanup.yml")}]}]}],
                                             sort_keys=False))
            (root / "ansible.cfg").write_text("[defaults]\nstdout_callback=default\nretry_files_enabled=False\n")
            environment = dict(os.environ, ANSIBLE_CONFIG=str(root / "ansible.cfg"), ANSIBLE_NOCOLOR="1",
                               ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                                    cwd=root, env=environment, capture_output=True, text=True, timeout=90)
            output = result.stdout + result.stderr
            self.assertNotIn(SECRET, output)
            self.assertFalse(workspace.exists(), output)
            self.assertEqual(self.state["tokens_revoked"], [99])
            return result, output

    def test_success_preserves_both_pins_existing_content_and_full_remote_requirements(self):
        result, output = self.run_tasks()
        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(len(self.state["syncs"]), 2)
        self.assertTrue(self.state["policy_observed"])
        self.assertCountEqual(yaml.safe_load(self.state["remote"]["requirements_file"])["collections"], self.entries)
        self.assertIn(("unrelated.existing", "1.0.0"), self.state["available"])
        self.assertTrue(all((entry["name"], entry["version"]) in self.state["available"] for entry in self.entries))

    def test_failed_sync_restores_full_requirements_and_still_cleans_authentication(self):
        self.state["fail_second_sync"] = True
        result, output = self.run_tasks()
        self.assertNotEqual(result.returncode, 0, output)
        self.assertEqual(len(self.state["syncs"]), 2)
        self.assertCountEqual(yaml.safe_load(self.state["remote"]["requirements_file"])["collections"], self.entries)
        self.assertIn(("unrelated.existing", "1.0.0"), self.state["available"])

    def test_failed_async_policy_never_starts_content_synchronization(self):
        self.state["fail_policy"] = True
        result, output = self.run_tasks()
        self.assertNotEqual(result.returncode, 0, output)
        self.assertEqual(self.state["syncs"], [])


if __name__ == "__main__":
    unittest.main()
