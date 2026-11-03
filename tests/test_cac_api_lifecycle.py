"""Exercise API-only service identity/token reuse and interrupted persistence."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from urllib.parse import urlsplit

SPEC = importlib.util.spec_from_file_location('cac_api_lifecycle', Path(__file__).resolve().parents[1]
                                            / 'src/cac_api_lifecycle.py')
lifecycle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lifecycle)


class FakeClient:
    hostname = 'https://target.example.invalid'

    def __init__(self):
        self.user = {'id': 11, 'username': 'synthetic-service', 'is_superuser': False,
                     'is_platform_auditor': False, 'is_system_auditor': False}
        self.inventory = {'id': 23, 'organization': 2, 'summary_fields': {'organization': {'name': 'Example'}}}
        self.type = {'id': 31, 'name': 'Service type', 'kind': 'cloud', 'inputs': {'fields': []}, 'injectors': {'env': {}}}
        self.grants = [{'content_type': 'awx.inventory', 'object_id': '23',
                        'summary_fields': {'role_definition': {'name': 'Inventory Admin'}}}]
        self.teams, self.tokens, self.credentials, self.eda_credentials = [], [], [], []
        self.calls, self.revoked, self.issued = [], [], 0
        self.fail_save, self.unknown_save = False, False

    def rows(self, path):
        endpoint = urlsplit(path).path
        if endpoint.endswith('/organizations/'):
            return [{'id': 2, 'name': 'Example'}]
        if endpoint.endswith('/inventories/'):
            return [deepcopy(self.inventory)]
        if endpoint.endswith('/users/'):
            return [deepcopy(self.user)]
        if endpoint.endswith('/role_user_assignments/'):
            return deepcopy(self.grants)
        if endpoint.endswith('/teams/'):
            return deepcopy(self.teams)
        if endpoint.endswith('/credential_types/'):
            return [deepcopy(self.type)]
        if endpoint.endswith('/credential-types/'):
            return [{'id': 31}]
        if endpoint.endswith('/eda-credentials/'):
            if self.unknown_save:
                raise lifecycle.LifecycleError('Synthetic unknown persistence')
            return deepcopy(self.eda_credentials)
        if endpoint.endswith('/credentials/'):
            return deepcopy(self.credentials)
        if endpoint.endswith('/tokens/'):
            return deepcopy(self.tokens)
        raise AssertionError('Unexpected endpoint ' + endpoint)

    def request(self, method, path, body=None, basic=None, token=None):
        self.calls.append((method, path))
        if method == 'DELETE':
            identity = int(path.rstrip('/').rsplit('/', 1)[-1])
            self.revoked.append(identity)
            self.tokens = [row for row in self.tokens if row['id'] != identity]
            return {}
        if method == 'GET' and path.endswith('/me/'):
            return {'results': [deepcopy(self.user)]}
        if method == 'POST' and path.endswith('/tokens/'):
            self.issued += 1
            row = dict(body, id=41, user=11, token='synthetic-private-token', expires=None)
            self.tokens.append(deepcopy(row))
            return row
        if method == 'POST' and path.endswith('/eda-credentials/'):
            if self.fail_save:
                raise lifecycle.LifecycleError('Synthetic save rejection')
            saved = dict(body, id=53, organization={'name': 'Example'},
                         credential_type={'name': 'Red Hat Ansible Automation Platform'})
            saved['inputs'] = dict(body['inputs'], oauth_token='$encrypted$')
            self.eda_credentials.append(saved)
            return {'id': 53}
        if method == 'POST' and path.endswith('/credentials/'):
            if self.fail_save:
                raise lifecycle.LifecycleError('Synthetic save rejection')
            saved = deepcopy(dict(body, id=52))
            saved['inputs']['controller_token'] = '$encrypted$'
            self.credentials.append(saved)
            return {'id': 52}
        raise AssertionError('Unexpected request ' + path)


class APILifecycleTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.contract = {'username': 'synthetic-service', 'inventory': 'Dedicated inventory',
                         'organization': 'Example', 'credential_name': 'Service credential',
                         'credential_type_name': 'Service type', 'token_description': 'Dedicated service token'}
        self.password = 'synthetic-long-prepared-password-' * 3
        self.ca = 'synthetic-public-trusted-ca'

    def reconcile(self):
        return lifecycle.service_access(self.client, self.contract, self.password, self.client.type, self.ca)

    def test_new_service_token_is_stored_directly_in_target_credential_and_reused(self):
        first = self.reconcile()
        self.assertTrue(first['changed'])
        self.assertEqual(self.client.issued, 1)
        self.assertEqual(self.client.credentials[0]['inputs']['controller_token'], '$encrypted$')
        before = deepcopy(self.client.credentials)
        second = self.reconcile()
        self.assertFalse(second['changed'])
        self.assertEqual(self.client.credentials, before)
        self.assertEqual(self.client.issued, 1)
        self.assertEqual(self.client.revoked, [])

    def test_existing_masked_legacy_credential_or_changed_binding_fails_closed_without_rotation(self):
        self.reconcile()
        for field in ('description', 'organization', 'credential_type'):
            original = deepcopy(self.client.credentials)
            self.client.credentials[0][field] = 'different-binding'
            with self.subTest(field=field), self.assertRaises(lifecycle.LifecycleError):
                self.reconcile()
            self.client.credentials = original
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.service_access(self.client, self.contract, self.password, self.client.type, 'different-ca')
        self.assertEqual(self.client.issued, 1)
        self.assertEqual(self.client.revoked, [])

    def test_existing_token_without_credential_never_mints_another(self):
        self.reconcile()
        self.client.credentials = []
        with self.assertRaises(lifecycle.LifecycleError):
            self.reconcile()
        self.assertEqual(self.client.issued, 1)

    def test_failed_service_save_revokes_only_the_proved_unsaved_new_token(self):
        self.client.fail_save = True
        with self.assertRaises(lifecycle.LifecycleError):
            self.reconcile()
        self.assertEqual(self.client.revoked, [41])
        self.assertEqual(self.client.credentials, [])

    def test_privileged_user_extra_grant_or_team_is_rejected_before_token_creation(self):
        for update in ('privilege', 'grant', 'team'):
            self.client = FakeClient()
            if update == 'privilege':
                self.client.user['is_superuser'] = True
            elif update == 'grant':
                self.client.grants.append(deepcopy(self.client.grants[0]))
            else:
                self.client.teams.append({'id': 9})
            with self.subTest(update=update), self.assertRaises(lifecycle.LifecycleError):
                self.reconcile()
            self.assertEqual(self.client.issued, 0)

    def test_existing_authenticated_service_password_is_omitted_from_resource_updates(self):
        resources = {'aap_user_accounts': [dict(self.client.user, password=self.password, update_secrets=False)],
                     'controller_roles': [{'user': self.contract['username'], 'inventory': self.contract['inventory'], 'role': 'admin'}],
                     'controller_credential_types': [deepcopy(self.client.type)]}
        normalized, schema = lifecycle.service_preflight(self.client, self.contract, self.password, resources)
        self.assertNotIn('password', normalized['aap_user_accounts'][0])
        self.assertIn('password', resources['aap_user_accounts'][0])
        self.assertEqual(schema, self.client.type)

    def test_eda_access_creates_once_then_preserves_masked_write_only_input(self):
        capability = {'credential_name': 'EDA access', 'organization': 'Example'}
        definitions = [{'name': 'EDA access', 'organization': 'Example',
                        'credential_type': 'Red Hat Ansible Automation Platform',
                        'inputs': {'host': self.client.hostname + '/api/controller', 'oauth_token': '', 'verify_ssl': True}}]
        self.assertTrue(lifecycle.eda_access(self.client, capability, definitions)['changed'])
        self.assertFalse(lifecycle.eda_access(self.client, capability, definitions)['changed'])
        self.assertEqual(self.client.issued, 1)
        self.client.eda_credentials[0]['inputs']['verify_ssl'] = False
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.eda_access(self.client, capability, definitions)
        self.assertEqual(self.client.issued, 1)

    def test_eda_failed_save_revokes_only_proved_absent_new_token(self):
        capability = {'credential_name': 'EDA access', 'organization': 'Example'}
        definitions = [{'name': 'EDA access', 'organization': 'Example',
                        'credential_type': 'Red Hat Ansible Automation Platform',
                        'inputs': {'host': self.client.hostname + '/api/controller', 'oauth_token': ''}}]
        self.client.fail_save = True
        with self.assertRaises(lifecycle.LifecycleError):
            lifecycle.eda_access(self.client, capability, definitions)
        self.assertEqual(self.client.revoked, [41])


if __name__ == '__main__':
    unittest.main()
