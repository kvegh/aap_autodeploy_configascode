"""Exercise Assistant Team import guards and cleanup without contacting AAP."""

import copy
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
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


PLAYBOOK = Path(__file__).resolve().parents[1] / "deploy-assistant-team.yml"


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class AssistantTeamConfigurationTests(unittest.TestCase):
    def run_tasks(self, root, tasks, variables, vault_password=None, environment=None):
        config = root / "ansible.cfg"
        config.write_text("[defaults]\nstdout_callback = default\nretry_files_enabled = False\n")
        fixture = root / "play.yml"
        fixture.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "vars": variables, "tasks": tasks,
        }], sort_keys=False))
        command = [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,"]
        if vault_password:
            command += ["--vault-id", "cac@" + str(vault_password)]
        command.append(str(fixture))
        env = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                   ANSIBLE_LOCAL_TEMP=str(root / "local"),
                   ANSIBLE_REMOTE_TEMP=str(root / "remote"))
        env.update(environment or {})
        result = subprocess.run(command, cwd=root, env=env,
                                capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        self.assertNotIn("synthetic-private-secret", output)
        self.assertNotIn("synthetic-gateway-token", output)
        return result.returncode, output

    def test_vault_loading_requires_complete_core_with_only_encrypted_snapshots(self):
        from ansible.parsing.vault import VaultLib, VaultSecret

        source = yaml.safe_load(PLAYBOOK.read_text())[0]
        selected = {
            "Read the encrypted Assistant Team configuration",
            "Require a fully Vault-encrypted Assistant Team configuration",
            "Decrypt and load the Assistant Team configuration with the attached Vault credentials",
            "Require complete ordinary Assistant Team definitions and secrets",
            "Require protected ordinary deployment credentials",
            "Select the ordinary encrypted file credential",
            "Require exactly one ordinary encrypted file credential",
            "Require fully encrypted deployment and authentication snapshots",
            "Require configuration without job launches or schedules",
        }
        guards = [task for task in source["pre_tasks"][-1]["block"]
                  if task["name"] in selected]
        self.assertEqual(len(guards), len(selected))
        secret = VaultSecret(b"synthetic-vault-password")
        snapshot = VaultLib().encrypt(b"synthetic-private-secret", secret=secret).decode()
        snapshot_inputs = {key: snapshot for key in [
            "environment_vault", "fresh_test_vault", "retire_test_vault",
            "claude_auth_recovery_vault", "codex_auth_recovery_vault", "bootstrap_auth_vault",
        ]}
        complete = {
            "assistant_team_capture_readiness": {
                "ordinary_aap_objects_complete": True,
                "ordinary_deployment_configuration_ready": True,
                "static_secrets_complete": True,
                "external_encrypted_configuration_embedded": True,
                "unresolved_secrets": [],
                # Optional maintenance and functional tests are separate gates.
                "ready_for_deployment": False,
                "authentication_maintenance_ready_for_target": False,
            },
            "assistant_team_required_secrets": [],
            "assistant_team_authentication_maintenance": {
                "included_in_default_dispatch": False,
                "configuration": {"controller_templates": [{
                    "name": "Excluded maintenance", "extra_vars": "{{ intentionally_missing_maintenance_input }}"}]},
            },
            "controller_templates_assistant_team": [{"name": str(i)} for i in range(7)],
            "controller_credentials_assistant_team": [{"inputs": snapshot_inputs}],
            **{name: "synthetic-private-secret" for name in [
                "assistant_team_hypervisor_ssh_username", "assistant_team_hypervisor_ssh_private_key",
                "assistant_team_guest_ssh_username", "assistant_team_guest_ssh_password",
                "assistant_team_guest_become_password", "assistant_team_playbook_vault_password",
            ]},
        }
        cases = [
            ("core ready with optional maintenance pending", {}, (), True, True),
            ("plaintext outer file", {}, (), False, False),
            ("missing readiness", {}, ("assistant_team_capture_readiness",), True, False),
            ("incomplete ordinary objects", {"assistant_team_capture_readiness": {
                **complete["assistant_team_capture_readiness"], "ordinary_aap_objects_complete": False}}, (), True, False),
            ("string readiness", {"assistant_team_capture_readiness": {
                **complete["assistant_team_capture_readiness"], "static_secrets_complete": "true"}}, (), True, False),
            ("unresolved secret", {"assistant_team_capture_readiness": {
                **complete["assistant_team_capture_readiness"], "unresolved_secrets": ["Missing input"]}}, (), True, False),
            ("required secret", {"assistant_team_required_secrets": ["Missing input"]}, (), True, False),
            ("missing runtime secret", {}, ("assistant_team_playbook_vault_password",), True, False),
            ("masked runtime secret", {"assistant_team_guest_ssh_password": "$encrypted$"}, (), True, False),
            ("missing core template", {"controller_templates_assistant_team": [{"name": "One"}]}, (), True, False),
            ("maintenance in default templates", {"controller_templates_assistant_team": [
                *complete["controller_templates_assistant_team"], {"name": "Excluded maintenance"}]}, (), True, False),
            ("no snapshot credential", {"controller_credentials_assistant_team": []}, (), True, False),
            ("plaintext embedded snapshot", {"controller_credentials_assistant_team": [{
                "inputs": {**snapshot_inputs, "bootstrap_auth_vault": "synthetic-private-secret"}}]}, (), True, False),
            ("job launch", {"controller_launch_jobs_assistant_team": [{"name": "Synthetic job"}]}, (), True, False),
            ("workflow launch", {"controller_workflow_launch_jobs": [{"name": "Synthetic workflow"}]}, (), True, False),
            ("schedule", {"controller_schedules_assistant_team": [{"name": "Synthetic schedule"}]}, (), True, False),
        ]
        with tempfile.TemporaryDirectory(prefix="assistant-cac-guards-") as directory:
            root = Path(directory)
            capture = root / "repository" / "vaults" / "cac" / "assistant_team_vault.yml"
            capture.parent.mkdir(parents=True)
            password = root / "vault-password"
            password.write_text("synthetic-vault-password\n")
            password.chmod(0o600)
            for name, overrides, missing, encrypted, succeeds in cases:
                with self.subTest(name=name):
                    variables = copy.deepcopy(complete)
                    variables.update(overrides)
                    for variable in missing:
                        variables.pop(variable)
                    data = yaml.safe_dump(variables).encode()
                    capture.write_bytes(VaultLib().encrypt(data, secret=secret, vault_id="cac")
                                        if encrypted else data)
                    capture.chmod(0o600)
                    status, output = self.run_tasks(root, guards, {
                        "cac_workspace": {"path": str(root)}, "debug_logging": True,
                    }, password)
                    self.assertEqual(status == 0, succeeds, output)

    def test_repository_guard_rejects_untrusted_or_embedded_credential_inputs(self):
        source = yaml.safe_load(PLAYBOOK.read_text())[0]
        guard = next(task for task in source["pre_tasks"]
                     if task["name"] == "Require a private configuration repository URL without embedded credentials")
        cases = [
            ("https://git.example.invalid/owner/repository.git", True),
            ("ssh://git@git.example.invalid/owner/repository.git", False),
            ("http://git.example.invalid/owner/repository.git", False),
            ("https://git:synthetic-private-secret@git.example.invalid/owner/repository.git", False),
            ("https://git@git.example.invalid/owner/repository.git", False),
            ("https://git.example.invalid/owner/repository.git?secret=value", False),
            ("https://git.example.invalid/owner/repository.git#fragment", False),
            ("https://git.example.invalid/owner/repository .git", False),
        ]
        # Repository URL diagnostics must not expose malformed embedded secrets.
        with tempfile.TemporaryDirectory(prefix="assistant-cac-url-") as directory:
            for url, succeeds in cases:
                with self.subTest(url=url):
                    status, output = self.run_tasks(Path(directory), [guard], {"aap_config_repo_url": url})
                    self.assertEqual(status == 0, succeeds, output)

    def test_git_token_is_required_without_disclosing_it(self):
        source = yaml.safe_load(PLAYBOOK.read_text())[0]
        guard = next(task for task in source["pre_tasks"]
                     if task["name"] == "Require the injected CaC Git token")
        with tempfile.TemporaryDirectory(prefix="assistant-cac-git-token-") as directory:
            for token in ("", "synthetic-private-secret"):
                with self.subTest(token_present=bool(token)):
                    status, output = self.run_tasks(Path(directory), [guard], {},
                                                    environment={"CAC_GIT_TOKEN": token})
                    self.assertEqual(status == 0, bool(token), output)

    def test_failed_import_revokes_only_its_token_and_always_removes_workspace(self):
        source = yaml.safe_load(PLAYBOOK.read_text())[0]
        cleanup = source["pre_tasks"][-1]["always"]
        requests = []
        response_status = [204]

        class Handler(BaseHTTPRequestHandler):
            def do_DELETE(self):
                requests.append((self.path, self.headers.get("Authorization")))
                self.send_response(response_status[0])
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="assistant-cac-cleanup-") as directory:
                root = Path(directory)
                for token_created, response in [(True, 204), (True, 500), (False, 204)]:
                    with self.subTest(token_created=token_created, revoke_response=response):
                        workspace = root / "checkout"
                        workspace.mkdir()
                        response_status[0] = response
                        requests.clear()
                        variables = {
                            "aap_hostname": "http://127.0.0.1:" + str(server.server_port),
                            "aap_validate_certs": True,
                            "debug_logging": True,
                            "cac_workspace": {"path": str(workspace)},
                        }
                        if token_created:
                            variables["cac_gateway_token"] = {
                                "json": {"id": 73, "token": "synthetic-gateway-token"}}
                        tasks = [{
                            "block": [{"ansible.builtin.fail": {"msg": "Synthetic import failure"}}],
                            "always": cleanup,
                        }]
                        status, output = self.run_tasks(root, tasks, variables)
                        self.assertNotEqual(status, 0, output)
                        self.assertFalse(workspace.exists(), output)
                        self.assertEqual(requests, [(
                            "/api/gateway/v1/tokens/73/", "Bearer synthetic-gateway-token")]
                            if token_created else [], output)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_lifecycle_ca_uses_installer_home_and_supports_reviewed_override(self):
        source = yaml.safe_load((PLAYBOOK.parent / "tasks" / "assistant-team-lifecycle.yml").read_text())[0]
        with tempfile.TemporaryDirectory(prefix="assistant-cac-ca-path-") as directory:
            for lifecycle, expected in [
                ({}, "/home/synthetic-installer/aap/tls/extracted/pem/directory-hash/ca-bundle.crt"),
                ({"ca_path": "/synthetic-reviewed/custom-ca.pem"}, "/synthetic-reviewed/custom-ca.pem"),
            ]:
                with self.subTest(override=bool(lifecycle)):
                    status, output = self.run_tasks(Path(directory), [{
                        "ansible.builtin.assert": {"that": ["cac_assistant_ca_path == expected_ca_path"]},
                        "vars": source["vars"],
                    }], {
                        "assistant_team_lifecycle": lifecycle,
                        "vault_ansible_user": "synthetic-ssh",
                        "vault_aap_install_user": "synthetic-installer",
                        "expected_ca_path": expected,
                    })
                    self.assertEqual(status, 0, output)

    def test_existing_service_password_is_verified_and_omitted_before_dispatch(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                wanted = 'Basic ' + base64.b64encode(b'synthetic-user:synthetic-private-secret').decode()
                valid = self.headers.get('Authorization') == wanted
                body = (b'{"results":[{"username":"synthetic-user","is_superuser":false,"is_platform_auditor":false}]}'
                        if valid else b'{"detail":"Rejected synthetic login"}')
                self.send_response(200 if valid else 401)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            source = yaml.safe_load((PLAYBOOK.parent / 'tasks/assistant-team-lifecycle.yml').read_text())[0]['block']
            existing = copy.deepcopy(next(task for task in source if task['name'] ==
                                          'Prove control and preserve the password of an existing service user'))
            existing['block'][0].pop('vars')
            existing['block'][0]['delegate_to'] = 'localhost'
            with tempfile.TemporaryDirectory(prefix='assistant-existing-password-') as directory:
                root = Path(directory)
                marker = root / 'definitions-updated'
                for count, password, succeeds in [
                    (1, 'synthetic-private-secret', True),
                    (1, 'wrong-synthetic-password', False),
                    (0, 'synthetic-private-secret', True),
                ]:
                    with self.subTest(existing_user=bool(count), authenticated=succeeds):
                        marker.unlink(missing_ok=True)
                        fixture = [{
                            'no_log': True,
                            'block': [existing, {
                                'name': 'Inspect the payload passed to the subsequent CoP dispatch',
                                'ansible.builtin.assert': {'that': [
                                    'aap_user_accounts | length == 1',
                                    "aap_user_accounts[0].username == 'synthetic-user'",
                                    "aap_user_accounts[0].email == 'changed@example.invalid'",
                                    "('password' not in aap_user_accounts[0]) == (cac_assistant_existing_user.json.count == 1)",
                                ]},
                            }, {
                                'name': 'Simulate subsequent definition updates',
                                'ansible.builtin.copy': {'dest': str(marker), 'content': 'updated', 'mode': '0600'},
                            }],
                        }]
                        status, output = self.run_tasks(root, fixture, {
                            'aap_hostname': 'http://127.0.0.1:' + str(server.server_port),
                            'cac_assistant_existing_user': {'json': {'count': count}},
                            'assistant_team_lifecycle': {'username': 'synthetic-user'},
                            'assistant_team_inventory_service_password': password,
                            'cac_assistant_ca_path': '/etc/pki/tls/certs/ca-bundle.crt',
                            'aap_user_accounts': [{'username': 'synthetic-user',
                                                   'email': 'changed@example.invalid',
                                                   'password': 'synthetic-private-secret',
                                                   'update_secrets': False}],
                        })
                        self.assertEqual(status == 0, succeeds, output)
                        self.assertEqual(marker.exists(), succeeds, output)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_service_password_must_be_verified_before_any_inventory_grant(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                wanted = 'Basic ' + base64.b64encode(b'synthetic-user:synthetic-private-secret').decode()
                valid = self.headers.get('Authorization') == wanted
                body = (b'{"results":[{"username":"synthetic-user","is_superuser":false,"is_platform_auditor":false}]}'
                        if valid else b'{"detail":"Rejected synthetic login"}')
                self.send_response(200 if valid else 401)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            source = yaml.safe_load((PLAYBOOK.parent / 'tasks/assistant-team-lifecycle.yml').read_text())[0]['block']
            names = ['Verify the encrypted service password identifies this nonprivileged account',
                     'Require service account control before assigning any inventory role']
            tasks = [copy.deepcopy(next(task for task in source if task['name'] == name)) for name in names]
            tasks[0].pop('vars')
            tasks[0]['delegate_to'] = 'localhost'
            with tempfile.TemporaryDirectory(prefix='assistant-service-grant-') as directory:
                root = Path(directory)
                marker = root / 'grant-applied'
                for password, succeeds in [('synthetic-private-secret', True), ('wrong-synthetic-password', False)]:
                    with self.subTest(authenticated=succeeds):
                        marker.unlink(missing_ok=True)
                        fixture = [{
                            'no_log': True,
                            'block': [*tasks, {'name': 'Simulate the subsequent inventory grant',
                                              'ansible.builtin.copy': {'dest': str(marker), 'content': 'granted', 'mode': '0600'}}],
                        }]
                        status, output = self.run_tasks(root, fixture, {
                            'aap_hostname': 'http://127.0.0.1:' + str(server.server_port),
                            'assistant_team_lifecycle': {'username': 'synthetic-user'},
                            'assistant_team_inventory_service_password': password,
                            'cac_assistant_ca_path': '/etc/pki/tls/certs/ca-bundle.crt',
                        })
                        self.assertEqual(status == 0, succeeds, output)
                        self.assertEqual(marker.exists(), succeeds, output)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
