"""Exercise installer replacement and target-scoped native registry timeout updates."""

import copy
from contextlib import contextmanager
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

import yaml


ROOT = Path(__file__).resolve().parents[1]
SECRET = "synthetic-registry-management-secret"


def collection_root():
    candidates = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
    candidates.append("/home/aaptra/codex-wd/tools/aap-cac-export/collections")
    return next((str(Path(p)) for p in candidates if p and
                 (Path(p) / "ansible_collections/ansible/platform/plugins/modules/route.py").is_file()), None)


@unittest.skipUnless(importlib.util.find_spec("ansible"), "requires installed Ansible")
class HubUploadTimeouts(unittest.TestCase):
    def run_play(self, directory, tasks, variables):
        directory = Path(directory)
        config = directory / "ansible.cfg"
        config.write_text("[defaults]\nretry_files_enabled=False\n")
        play = directory / "play.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "vars": variables, "tasks": tasks,
        }], sort_keys=False))
        env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                   ANSIBLE_LOCAL_TEMP=str(directory / "local"),
                   ANSIBLE_REMOTE_TEMP=str(directory / "remote"))
        if collection_root():
            env["ANSIBLE_COLLECTIONS_PATH"] = collection_root()
        return subprocess.run(
            [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
        )

    def test_installer_replaces_the_old_timeout_and_rerun_is_idempotent(self):
        plays = yaml.safe_load((ROOT / "03-aap-install.yml").read_text())
        block = next(task for task in plays[-1]["tasks"] if task.get("name") == "Start a new AAP installation")
        self.assertEqual(block["when"], "aap_installer_resume_job_id is not defined")
        task = next(task for task in block["block"] if task["name"] ==
                    "Set the supported Hub worker timeout in installer inventory")
        with tempfile.TemporaryDirectory(prefix="hub-installer-timeout-") as directory:
            inventory = Path(directory) / "fixture" / "inventory"
            inventory.parent.mkdir()
            inventory.write_text("[all:vars]\ncontroller_gunicorn_timeout=10\n hub_gunicorn_timeout = 10\n")
            variables = dict(yaml.safe_load((ROOT / "vars/main.yml").read_text()),
                             installer_extract_dir=directory, installer_dir_name="fixture")
            first = self.run_play(directory, [task], variables)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(inventory.read_text(),
                             "[all:vars]\ncontroller_gunicorn_timeout=10\nhub_gunicorn_timeout=200\n")
            second = self.run_play(directory, [task], variables)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("changed=0", second.stdout)

    @contextmanager
    def registry_fixture(self):
        if not collection_root():
            self.skipTest("requires existing ansible.platform route action")
        plays = yaml.safe_load((ROOT / "04-aap-config.yml").read_text())
        base = next(task["block"] for task in plays[0]["pre_tasks"] if task.get("name") ==
                    "Retrieve and load the encrypted shared configuration")
        task = next(task for task in base if task.get("name") ==
                    "Persist upload timeouts only on the native Hub registry route")
        route = {"id": 91, "name": "hub container registry", "description": "Native registry",
                 "gateway_path": "/v2/", "service_path": "/v2/", "service_cluster": 73,
                 "http_port": 31, "service_port": 8444, "is_service_https": True,
                 "enable_gateway_auth": True, "enable_mtls": False, "is_internal_route": False,
                 "reject_failed_basic_auth": False, "node_tags": "",
                 "request_timeout_seconds": None, "idle_timeout_seconds": None}
        other = dict(route, id=92, name="hub ui", gateway_path="/ui/", service_path="/ui/")
        state = {}

        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, status, body):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("X-API-Version", "1")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def do_GET(self):
                path = urlsplit(self.path)
                if self.headers.get("Authorization") != "Bearer " + SECRET:
                    return self.respond(401, {"detail": "Synthetic authentication required"})
                if path.path == "/":
                    # The native platform SDK validates its token at the base URL.
                    return self.respond(200, {})
                if path.path == "/api/gateway/v1/ping/":
                    return self.respond(200, {"version": "2.7"})
                if path.path == "/api/gateway/v1/settings/all/":
                    return self.respond(200, {"request_timeout": 30, "idle_timeout": 15})
                if path.path == "/api/gateway/v1/routes/":
                    rows = [state["route"], state["other"]]
                    if state.get("duplicate"):
                        rows.append(dict(state["route"], id=93))
                    query = parse_qs(path.query)
                    if "name" in query:
                        wanted = query["name"][0]
                        rows = [row for row in rows if wanted in (row["name"], str(row["id"]))]
                    # Gateway list responses can hide populated timeout fields.
                    rows = [dict(row, request_timeout_seconds=None, idle_timeout_seconds=None) for row in rows]
                    return self.respond(200, {"count": len(rows), "results": rows,
                                              "next": "/unread-page/" if state.get("next") else None})
                if path.path == "/api/gateway/v1/routes/91/":
                    return self.respond(200, state["route"])
                if path.path == "/api/gateway/v1/service_clusters/73/":
                    return self.respond(200, {"id": 73, "name": state.get("cluster_name", "hub"), "service_type": 55})
                if path.path == "/api/gateway/v1/service_types/55/":
                    return self.respond(200, {"id": 55, "name": state.get("type_name", "hub")})
                state["unexpected"].append(("GET", path.path))
                self.respond(404, {"detail": "Unexpected synthetic endpoint"})

            def do_PATCH(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path != "/api/gateway/v1/routes/91/":
                    state["unexpected"].append(("PATCH", self.path))
                    return self.respond(400, {"detail": "Wrong receiver route"})
                if self.headers.get("Authorization") != "Bearer " + SECRET:
                    return self.respond(401, {})
                changed = {key for key, value in body.items() if state["route"].get(key) != value}
                state["patches"].append(changed)
                state["route"].update(body)
                self.respond(200, state["route"])

            def do_POST(self):
                state["unexpected"].append(("POST", self.path))
                self.respond(400, {"detail": "Creating a route is outside the operation"})

        server = ThreadingHTTPServer(("127.0.0.1", 0), API)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        defaults = yaml.safe_load((ROOT / "vars/main.yml").read_text())
        variables = dict(defaults, aap_hostname="http://127.0.0.1:" + str(server.server_port),
                         aap_token=SECRET, aap_validate_certs=True)
        try:
            with tempfile.TemporaryDirectory(prefix="hub-registry-timeout-") as directory:
                yield task, state, variables, directory, route, other
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_native_route_uses_receiver_ids_preserves_security_and_is_idempotent(self):
        if not importlib.util.find_spec("requests"):
            self.skipTest("native ansible.platform manager requires existing requests")
        with self.registry_fixture() as (task, state, variables, directory, route, other):
            state.update(route=copy.deepcopy(route), other=copy.deepcopy(other), patches=[], unexpected=[])
            for attempt in range(2):
                result = self.run_play(directory, [task], variables)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                self.assertNotIn(SECRET, output)
            self.assertEqual(state["patches"], [{"request_timeout_seconds", "idle_timeout_seconds"}])
            self.assertEqual(state["other"], other)
            self.assertEqual(state["unexpected"], [])

    def test_wrong_registry_route_or_hub_ownership_stops_before_any_mutation(self):
        with self.registry_fixture() as (task, state, variables, directory, route, other):
            for scenario in ("service_path", "enable_gateway_auth", "is_internal_route",
                             "cluster_name", "type_name", "duplicate", "next"):
                with self.subTest(scenario=scenario):
                    state.clear()
                    state.update(route=copy.deepcopy(route), other=copy.deepcopy(other), patches=[], unexpected=[])
                    if scenario == "service_path":
                        state["route"][scenario] = "/unrelated/"
                    elif scenario == "enable_gateway_auth":
                        state["route"][scenario] = False
                    elif scenario == "is_internal_route":
                        state["route"][scenario] = True
                    elif scenario in ("cluster_name", "type_name"):
                        state[scenario] = "controller"
                    else:
                        state[scenario] = True
                    result = self.run_play(directory, [task], variables)
                    output = result.stdout + result.stderr
                    self.assertNotEqual(result.returncode, 0, output)
                    self.assertNotIn(SECRET, output)
                    self.assertEqual(state["patches"], [])
                    self.assertEqual(state["other"], other)
                    self.assertEqual(state["unexpected"], [])


if __name__ == "__main__":
    unittest.main()
