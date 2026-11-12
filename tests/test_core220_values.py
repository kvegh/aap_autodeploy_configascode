"""Accept native core 2.20 YAML integers without accepting booleans as IDs."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest

from ansible.errors import AnsibleFilterError


ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


yaml_values = load("core220_yaml_values", "src/cac_yaml.py")
allocation = load("core220_allocation", "src/aap_name_allocation.py")
route = load("core220_route", "filter_plugins/aap_instance_route.py")
metadata = load("core220_metadata", "filter_plugins/cac_import.py")
identity = load("core220_identity", "filter_plugins/aap_inventory_identity.py")
keys = load("core220_keys", "src/aap_instance_keys.py")
aiops = load("core220_aiops", "src/aap_aiops_settings.py")
setup = load("core220_setup", "filter_plugins/use_case_setup.py")


class Core220ValueTests(unittest.TestCase):
    def test_reservation_accepts_yaml_counter_and_keeps_prior_allocation_unchanged(self):
        state = yaml_values.load_repository_yaml(
            "schema_version: 1\nnext_number: 19\nreservations:\n"
            "  previous:\n    number: 18\n    vm_name: aap27-test-18\n"
        )
        # Ansible 2.20 carries source metadata on integer subclasses. This test
        # must exercise those values, rather than ordinary Python-only fixtures.
        self.assertIsInstance(state["next_number"], int)
        self.assertIsNot(type(state["next_number"]), int)
        before = copy.deepcopy(state)
        updated, record = allocation.reserve(
            state, "aap27-test", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "a" * 32,
            state["next_number"],
        )
        self.assertEqual(record["number"], 19)
        self.assertEqual(updated["next_number"], 20)
        self.assertEqual(updated["reservations"]["previous"], before["reservations"]["previous"])
        self.assertEqual(state, before)

    def test_reservation_still_refuses_boolean_counters_floors_and_history(self):
        original = {"schema_version": 1, "next_number": 19, "reservations": {
            "previous": {"number": 18, "vm_name": "aap27-test-18"},
        }}
        for value in (True, False, 19.0, "19"):
            for field in ("next_number", "floor", "history"):
                with self.subTest(value=value, field=field):
                    state = copy.deepcopy(original)
                    floor = 19
                    if field == "floor":
                        floor = value
                    elif field == "history":
                        state["reservations"]["previous"]["number"] = value
                    else:
                        state[field] = value
                    with self.assertRaises(ValueError):
                        allocation.reserve(state, "aap27-test",
                                           "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "a" * 32, floor)

    def test_pinned_hypervisor_accepts_yaml_port_and_refuses_boolean_port(self):
        pin = yaml_values.load_repository_yaml(
            "address: 192.0.2.10\npublic_ip: 198.51.100.20\nuser: operator\n"
            "port: 22\nmachine_id: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "host_keys: ['ssh-ed25519 AAAA']\nisolation_bridges: [virbr0]\n"
            "isolation_dns_bridges: [virbr0]\n"
        )
        self.assertEqual(route.hypervisor_pin(pin), pin)
        for value in (True, False, 22.0, "22"):
            with self.subTest(value=value), self.assertRaises(AnsibleFilterError):
                route.hypervisor_pin(dict(pin, port=value))

    def test_native_access_plan_accepts_loaded_port_without_accepting_boolean(self):
        from test_aap_hypervisor_access import fixture

        expected, observed, *_ = fixture()
        original = allocation.ownership.plan(expected, observed)
        loaded = yaml_values.load_repository_yaml(json.dumps({
            "expected": expected, "observed": observed,
        }))
        port = loaded["expected"]["route"]["hypervisor"]["port"]
        self.assertIsInstance(port, int)
        self.assertIsNot(type(port), int)
        self.assertEqual(allocation.ownership.plan(loaded["expected"], loaded["observed"]), original)
        for invalid in (True, False, 2222.0, "2222"):
            changed = copy.deepcopy(loaded["expected"])
            changed["route"]["hypervisor"]["port"] = invalid
            with self.subTest(port=invalid), self.assertRaises(ValueError):
                allocation.ownership.plan(changed, loaded["observed"])

    def test_import_metadata_accepts_yaml_schema_counts_and_rejects_booleans(self):
        config = yaml_values.load_repository_yaml(
            "schema_version: 1\nproject_id: assistant-team\nrequired_template_label: fixture\n"
            "resource_variables:\n  controller_templates: captured.templates\n"
            "checks:\n  resource_counts:\n    controller_templates: 1\ncapabilities: {}\n"
        )
        metadata.import_metadata(config, "assistant-team")
        for field in ("schema", "count"):
            for value in (True, False, 1.0, "1"):
                bad = copy.deepcopy(config)
                if field == "schema":
                    bad["schema_version"] = value
                else:
                    bad["checks"]["resource_counts"]["controller_templates"] = value
                with self.subTest(field=field, value=value), self.assertRaises(AnsibleFilterError):
                    metadata.import_metadata(bad, "assistant-team")

    def test_inventory_and_api_ids_accept_yaml_integers_without_boolean_coercion(self):
        value = yaml_values.load_repository_yaml("number: 22\n")["number"]
        self.assertEqual(identity.inventory_counter(value), 22)
        self.assertEqual(keys.canonical_api_port(value), 22)
        self.assertTrue(aiops.positive_id(value))
        for invalid in (True, False, 22.0, 0, -1):
            with self.subTest(value=invalid):
                self.assertFalse(aiops.positive_id(invalid))
                with self.assertRaises(AnsibleFilterError):
                    identity.inventory_counter(invalid)
                with self.assertRaises(keys.StoreError):
                    keys.canonical_api_port(invalid)

    def test_native_credential_selection_accepts_yaml_ids_and_rejects_booleans(self):
        credentials = yaml_values.load_repository_yaml(
            "- id: 12\n  name: AAP API/MCP Auth Token Store\n  credential_type: 46\n"
            "  summary_fields:\n    credential_type:\n      name: Pseudo Instance Key Store\n"
        )
        self.assertEqual(setup.instance_store_credentials(credentials), credentials)
        for field in ("id", "credential_type"):
            for invalid in (True, False, 12.0, "12"):
                changed = copy.deepcopy(credentials)
                changed[0][field] = invalid
                with self.subTest(field=field, value=invalid), self.assertRaises(AnsibleFilterError):
                    setup.instance_store_credentials(changed)


if __name__ == "__main__":
    unittest.main()
