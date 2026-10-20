"""Exercise persistent MCP provisioning with real tasks and an offline Gateway."""

import base64
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
from urllib.parse import parse_qs, urlsplit

try:
    import yaml
except ImportError:
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
BEARER = "synthetic-persistent-mcp-secret"
MANAGEMENT = "synthetic-management-secret"
PASSWORD = "synthetic-final-admin-secret"


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class McpAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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
                parsed = urlsplit(self.path)
                authorization = self.headers.get("Authorization")
                if parsed.path.endswith("/me/"):
                    if authorization != "Bearer " + BEARER or cls.state["expired"]:
                        return self.respond(401, {"detail": "Expired or invalid token"})
                    return self.respond(200, {"count": 1, "results": [
                        {"id": 1, "username": cls.state.get("identity", "admin")}]})
                if authorization != "Bearer " + MANAGEMENT:
                    return self.respond(403, {})
                if parsed.path.endswith("/users/"):
                    return self.respond(200, {"count": 1, "results": [{"id": 1, "username": "admin"}]})
                if parsed.path.endswith("/tokens/"):
                    if parse_qs(parsed.query) != {"description": ["MCP admin token"], "user": ["1"]}:
                        return self.respond(400, {})
                    return self.respond(200, {"count": len(cls.state["tokens"]), "results": cls.state["tokens"]})
                self.respond(404, {})

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                expected = "Basic " + base64.b64encode(("admin:" + PASSWORD).encode()).decode()
                if self.headers.get("Authorization") != expected:
                    return self.respond(401, {})
                if payload != {"description": "MCP admin token", "scope": "write", "application": None}:
                    return self.respond(400, {})
                cls.state["created"] += 1
                item = {"id": 100 + cls.state["created"], "description": "MCP admin token", "user": 1,
                        "scope": "write", "application": None, "expires": "2030-01-01T00:00:00Z"}
                cls.state["tokens"].append(item)
                self.respond(201, dict(item, token=BEARER))

            def do_DELETE(self):
                token_id = int(self.path.rstrip("/").split("/")[-1])
                cls.state["deleted"].append(token_id)
                cls.state["tokens"] = [item for item in cls.state["tokens"] if item["id"] != token_id]
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
        self.state.clear()
        self.state.update(tokens=[], created=0, deleted=[], expired=False)
        self.directory = tempfile.TemporaryDirectory(prefix="mcp-access-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.storage = self.root / "protected"
        self.token_file = self.storage / "mcp-token.json"

    def run_tasks(self, save_failure=None, unknown_save=False):
        tasks = yaml.safe_load((ROOT / "tasks/mcp-access.yml").read_text())
        tasks[0]["vars"]["cac_mcp_directory"] = str(self.storage)

        def relocate(items):
            for task in items:
                if "delegate_to" in task:
                    task["delegate_to"] = "localhost"
                    task["vars"] = {"ansible_connection": "local", "ansible_become": False}
                for module in ("ansible.builtin.copy", "ansible.builtin.file"):
                    if module in task:
                        task[module]["owner"] = str(os.getuid())
                        task[module]["group"] = str(os.getgid())
                if "ansible.builtin.assert" in task:
                    task["ansible.builtin.assert"]["that"] = [
                        item.replace(".stat.uid == 0", ".stat.uid == " + str(os.getuid()))
                        for item in task["ansible.builtin.assert"]["that"]]
                if task.get("name") == "Save the MCP token atomically on its target" and save_failure:
                    saved_copy = {"ansible.builtin.copy": task.pop("ansible.builtin.copy"), "diff": False}
                    failure = {"ansible.builtin.fail": {"msg": "Synthetic failed token save"}}
                    task.pop("diff", None)
                    task["block"] = ([saved_copy, failure] if save_failure == "after" else [failure])
                if unknown_save and task.get("name") in (
                    "Check the target copy after an interrupted token save",
                    "Inspect token storage when its saved contents could not be read",
                ):
                    task.pop("ansible.builtin.slurp", None)
                    task.pop("ansible.builtin.stat", None)
                    task["ansible.builtin.fail"] = {"msg": "Synthetic unreachable storage"}
                for key in ("block", "rescue", "always"):
                    relocate(task.get(key, []))

        relocate(tasks)
        variables = {"aap_hostname": self.target, "aap_username": "admin", "aap_password": PASSWORD,
                     "aap_token": MANAGEMENT, "aap_validate_certs": True, "debug_logging": True,
                     "vault_ansible_user": "synthetic-ssh-user", "vault_ansible_password": "synthetic-ssh-secret",
                     "ansible_python_interpreter": sys.executable}
        fixture = self.root / "play.yml"
        fixture.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                                          "vars": variables, "tasks": tasks}], sort_keys=False))
        config = self.root / "ansible.cfg"
        config.write_text("[defaults]\nstdout_callback=default\nretry_files_enabled=False\n")
        environment = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                           ANSIBLE_LOCAL_TEMP=str(self.root / "local"), ANSIBLE_REMOTE_TEMP=str(self.root / "remote"))
        result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                                cwd=self.root, env=environment, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        for secret in (BEARER, MANAGEMENT, PASSWORD, "synthetic-ssh-secret"):
            self.assertNotIn(secret, output)
        return result, output

    def create_and_check(self):
        result, output = self.run_tasks()
        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(self.state["created"], 1)
        self.assertEqual(self.state["deleted"], [])
        record = json.loads(self.token_file.read_text())
        self.assertEqual(record["token"], BEARER)
        self.assertEqual((record["target"], record["username"], record["scope"]), (self.target, "admin", "write"))
        self.assertEqual(self.storage.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.token_file.stat().st_mode & 0o777, 0o600)

    def test_creation_and_rerun_preserve_the_recoverable_target_token(self):
        self.create_and_check()
        original = self.token_file.read_bytes()
        result, output = self.run_tasks()
        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(self.state["created"], 1)
        self.assertEqual(self.state["deleted"], [])
        self.assertEqual(self.token_file.read_bytes(), original)

    def test_manual_token_is_preserved_and_the_missing_copy_is_reported(self):
        self.state["tokens"] = [{"id": 44, "description": "MCP admin token", "user": 1,
                                 "scope": "write", "application": None}]
        result, output = self.run_tasks()
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("cannot be recovered through the API", output)
        self.assertEqual(self.state["created"], 0)
        self.assertEqual(self.state["deleted"], [])
        self.assertFalse(self.token_file.exists())

    def test_save_failure_revokes_only_an_unsaved_new_token(self):
        for failure, unknown, deleted in (("before", False, [101]), ("after", False, []), ("before", True, [])):
            with self.subTest(failure=failure, unknown=unknown):
                self.state.update(tokens=[], created=0, deleted=[])
                self.token_file.unlink(missing_ok=True)
                result, output = self.run_tasks(save_failure=failure, unknown_save=unknown)
                self.assertNotEqual(result.returncode, 0, output)
                self.assertEqual(self.state["deleted"], deleted, output)

    def test_invalid_saved_access_fails_without_rotation(self):
        self.create_and_check()
        record = json.loads(self.token_file.read_text())
        cases = [
            ("target", "https://unrelated.example.invalid"),
            ("username", "unexpected-user"),
            ("scope", "read"),
            ("id", 999),
            ("token", "synthetic-wrong-bearer"),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                changed = dict(record, **{field: value})
                self.token_file.write_text(json.dumps(changed))
                result, output = self.run_tasks()
                self.assertNotEqual(result.returncode, 0, output)
                self.assertEqual(self.state["created"], 1)
                self.assertEqual(self.state["deleted"], [])
        self.token_file.write_text(json.dumps(record))
        self.state["expired"] = True
        result, output = self.run_tasks()
        self.assertNotEqual(result.returncode, 0, output)
        self.assertEqual(self.state["created"], 1)
        self.assertEqual(self.state["deleted"], [])

    def test_wrong_existing_scope_or_duplicate_tokens_fail_without_mutation(self):
        item = {"id": 44, "description": "MCP admin token", "user": 1, "scope": "read", "application": None}
        for tokens in ([item], [dict(item, scope="write"), dict(item, id=45, scope="write")]):
            with self.subTest(tokens=tokens):
                self.state["tokens"] = tokens
                result, output = self.run_tasks()
                self.assertNotEqual(result.returncode, 0, output)
                self.assertEqual(self.state["created"], 0)
                self.assertEqual(self.state["deleted"], [])

    def test_expired_manual_token_fails_without_creating_a_replacement(self):
        self.state["tokens"] = [{"id": 44, "description": "MCP admin token", "user": 1,
                                 "scope": "write", "application": None,
                                 "expires": "2000-01-01T00:00:00.123456Z"}]
        result, output = self.run_tasks()
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn("MCP access needs review", output)
        self.assertEqual(self.state["created"], 0)
        self.assertEqual(self.state["deleted"], [])
        self.assertFalse(self.token_file.exists())

    def test_base_provisions_persistent_mcp_after_final_login_and_preserves_run_cleanup(self):
        source = yaml.safe_load((ROOT / "04-aap-config.yml").read_text())[0]
        configured = next(task for task in source["pre_tasks"] if "block" in task)
        names = [task["name"] for task in configured["block"]]
        self.assertLess(names.index("Verify the configured administrator password after applying base"),
                        names.index("Prepare persistent administrator MCP access"))
        cleanup = configured["always"][0]["block"][0]["ansible.builtin.uri"]
        self.assertIn("cac_gateway_token.json.id", cleanup["url"])
        self.assertNotIn("cac_mcp_created", cleanup["url"])


if __name__ == "__main__":
    unittest.main()
