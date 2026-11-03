"""Exercise the installed EDA module and Controller with an in-memory API."""

import copy
import importlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class ModuleFinished(Exception):
    def __init__(self, result, failed=False):
        self.result = result
        self.failed = failed


class ActivationImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("ansible") is None:
            raise unittest.SkipTest("requires installed Ansible")
        roots = [Path(value) for value in os.environ.get(
            "ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep) if value]
        roots.extend((Path.home() / ".ansible/collections", ROOT.parents[2] /
                      "tools/aap-cac-export/collections"))
        collection_root = next((root for root in roots if (root /
            "ansible_collections/ansible/eda/plugins/modules/rulebook_activation.py"
        ).is_file()), None)
        if collection_root is None:
            raise unittest.SkipTest("requires already-installed ansible.eda")
        sys.path.insert(0, str(collection_root))
        cls.native = importlib.import_module(
            "ansible_collections.ansible.eda.plugins.modules.rulebook_activation")
        cls.Response = importlib.import_module(
            "ansible_collections.ansible.eda.plugins.module_utils.client").Response
        spec = importlib.util.spec_from_file_location(
            "cac_activation_guard_under_test", ROOT / "library/aap_cac_activation.py")
        cls.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.guard)

    def setUp(self):
        self.activation = None
        self.requests = []
        self.arguments = {
            "name": "Synthetic activation", "description": "Revised definition",
            "project_name": "Synthetic project", "rulebook_name": "example.yml",
            "decision_environment_name": "Synthetic environment",
            "organization_name": "Synthetic organization", "state": "present",
            # The upstream default is true: the import guard must override it.
            "enabled": True, "restart": False,
        }

    def existing(self, enabled):
        self.activation = {
            "id": 41, "name": "Synthetic activation", "description": "Old definition",
            "is_enabled": enabled, "rulebook_id": 2, "decision_environment_id": 3,
            "organization_id": 4, "eda_credentials": [], "restart_policy": "on-failure",
            "log_level": "error", "restart_on_project_update": False,
            "enable_persistence": False,
        }

    def run_import(self, **overrides):
        owner = self
        arguments = dict(self.arguments, **overrides)

        class Module:
            def __init__(self, argument_spec, **kwargs):
                self.params = {key: value.get("default") for key, value in argument_spec.items()}
                self.params.update(copy.deepcopy(arguments))
                self.check_mode = False

            @staticmethod
            def exit_json(**result):
                raise ModuleFinished(result)

            @staticmethod
            def fail_json(**result):
                raise ModuleFinished(result, failed=True)

            @staticmethod
            def warn(message):
                raise AssertionError(message)

        class Client:
            """Mock transport only; retain real resource lookup and diff logic."""

            def __init__(self, **kwargs):
                pass

            def get(self, endpoint, **kwargs):
                owner.requests.append(("GET", endpoint, copy.deepcopy(kwargs)))
                if endpoint == "config":
                    return owner.Response(200, "{}")
                if endpoint == "activations":
                    items = [copy.deepcopy(owner.activation)] if owner.activation else []
                else:
                    ids = {"projects": 1, "rulebooks": 2, "decision-environments": 3,
                           "organizations": 4}
                    if endpoint not in ids:
                        raise AssertionError("Unexpected lookup: " + endpoint)
                    items = [{"id": ids[endpoint], "name": kwargs["data"]["name"]}]
                return owner.Response(200, json.dumps({"count": len(items), "results": items}))

            def post(self, endpoint, **kwargs):
                if endpoint != "activations" or owner.activation is not None:
                    raise AssertionError("Unexpected POST: " + endpoint)
                owner.requests.append(("POST", endpoint, copy.deepcopy(kwargs)))
                owner.activation = dict(copy.deepcopy(kwargs["data"]), id=41, eda_credentials=[])
                return owner.Response(201, json.dumps(owner.activation))

            def patch(self, endpoint, **kwargs):
                if endpoint != "activations" or kwargs["id"] != 41:
                    raise AssertionError("Unexpected PATCH: " + endpoint)
                owner.requests.append(("PATCH", endpoint, copy.deepcopy(kwargs)))
                owner.activation.update(copy.deepcopy(kwargs["data"]))
                return owner.Response(200, json.dumps(owner.activation))

        # Guard changes are scoped: other tests still see the original module.
        with patch.object(self.native, "AnsibleModule", Module), \
                patch.object(self.native, "Controller", self.native.Controller), \
                patch.object(self.native, "create_params", self.native.create_params), \
                patch.object(self.native, "Client", Client), \
                patch.object(socket.socket, "connect", side_effect=AssertionError("Network forbidden")):
            self.guard.install_safety_guard(self.native)
            try:
                self.native.main()
            except ModuleFinished as result:
                return result
        self.fail("Module did not report its result")

    def test_new_activation_is_created_disabled_and_second_import_is_unchanged(self):
        result = self.run_import()
        self.assertFalse(result.failed)
        self.assertTrue(result.result["changed"])
        self.assertIs(self.activation["is_enabled"], False)
        self.assertEqual(self.activation["description"], "Revised definition")
        self.assertEqual([method for method, _, _ in self.requests if method != "GET"], ["POST"])
        self.requests.clear()
        rerun = self.run_import()
        self.assertFalse(rerun.failed)
        self.assertFalse(rerun.result["changed"])
        self.assertTrue(all(method == "GET" for method, _, _ in self.requests))

    def test_disabled_activation_definition_updates_and_remains_disabled(self):
        self.assert_existing_update(False)

    def test_enabled_activation_definition_updates_and_remains_enabled(self):
        self.assert_existing_update(True)

    def assert_existing_update(self, enabled):
        self.existing(enabled)
        result = self.run_import()
        self.assertFalse(result.failed)
        self.assertTrue(result.result["changed"])
        self.assertIs(self.activation["is_enabled"], enabled)
        self.assertEqual(self.activation["description"], "Revised definition")
        self.assertEqual([method for method, _, _ in self.requests if method != "GET"], ["PATCH"])
        self.requests.clear()
        rerun = self.run_import()
        self.assertFalse(rerun.failed)
        self.assertFalse(rerun.result["changed"])
        self.assertTrue(all(method == "GET" for method, _, _ in self.requests))

    def test_operational_state_changes_are_refused_before_any_api_request(self):
        for arguments in ({"state": "enabled"}, {"state": "disabled"},
                          {"state": "absent"}, {"restart": True}):
            with self.subTest(arguments=arguments):
                self.requests.clear()
                result = self.run_import(**arguments)
                self.assertTrue(result.failed)
                self.assertIn("only update definitions", result.result["msg"])
                self.assertEqual(self.requests, [])

    def test_unknown_existing_enabled_state_prevents_writes(self):
        for enabled in (None, "false", 0):
            with self.subTest(enabled=enabled):
                self.existing(enabled)
                self.requests.clear()
                result = self.run_import()
                self.assertTrue(result.failed)
                self.assertIn("unambiguous enabled state", result.result["msg"])
                self.assertTrue(all(method == "GET" for method, _, _ in self.requests))

    def test_real_ansible_action_loads_installed_module_and_refuses_state_change(self):
        with tempfile.TemporaryDirectory(prefix="cac-activation-action-") as temporary:
            environment = dict(
                os.environ,
                ANSIBLE_ACTION_PLUGINS=str(ROOT / "action_plugins"),
                ANSIBLE_LIBRARY=str(ROOT / "library"),
                ANSIBLE_LOCAL_TEMP=str(Path(temporary) / "local"),
                ANSIBLE_REMOTE_TEMP=str(Path(temporary) / "remote"),
            )
            arguments = {
                "name": "Synthetic activation", "state": "disabled",
                "controller_host": "https://aap.example.invalid",
                "controller_token": "synthetic-secret-canary",
            }
            process = subprocess.run(
                [sys.executable, "-m", "ansible.cli.adhoc", "localhost", "-i", "localhost,",
                 "-c", "local", "-m", "aap_cac_activation", "-a", json.dumps(arguments)],
                cwd=ROOT, env=environment, text=True, capture_output=True, timeout=30,
            )
            output = process.stdout + process.stderr
            self.assertNotEqual(process.returncode, 0)
            self.assertIn("only update definitions", output)
            self.assertNotIn("ModuleNotFoundError", output)
            self.assertNotIn("synthetic-secret-canary", output)


if __name__ == "__main__":
    unittest.main()
