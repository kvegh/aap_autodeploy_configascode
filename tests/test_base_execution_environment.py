"""Verify receiver-local base EE inputs and password-rotation boundaries offline."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
CURRENT = "synthetic-current-receiver-secret"
DESIRED = "synthetic-final-receiver-secret"
REDHAT = "synthetic-redhat-registry-secret"
DIGEST = "sha256:" + "a" * 64


def variables():
    return {
        "aap_default_execution_environment": "ee-proj-aap-cac-v2",
        "aap_hostname": "https://receiver.example.invalid:8448",
        "aap_username": "receiver-admin", "aap_password": DESIRED,
        "cac_gateway_login_password": CURRENT,
        "aap_registry_route_timeout": 600, "aap_hub_gunicorn_timeout": 200,
        "cac_registry_route_readback": {"json": {"request_timeout_seconds": 600, "idle_timeout_seconds": 600}},
        "controller_execution_environments_base": [
            {"name": "ee-proj-aap-cac-v2", "image": "source.example.invalid/reviewed-v2@" + DIGEST,
             "credential": "Project AAP CaC EE registry", "pull": "missing"},
            {"name": "Unrelated custom EE", "image": "other.example.invalid/custom:1", "credential": "Unrelated registry"},
        ],
        "controller_credentials_base": [
            {"name": "Project AAP CaC EE registry", "credential_type": "Container Registry", "inputs": {"verify_ssl": True}},
            {"name": "Unrelated registry", "credential_type": "Container Registry",
             "inputs": {"host": "other.example.invalid", "username": "another-user", "password": "synthetic-other-secret"}},
            {"name": "Red Hat registry", "credential_type": "Container Registry",
             "inputs": {"host": "registry.redhat.io", "username": "synthetic-redhat-user", "password": REDHAT, "verify_ssl": True}},
        ],
    }


class ReceiverExecutionEnvironment(unittest.TestCase):
    def run_case(self, values, worker=200, returned_registry="receiver.example.invalid:8448"):
        tasks = copy.deepcopy(yaml.safe_load((ROOT / "tasks/base-execution-environment.yml").read_text()))
        with tempfile.TemporaryDirectory(prefix="receiver-ee-fixture-") as directory:
            root = Path(directory)
            for task in tasks:
                if "ansible.builtin.include_vars" in task:
                    task["ansible.builtin.include_vars"]["file"] = str(ROOT / "execution-environment/build-vars.yml")
                if task.get("name") == "Resolve the actual receiver install-user UID for native rootless storage":
                    task.clear()
                    task.update({"name": "Supply the synthetic install-user UID", "ansible.builtin.set_fact": {
                        "aap_ee_receiver_uid": {"stdout": "1000"}}})
                if task.get("name") == "Inspect the receiver's running Hub API as its existing installer user":
                    task.clear()
                    task["name"] = "Supply the synthetic native Hub container observation"
                    task["ansible.builtin.set_fact"] = {"aap_ee_receiver_hub_api": {"stdout": json.dumps([
                        {"State": {"Running": True}, "Config": {"Cmd": ["gunicorn", "--timeout", str(worker)]}}
                    ])}}
                if task.get("name") == "Build and verify the image on the selected receiver through its pinned SSH route":
                    task["ansible.builtin.include_tasks"] = {"file": str(root / "build-stub.yml")}
            stub = [
                {"name": "Require actual receiver build authentication rather than the desired next password",
                 "ansible.builtin.assert": {"that": [
                     "aap_ee_registry == 'receiver.example.invalid:8448'",
                     "aap_ee_registry_username == 'receiver-admin'",
                     "aap_ee_registry_password == current_password",
                     "aap_ee_redhat_password == redhat_password",
                     "aap_ee_image_name == 'ee-proj-aap-cac-v2'",
                 ]}, "no_log": True},
                {"ansible.builtin.set_fact": {"aap_ee_build_result": {
                    "image": returned_registry + "/ee-proj-aap-cac-v2@" + DIGEST, "verified": True}}, "no_log": True},
            ]
            (root / "build-stub.yml").write_text(yaml.safe_dump(stub, sort_keys=False))
            tasks.append({"name": "Retain only the synthetic fixture result", "ansible.builtin.copy": {
                "content": "{{ {'environments': controller_execution_environments_base, 'credentials': controller_credentials_base} | to_json }}",
                "dest": str(root / "result.json"), "mode": "0600"}, "no_log": True})
            values = dict(values, current_password=CURRENT, redhat_password=REDHAT)
            play = root / "play.yml"
            play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                                            "vars": values, "tasks": tasks}], sort_keys=False))
            env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"),
                       ANSIBLE_NOCOLOR="1")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
            output = result.stdout + result.stderr
            for secret in (CURRENT, DESIRED, REDHAT):
                self.assertNotIn(secret, output)
            data = json.loads((root / "result.json").read_text()) if (root / "result.json").exists() else None
            return result.returncode, output, data

    def test_actual_build_login_and_final_pull_login_are_receiver_local(self):
        original = variables()
        code, output, result = self.run_case(original)
        self.assertEqual(code, 0, output)
        self.assertEqual(result["environments"][0]["image"], "receiver.example.invalid:8448/ee-proj-aap-cac-v2@" + DIGEST)
        self.assertEqual(result["environments"][1], original["controller_execution_environments_base"][1])
        self.assertEqual(result["credentials"][0]["inputs"], {"host": "receiver.example.invalid:8448",
                         "username": "receiver-admin", "password": DESIRED, "verify_ssl": True})
        self.assertEqual(result["credentials"][1:], original["controller_credentials_base"][1:])

    def test_old_hub_worker_timeout_blocks_before_build(self):
        code, _, result = self.run_case(variables(), worker=10)
        self.assertNotEqual(code, 0)
        self.assertIsNone(result)

    def test_shared_registry_credential_is_not_rebound(self):
        data = variables()
        data["controller_execution_environments_base"][1]["credential"] = "Project AAP CaC EE registry"
        code, _, result = self.run_case(data)
        self.assertNotEqual(code, 0)
        self.assertIsNone(result)

    def test_result_from_another_hub_is_refused(self):
        code, _, result = self.run_case(variables(), returned_registry="source.example.invalid")
        self.assertNotEqual(code, 0)
        self.assertIsNone(result)

    def test_default_build_precedes_dispatch_and_preserves_the_pinned_route(self):
        play = yaml.safe_load((ROOT / "04-aap-config.yml").read_text())[0]
        base = next(task["block"] for task in play["pre_tasks"] if task.get("name") ==
                    "Retrieve and load the encrypted shared configuration")
        names = [task["name"] for task in base]
        self.assertLess(names.index("Persist upload timeouts only on the native Hub registry route"),
                        names.index("Build the reviewed default in the receiving AAP before creating its EE definitions"))
        self.assertLess(names.index("Build the reviewed default in the receiving AAP before creating its EE definitions"),
                        names.index("Combine shared configuration without logging credential inputs"))
        self.assertLess(names.index("Combine shared configuration without logging credential inputs"),
                        names.index("Apply shared AAP configuration"))
        tasks = yaml.safe_load((ROOT / "tasks/base-execution-environment.yml").read_text())
        build = next(task for task in tasks if task.get("name") ==
                     "Build and verify the image on the selected receiver through its pinned SSH route")
        apply = build["ansible.builtin.include_tasks"]["apply"]
        self.assertIn("aap_instance_route.aap_hostname", apply["delegate_to"])
        self.assertEqual(apply["become_user"], "{{ vault_aap_install_user }}")
        self.assertEqual(apply["vars"]["ansible_ssh_common_args"], "{{ aap_instance_ssh_args }}")
        self.assertIs(apply["vars"]["ansible_host_key_checking"], True)


if __name__ == "__main__":
    unittest.main()
