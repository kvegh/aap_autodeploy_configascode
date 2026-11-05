"""Prove new AIOps data can bootstrap without fabricated guest or API identities."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import os
from types import SimpleNamespace
import subprocess
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
from ansible.utils.unsafe_proxy import AnsibleUnsafeText, wrap_var


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tested_aiops_settings", ROOT / "src/aap_aiops_settings.py")
settings = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(settings)


def fixture(number=7):
    pin = {"address": "192.0.2.20", "public_ip": "192.0.2.20", "user": "manager", "port": 2222,
           "machine_id": "a" * 32, "host_keys": ["ssh-ed25519 AAAA"]}
    hypervisor = {"ansible_host": pin["address"], "public_ipv4": pin["public_ip"], "ansible_user": pin["user"],
                  "ansible_port": pin["port"], "machine_id": pin["machine_id"], "host_keys": pin["host_keys"],
                  "isolation_policy": {"bridges": ["vmbr0"], "dns_bridges": ["vmbr0"]}}
    instance = {"aap_instance_number": number, "ansible_fqdn": "aap27.v%02d.example.invalid" % number,
                "ansible_host": "192.168.70.10", "vm_uuid": "11111111-2222-3333-4444-555555555555",
                "hypervisor_host": "recovery-host"}
    instance["vm_resource"] = {"vm_name": "aap27-test-%d" % number, "verified": True,
        "address": instance["ansible_host"], "uuid": instance["vm_uuid"], "hypervisor_machine_id": pin["machine_id"],
        "disk": "/opt/vms/aap27-test-%d.disk.qcow2" % number}
    context = settings.selected_context(instance, hypervisor, "https://" + instance["ansible_fqdn"],
                                        "example.invalid", {}, "aap27-v%02d" % number)
    capture = {"aiops_instances": {}, "aiops_event_stream_password": wrap_var("legacy-password-unchanged"),
               "unrelated": {"injector": wrap_var("{{ forbidden_expression }}")}}
    runtime = {"schema_version": 1, "instances": {}}
    return context, capture, runtime, instance, hypervisor


def guest(context, role="testserver1"):
    name = role + "-" + context["version"]
    resource = {"vm_name": name, "verified": True, "uuid": "22222222-2222-3333-4444-555555555555",
        "disk": "/opt/vms/" + name + ".disk.qcow2", "network": "isolated", "bridge": "vmbr0",
        "address": "192.168.70.20", "mac": "52:54:00:12:34:56", "machine_id": "b" * 32,
        "hypervisor_machine_id": context["hypervisor"]["machine_id"], "host_keys": ["ssh-ed25519 BBBB"],
        "user": "automation", "port": 22, "vcpus": 1, "memory_mb": 2048, "disk_gb": 10,
        "source_image_sha256": "c" * 64, "packages_updated": True}
    return {"aap_instance_number": context["instance_number"], "hypervisor_host": context["hypervisor_name"],
            "vm_resource": resource, "ansible_host": resource["address"], "vm_uuid": resource["uuid"],
            "machine_id": resource["machine_id"], "host_keys": resource["host_keys"],
            "ansible_user": resource["user"], "ansible_port": resource["port"]}


def zabbix_guest(context):
    source = guest(context, "zabbix")
    resource = source["vm_resource"]
    for field in ("vcpus", "memory_mb", "disk_gb", "source_image_sha256", "packages_updated"):
        resource.pop(field)
    resource.update(schema_version=1, instance_name=context["instance_name"], instance_number=context["instance_number"],
        source_sha256="c" * 64, guest_host_keys=deepcopy(resource["host_keys"]), ip=resource["address"],
        public_hostname=context["zabbix_fqdn"], certificate=context["zabbix_fqdn"],
        api_url="http://" + resource["address"] + "/api_jsonrpc.php",
        nginx_file="/etc/nginx/conf.d/demo-zabbix-" + context["version"] + ".conf",
        auth_file="/etc/nginx/demo-zabbix-" + context["version"] + ".htpasswd",
        host_id="10", item_id="20", trigger_id="30")
    return source


class ReadOnlyTarget:
    def __init__(self, context):
        self.hostname = context["aap_origin"]
        self.calls = []
        self.template = {"id": 21, "name": "Simulate Website Outage", "project": 2,
                         "playbook": "playbooks/inject_website_fault.yml", "webhook_service": "gitlab"}
        identity = "33333333-2222-3333-4444-555555555555"
        self.stream = {"uuid": identity, "name": "Selected Stream", "organization": {"name": "Example"},
            "url": self.hostname + "/eda-event-streams/api/eda/v1/external_event_stream/" + identity + "/post/",
            "eda_credential": {"name": "Selected Basic", "inputs": {"username": "stream-user", "password": "$encrypted$"}}}
        self.kind = {"id": 1, "kind": "ssh", "managed": True}
        self.credential = {"id": 4, "name": "Base guest Machine", "credential_type": 1}

    def rows(self, path):
        self.calls.append(("GET", path))
        parsed = urlsplit(path)
        query = parse_qs(parsed.query)
        if parsed.path.endswith("/credentials/"):
            assert query["name"] == ["Base guest Machine"]
            return [deepcopy(self.credential)]
        if parsed.path.endswith("/projects/"):
            return [{"id": 2, "name": "Self Healing"}]
        if parsed.path.endswith("/job_templates/"):
            assert query == {"name": ["Simulate Website Outage"], "project": ["2"]}
            return [deepcopy(self.template)]
        if parsed.path.endswith("/event-streams/"):
            return [deepcopy(self.stream)]
        raise AssertionError(path)

    def request(self, method, path, body=None):
        assert method == "GET" and body is None, "Preparation must never create or rotate target API resources."
        self.calls.append((method, path))
        if path == "/api/controller/v2/credential_types/1/":
            return deepcopy(self.kind)
        if path == "/api/controller/v2/job_templates/21/webhook_key/":
            return {"webhook_key": "native-target-webhook-key-unchanged"}
        raise AssertionError(path)


def resources(password):
    return {"controller_templates": [{"name": "Simulate Website Outage", "project": "Self Healing",
        "playbook": "playbooks/inject_website_fault.yml", "webhook_service": "gitlab"}],
        "eda_event_streams": [{"name": "Selected Stream", "organization": "Example", "credential_name": "Selected Basic"}],
        "eda_credentials": [{"name": "Selected Basic", "inputs": {"auth_type": "basic", "username": "stream-user",
                                                                       "password": password}}]}


class InstancePreparationTests(unittest.TestCase):
    def prepare(self, capture=None, runtime=None, context=None, source_hosts=None):
        default, old, old_runtime, _, _ = fixture()
        return settings.prepare_documents(capture or old, runtime or old_runtime, context or default,
            "Base guest Machine", source_hosts, password_factory=lambda: "new-synthetic-password-" + "x" * 48)

    def test_names_come_from_selected_allocation_not_inventory_alias(self):
        context, _, _, instance, hypervisor = fixture()
        self.assertEqual(context["website_fqdn"], "redhat.v07.example.invalid")
        self.assertEqual(context["zabbix_fqdn"], "zabbix.v07.example.invalid")
        for field, bad in [("aap_instance_number", True), ("ansible_fqdn", "aap27.v08.example.invalid"),
                           ("vm_uuid", "44444444-2222-3333-4444-555555555555")]:
            candidate = deepcopy(instance)
            candidate[field] = bad
            with self.assertRaises(Exception):
                settings.selected_context(candidate, hypervisor, context["aap_origin"], "example.invalid", {}, "aap27-v07")

    def test_old_actual_url_is_allowed_only_for_already_saved_instance(self):
        context, _, _, instance, hypervisor = fixture()
        instance["ansible_fqdn"] = context["instance_name"] + ".example.invalid"
        origin = "https://" + instance["ansible_fqdn"]
        with self.assertRaises(Exception):
            settings.selected_context(instance, hypervisor, origin, "example.invalid", {}, "aap27-v07")
        accepted = settings.selected_context(instance, hypervisor, origin, "example.invalid", {context["instance_name"]: {}}, "aap27-v07")
        self.assertEqual(accepted["aap_origin"], origin)

    def test_native_decimal_text_counter_reuses_inventory_normalization(self):
        context, _, _, instance, hypervisor = fixture()
        instance["aap_instance_number"] = "7"
        self.assertEqual(settings.selected_context(instance, hypervisor, context["aap_origin"],
            "example.invalid", {}, "aap27-v07"), context)
        self.assertEqual(instance["aap_instance_number"], "7")
        for value in (True, 7.0, "07", "+7", " 7", "7.0", "٧", "7\n", "7" * 64):
            instance["aap_instance_number"] = value
            with self.subTest(value=value), self.assertRaises(Exception):
                settings.selected_context(instance, hypervisor, context["aap_origin"], "example.invalid", {}, "aap27-v07")

    def test_first_import_needs_no_fabricated_guest_or_artifact(self):
        context, capture, runtime, _, _ = fixture()
        before = deepcopy((capture, runtime))
        after, protected = self.prepare(capture, runtime)
        row = after["aiops_instances"][context["instance_name"]]
        self.assertEqual(set(row), {"guest_machine_credential_name", "testserver_monitoring_enabled", "event_stream_password"})
        self.assertIs(row["testserver_monitoring_enabled"], False)
        self.assertEqual(protected["instances"], {context["instance_name"]: {}})
        self.assertEqual((capture, runtime), before)
        self.assertIsInstance(after["unrelated"]["injector"], AnsibleUnsafeText)

    def test_password_is_saved_once_and_rerun_does_not_generate_or_rotate(self):
        context, _, _, _, _ = fixture()
        first, runtime = self.prepare()
        def forbidden():
            raise AssertionError("A retry must not generate another password.")
        after, protected = settings.prepare_documents(first, runtime, context, "Base guest Machine", password_factory=forbidden)
        self.assertEqual((after, protected), (first, runtime))

    def test_existing_password_and_all_other_instance_data_remain_unchanged(self):
        context, capture, runtime, _, _ = fixture()
        legacy_name = "aap27-test-6"
        capture["aiops_instances"][legacy_name] = {"guest_machine_credential_name": "Old base", "tra": {"keep": True}}
        runtime["instances"][legacy_name] = {"demo_zabbix_event_stream": {"password": capture["aiops_event_stream_password"]},
                                           "demo_claude_vertex_auth": {"adc": wrap_var("{{ literal-only }}")}}
        after, protected = self.prepare(capture, runtime)
        expected = dict(capture["aiops_instances"][legacy_name], event_stream_password=capture["aiops_event_stream_password"])
        self.assertEqual(after["aiops_instances"][legacy_name], expected)
        self.assertEqual(protected["instances"][legacy_name], runtime["instances"][legacy_name])
        self.assertNotEqual(after["aiops_instances"][context["instance_name"]]["event_stream_password"],
                            capture["aiops_event_stream_password"])

    def test_conflicting_legacy_material_refuses_without_input_mutation(self):
        _, capture, runtime, _, _ = fixture()
        capture["aiops_instances"]["aap27-test-6"] = {}
        runtime["instances"]["aap27-test-6"] = {"demo_zabbix_event_stream": {"password": "another-password"}}
        before = deepcopy((capture, runtime))
        with self.assertRaises(Exception): self.prepare(capture, runtime)
        self.assertEqual((capture, runtime), before)

    def test_existing_credential_binding_cannot_silently_change(self):
        context, capture, runtime, _, _ = fixture()
        capture["aiops_instances"][context["instance_name"]] = {"guest_machine_credential_name": "Other credential"}
        with self.assertRaises(Exception): self.prepare(capture, runtime)

    def test_native_source_guest_is_accepted_without_changing_its_identity(self):
        context, _, _, _, _ = fixture()
        source = guest(context)
        after, _ = self.prepare(source_hosts={"testserver1-v07": source})
        self.assertEqual(after["aiops_instances"][context["instance_name"]]["testserver1"], source["vm_resource"])
        self.assertNotIn("tra", after["aiops_instances"][context["instance_name"]])

    def test_copied_foreign_unverified_or_conflicting_guest_is_rejected(self):
        context, capture, runtime, _, _ = fixture()
        original = guest(context)
        for path, value in [(('vm_resource', 'vm_name'), 'testserver1-v06'),
                            (('vm_resource', 'verified'), False),
                            (('vm_resource', 'hypervisor_machine_id'), 'd' * 32),
                            (('machine_id',), 'd' * 32), (('aap_instance_number',), 8)]:
            candidate = deepcopy(original)
            target = candidate
            for field in path[:-1]: target = target[field]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(Exception):
                self.prepare(capture, runtime, source_hosts={"testserver1-v07": candidate})

    def test_same_identity_cannot_be_reused_under_another_allocation(self):
        context, capture, runtime, _, _ = fixture()
        original = guest(context)
        capture["aiops_instances"]["aap27-test-6"] = {"testserver1": deepcopy(original["vm_resource"])}
        with self.assertRaises(Exception):
            self.prepare(capture, runtime, source_hosts={"testserver1-v07": original})

    def test_empty_future_namespace_does_not_inherit_legacy_password(self):
        context, capture, runtime, _, _ = fixture()
        capture["aiops_instances"][context["instance_name"]] = {"guest_machine_credential_name": "Base guest Machine"}
        after, _ = self.prepare(capture, runtime)
        self.assertNotEqual(after["aiops_instances"][context["instance_name"]]["event_stream_password"],
                            capture["aiops_event_stream_password"])

    def test_existing_verified_instance_without_known_secret_is_preserved_for_review(self):
        context, capture, runtime, _, _ = fixture()
        capture["aiops_instances"][context["instance_name"]] = {"guest_machine_credential_name": "Base guest Machine",
            "testserver1": guest(context)["vm_resource"]}
        with self.assertRaises(Exception): self.prepare(capture, runtime)

    def test_native_zabbix_fields_and_string_ids_remain_its_own_provenance(self):
        context, capture, runtime, _, _ = fixture()
        capture["aiops_zabbix_source_image"] = {"sha256": "c" * 64}
        source = zabbix_guest(context)
        source["aap_instance_number"] = "7"
        after, _ = self.prepare(capture, runtime, source_hosts={"zabbix-v07": source})
        self.assertEqual(after["aiops_instances"][context["instance_name"]]["zabbix"], source["vm_resource"])
        self.assertNotIn("source_image_sha256", after["aiops_instances"][context["instance_name"]]["zabbix"])
        for field, bad in [("schema_version", True), ("source_sha256", "d" * 64),
                           ("api_url", "http://192.168.70.99/api_jsonrpc.php"), ("public_hostname", "foreign.example.invalid"),
                           ("guest_host_keys", ["ssh-ed25519 CCCC"]), ("trigger_id", "-3")]:
            candidate = deepcopy(source)
            candidate["vm_resource"][field] = bad
            with self.subTest(field=field), self.assertRaises(Exception):
                self.prepare(capture, runtime, source_hosts={"zabbix-v07": candidate})

    def test_read_native_resources_and_preserve_webhook_on_retry(self):
        context, _, _, _, _ = fixture()
        capture, runtime = self.prepare()
        password = capture["aiops_instances"][context["instance_name"]]["event_stream_password"]
        client = ReadOnlyTarget(context)
        native = settings.target_readbacks(client, context, resources(password))
        after, protected = settings.complete_documents(capture, runtime, context, native)
        again = settings.complete_documents(after, protected, context, native)
        self.assertEqual(again, (after, protected))
        self.assertEqual(protected["instances"][context["instance_name"]]["demo_website_fault_template_id"], 21)
        self.assertTrue(all(method == "GET" for method, _ in client.calls))
        self.assertIsInstance(native["demo_website_webhook_key"], AnsibleUnsafeText)

    def test_native_stream_explicit_default_https_port_preserves_canonical_url(self):
        context, _, _, _, _ = fixture()
        client = ReadOnlyTarget(context)
        canonical = client.stream["url"]
        client.stream["url"] = canonical.replace(context["aap_fqdn"], context["aap_fqdn"] + ":443")
        readback = settings.target_readbacks(client, context, resources("x" * 64))
        self.assertEqual(readback["demo_zabbix_event_stream"]["url"], canonical)
        capture, runtime = self.prepare()
        password = capture["aiops_instances"][context["instance_name"]]["event_stream_password"]
        readback = settings.target_readbacks(ReadOnlyTarget(context), context, resources(password))
        capture, runtime = settings.complete_documents(capture, runtime, context, readback)
        runtime["instances"][context["instance_name"]]["demo_zabbix_event_stream"]["url"] = client.stream["url"]
        expected = deepcopy(runtime)
        _, unchanged = settings.complete_documents(capture, runtime, context, readback)
        self.assertEqual(unchanged, expected)
        for suffix in (":444", ":0443", ":443@foreign.example.invalid"):
            client.stream["url"] = canonical.replace(context["aap_fqdn"], context["aap_fqdn"] + suffix)
            with self.subTest(suffix=suffix), self.assertRaises(Exception):
                settings.target_readbacks(client, context, resources("x" * 64))

    def test_foreign_native_urls_or_projects_are_never_substituted(self):
        context, _, _, _, _ = fixture()
        for field in ("url", "project", "hostname", "organization", "credential"):
            client = ReadOnlyTarget(context)
            if field == "url": client.stream["url"] = client.stream["url"].replace("v07", "v06")
            elif field == "project": client.template["project"] = 99
            elif field == "hostname": client.hostname = "https://foreign.example.invalid"
            elif field == "credential": client.stream["eda_credential"]["name"] = "Other Basic"
            else: client.stream["organization"]["name"] = "Other organization"
            with self.subTest(field=field), self.assertRaises(Exception):
                settings.target_readbacks(client, context, resources("x" * 64))

    def test_existing_native_webhook_or_stream_identity_cannot_be_rotated(self):
        context, _, _, _, _ = fixture()
        capture, runtime = self.prepare()
        password = capture["aiops_instances"][context["instance_name"]]["event_stream_password"]
        native = settings.target_readbacks(ReadOnlyTarget(context), context, resources(password))
        capture, runtime = settings.complete_documents(capture, runtime, context, native)
        for field, value in [("demo_website_fault_template_id", 99),
                             ("demo_website_webhook_key", "different-native-webhook-value")]:
            candidate = dict(native, **{field: value})
            with self.assertRaises(Exception): settings.complete_documents(capture, runtime, context, candidate)

    def test_base_machine_credential_is_existing_native_type_and_read_only(self):
        context, _, _, _, _ = fixture()
        client = ReadOnlyTarget(context)
        self.assertEqual(settings.base_machine_credential(client, "Base guest Machine"), "Base guest Machine")
        client.kind["managed"] = False
        with self.assertRaises(Exception): settings.base_machine_credential(client, "Base guest Machine")
        self.assertTrue(all(method == "GET" for method, _ in client.calls))


class EncryptedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="aiops-data-publication-test-")
        self.root = Path(self.temporary.name)
        self.bare = self.root / "remote.git"
        self.workspace = self.root / "aap-project-cac-synthetic"
        self.workspace.mkdir(mode=0o700)
        self.checkout = self.workspace / "repository"
        self.context, capture, runtime, self.instance, self.hypervisor = fixture()
        capture.update(aiops_website_dns_zone="example.invalid", aiops_guest_machine_credential_name="Base guest Machine",
                       aiops_configuration_ready=True)
        capture["cac_import_metadata"] = {"schema_version": 1, "project_id": "aiops-selfhealing-demo",
            "required_template_label": "synthetic-aiops", "resource_variables": {"controller_templates": "synthetic_templates"},
            "checks": {}, "capabilities": {}}
        capture["synthetic_templates"] = []
        capture["aiops_instances"]["aap27-test-6"] = {"guest_machine_credential_name": "Previous base",
            "unrelated_literal": wrap_var("{{ protected_existing_literal }}")}
        runtime["instances"]["aap27-test-6"] = {"demo_zabbix_event_stream": {"password": capture["aiops_event_stream_password"]}}
        self.vault = VaultLib([("cac", VaultSecret(b"synthetic-capture-password")),
                               ("default", VaultSecret(b"synthetic-runtime-password"))])
        spec = importlib.util.spec_from_file_location("tested_aiops_action", ROOT / "action_plugins/aap_cac_prepare_aiops.py")
        self.plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.plugin)
        self.git("init", "--quiet", "--bare", "--initial-branch=main", str(self.bare))
        self.git("clone", "--quiet", str(self.bare), str(self.checkout))
        self.write_pair(self.checkout, capture, runtime)
        self.git("-C", str(self.checkout), "add", "--all")
        self.commit(self.checkout, "Initial encrypted fixture")
        self.git("-C", str(self.checkout), "push", "--quiet", "origin", "main")
        self.git("-C", str(self.checkout), "remote", "set-url", "origin", "https://example.invalid/aiops-secrets.git")
        self.git("-C", str(self.checkout), "config", "url." + str(self.bare) + ".insteadOf",
                 "https://example.invalid/aiops-secrets.git")
        askpass = self.workspace / "git-askpass"
        askpass.write_text("#!/bin/sh\nexit 1\n")
        askpass.chmod(0o700)
        self.variables = {**deepcopy(capture), "cac_workspace": {"path": str(self.workspace)},
            "cac_project_contract": {"project_id": "aiops-selfhealing-demo", "configuration_file": self.plugin.CAPTURE,
                                     "repository": "https://example.invalid/aiops-secrets.git"},
            "aap_instance_key": "aap27-v07",
            "hostvars": {"aap27-v07": self.instance, "recovery-host": self.hypervisor}}
        self.client = ReadOnlyTarget(self.context)
        self.real_run = subprocess.run

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, checkout, message):
        self.git("-C", str(checkout), "-c", "user.name=Synthetic fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "--quiet", "-m", message)

    def write_pair(self, checkout, capture, runtime):
        runtime_path = checkout / self.plugin.RUNTIME
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_bytes(self.vault.encrypt(yaml.dump(runtime, Dumper=self.plugin.vault_yaml.VaultDumper,
                                                             sort_keys=False).encode(), secret=self.vault.secrets[1][1]))
        capture = deepcopy(capture)
        capture["aiops_runtime_settings_vault"] = runtime_path.read_text()
        capture_path = checkout / self.plugin.CAPTURE
        capture_path.parent.mkdir(parents=True, exist_ok=True)
        capture_path.write_bytes(self.vault.encrypt(yaml.dump(capture, Dumper=self.plugin.vault_yaml.VaultDumper,
                                                             sort_keys=False).encode(), secret=self.vault.secrets[0][1], vault_id="cac"))

    def remote_pair(self):
        capture = self.git("--git-dir", str(self.bare), "show", "main:" + self.plugin.CAPTURE).encode() + b"\n"
        runtime = self.git("--git-dir", str(self.bare), "show", "main:" + self.plugin.RUNTIME).encode() + b"\n"
        return (AnsibleLoader(self.vault.decrypt(capture)).get_single_data(),
                AnsibleLoader(self.vault.decrypt(runtime)).get_single_data(), capture, runtime)

    def action(self, operation="pre", vault=None):
        action = object.__new__(self.plugin.ActionModule)
        action._task = SimpleNamespace(check_mode=False, args={"operation": operation, "authentication": {
            "hostname": self.context["aap_origin"], "token": "synthetic-api-token", "username": "", "password": ""}})
        action._loader = DataLoader()
        action._loader.set_vault_secrets((vault or self.vault).secrets)
        action._templar = SimpleNamespace(available_variables={}, template=deepcopy)
        with mock.patch.object(ActionBase, "run", return_value={}), \
                mock.patch.object(self.plugin.settings.lifecycle, "Client", return_value=self.client), \
                mock.patch.dict(os.environ, {"CAC_GIT_TOKEN": "synthetic-private-repository-token"}):
            return action.run(task_vars=self.variables)

    def test_actual_git_two_vaults_literal_preservation_and_idempotence(self):
        before_capture, before_runtime, _, _ = self.remote_pair()
        result = self.action()
        self.assertTrue(result["prepared"])
        capture, runtime, cipher, runtime_cipher = self.remote_pair()
        selected = capture["aiops_instances"][self.context["instance_name"]]
        self.assertEqual(set(selected), {"guest_machine_credential_name", "event_stream_password", "testserver_monitoring_enabled"})
        self.assertEqual(runtime["instances"][self.context["instance_name"]], {})
        self.assertEqual(capture["unrelated"], before_capture["unrelated"])
        self.assertEqual(runtime["instances"]["aap27-test-6"], before_runtime["instances"]["aap27-test-6"])
        self.assertTrue(cipher.startswith(b"$ANSIBLE_VAULT;1.2;AES256;cac\n"))
        self.assertTrue(runtime_cipher.startswith(b"$ANSIBLE_VAULT;1.1;AES256\n"))
        self.assertEqual(capture["aiops_runtime_settings_vault"], runtime_cipher.decode())
        self.assertNotIn(selected["event_stream_password"].encode(), cipher + runtime_cipher)
        accepted = self.git("--git-dir", str(self.bare), "rev-parse", "main")
        self.assertFalse(self.action()["changed"])
        self.assertEqual(self.git("--git-dir", str(self.bare), "rev-parse", "main"), accepted)
        self.assertFalse(list(self.checkout.rglob(".aiops-settings-*")))
        self.assertEqual(self.git("-C", str(self.checkout), "status", "--porcelain"), "")

    def test_post_reads_native_ids_then_publishes_ciphertext_and_preserves_key(self):
        self.action()
        capture, runtime, _, _ = self.remote_pair()
        password = capture["aiops_instances"][self.context["instance_name"]]["event_stream_password"]
        self.variables["cac_import_resources"] = resources(password)
        self.assertTrue(self.action("post")["prepared"])
        capture, runtime, _, cipher = self.remote_pair()
        selected = runtime["instances"][self.context["instance_name"]]
        self.assertEqual(selected["demo_website_fault_template_id"], 21)
        self.assertEqual(selected["demo_zabbix_event_stream"]["password"], password)
        self.assertEqual(capture["aiops_runtime_settings_vault"], cipher.decode())
        self.assertFalse(self.action("post")["changed"])
        self.assertTrue(all(method == "GET" for method, _ in self.client.calls))

    def test_lost_push_acknowledgement_reuses_accepted_password(self):
        calls = 0
        def lost_response(args, **kwargs):
            nonlocal calls
            response = self.real_run(args, **kwargs)
            if len(args) > 3 and args[0] == "git" and args[3] == "push":
                calls += 1
                return subprocess.CompletedProcess(args, 1, response.stdout, "synthetic connection lost after acceptance")
            return response
        with mock.patch.object(self.plugin.subprocess, "run", side_effect=lost_response), \
                mock.patch.object(self.plugin.settings.secrets, "token_urlsafe", return_value="synthetic-accepted-password-" + "x" * 48) as generator:
            self.assertTrue(self.action()["prepared"])
            self.assertEqual(generator.call_count, 1)
        self.assertEqual(calls, 1)
        capture, _, _, _ = self.remote_pair()
        self.assertEqual(capture["aiops_instances"][self.context["instance_name"]]["event_stream_password"],
                         "synthetic-accepted-password-" + "x" * 48)

    def test_concurrent_encrypted_update_is_preserved_without_force(self):
        competitor = self.root / "competitor"
        self.git("clone", "--quiet", str(self.bare), str(competitor))
        pushed = False
        calls = []
        def competing_push(args, **kwargs):
            nonlocal pushed
            if args[0] == "git":
                calls.append(args)
            if len(args) > 3 and args[0] == "git" and args[3] == "push" and not pushed:
                pushed = True
                old_capture, old_runtime, _, _ = self.remote_pair()
                old_capture["concurrent_literal"] = wrap_var("{{ other_writer_preserved }}")
                old_runtime["instances"]["aap27-test-6"]["demo_website_fault_template_id"] = 66
                self.write_pair(competitor, old_capture, old_runtime)
                self.git("-C", str(competitor), "add", "--all")
                self.commit(competitor, "Concurrent encrypted update")
                self.git("-C", str(competitor), "push", "--quiet", "origin", "main")
            return self.real_run(args, **kwargs)
        with mock.patch.object(self.plugin.subprocess, "run", side_effect=competing_push):
            self.assertTrue(self.action()["prepared"])
        capture, runtime, _, _ = self.remote_pair()
        self.assertEqual(capture["concurrent_literal"], "{{ other_writer_preserved }}")
        self.assertIsInstance(capture["concurrent_literal"], AnsibleUnsafeText)
        self.assertEqual(runtime["instances"]["aap27-test-6"]["demo_website_fault_template_id"], 66)
        self.assertFalse(any("--force" in arg or arg.startswith("+") for args in calls for arg in args))

    def test_denied_writer_cannot_precede_role_credential_creation(self):
        initial = self.git("--git-dir", str(self.bare), "rev-parse", "main")
        def denied_push(args, **kwargs):
            if len(args) > 3 and args[0] == "git" and args[3] == "push":
                return subprocess.CompletedProcess(args, 1, "", "403 write access denied")
            return self.real_run(args, **kwargs)
        with mock.patch.object(self.plugin.subprocess, "run", side_effect=denied_push), self.assertRaises(AnsibleActionFail):
            self.action()
        self.assertEqual(self.git("--git-dir", str(self.bare), "rev-parse", "main"), initial)
        # The failed checkout remains private and will be removed by the existing
        # importer always block. No target POST/PATCH was possible in this action.
        self.assertTrue(all(method == "GET" for method, _ in self.client.calls))

    def test_wrong_runtime_key_preserves_accepted_git_state_and_exposes_no_secret(self):
        initial = self.git("--git-dir", str(self.bare), "rev-parse", "main")
        wrong = VaultLib([self.vault.secrets[0], ("default", VaultSecret(b"wrong-runtime-password"))])
        with self.assertRaisesRegex(AnsibleActionFail, "preparation failed") as raised:
            self.action(vault=wrong)
        self.assertNotIn("legacy-password", str(raised.exception))
        self.assertEqual(self.git("--git-dir", str(self.bare), "rev-parse", "main"), initial)
        self.assertFalse(self.client.calls)

    def test_review_hold_refuses_before_any_commit_or_target_access(self):
        for hold in ("configuration_ready", "declared_review_items"):
            with self.subTest(hold=hold):
                before_capture, before_runtime, _, _ = self.remote_pair()
                if hold == "configuration_ready":
                    before_capture["aiops_configuration_ready"] = False
                else:
                    before_capture["aiops_configuration_ready"] = True
                    before_capture["review_items"] = ["operator review is still required"]
                    before_capture["cac_import_metadata"]["checks"] = {"empty_lists": ["review_items"]}
                self.write_pair(self.checkout, before_capture, before_runtime)
                self.git("-C", str(self.checkout), "add", "--all")
                self.commit(self.checkout, "Retain operator review hold")
                self.git("-C", str(self.checkout), "push", "--quiet", "origin", "HEAD:refs/heads/main")
                head = self.git("--git-dir", str(self.bare), "rev-parse", "main")
                with self.assertRaises(AnsibleActionFail): self.action()
                self.assertEqual(self.git("--git-dir", str(self.bare), "rev-parse", "main"), head)
                self.assertFalse(self.client.calls)

    def test_launch_review_hold_overrides_ready_capture_before_any_commit(self):
        initial = self.git("--git-dir", str(self.bare), "rev-parse", "main")
        self.variables["aiops_configuration_ready"] = False
        with self.assertRaises(AnsibleActionFail): self.action()
        self.assertEqual(self.git("--git-dir", str(self.bare), "rev-parse", "main"), initial)
        self.assertFalse(self.client.calls)

    def test_actual_ansible_action_in_both_native_modes(self):
        for native in ("false", "true"):
            with self.subTest(native=native):
                fixture_case = EncryptedPublicationTests()
                fixture_case.setUp()
                try:
                    fixture_case.native_action(native)
                finally:
                    fixture_case.tearDown()

    def native_action(self, native):
        plugin_dir = self.root / "action_plugins"
        plugin_dir.mkdir()
        wrapper = plugin_dir / "aap_cac_prepare_aiops.py"
        wrapper.write_text(
            "from importlib.util import module_from_spec, spec_from_file_location\n"
            "spec = spec_from_file_location('native_aiops_action', " + repr(str(ROOT / 'action_plugins/aap_cac_prepare_aiops.py')) + ")\n"
            "module = module_from_spec(spec); spec.loader.exec_module(module)\n"
            "spec = spec_from_file_location('native_aiops_fixtures', " + repr(str(Path(__file__).resolve())) + ")\n"
            "fixtures = module_from_spec(spec); spec.loader.exec_module(fixtures)\n"
            "context = fixtures.fixture()[0]\n"
            "module.settings.lifecycle.Client = lambda *args: fixtures.ReadOnlyTarget(context)\n"
            "ActionModule = module.ActionModule\n")
        inventory = self.root / "inventory.yml"
        inventory.write_text(yaml.dump({"all": {"hosts": {
            "localhost": {"ansible_connection": "local"},
            "aap27-v07": self.instance, "recovery-host": self.hypervisor}}}))
        capture_key, runtime_key = self.root / "capture-key", self.root / "runtime-key"
        capture_key.write_text("synthetic-capture-password")
        runtime_key.write_text("synthetic-runtime-password")
        runtime_key.chmod(0o600)
        capture_key.chmod(0o600)
        password = "{{ aiops_instances['aap27-test-7'].event_stream_password }}"
        variables = {key: value for key, value in self.variables.items() if key != "hostvars"}
        variables["cac_import_resources"] = resources(password)
        playbook = self.root / "fixture.yml"
        playbook.write_text(yaml.dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
            "vars": variables, "tasks": [
                {"name": "Prepare encrypted selected namespace before any roles", "aap_cac_prepare_aiops": {
                    "operation": "pre", "authentication": {"hostname": self.context["aap_origin"],
                    "token": "synthetic-api-token", "username": "", "password": ""}}, "no_log": True},
                {"name": "Reload accepted capture for native nested rendering", "ansible.builtin.include_vars": {
                    "file": str(self.checkout / self.plugin.CAPTURE)}, "no_log": True},
                {"name": "Retain native target identifiers after simulated existing roles", "aap_cac_prepare_aiops": {
                    "operation": "post", "authentication": {"hostname": self.context["aap_origin"],
                    "token": "synthetic-api-token", "username": "", "password": ""}}, "no_log": True},
            ]}], Dumper=self.plugin.vault_yaml.VaultDumper, sort_keys=False))
        environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(self.root / "local"),
            ANSIBLE_REMOTE_TEMP=str(self.root / "remote"), ANSIBLE_ACTION_PLUGINS=str(plugin_dir) + ":" + str(ROOT / "action_plugins"),
            ANSIBLE_JINJA2_NATIVE=native, ANSIBLE_NOCOLOR="1", CAC_GIT_TOKEN="synthetic-private-repository-token")
        result = subprocess.run(["python3.12", "-m", "ansible.cli.playbook", "-i", str(inventory),
            "--vault-id", "cac@" + str(capture_key), "--vault-id", "default@" + str(runtime_key), str(playbook)],
            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        capture, runtime, _, runtime_cipher = self.remote_pair()
        selected = runtime["instances"][self.context["instance_name"]]
        self.assertEqual(selected["demo_website_fault_template_id"], 21)
        self.assertEqual(selected["demo_zabbix_event_stream"]["password"],
                         capture["aiops_instances"][self.context["instance_name"]]["event_stream_password"])
        self.assertEqual(capture["aiops_runtime_settings_vault"], runtime_cipher.decode())
        self.assertNotIn(selected["demo_zabbix_event_stream"]["password"], result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
