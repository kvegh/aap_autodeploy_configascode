"""Run the importer's real Vault guards and cleanup without contacting AAP."""

import copy
import json
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


PLAYBOOK = Path(__file__).resolve().parents[1] / "deploy-orchestrator-demo.yml"


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class OrchestratorConfigurationTests(unittest.TestCase):
    def test_interpreter_expression_survives_cop_import_and_resolves_at_job_runtime(self):
        roots = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
        roles = next((Path(root) / "ansible_collections/infra/aap_configuration/roles"
                      for root in roots if root and (
                          Path(root) / "ansible_collections/infra/aap_configuration/roles/controller_hosts/tasks/main.yml"
                      ).is_file()), None)
        if roles is None:
            self.skipTest("requires installed infra.aap_configuration")

        from ansible.plugins.loader import init_plugin_loader
        from ansible.utils.collection_loader import AnsibleCollectionConfig
        from ansible.parsing.dataloader import DataLoader
        from ansible.template import Templar
        from ansible.module_utils.common.validation import check_type_dict

        if AnsibleCollectionConfig.collection_finder is None:
            init_plugin_loader()
        wildcard = yaml.safe_load((roles / "dispatch/tasks/include_wildcard_vars.yml").read_text())[0]
        host_tasks = yaml.safe_load((roles / "controller_hosts/tasks/main.yml").read_text())
        host_parameters = next(task["ansible.controller.host"] for block in host_tasks
                               for task in block.get("block", []) if "ansible.controller.host" in task)
        loader = DataLoader()
        expression = "{{ ansible_playbook_python }}"
        for tag in ("", "!unsafe "):
            with self.subTest(literal=bool(tag)):
                data = loader.load(
                    "controller_hosts_orchestrator:\n"
                    "  - name: localhost\n"
                    "    inventory: Synthetic inventory\n"
                    "    variables:\n"
                    "      ansible_connection: local\n"
                    "      ansible_python_interpreter: " + tag + '"' + expression + '"\n')
                variables = {**data, **wildcard["vars"],
                             "aap_configuration_all_vars": ["controller_hosts"],
                             "item": "controller_hosts_orchestrator",
                             "ansible_playbook_python": "/import/bin/python"}
                templar = Templar(loader=loader, variables=variables)
                combined = {templar.template(key): value for key, value in
                            templar.template(wildcard["ansible.builtin.set_fact"]).items()}
                variables.update(combined)
                variables.update({"__controller_host_item": combined["controller_hosts"][0],
                                  "aap_hostname": "https://aap.example.invalid",
                                  "aap_token": "synthetic-gateway-token", "aap_validate_certs": True,
                                  "controller_configuration_host_enforce_defaults": False,
                                  "omit": "__omit__"})
                rendered = Templar(loader=loader, variables=variables).template(host_parameters)
                # Use the real module argument conversion and the API JSON boundary.
                saved = json.loads(json.dumps(check_type_dict(rendered["variables"])))
                self.assertEqual(saved["ansible_python_interpreter"], expression if tag else "/import/bin/python")
                runtime = Templar(loader=loader, variables={
                    "ansible_playbook_python": "/runtime/bin/python"}).template(saved)
                self.assertEqual(runtime["ansible_python_interpreter"],
                                 "/runtime/bin/python" if tag else "/import/bin/python")

    def run_tasks(self, root, tasks, variables, vault_password=None):
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
        environment = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                           ANSIBLE_LOCAL_TEMP=str(root / "local"),
                           ANSIBLE_REMOTE_TEMP=str(root / "remote"))
        result = subprocess.run(command, cwd=root, env=environment,
                                capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        self.assertNotIn("synthetic-registry-password", output)
        self.assertNotIn("synthetic-gateway-token", output)
        return result.returncode, output

    def test_vault_loading_rejects_plaintext_incomplete_or_executable_configurations(self):
        from ansible.parsing.vault import VaultLib, VaultSecret

        source = yaml.safe_load(PLAYBOOK.read_text())[0]
        selected = {
            "Read the encrypted Orchestrator configuration",
            "Require a fully Vault-encrypted Orchestrator configuration",
            "Decrypt and load the Orchestrator configuration with the attached Vault credentials",
            "Require a reviewed and complete Orchestrator configuration",
            "Require the protected Orchestrator registry inputs",
            "Require configuration without job launches or schedules",
        }
        guards = [task for task in source["pre_tasks"][-1]["block"]
                  if task["name"] in selected]
        self.assertEqual(len(guards), len(selected))
        complete = {
            "orchestrator_capture_readiness": {
                "aap_object_definitions_complete": True,
                "static_secrets_recovered": True,
                "portable_to_new_aap": True,
                "remaining_review": [],
                # Functional OCP execution is separate from importing definitions.
                "tested_on_clean_aap": False,
            },
            "orchestrator_registry_username": "synthetic-registry-user",
            "orchestrator_registry_password": "synthetic-registry-password",
            "controller_schedules_orchestrator": [],
        }
        cases = [
            ("complete encrypted capture", {}, (), True, True),
            ("plaintext capture", {}, (), False, False),
            ("missing readiness", {}, ("orchestrator_capture_readiness",), True, False),
            ("incomplete objects", {"orchestrator_capture_readiness": {
                **complete["orchestrator_capture_readiness"], "aap_object_definitions_complete": False}}, (), True, False),
            ("readiness string", {"orchestrator_capture_readiness": {
                **complete["orchestrator_capture_readiness"], "portable_to_new_aap": "true"}}, (), True, False),
            ("review outstanding", {"orchestrator_capture_readiness": {
                **complete["orchestrator_capture_readiness"], "remaining_review": ["Review capture"]}}, (), True, False),
            ("missing password", {}, ("orchestrator_registry_password",), True, False),
            ("masked password", {"orchestrator_registry_password": "$encrypted$"}, (), True, False),
            ("job launch", {"controller_launch_jobs_orchestrator": [{"name": "Synthetic job"}]}, (), True, False),
            ("workflow launch", {"controller_workflow_launch_jobs": [{"name": "Synthetic workflow"}]}, (), True, False),
            ("schedule", {"controller_schedules_orchestrator": [{"name": "Synthetic schedule"}]}, (), True, False),
        ]
        with tempfile.TemporaryDirectory(prefix="orchestrator-cac-guards-") as directory:
            root = Path(directory)
            capture = root / "repository" / "cac" / "orchestrator.yml"
            capture.parent.mkdir(parents=True)
            password = root / "vault-password"
            password.write_text("synthetic-vault-password\n")
            password.chmod(0o600)
            secret = VaultSecret(b"synthetic-vault-password")
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
            with tempfile.TemporaryDirectory(prefix="orchestrator-cac-cleanup-") as directory:
                root = Path(directory)
                for token_created, response in [(True, 204), (True, 500), (False, 204)]:
                    with self.subTest(token_created=token_created, revoke_response=response):
                        workspace = root / "checkout"
                        workspace.mkdir()
                        (workspace / "git-askpass").write_text("synthetic helper")
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


if __name__ == "__main__":
    unittest.main()
