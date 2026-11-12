"""Verify protected configuration roundtrips on the supported core 2.20 runtime."""

import importlib.util
from pathlib import Path
import unittest

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.template import Templar, is_trusted_as_template


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cac_yaml_under_test", ROOT / "src/cac_yaml.py")
cac_yaml = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cac_yaml)


class ProtectedYamlTests(unittest.TestCase):
    def test_repository_references_evaluate_but_explicit_literals_do_not(self):
        loaded = cac_yaml.load_repository_yaml(
            'ordinary: "{{ fixture_value }}"\n'
            'literal: !unsafe "{{ fixture_value }}"\n'
            'nested:\n  - !unsafe "{% if fixture_value %}literal{% endif %}"\n'
        )
        self.assertTrue(is_trusted_as_template(loaded["ordinary"]))
        self.assertFalse(is_trusted_as_template(loaded["literal"]))
        self.assertEqual(cac_yaml.literal_paths(loaded), {("literal",), ("nested", 0)})
        dumped = yaml.dump(loaded, Dumper=cac_yaml.VaultDumper, sort_keys=False)
        restored = cac_yaml.load_repository_yaml(dumped)
        self.assertEqual(restored, loaded)
        self.assertEqual(cac_yaml.literal_paths(restored), cac_yaml.literal_paths(loaded))
        rendered = Templar(loader=DataLoader(), variables={"fixture_value": "resolved"}).template(restored)
        self.assertEqual(rendered["ordinary"], "resolved")
        self.assertEqual(rendered["literal"], "{{ fixture_value }}")
        self.assertEqual(rendered["nested"], ["{% if fixture_value %}literal{% endif %}"])

    def test_api_text_is_stored_as_literal_without_trusting_it(self):
        # These values originate outside repository configuration. Dumping must
        # never turn them into executable references when the Vault is reloaded.
        values = {"injector": "{{ secret_canary }}", "variables": '{"value":"{{ secret_canary }}"}'}
        restored = cac_yaml.load_repository_yaml(yaml.dump(values, Dumper=cac_yaml.VaultDumper))
        self.assertEqual(cac_yaml.literal_paths(restored), {("injector",), ("variables",)})
        rendered = Templar(loader=DataLoader(), variables={"secret_canary": "must-not-appear"}).template(restored)
        self.assertEqual(rendered, values)

    def test_vault_roundtrip_preserves_values_tags_and_header(self):
        values = cac_yaml.load_repository_yaml('ordinary: "{{ token }}"\nliteral: !unsafe "{{ token }}"\n')
        secret = VaultSecret(b"synthetic-test-password")
        vault = VaultLib([("cac", secret)])
        sealed = vault.encrypt(yaml.dump(values, Dumper=cac_yaml.VaultDumper), secret=secret, vault_id="cac")
        self.assertEqual(sealed.splitlines()[0], b"$ANSIBLE_VAULT;1.2;AES256;cac")
        restored = cac_yaml.load_repository_yaml(vault.decrypt(sealed))
        self.assertEqual(restored, values)
        self.assertEqual(cac_yaml.literal_paths(restored), {("literal",)})

    def test_custom_dump_does_not_mutate_the_vendor_serializer(self):
        value = {"literal": "{{ untrusted_canary }}", "data": [1, False, None]}
        vendor_before = yaml.dump(value, Dumper=AnsibleDumper)
        yaml.dump(value, Dumper=cac_yaml.VaultDumper)
        self.assertEqual(yaml.dump(value, Dumper=AnsibleDumper), vendor_before)


if __name__ == "__main__":
    unittest.main()
