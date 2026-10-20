"""Exercise initial-password bootstrap and configured-password reruns offline."""

import base64
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

try:
    import yaml
except ImportError:
    yaml = None


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class GatewayBaseLoginTests(unittest.TestCase):
    def test_bootstrap_and_reruns_use_the_expected_password_without_logging_secrets(self):
        source = yaml.safe_load((ROOT / "tasks/gateway-base-login.yml").read_text())
        requests = []
        scenario = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                encoded = self.headers.get("Authorization", "").removeprefix("Basic ")
                supplied = base64.b64decode(encoded).decode().split(":", 1)[1]
                requests.append(supplied)
                status = scenario.get("status", 201 if supplied == scenario["current"] else 401)
                data = {"id": 73, "token": "synthetic-gateway-token"} if status == 201 else {"detail": "Rejected"}
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old = "synthetic-installer-secret"
        new = "synthetic-configured-secret"
        cases = [
            ("first rotation", new, old, None, True, [new, old]),
            ("configured-password rerun", new, new, None, True, [new]),
            ("legacy installer-only configuration", None, old, None, True, [old]),
            ("neither password accepted", new, "synthetic-other-secret", None, False, [new, old]),
            ("server failure does not trigger installer access", new, old, 503, False, [new]),
            ("forbidden login does not trigger installer access", new, old, 403, False, [new]),
            ("empty configured password", "", old, None, False, []),
        ]
        try:
            with tempfile.TemporaryDirectory(prefix="gateway-base-login-") as directory:
                root = Path(directory)
                bundle = root / "ansible-automation-platform-containerized-setup-bundle-test-x86_64"
                bundle.mkdir()
                inventory = bundle / "inventory"
                for name, desired, current, status_override, succeeds, expected in cases:
                    with self.subTest(name=name):
                        requests.clear()
                        scenario.clear()
                        scenario["current"] = current
                        if status_override:
                            scenario["status"] = status_override
                        # A rerun must succeed even when the old installer is unavailable.
                        if desired == current or status_override or desired == "":
                            inventory.unlink(missing_ok=True)
                        else:
                            inventory.write_text("gateway_admin_password='" + old + "'\n")
                        tasks = copy.deepcopy(source)
                        bootstrap = next(task for task in tasks if "block" in task)
                        reader = bootstrap["block"][0]
                        # Keep the real installer parser; execute it locally in this fixture.
                        reader["delegate_to"] = "localhost"
                        reader["vars"] = {"ansible_connection": "local", "ansible_become": False}
                        tasks.append({"name": "Check the selected token", "ansible.builtin.assert": {
                            "that": ["cac_gateway_token.json.id == 73", "cac_gateway_token.json.token == 'synthetic-gateway-token'",
                                     "cac_gateway_login_password == expected_current_password",
                                     "aap_password | default(none) == expected_desired_password"]},
                            "no_log": True})
                        variables = {
                            "aap_hostname": "http://127.0.0.1:" + str(server.server_port),
                            "aap_username": "test-user", "aap_validate_certs": True,
                            "installer_extract_dir": str(root), "aap_version": "test",
                            "expected_current_password": current,
                            "expected_desired_password": desired,
                        }
                        if desired is not None:
                            variables["aap_password"] = desired
                        fixture = root / "play.yml"
                        fixture.write_text(yaml.safe_dump([{
                            "hosts": "localhost", "connection": "local", "gather_facts": False,
                            "vars": variables, "tasks": tasks}], sort_keys=False))
                        config = root / "ansible.cfg"
                        config.write_text("[defaults]\nstdout_callback=default\nretry_files_enabled=False\n")
                        env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                                   ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"))
                        result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                                                env=env, cwd=root, capture_output=True, text=True, timeout=30)
                        output = result.stdout + result.stderr
                        for secret in (old, new, "synthetic-gateway-token"):
                            self.assertNotIn(secret, output)
                        self.assertEqual(result.returncode == 0, succeeds, output)
                        self.assertEqual(requests, expected, output)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
