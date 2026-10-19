"""Exercise PAH setup guards and token persistence against a local fake API."""

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
TASKS = ROOT / "tasks"


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class PahBaseTests(unittest.TestCase):
    def run_play(self, variables, tasks):
        with tempfile.TemporaryDirectory(prefix="pah-base-test-") as directory:
            root = Path(directory)
            (root / "ansible.cfg").write_text("[defaults]\nretry_files_enabled = False\n")
            playbook = root / "play.yml"
            playbook.write_text(yaml.safe_dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": variables, "tasks": tasks,
            }], sort_keys=False))
            environment = dict(os.environ, ANSIBLE_CONFIG=str(root / "ansible.cfg"),
                               ANSIBLE_LOCAL_TEMP=str(root / "local"),
                               ANSIBLE_REMOTE_TEMP=str(root / "remote"), ANSIBLE_NOCOLOR="1")
            return subprocess.run(
                [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(playbook)],
                cwd=root, env=environment, capture_output=True, text=True, timeout=40,
            )

    def test_sync_and_public_source_fallback_are_rejected(self):
        names = ["rh-certified", "validated", "community"]
        credentials = [{"name": "PAH " + name, "repository": name} for name in names]
        complete = {
            "pah_base": {"organization": "Synthetic organization", "download_credentials": credentials},
            "aap_organizations_base": [{"name": "Synthetic organization", "galaxy_credentials":
                                        [item["name"] for item in credentials]}],
            "hub_collection_remotes_base": [{"name": name} for name in names],
            "hub_collection_repositories_base": [
                {"name": name, "remote": name, "sync": False, "update_repo": False,
                 "distribution": {"name": name, "state": "present"}} for name in names],
        }
        cases = [("safe", complete, True)]
        for field in ("sync", "update_repo"):
            changed = copy.deepcopy(complete)
            changed["hub_collection_repositories_base"][0][field] = True
            cases.append((field, changed, False))
        changed = copy.deepcopy(complete)
        changed["aap_organizations_base"][0]["galaxy_credentials"].append("Public Galaxy")
        cases.append(("public fallback", changed, False))
        changed = copy.deepcopy(complete)
        changed["pah_base"]["download_credentials"].reverse()
        cases.append(("wrong source order", changed, False))
        for name, variables, succeeds in cases:
            with self.subTest(name=name):
                result = self.run_play(variables, [{"ansible.builtin.include_tasks":
                                                    str(TASKS / "pah-base-validate.yml")}])
                self.assertEqual(result.returncode == 0, succeeds, result.stdout + result.stderr)

    def test_tokens_survive_reruns_and_failed_saves_are_cleaned_safely(self):
        roots = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
        if not any((Path(root) / "ansible_collections/ansible/controller").is_dir()
                   for root in roots if root):
            self.skipTest("requires installed ansible.controller")
        state = {"credentials": [], "tokens_created": 0, "tokens_deleted": [], "save_mode": "ok"}

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
                endpoint = urlsplit(self.path).path.rstrip("/").split("/")[-1]
                items = {
                    "credentials": state["credentials"],
                    "credential_types": [{"id": 3, "name": "Ansible Galaxy/Automation Hub API Token", "kind": "galaxy"}],
                    "organizations": [{"id": 1, "name": "Synthetic organization"}],
                    "me": [{"id": 1, "username": "synthetic-user"}],
                }.get(endpoint)
                if items is None:
                    self.respond(404, {"detail": "Unexpected test request"})
                else:
                    self.respond(200, {"count": len(items), "results": items, "next": None, "previous": None})

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path.endswith("/tokens/"):
                    if payload["scope"] != "read":
                        return self.respond(400, {"detail": "Expected read scope"})
                    state["tokens_created"] += 1
                    return self.respond(201, {"id": state["tokens_created"], "token": "synthetic-persistent-secret"})
                if self.path.endswith("/credentials/"):
                    if state["save_mode"] != "fail-before-save":
                        credential = dict(payload, id=1, url="/api/controller/v2/credentials/1/",
                                          inputs=dict(payload["inputs"], token="$encrypted$"),
                                          summary_fields={"organization": {"name": "Synthetic organization"},
                                                          "credential_type": {"kind": "galaxy"}})
                        state["credentials"].append(credential)
                    return self.respond(201 if state["save_mode"] == "ok" else 400,
                                        state["credentials"][0] if state["save_mode"] == "ok" else
                                        {"detail": "Synthetic interrupted credential save"})
                self.respond(404, {"detail": "Unexpected test request"})

            def do_DELETE(self):
                state["tokens_deleted"].append(int(self.path.rstrip("/").split("/")[-1]))
                self.respond(204, {})

        server = ThreadingHTTPServer(("127.0.0.1", 0), API)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        target = "http://127.0.0.1:" + str(server.server_port)
        variables = {
            "aap_hostname": target, "aap_token": "synthetic-management-secret",
            "aap_username": "synthetic-user", "aap_password": "synthetic-admin-secret",
            "aap_validate_certs": True, "debug_logging": True,
            "pah_base": {"organization": "Synthetic organization"},
            "cac_pah_credential": {"name": "Synthetic PAH credential", "repository": "rh-certified"},
            "cac_pah_repository_url": target + "/api/galaxy/content/rh-certified/",
        }
        tasks = [{"ansible.builtin.include_tasks": str(TASKS / "pah-download-credential.yml")}]
        try:
            for attempt in range(2):
                result = self.run_play(variables, tasks)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(state["tokens_created"], 1)
                self.assertEqual(state["tokens_deleted"], [])
                for secret in ("synthetic-persistent-secret", "synthetic-management-secret", "synthetic-admin-secret"):
                    self.assertNotIn(secret, result.stdout + result.stderr)
            for mode, deleted in (("fail-before-save", [2]), ("fail-after-save", [2])):
                state["credentials"] = []
                state["save_mode"] = mode
                result = self.run_play(variables, tasks)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(state["tokens_deleted"], deleted)
                self.assertNotIn("synthetic-persistent-secret", result.stdout + result.stderr)
            # URL drift stops before token generation or credential mutation.
            state["credentials"][0]["inputs"]["url"] = "https://unrelated.example.invalid/api/"
            result = self.run_play(variables, tasks)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(state["tokens_created"], 3)
            self.assertEqual(state["tokens_deleted"], [2])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
