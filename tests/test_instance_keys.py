"""Exercise per-instance selection, source synchronization and real encrypted Git."""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

import yaml
from ansible.errors import AnsibleActionFail
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase
from ansible.utils.unsafe_proxy import wrap_var

ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


keys = load("test_instance_keys", "src/aap_instance_keys.py")
vault_yaml = load("instance_keys_yaml", "src/cac_yaml.py")


def saved(name="one", token="synthetic-instance-one-token", identity=1):
    return {"target": "https://" + name + ".example.invalid", "username": "admin", "scope": "write",
            "id": identity, "token": token, "expires": "2030-01-01T00:00:00Z"}


class FakeSource:
    origin = "https://source.example.invalid"

    def __init__(self):
        self.credential = None
        self.calls = []
        self.host = None
        self.native_credential = None

    def rows(self, path):
        if path.startswith("hosts/"):
            return [deepcopy(self.host)] if self.host else []
        if path.startswith(("job_templates/", "workflow_job_template_nodes/")):
            return []
        if "unified_job_templates" in path:
            return []
        if path.startswith("credentials/?name=one%20MCP"):
            return [deepcopy(self.native_credential)] if self.native_credential else []
        if path.startswith("credential_types/"):
            return [dict(keys.type_definition(), id=46, managed=False)]
        if path.startswith("organizations/"):
            return [{"id": 1, "name": "Example"}]
        if path.startswith("credentials/"):
            if not self.credential:
                return []
            row = deepcopy(self.credential)
            row["inputs"] = {"instance_tokens": "$encrypted$"}
            return [row]
        raise AssertionError(path)

    def request(self, method, path, body=None):
        if method == "GET" and path.startswith("jobs/"):
            return {"status": "running", "job_template": 456, "scm_revision": "a" * 40}
        self.calls.append((method, path))
        if method == "DELETE":
            if path.startswith("hosts/"):
                self.host = None
            elif path == "credentials/45/":
                self.native_credential = None
            else:
                raise AssertionError(path)
            return {}
        if method == "POST":
            self.credential = dict(deepcopy(body), id=91)
        elif method == "PATCH":
            self.credential.update(deepcopy(body))
        else:
            raise AssertionError(method)
        return {"id": self.credential["id"]}


class InstanceKeyTests(unittest.TestCase):
    def test_inventory_registration_retains_literal_json_variable_tags(self):
        from test_aap_name_allocation import RoutingTests
        route = RoutingTests().route()
        original = wrap_var(json.dumps({"ansible_host": route["hypervisor"]["address"],
                                       "ansible_python_interpreter": "{{ ansible_playbook_python }}"}))
        configuration = {"host_inventory_configuration": {
            "hosts": [{"name": "fixture-hypervisor", "inventory": "Shared", "variables": original}],
            "groups": [{"name": "guests", "inventory": "Shared", "variables": {
                "hypervisor_host": "fixture-hypervisor"}, "hosts": []}]}}
        updated = keys.merge_inventory(configuration, route["vm_name"], route, {})
        restored = AnsibleLoader(yaml.dump(updated, Dumper=vault_yaml.VaultDumper).encode()).get_single_data()
        row = restored["host_inventory_configuration"]["hosts"][0]
        self.assertTrue(getattr(row["variables"], "__UNSAFE__", False))
        self.assertEqual(keys.inventory_variables(row)["ansible_python_interpreter"],
                         "{{ ansible_playbook_python }}")
        self.assertEqual(keys.merge_inventory(restored, route["vm_name"], route, {}), restored)

    def test_inventory_registration_preserves_other_hosts_and_refuses_conflicting_placement(self):
        from test_aap_name_allocation import RoutingTests
        route = RoutingTests().route()
        configuration = {"host_inventory_configuration": {
            "inventories": [{"name": "Shared"}],
            "hosts": [{"name": "fixture-hypervisor", "inventory": "Shared", "variables": {
                "ansible_host": route["hypervisor"]["address"], "keep": True}},
                {"name": "unrelated", "inventory": "Shared", "variables": ""}],
            "groups": [{"name": "guests", "inventory": "Shared", "variables": {
                "hypervisor_host": "fixture-hypervisor"}, "hosts": ["unrelated"]}]}}
        original = deepcopy(configuration)
        updated = keys.merge_inventory(configuration, route["vm_name"], route, {"bridges": ["virbr0"]})
        self.assertEqual(configuration, original)
        data = updated["host_inventory_configuration"]
        selected = next(row for row in data["hosts"] if row["name"] == route["vm_name"])
        self.assertEqual(selected["variables"]["ansible_fqdn"], "aap27-test-15.example.invalid")
        self.assertEqual(selected["variables"]["aap_instance_number"], 15)
        self.assertEqual(selected["variables"]["hypervisor_host"], "fixture-hypervisor")
        self.assertEqual(data["groups"][0]["hosts"], ["unrelated", route["vm_name"]])
        self.assertTrue(data["hosts"][0]["variables"]["keep"])
        self.assertNotIn("token", json.dumps(data))
        self.assertEqual(keys.merge_inventory(updated, route["vm_name"], route,
                         {"bridges": ["virbr0"]}), updated)
        broken = deepcopy(updated)
        broken["host_inventory_configuration"]["hosts"][-1]["variables"]["ansible_fqdn"] = "other.example.invalid"
        with self.assertRaises(keys.StoreError):
            keys.merge_inventory(broken, route["vm_name"], route, {})

    def test_selected_name_controls_url_and_token_and_unknown_or_mismatched_hosts_fail(self):
        first = keys.merge_record({}, "one", saved())
        second = keys.merge_record(first, "two", saved("two", "synthetic-instance-two-token", 2))
        data = keys.document(second["aap_instance_api_credentials"])
        for name, token in (("one", "synthetic-instance-one-token"), ("two", "synthetic-instance-two-token")):
            result = keys.select_access(data, wrap_var(name), {"ansible_fqdn": name + ".example.invalid"})
            self.assertEqual(result["token"], token)
            self.assertTrue(result["validate_certs"])
        for name, host in (("missing", "missing.example.invalid"), ("one", "two.example.invalid")):
            with self.assertRaises(keys.StoreError):
                keys.select_access(data, name, {"ansible_fqdn": host})

    def test_existing_record_cannot_be_silently_rotated_and_other_instances_are_preserved(self):
        original = {"unrelated": {"keep": True}}
        first = keys.merge_record(original, "one", saved())
        self.assertEqual(original, {"unrelated": {"keep": True}})
        self.assertEqual(keys.merge_record(first, "one", saved()), first)
        for changed in (dict(saved(), token="another-token"), dict(saved(), target="https://other.example.invalid"),
                        dict(saved(), id=99), dict(saved(), scope="read")):
            with self.assertRaises(keys.StoreError):
                keys.merge_record(first, "one", changed)

    def test_expired_missing_and_non_https_access_is_refused(self):
        first = keys.merge_record({}, "one", saved())["aap_instance_api_credentials"]
        for field, value in (("expires", "2000-01-01T00:00:00Z"), ("token", "$encrypted$"),
                             ("hostname", "http://one.example.invalid"), ("token_id", True)):
            broken = deepcopy(first)
            broken["one"][field] = value
            with self.assertRaises(keys.StoreError):
                keys.select_access(keys.document(broken), "one", {"ansible_fqdn": "one.example.invalid"})

    def test_source_store_is_created_then_updated_and_reruns_are_idempotent(self):
        client = FakeSource()
        records = keys.merge_record({}, "one", saved())["aap_instance_api_credentials"]
        first = keys.ensure_source_store(client, records, "Example")
        self.assertTrue(first["changed"])
        self.assertFalse(keys.ensure_source_store(client, records, "Example")["changed"])
        records = keys.merge_record({"aap_instance_api_credentials": records}, "two",
                                   saved("two", "synthetic-second-token", 2))["aap_instance_api_credentials"]
        self.assertTrue(keys.ensure_source_store(client, records, "Example")["changed"])
        self.assertEqual(client.calls, [("POST", "credentials/"), ("PATCH", "credentials/91/")])
        self.assertEqual(set(json.loads(client.credential["inputs"]["instance_tokens"])["instances"]), {"one", "two"})
        client.credential["organization"] = 99
        with self.assertRaises(keys.StoreError):
            keys.ensure_source_store(client, records, "Example")

    def test_action_uses_only_injected_file_and_refuses_native_api_overrides(self):
        module = load("test_instance_access_action", "action_plugins/aap_instance_access.py")
        data = keys.document(keys.merge_record({}, "one", saved())["aap_instance_api_credentials"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "keys.json"
            path.write_text(json.dumps(data))
            plugin = module.ActionModule.__new__(module.ActionModule)
            plugin._task = SimpleNamespace(args={"instance_name": "one", "fqdn": "one.example.invalid"})
            env = {"AAP_INSTANCE_KEY_STORE_FILE": str(path), "AAP_HOSTNAME": "", "AAP_TOKEN": "",
                   "AAP_USERNAME": "", "AAP_PASSWORD": ""}
            with mock.patch.object(ActionBase, "run", return_value={}), mock.patch.dict(os.environ, env):
                response = plugin.run(task_vars={"AAP_INSTANCE_KEY_STORE_FILE": "/untrusted"})
                self.assertEqual(response["authentication"]["token"], saved()["token"])
                with mock.patch.dict(os.environ, {"AAP_TOKEN": "synthetic-native-override"}):
                    self.assertIn("shared instance token store", plugin.run(task_vars={})["access_error"])
                path.write_text("not-json")
                self.assertIn("could not be read or validated", plugin.run(task_vars={})["access_error"])

    def test_real_git_publication_retains_other_data_and_repairs_failed_source_synchronization(self):
        module = load("test_publish_instance_action", "action_plugins/aap_publish_instance_keys.py")
        real_run = subprocess.run
        client = FakeSource()
        secret = VaultSecret(b"fixture-cac-password")
        environment_secret = VaultSecret(b"fixture-environment-password")
        vault = VaultLib([("cac", secret), ("default", environment_secret)])
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            remote = base / "remote.git"
            seed = base / "seed"
            seed.mkdir()

            def git(path, *args):
                return real_run(["git", "-C", str(path), *args], text=True, capture_output=True, check=True)

            real_run(["git", "init", "--bare", "--initial-branch=main", str(remote)], capture_output=True, check=True)
            git(seed, "init", "--initial-branch=main")
            relative = "vaults/cac/aap_autodeploy_configascode-cac-vault.yml"
            target = seed / relative
            target.parent.mkdir(parents=True)
            original = {"keep": "unchanged", "injector": wrap_var("{{ literal_runtime_token }}")}
            target.write_bytes(vault.encrypt(yaml.dump(original, Dumper=vault_yaml.VaultDumper), vault_id="cac"))
            git(seed, "add", ".")
            git(seed, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "Initialize")
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "origin", "main")
            project = base / "project"
            project.mkdir()
            (project / "myvars").write_bytes(vault.encrypt(yaml.safe_dump({
                "git_url": "https://git.example.invalid/fixture-owner/autodeploy.git"}), vault_id="default"))
            loader = DataLoader()
            loader.set_vault_secrets([("cac", secret), ("default", environment_secret)])

            def redirected(command, *args, **kwargs):
                self.assertNotIn(saved()["token"], " ".join(command))
                replaced = [str(remote) if item == "https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git"
                            else item for item in command]
                self.assertFalse(any(item.startswith(("https://", "http://", "git@")) for item in replaced))
                return real_run(replaced, *args, **kwargs)

            def run(name, record, operation=None):
                plugin = module.ActionModule.__new__(module.ActionModule)
                plugin._task = SimpleNamespace(args={"instance_name": name, "record": record, "organization": "Example"}, check_mode=False)
                if operation:
                    plugin._task.args["operation"] = operation
                plugin._loader = loader
                return plugin.run(task_vars={"awx_job_id": 123, "awx_job_template_id": 456,
                                             "awx_project_revision": "a" * 40})

            with mock.patch.object(ActionBase, "run", return_value={}), mock.patch.object(module, "ROOT", project), \
                 mock.patch.object(module, "SourceClient", return_value=client), \
                 mock.patch.object(module.subprocess, "run", side_effect=redirected), \
                 mock.patch.dict(os.environ, {"CAC_GIT_TOKEN": "synthetic-writer-token"}):
                original_request = client.request

                def failed_save(method, path, body=None):
                    if method != "GET":
                        raise keys.StoreError("Synthetic failed API save")
                    return original_request(method, path, body)

                with mock.patch.object(client, "request", side_effect=failed_save):
                    # The action loads its own copy of StoreError; all failures remain protected.
                    with self.assertRaises(AnsibleActionFail):
                        run("one", saved())
                self.assertEqual(git(remote, "rev-list", "--count", "main").stdout.strip(), "2")
                self.assertTrue(run("one", saved())["changed"])
                self.assertFalse(run("one", saved())["changed"])
                self.assertTrue(run("two", saved("two", "synthetic-second-token", 2))["changed"])
                git(seed, "fetch", "origin", "main")
                git(seed, "checkout", "--detach", "FETCH_HEAD")
                allocation = {"aap_vm_allocation": {"schema_version": 1, "next_number": 3,
                    "reservations": {name: {"vm_name": name, "number": number,
                        "instance_route": {"aap_hostname": "https://" + name + ".example.invalid"}}
                        for name, number in (("one", 1), ("two", 2))}}}
                inventory = {"host_inventory_configuration": {
                    "hosts": [{"name": "one"}, {"name": "two"}],
                    "groups": [{"name": "fixture", "hosts": ["one", "two"]}]}}
                for extra, data in (("state/aap_vm_allocations_vault.yml", allocation),
                                    ("cac/host_inventory.yml", inventory)):
                    output = seed / extra
                    output.parent.mkdir(exist_ok=True, parents=True)
                    output.write_bytes(vault.encrypt(yaml.safe_dump(data), vault_id="cac"))
                    git(seed, "add", extra)
                git(seed, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "commit", "-m", "Add retirement fixture")
                git(seed, "push", "origin", "HEAD:main")
                client.host = {"id": 25, "variables": json.dumps({"ansible_fqdn": "one.example.invalid"})}
                client.native_credential = {"id": 45, "inputs": {"host": "https://one.example.invalid"}}
                self.assertTrue(run("one", {"target": "https://one.example.invalid"}, "retire")["changed"])
                self.assertFalse(run("one", {"target": "https://one.example.invalid"}, "retire")["changed"])
                retired = AnsibleLoader(vault.decrypt(git(remote, "show",
                    "main:state/aap_vm_allocations_vault.yml").stdout)).get_single_data()["aap_vm_allocation"]
                self.assertEqual(retired["next_number"], 3)
                self.assertTrue(retired["reservations"]["one"]["decommissioned"])
                self.assertNotIn("decommissioned", retired["reservations"]["two"])
                retained = AnsibleLoader(vault.decrypt(git(remote, "show",
                    "main:cac/host_inventory.yml").stdout)).get_single_data()["host_inventory_configuration"]
                self.assertEqual(retained["hosts"], [{"name": "two"}])
                self.assertEqual(retained["groups"][0]["hosts"], ["two"])
                self.assertIsNone(client.host)
                self.assertIsNone(client.native_credential)
            configuration = AnsibleLoader(vault.decrypt(git(remote, "show", "main:" + relative).stdout)).get_single_data()
            self.assertEqual(set(configuration["aap_instance_api_credentials"]), {"two"})
            self.assertEqual(configuration["keep"], original["keep"])
            self.assertEqual(vault_yaml.literal_paths(configuration), vault_yaml.literal_paths(original))


if __name__ == "__main__":
    unittest.main()
