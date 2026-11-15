"""Private owner state must catch import-generated keys outside the AAP disk."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_owner_snapshots', ROOT/'src/aap_snapshot_owner_state.py')
owner = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(owner)
SELECTED = 'aap27-test-23'
SECRET = 'synthetic-runtime-vault-key'


def aiops():
    runtime = {'schema_version': 1, 'instances': {SELECTED: {'demo_website_webhook_key': 'synthetic-webhook',
                                                          'demo_zabbix_event_stream': {'url': 'https://aap.example.invalid/events/synthetic/'}}}}
    vault = VaultLib([('default', VaultSecret(SECRET.encode()))])
    return {'cac_import_metadata': {'project_id': 'aiops-selfhealing-demo'}, 'aiops_playbook_vault_password': SECRET,
            'aiops_instances': {SELECTED: {'event_stream_password': 'synthetic-stream-password'}},
            'aiops_runtime_settings_vault': vault.encrypt(yaml.safe_dump(runtime).encode()).decode()}, runtime, vault


class OwnerStateTests(unittest.TestCase):
    def test_selected_webhook_stream_and_ids_block_rollback_when_import_changes_them(self):
        capture, runtime, vault = aiops(); before = owner.selected_state('aiops', capture, SELECTED)
        for field, value in [('demo_website_webhook_key', 'changed'), ('demo_website_fault_template_id', 17),
                             ('demo_zabbix_event_stream', {'url': 'https://aap.example.invalid/events/changed/'})]:
            with self.subTest(field=field):
                changed = deepcopy(runtime); changed['instances'][SELECTED][field] = value
                new = dict(capture, aiops_runtime_settings_vault=vault.encrypt(yaml.safe_dump(changed).encode()).decode())
                self.assertNotEqual(owner.selected_state('aiops', new, SELECTED), before)

    def test_aiops_cipher_reencryption_and_other_instance_changes_are_ignored(self):
        capture, runtime, vault = aiops(); before = owner.selected_state('aiops', capture, SELECTED)
        runtime['instances']['aap27-test-24'] = {'demo_website_webhook_key': 'other'}
        capture['aiops_instances']['aap27-test-24'] = {'event_stream_password': 'other'}
        capture['aiops_runtime_settings_vault'] = vault.encrypt(yaml.safe_dump(runtime).encode()).decode()
        self.assertEqual(owner.selected_state('aiops', capture, SELECTED), before)

    def test_private_selected_namespace_creation_and_windows_cipher_change_are_not_invisible(self):
        win = {'cac_import_metadata': {'project_id': 'disconnected-windows-patching'},
               'windows_disconnected_instance_profiles': {}, 'windows_disconnected_runtime_ciphertexts': {}}
        before = owner.selected_state('windows_disconnected', win, SELECTED)
        win['windows_disconnected_instance_profiles'][SELECTED] = {'instance': SELECTED}
        with self.assertRaises(ValueError): owner.selected_state('windows_disconnected', win, SELECTED)
        win['windows_disconnected_runtime_ciphertexts'][SELECTED] = '$ANSIBLE_VAULT;1.1;AES256\nsynthetic-cipher'
        self.assertNotEqual(owner.selected_state('windows_disconnected', win, SELECTED), before)
        selected = owner.selected_state('windows_disconnected', win, SELECTED)
        win['windows_disconnected_instance_profiles']['aap27-test-24'] = {'instance': 'aap27-test-24'}
        win['windows_disconnected_runtime_ciphertexts']['aap27-test-24'] = 'other'
        self.assertEqual(owner.selected_state('windows_disconnected', win, SELECTED), selected)

    def test_literal_scalar_semantics_are_part_of_the_selected_fingerprint(self):
        normal = owner.codec.load_repository_yaml("token: '{{ expression }}'\n")
        literal = owner.codec.load_repository_yaml("token: !unsafe '{{ expression }}'\n")
        self.assertEqual(normal, literal)
        self.assertNotEqual(owner.fingerprint(normal), owner.fingerprint(literal))

    def test_fixed_owner_reader_keeps_authentication_scoped_and_never_pushes(self):
        capture, _, _ = aiops()
        windows = {'cac_import_metadata': {'project_id': 'disconnected-windows-patching'},
                   'windows_disconnected_instance_profiles': {}, 'windows_disconnected_runtime_ciphertexts': {}}
        vault = VaultLib([('default', VaultSecret(b'synthetic-outer-key'))])
        documents = {'aiops': capture, 'windows_disconnected': windows}; calls=[]
        bootstrap = {'cac_bootstrap_git_credentials': {}, 'cac_bootstrap_vault_credentials': {}}
        for name in owner.OWNERS:
            bootstrap['cac_bootstrap_git_credentials'][name] = {'repository_url': 'https://git.example.invalid/team/' + name + '.git', 'token': 'synthetic-' + name}
            bootstrap['cac_bootstrap_vault_credentials'][name] = {'vault_password': 'synthetic-outer-key'}
        def run(args, **kw):
            calls.append((args, kw)); command=args[3]
            self.assertEqual(kw['env']['GIT_CONFIG_VALUE_1'], 'false'); self.assertEqual(kw['env']['GIT_CONFIG_VALUE_2'], 'true')
            self.assertNotIn('synthetic-', ' '.join(args))
            if command=='show':
                name=Path(args[2]).name
                if args[4].endswith('vaults/runtime/aiops-selfhealing-demo-runtime-vault.yml'):
                    return SimpleNamespace(returncode=0, stdout=capture['aiops_runtime_settings_vault'])
                text=yaml.safe_dump(documents[name]); return SimpleNamespace(returncode=0,stdout=vault.encrypt(text.encode()).decode())
            self.assertIn(command, ('init','remote','fetch')); return SimpleNamespace(returncode=0, stdout='')
        with tempfile.TemporaryDirectory() as directory:
            states=owner.read(bootstrap, directory, SELECTED, 'https://git.example.invalid/team/central.git', run)
        self.assertEqual(set(states),set(owner.OWNERS)); self.assertFalse(any('push' in args for args,_ in calls))
        bootstrap['cac_bootstrap_git_credentials']['aiops']['repository_url']='https://foreign.example.invalid/team/private.git'
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            owner.read(bootstrap,directory,SELECTED,'https://git.example.invalid/team/central.git',run)


if __name__=='__main__':unittest.main()
