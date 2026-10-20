"""Exercise first install, reuse, collisions and interrupted token storage."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

SOURCE = Path(__file__).resolve().parents[1] / 'library/assistant_lifecycle_token.py'
SPEC = importlib.util.spec_from_file_location('assistant_lifecycle_token', SOURCE)
library = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(library)


class FakeClient:
    hostname = 'https://target.example.invalid'

    def __init__(self, config):
        self.config = config
        self.user = {'id': 11, 'username': config['username'], 'is_superuser': False,
                     'is_platform_auditor': False, 'is_system_auditor': False}
        self.grants = [{'content_type': 'awx.inventory', 'object_id': '23',
                        'summary_fields': {'role_definition': {'name': 'Inventory Admin'}}}]
        self.teams = []
        self.type = dict(config['credential_type'], id=31)
        self.credentials = []
        self.tokens = []
        self.issued = 0
        self.deleted = []
        self.reject_identity = False

    def rows(self, path):
        endpoint = urlsplit(path).path
        if endpoint.endswith('/organizations/'):
            return [{'id': 2, 'name': self.config['organization']}]
        if endpoint.endswith('/inventories/'):
            return [{'id': 23, 'name': self.config['inventory'], 'organization': 2}]
        if endpoint.endswith('/users/'):
            return [copy.deepcopy(self.user)]
        if endpoint.endswith('/role_user_assignments/'):
            return copy.deepcopy(self.grants)
        if endpoint.endswith('/teams/'):
            return copy.deepcopy(self.teams)
        if endpoint.endswith('/credential_types/'):
            return [copy.deepcopy(self.type)]
        if endpoint.endswith('/credentials/'):
            return copy.deepcopy(self.credentials)
        if endpoint.endswith('/tokens/'):
            return copy.deepcopy(self.tokens)
        raise AssertionError('Unexpected endpoint')

    def request(self, method, path, body=None, token=None, basic=None):
        if method == 'POST':
            assert basic == (self.config['username'], self.config['password'])
            assert body == {'description': self.config['description'], 'scope': 'write', 'application': None}
            self.issued += 1
            created = dict(body, id=41, user=11, token='synthetic-private-service-token', expires='2036-01-01T00:00:00Z')
            self.tokens.append(copy.deepcopy(created))
            return created
        if method == 'DELETE':
            self.deleted.append(int(path.rstrip('/').rsplit('/', 1)[-1]))
            self.tokens = [item for item in self.tokens if item['id'] not in self.deleted]
            return {}
        if method == 'GET' and path == '/api/controller/v2/me/':
            if self.reject_identity:
                raise library.LifecycleError('Synthetic identity rejection')
            assert token == 'synthetic-private-service-token'
            return {'results': [copy.deepcopy(self.user)]}
        raise AssertionError('Unexpected request')


class TokenTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.root.chmod(0o700)
        self.ca = self.root / 'ca.pem'
        self.ca.write_text('synthetic-verified-ca')
        self.config = {'username': 'synthetic-inventory-service', 'password': 'synthetic-new-target-password',
                       'inventory': 'Synthetic Inventory', 'organization': 'Synthetic Organization',
                       'credential': 'Synthetic lifecycle credential', 'description': 'Synthetic service access',
                       'credential_type': {'name': 'Synthetic lifecycle type', 'kind': 'cloud',
                                           'inputs': {'fields': []}, 'injectors': {'env': {}}},
                       'ca_path': str(self.ca)}
        self.client = FakeClient(self.config)
        self.store = library.Store(self.root / 'token.json', owner=os.geteuid())

    def tearDown(self):
        self.directory.cleanup()

    def run_reconcile(self, store=None, check_mode=False):
        return library.reconcile(self.client, self.config, store or self.store, check_mode=check_mode)

    def test_first_install_persists_one_service_token_for_exact_target_inventory(self):
        result = self.run_reconcile()
        self.assertTrue(result['changed'])
        self.assertEqual(self.client.issued, 1)
        saved = self.store.read()
        self.assertEqual(saved['inventory_id'], 23)
        self.assertEqual(saved['target'], self.client.hostname)
        self.assertEqual(saved['username'], self.config['username'])
        self.assertEqual(result['credential_inputs']['inventory_id'], '23')
        self.assertEqual(result['credential_inputs']['controller_host'], self.client.hostname)
        self.assertEqual(os.stat(self.store.path).st_mode & 0o777, 0o600)

    def test_rerun_preserves_token_and_matching_masked_credential(self):
        first = self.run_reconcile()
        inputs = copy.deepcopy(first['credential_inputs'])
        inputs['controller_token'] = '$encrypted$'
        self.client.credentials = [{'organization': 2, 'credential_type': 31, 'inputs': inputs}]
        second = self.run_reconcile()
        self.assertFalse(second['changed'])
        self.assertEqual(self.client.issued, 1)
        self.assertEqual(first['credential_inputs'], second['credential_inputs'])

    def test_partial_credential_failure_reuses_already_saved_token(self):
        first = self.run_reconcile()
        second = self.run_reconcile()
        self.assertEqual(first['token_id'], second['token_id'])
        self.assertEqual(self.client.issued, 1)

    def test_existing_credential_target_type_ca_and_checksum_collisions_do_not_rotate(self):
        first = self.run_reconcile()
        original = {'organization': 2, 'credential_type': 31, 'inputs': first['credential_inputs']}
        for field in ['organization', 'credential_type', 'controller_host', 'controller_ca', 'material_sha256']:
            with self.subTest(field=field):
                old = copy.deepcopy(original)
                if field in ('organization', 'credential_type'):
                    old[field] = 999
                else:
                    old['inputs'][field] = 'different-binding'
                self.client.credentials = [old]
                with self.assertRaises(library.LifecycleError):
                    self.run_reconcile()
        self.assertEqual(self.client.issued, 1)
        self.assertEqual(self.client.deleted, [])

    def test_ca_bundle_change_requires_review_without_reissuing_access(self):
        self.run_reconcile()
        self.ca.write_text('synthetic-different-ca')
        with self.assertRaises(library.LifecycleError):
            self.run_reconcile()
        self.assertEqual(self.client.issued, 1)
        self.assertEqual(self.client.deleted, [])

    def test_wrong_target_ca_owner_inventory_or_token_id_never_rotates(self):
        self.run_reconcile()
        original = self.store.read()
        for field, value in [('target', 'https://other.example.invalid'), ('ca_sha256', 'different'),
                             ('user_id', 999), ('inventory_id', 999), ('token_id', 999)]:
            with self.subTest(field=field):
                self.store.write(dict(original, **{field: value}))
                with self.assertRaises(library.LifecycleError):
                    self.run_reconcile()
        self.assertEqual(self.client.issued, 1)
        self.assertEqual(self.client.deleted, [])

    def test_existing_api_token_without_saved_value_fails_closed(self):
        self.run_reconcile()
        self.store.path.unlink()
        with self.assertRaises(library.LifecycleError):
            self.run_reconcile()
        self.assertEqual(self.client.issued, 1)
        self.assertEqual(self.client.deleted, [])

    def test_admin_auditor_extra_role_team_and_schema_collisions_are_rejected(self):
        variants = [('is_superuser', True), ('is_system_auditor', True), ('is_platform_auditor', True)]
        for field, value in variants:
            with self.subTest(field=field):
                self.client = FakeClient(self.config)
                self.client.user[field] = value
                with self.assertRaises(library.LifecycleError):
                    self.run_reconcile()
        self.client = FakeClient(self.config)
        self.client.grants.append(copy.deepcopy(self.client.grants[0]))
        with self.assertRaises(library.LifecycleError):
            self.run_reconcile()
        self.client = FakeClient(self.config)
        self.client.teams = [{'id': 1}]
        with self.assertRaises(library.LifecycleError):
            self.run_reconcile()
        self.client = FakeClient(self.config)
        self.client.type['injectors'] = {'env': {'OTHER_PURPOSE': 'value'}}
        with self.assertRaises(library.LifecycleError):
            self.run_reconcile()
        self.assertFalse(self.store.path.exists())

    def test_failed_identity_revokes_only_the_new_unsaved_token(self):
        self.client.reject_identity = True
        with self.assertRaises(library.LifecycleError):
            self.run_reconcile()
        self.assertEqual(self.client.deleted, [41])
        self.assertFalse(self.store.path.exists())

    def test_failed_write_with_proved_missing_copy_revokes_new_token(self):
        class FailedStore:
            def read(self):
                return None

            def write(self, document):
                raise OSError('Synthetic storage failure')

        with self.assertRaises(OSError):
            self.run_reconcile(FailedStore())
        self.assertEqual(self.client.deleted, [41])

    def test_interruption_after_atomic_replace_preserves_saved_token(self):
        outer = self.store

        class InterruptedStore:
            def read(self):
                return outer.read()

            def write(self, document):
                outer.write(document)
                raise OSError('Synthetic post-save interruption')

        with self.assertRaises(OSError):
            self.run_reconcile(InterruptedStore())
        self.assertTrue(self.store.read()['token'])
        self.assertEqual(self.client.deleted, [])
        self.assertFalse(self.run_reconcile()['changed'])

    def test_uncertain_save_outcome_preserves_token_for_operator_review(self):
        class UncertainStore:
            reads = 0

            def read(self):
                self.reads += 1
                if self.reads == 1:
                    return None
                raise OSError('Synthetic unreadable storage')

            def write(self, document):
                raise OSError('Synthetic uncertain write')

        with self.assertRaises(OSError):
            self.run_reconcile(UncertainStore())
        self.assertEqual(self.client.deleted, [])

    def test_expired_duplicate_and_wrong_owner_tokens_preserved_for_review(self):
        self.run_reconcile()
        original = copy.deepcopy(self.client.tokens)
        for change in ['expired', 'duplicate', 'owner']:
            with self.subTest(change=change):
                self.client.tokens = copy.deepcopy(original)
                if change == 'expired':
                    self.client.tokens[0]['expires'] = '2000-01-01T00:00:00Z'
                elif change == 'duplicate':
                    self.client.tokens.append(dict(original[0], id=42))
                else:
                    self.client.tokens[0]['user'] = 999
                with self.assertRaises(library.LifecycleError):
                    self.run_reconcile()
        self.assertEqual(self.client.issued, 1)
        self.assertEqual(self.client.deleted, [])

    def test_insecure_file_and_symlink_are_rejected(self):
        self.run_reconcile()
        self.store.path.chmod(0o644)
        with self.assertRaises(library.LifecycleError):
            self.run_reconcile()
        self.store.path.unlink()
        self.store.path.symlink_to(self.ca)
        with self.assertRaises(library.LifecycleError):
            self.run_reconcile()
        self.assertEqual(self.client.deleted, [])

    def test_check_mode_does_not_create_token_or_file(self):
        result = self.run_reconcile(check_mode=True)
        self.assertTrue(result['requires_token_creation'])
        self.assertEqual(self.client.issued, 0)
        self.assertFalse(self.store.path.exists())


if __name__ == '__main__':
    unittest.main()
