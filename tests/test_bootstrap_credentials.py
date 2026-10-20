"""Exercise actual bootstrap tasks against an isolated Controller API."""

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
from urllib.parse import parse_qs, urlsplit

try:
    import yaml
except ImportError:
    yaml = None


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class BootstrapCredentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        roots = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
        if not any((Path(root) / "ansible_collections/ansible/controller").is_dir() for root in roots if root):
            raise unittest.SkipTest("requires installed ansible.controller")
        cls.state = {}

        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, status, body):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("X-API-Product-Version", "4.8.11")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def do_GET(self):
                parsed = urlsplit(self.path)
                kind = parsed.path.rstrip("/").split("/")[-1]
                if kind == "me":
                    rows = [{"id": 1, "username": "synthetic-user"}]
                elif kind == "organizations":
                    rows = [{"id": 1, "name": "Synthetic organization"}]
                elif kind in ("credential_types", "credentials"):
                    rows = cls.state[kind]
                    query = parse_qs(parsed.query)
                    for key in ("name", "organization", "credential_type"):
                        if key in query:
                            rows = [row for row in rows if str(row.get(key)) == query[key][0]]
                else:
                    return self.respond(404, {})
                self.respond(200, {"count": len(rows), "results": rows, "next": None, "previous": None})

            def do_POST(self):
                kind = urlsplit(self.path).path.rstrip("/").split("/")[-1]
                if kind not in ("credential_types", "credentials"):
                    return self.respond(404, {})
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                cls.state["writes"].append((kind, copy.deepcopy(payload)))
                item = dict(payload, id=len(cls.state[kind]) + 20)
                item["url"] = "/api/controller/v2/" + kind + "/" + str(item["id"]) + "/"
                if kind == "credential_types":
                    item["managed"] = False
                else:
                    credential_type = next(row for row in cls.state["credential_types"]
                                           if row["id"] == payload["credential_type"])
                    item["summary_fields"] = {"organization": {"name": "Synthetic organization"},
                                              "credential_type": {"name": credential_type["name"]}}
                    item["inputs"] = {key: value if key == "vault_id" else "$encrypted$"
                                      for key, value in payload["inputs"].items()}
                cls.state[kind].append(item)
                self.respond(201, item)

            def do_PATCH(self):
                cls.state["unexpected_patch"] = True
                self.respond(400, {"detail": "A rerun must preserve existing secrets"})

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
        self.state.update(credential_types=[{"id": 8, "name": "Vault", "kind": "vault", "managed": True}],
                          credentials=[], writes=[], unexpected_patch=False)
        self.variables = {
            "aap_hostname": self.target, "aap_token": "synthetic-management-secret", "aap_validate_certs": True,
            "debug_logging": True, "pah_base": {"organization": "Synthetic organization"},
            "cac_bootstrap_git_credentials": {key: {"token": "synthetic-" + key + "-secret"}
                                              for key in ("base", "assistant_team", "windows_disconnected", "orchestrator")},
            "cac_bootstrap_vault_credentials": {"cac": {"name": "Synthetic CaC vault", "vault_id": "cac",
                                                         "vault_password": "synthetic-vault-secret"}},
        }

    def run_tasks(self, variables=None):
        with tempfile.TemporaryDirectory(prefix="bootstrap-credential-test-") as directory:
            root = Path(directory)
            (root / "ansible.cfg").write_text("[defaults]\nstdout_callback=default\nretry_files_enabled=False\n")
            fixture = root / "play.yml"
            fixture.write_text(yaml.safe_dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": variables if variables is not None else self.variables,
                "tasks": [{"ansible.builtin.include_tasks": str(ROOT / "tasks/bootstrap-credentials.yml")}],
            }], sort_keys=False))
            environment = dict(os.environ, ANSIBLE_CONFIG=str(root / "ansible.cfg"), ANSIBLE_NOCOLOR="1",
                               ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                                    env=environment, cwd=root, capture_output=True, text=True, timeout=75)
            output = result.stdout + result.stderr
            for secret in ("synthetic-management-secret", "synthetic-vault-secret", *[
                item["token"] for item in self.variables["cac_bootstrap_git_credentials"].values()]):
                self.assertNotIn(secret, output)
            return result, output

    def test_creation_and_rerun_preserve_all_five_secrets(self):
        result, output = self.run_tasks()
        self.assertEqual(result.returncode, 0, output)
        created = [body for kind, body in self.state["writes"] if kind == "credentials"]
        self.assertEqual(len(created), 5)
        self.assertEqual({body["inputs"]["token"] for body in created if "token" in body["inputs"]},
                         {item["token"] for item in self.variables["cac_bootstrap_git_credentials"].values()})
        self.assertEqual(next(body for body in created if "vault_password" in body["inputs"])["inputs"]["vault_id"], "cac")
        custom = next(row for row in self.state["credential_types"] if row["name"] == "Cac_git_token_type")
        self.assertEqual(custom["injectors"], {"env": {"CAC_GIT_TOKEN": "{{ token }}"}})
        self.state["writes"].clear()
        result, output = self.run_tasks()
        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(self.state["writes"], [])
        self.assertFalse(self.state["unexpected_patch"])

    def test_incomplete_bootstrap_is_rejected_before_api_mutation(self):
        del self.variables["cac_bootstrap_git_credentials"]["orchestrator"]
        result, output = self.run_tasks()
        self.assertNotEqual(result.returncode, 0, output)
        self.assertEqual(self.state["writes"], [])

    def test_unrelated_existing_type_is_preserved_and_rejected(self):
        self.state["credential_types"].append({"id": 12, "name": "Cac_git_token_type", "kind": "cloud",
                                                "managed": False, "inputs": {}, "injectors": {"env": {"UNRELATED": "value"}}})
        result, output = self.run_tasks()
        self.assertNotEqual(result.returncode, 0, output)
        self.assertEqual(self.state["writes"], [])

    def test_absent_bootstrap_remains_optional_for_generic_base(self):
        variables = {key: value for key, value in self.variables.items() if not key.startswith("cac_bootstrap_")}
        result, output = self.run_tasks(variables)
        self.assertEqual(result.returncode, 0, output)
        self.assertEqual(self.state["writes"], [])


if __name__ == "__main__":
    unittest.main()
