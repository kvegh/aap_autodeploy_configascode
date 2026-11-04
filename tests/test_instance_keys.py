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
from urllib.parse import parse_qs, urlsplit

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


def retirement_fixture():
    from test_decommission_guest_access import fixture, RETIRE
    policy, retirement, route, resources, xmls, networks = fixture()
    resources["aap"] = {"uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "disk": retirement["disk"], "address": route["vm_ip"], "mac": "52:54:00:12:34:56",
        "bridge": "vmbr0", "network": "isolated", "verified": True}
    resources["zabbix"].update(machine_id="b" * 32, host_keys=["ssh-ed25519 BBBB"])
    for number, role in enumerate(("testserver1", "tra"), 4):
        resources[role] = {"vm_name": role + "-v07", "uuid": "%08d-2222-3333-4444-555555555555" % number,
            "disk": "/opt/vms/" + role + "-v07.disk.qcow2", "address": "192.168.70.%d" % (number * 10),
            "mac": "52:54:00:12:34:%02d" % (number + 55), "bridge": "vmbr0", "network": "isolated",
            "verified": True, "machine_id": str(number) * 32, "host_keys": ["ssh-ed25519 CCCC"]}
    retirement = RETIRE.resources(route, "example.invalid", "/opt/vms", resources)
    plan = RETIRE.guest_access_plan(policy, retirement, route, resources, xmls, networks)
    transition = {key: plan[key] for key in ("previous_policy", "desired_policy", "identities")}
    record = {"vm_name": route["vm_name"], "number": 7, "prefix": "aap27-test",
              "hypervisor_id": route["hypervisor"]["machine_id"], "instance_route": route, "instance_resources": resources}
    context = keys.isolation_retirement_context(record, route["vm_name"], route["aap_hostname"], transition)
    zone_rules = [{"zone": "libvirt", "rule": rule} for rule in sorted(context["removed_rules"])]
    zone_rules += [{"zone": "libvirt", "rule": "unrelated"}, {"zone": "public", "rule": sorted(context["removed_rules"])[0]}]
    host_variables = {"ansible_host": route["hypervisor"]["address"], "ansible_port": 2222,
        "ansible_user": route["hypervisor"]["user"], "machine_id": route["hypervisor"]["machine_id"],
        "host_keys": route["hypervisor"]["host_keys"], "isolation_policy": policy,
        "hactar_isolation_policy": policy, "firewall_additional_zone_rules": zone_rules,
        "ansible_python_interpreter": "{{ ansible_playbook_python }}"}
    shared = {"host_inventory_configuration": {"inventories": [{"name": "Shared"}],
        "hosts": [{"name": "fixture-hypervisor", "inventory": "Shared", "variables": wrap_var(json.dumps(host_variables))}],
        "groups": [{"name": "guests", "inventory": "Shared", "hosts": []},
                   {"name": "foreign", "inventory": "Other", "hosts": [route["vm_name"]]}]}}
    for guest in context["guests"]:
        values = {"ansible_host": guest["address"], "hypervisor_host": "fixture-hypervisor",
                  "vm_uuid": guest["metadata"]["uuid"]}
        if guest["role"] == "aap":
            values.update(ansible_fqdn=urlsplit(route["aap_hostname"]).hostname, host_keys=route["guest_host_keys"])
        else:
            values.update(machine_id=guest["metadata"]["machine_id"], host_keys=guest["metadata"]["host_keys"])
        shared["host_inventory_configuration"]["hosts"].append({"name": guest["name"], "inventory": "Shared", "variables": values})
        shared["host_inventory_configuration"]["groups"][0]["hosts"].append(guest["name"])
    shared["host_inventory_configuration"]["hosts"] += [
        {"name": "other-v08", "inventory": "Shared", "variables": {"keep": True}},
        {"name": route["vm_name"], "inventory": "Other", "variables": {"ansible_host": "198.51.100.99"}}]
    shared["host_inventory_configuration"]["groups"][0]["hosts"].append("other-v08")
    recovery_variables = {"aap_hypervisor_pin": route["hypervisor"],
        "aap_hypervisor_isolation_https_clients": policy["https_clients"],
        "aap_hypervisor_isolation_protected_ipv4": policy["protected_ipv4"],
        "aap_hypervisor_isolation_host_clients": policy["guest_host_clients"],
        "hactar_isolation_policy": policy, "keep": "{{ literal_recovery_setting }}"}
    main = keys.merge_record({}, route["vm_name"], dict(saved("aap27.v07"), target=route["aap_hostname"]))
    main = keys.merge_record(main, "other", saved("other", "synthetic-other-token", 2))
    main["autodeploy_configuration"] = {"inventories": [{"name": "Deploy Recovery", "variables": wrap_var(json.dumps(recovery_variables))}],
        "credentials": [{"name": "shared-machine", "inputs": {"keep": wrap_var("{{ literal_machine_key }}")}},
                        {"name": route["vm_name"] + " MCP and API token"}]}
    hactar = {"controller_hosts_hactar_recovery": [{"name": "fixture-recovery-hypervisor", "inventory": "Recovery",
                "variables": wrap_var(json.dumps({"ansible_host": route["hypervisor"]["address"], "keep": "{{ literal_capture }}"}))}],
               "controller_groups_hactar_recovery": []}
    allocation = {"aap_vm_allocation": {"schema_version": 1, "next_number": 9,
        "reservations": {"selected-request": record, "other-request": {"vm_name": "other", "number": 8, "keep": True}}}}
    return context, transition, main, shared, hactar, allocation


class FakeRetirementSource(FakeSource):
    def __init__(self, main, shared, hactar):
        super().__init__()
        self.inventories = {1: {"id": 1, "name": "Shared", "variables": "{}"},
                            2: {"id": 2, "name": "Recovery", "variables": "{}"},
                            3: {"id": 3, "name": "Deploy Recovery", "variables": json.dumps(keys.inventory_variables(main["autodeploy_configuration"]["inventories"][0]))}}
        self.hosts = {}
        for index, row in enumerate(shared["host_inventory_configuration"]["hosts"], 10):
            inventory = 1 if row["inventory"] == "Shared" else 99
            self.hosts[index] = dict(deepcopy(row), id=index, inventory=inventory,
                                    variables=json.dumps(keys.inventory_variables(row)))
        for index, row in enumerate(hactar["controller_hosts_hactar_recovery"], 30):
            self.hosts[index] = dict(deepcopy(row), id=index, inventory=2,
                                    variables=json.dumps(keys.inventory_variables(row)))

    def rows(self, path):
        query = parse_qs(urlsplit(path).query)
        if path.startswith("inventories/"):
            return [deepcopy(row) for row in self.inventories.values() if row["name"] == query["name"][0]]
        if path.startswith("hosts/"):
            return [deepcopy(row) for row in self.hosts.values()
                    if row["name"] == query["name"][0] and row["inventory"] == int(query["inventory"][0])]
        if path.startswith("credentials/") and query.get("name", [None])[0] != keys.CREDENTIAL_NAME:
            return []
        return super().rows(path)

    def request(self, method, path, body=None):
        if path.startswith(("hosts/", "inventories/")):
            self.calls.append((method, path))
            collection = self.hosts if path.startswith("hosts/") else self.inventories
            identity = int(path.split("/")[1])
            if method == "DELETE":
                del collection[identity]
                return {}
            if method == "PATCH":
                collection[identity].update(deepcopy(body))
                return deepcopy(collection[identity])
            raise AssertionError((method, path))
        return super().request(method, path, body)


class InstanceKeyTests(unittest.TestCase):
    def test_retirement_updates_only_owned_capture_data_and_preserves_literal_wrappers(self):
        context, transition, main, shared, hactar, allocation = retirement_fixture()
        original = deepcopy((main, shared, hactar, allocation))
        retired_shared = keys.retire_inventory_capture(shared, context, "shared")
        hosts = retired_shared["host_inventory_configuration"]["hosts"]
        self.assertEqual([(row["name"], row["inventory"]) for row in hosts],
                         [("fixture-hypervisor", "Shared"), ("other-v08", "Shared"), (context["route"]["vm_name"], "Other")])
        self.assertEqual(retired_shared["host_inventory_configuration"]["groups"][0]["hosts"], ["other-v08"])
        self.assertEqual(retired_shared["host_inventory_configuration"]["groups"][1], shared["host_inventory_configuration"]["groups"][1])
        self.assertTrue(getattr(hosts[0]["variables"], "__UNSAFE__", False))
        values = keys.inventory_variables(hosts[0])
        self.assertEqual(values["isolation_policy"], transition["desired_policy"])
        self.assertEqual(values["hactar_isolation_policy"], transition["desired_policy"])
        self.assertEqual(values["ansible_python_interpreter"], "{{ ansible_playbook_python }}")
        self.assertEqual(values["firewall_additional_zone_rules"], keys.inventory_variables(shared["host_inventory_configuration"]["hosts"][0])["firewall_additional_zone_rules"][-2:])
        for kind, before in (("shared", shared), ("autodeploy", main), ("hactar", hactar)):
            updated = keys.retire_inventory_capture(before, context, kind)
            restored = AnsibleLoader(yaml.dump(updated, Dumper=vault_yaml.VaultDumper).encode()).get_single_data()
            self.assertEqual(vault_yaml.literal_paths(updated), vault_yaml.literal_paths(restored))
            self.assertEqual(keys.retire_inventory_capture(restored, context, kind), restored)
        self.assertEqual((main, shared, hactar, allocation), original)
        for kind in ("identity", "desired", "extra", "omitted"):
            invalid = deepcopy(transition)
            if kind == "identity": invalid["identities"][0]["ipv4"] = "192.168.70.30"
            if kind == "desired": invalid["desired_policy"] = invalid["previous_policy"]
            if kind == "extra": invalid["new_grant"] = True
            if kind == "omitted":
                invalid["identities"] = invalid["identities"][1:]
                invalid["desired_policy"]["guest_host_clients"].insert(0, deepcopy(invalid["previous_policy"]["guest_host_clients"][0]))
                invalid["desired_policy"]["https_clients"].insert(0, deepcopy(invalid["previous_policy"]["https_clients"][0]))
            with self.subTest(kind=kind), self.assertRaises(keys.StoreError):
                keys.isolation_retirement_context(allocation["aap_vm_allocation"]["reservations"]["selected-request"],
                    context["route"]["vm_name"], context["route"]["aap_hostname"], invalid)
        for field, value in (("number", 8), ("prefix", "other"), ("hypervisor_id", "2" * 32)):
            invalid_record = dict(allocation["aap_vm_allocation"]["reservations"]["selected-request"], **{field: value})
            with self.subTest(field=field), self.assertRaises(keys.StoreError):
                keys.isolation_retirement_context(invalid_record, context["route"]["vm_name"], context["route"]["aap_hostname"], transition)

    def test_foreign_live_guest_identity_refuses_all_source_mutation(self):
        context, transition, main, shared, hactar, allocation = retirement_fixture()
        for field in ("ansible_host", "vm_uuid", "machine_id"):
            client = FakeRetirementSource(main, shared, hactar)
            row = next(row for row in client.hosts.values() if row["name"] == "testserver1-v07")
            variables = json.loads(row["variables"])
            variables[field] = "foreign"
            row["variables"] = json.dumps(variables)
            with self.subTest(field=field), self.assertRaises(keys.StoreError):
                keys.source_retirement_operations(client, shared, main, hactar, context)
            self.assertEqual(client.calls, [])
        client = FakeRetirementSource(main, shared, hactar)
        variables = json.loads(client.inventories[3]["variables"])
        variables["aap_hypervisor_isolation_host_clients"] = []
        client.inventories[3]["variables"] = json.dumps(variables)
        with self.assertRaises(keys.StoreError):
            keys.source_retirement_operations(client, shared, main, hactar, context)
        self.assertEqual(client.calls, [])

    def test_isolation_argument_is_refused_on_publication_before_any_connection(self):
        module = load("retirement_argument_guard", "action_plugins/aap_publish_instance_keys.py")
        plugin = module.ActionModule.__new__(module.ActionModule)
        plugin._task = SimpleNamespace(args={"instance_name": "one", "record": saved(),
            "organization": "Example", "isolation_retirement": {}}, check_mode=False)
        with mock.patch.object(ActionBase, "run", return_value={}), mock.patch.object(module, "SourceClient") as source:
            with self.assertRaises(AnsibleActionFail):
                plugin.run(task_vars={})
            source.assert_not_called()

    def test_real_encrypted_retirement_preserves_other_guests_and_repairs_source_retry(self):
        module = load("test_isolation_retirement_action", "action_plugins/aap_publish_instance_keys.py")
        context, transition, main, shared, hactar, allocation = retirement_fixture()
        client = FakeRetirementSource(main, shared, hactar)
        real_run = subprocess.run
        secret = VaultSecret(b"fixture-retirement-password")
        environment_secret = VaultSecret(b"fixture-environment-password")
        vault = VaultLib([("cac", secret), ("default", environment_secret)])
        documents = {"vaults/cac/aap_autodeploy_configascode-cac-vault.yml": main,
            "cac/host_inventory.yml": shared, "cac/hactar_recovery.yml": hactar,
            "state/aap_vm_allocations_vault.yml": allocation}
        with tempfile.TemporaryDirectory(prefix="encrypted-retirement-git-") as temporary:
            directory = Path(temporary)
            remote, seed, project = (directory / name for name in ("remote.git", "seed", "project"))
            seed.mkdir(); project.mkdir()

            def git(path, *args):
                return real_run(["git", "-C", str(path), *args], text=True, capture_output=True, check=True)

            real_run(["git", "init", "--bare", "--initial-branch=main", str(remote)], capture_output=True, check=True)
            git(seed, "init", "--initial-branch=main")
            for relative, value in documents.items():
                path = seed / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(vault.encrypt(yaml.dump(value, Dumper=vault_yaml.VaultDumper), vault_id="cac"))
            git(seed, "add", ".")
            git(seed, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "Initialize encrypted captures")
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "origin", "main")
            (project / "myvars").write_bytes(vault.encrypt(yaml.safe_dump({"git_url":
                "https://git.example.invalid/fixture-owner/autodeploy.git"}), vault_id="default"))
            loader = DataLoader()
            loader.set_vault_secrets([("cac", secret), ("default", environment_secret)])

            def redirected(command, *args, **kwargs):
                self.assertNotIn("synthetic-instance-one-token", " ".join(command))
                replaced = [str(remote) if item == "https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git"
                            else item for item in command]
                self.assertFalse(any(item.startswith(("https://", "http://", "git@")) for item in replaced))
                return real_run(replaced, *args, **kwargs)

            def run(supplied=transition):
                plugin = module.ActionModule.__new__(module.ActionModule)
                plugin._task = SimpleNamespace(args={"instance_name": context["route"]["vm_name"],
                    "record": {"target": context["route"]["aap_hostname"]}, "organization": "Example",
                    "operation": "retire", "isolation_retirement": supplied}, check_mode=False)
                plugin._loader = loader
                return plugin.run(task_vars={"awx_job_id": 123, "awx_job_template_id": 456, "awx_project_revision": "a" * 40})

            with mock.patch.object(ActionBase, "run", return_value={}), mock.patch.object(module, "ROOT", project), \
                 mock.patch.object(module, "SourceClient", return_value=client), \
                 mock.patch.object(module.subprocess, "run", side_effect=redirected), \
                 mock.patch.dict(os.environ, {"CAC_GIT_TOKEN": "synthetic-writer-token"}):
                invalid = deepcopy(transition)
                invalid["identities"][0]["ipv4"] = "192.168.70.30"
                with self.assertRaises(AnsibleActionFail): run(invalid)
                self.assertEqual(git(remote, "rev-list", "--count", "main").stdout.strip(), "1")
                self.assertEqual(client.calls, [])
                row = next(row for row in client.hosts.values() if row["name"] == "tra-v07")
                saved_variables = row["variables"]
                row["variables"] = json.dumps(dict(json.loads(saved_variables), vm_uuid="foreign"))
                with self.assertRaises(AnsibleActionFail): run()
                self.assertEqual(git(remote, "rev-list", "--count", "main").stdout.strip(), "1")
                self.assertEqual(client.calls, [])
                row["variables"] = saved_variables
                original_request = client.request

                def failed_source_save(method, path, body=None):
                    if method != "GET": raise keys.StoreError("Synthetic interrupted source synchronization")
                    return original_request(method, path, body)

                with mock.patch.object(client, "request", side_effect=failed_source_save):
                    with self.assertRaises(AnsibleActionFail): run()
                self.assertEqual(git(remote, "rev-list", "--count", "main").stdout.strip(), "2")
                self.assertTrue(run()["changed"])
                self.assertFalse(run()["changed"])
                self.assertEqual(git(remote, "rev-list", "--count", "main").stdout.strip(), "2")
            restored = {}
            for relative in documents:
                ciphertext = git(remote, "show", "main:" + relative).stdout.encode()
                self.assertTrue(ciphertext.startswith(b"$ANSIBLE_VAULT;"))
                restored[relative] = AnsibleLoader(vault.decrypt(ciphertext)).get_single_data()
            state = restored["state/aap_vm_allocations_vault.yml"]["aap_vm_allocation"]
            self.assertEqual(state["next_number"], allocation["aap_vm_allocation"]["next_number"])
            expected_record = deepcopy(allocation["aap_vm_allocation"]["reservations"]["selected-request"])
            expected_record["decommissioned"] = True
            self.assertEqual(state["reservations"]["selected-request"], expected_record)
            self.assertEqual(state["reservations"]["other-request"], allocation["aap_vm_allocation"]["reservations"]["other-request"])
            retired_main = restored["vaults/cac/aap_autodeploy_configascode-cac-vault.yml"]
            self.assertEqual(set(retired_main["aap_instance_api_credentials"]), {"other"})
            self.assertEqual(retired_main["autodeploy_configuration"]["credentials"], main["autodeploy_configuration"]["credentials"][:1])
            for kind, relative in (("shared", "cac/host_inventory.yml"), ("autodeploy", "vaults/cac/aap_autodeploy_configascode-cac-vault.yml"),
                                   ("hactar", "cac/hactar_recovery.yml")):
                self.assertEqual(keys.retire_inventory_capture(restored[relative], context, kind), restored[relative])
            self.assertEqual([(row["name"], row["inventory"]) for row in client.hosts.values()],
                [("fixture-hypervisor", 1), ("other-v08", 1), (context["route"]["vm_name"], 99), ("fixture-recovery-hypervisor", 2)])
            self.assertEqual(keys.source_retirement_operations(client, restored["cac/host_inventory.yml"],
                retired_main, restored["cac/hactar_recovery.yml"], context), [])

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
