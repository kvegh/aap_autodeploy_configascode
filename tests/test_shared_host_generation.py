"""Exercise one encrypted counter across host/AAP allocation, retries and failures."""

import copy
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.parsing.vault import VaultLib, VaultSecret

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('shared_generation', ROOT / 'src/aap_name_allocation.py')
allocation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(allocation)
sys.path.insert(0, str(ROOT / 'src'))
from cac_yaml import VaultDumper, literal_paths, load_repository_yaml


def seed():
    return {'schema_version': 1, 'next_number': 22, 'reservations': {
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa': {
            'number': 21, 'vm_name': 'aap27-test-21', 'prefix': 'aap27-test',
            'hypervisor_id': '1' * 32, 'instance_route': {'keep': 'unchanged'}}}}


class SharedHostGenerationTests(unittest.TestCase):
    def test_one_authoritative_increment_preserves_history_and_guest_failure_consumption(self):
        before = seed()
        state, request, record = allocation.reserve_host_generation(before, 'aap27-test', 'a' * 64, '2' * 32)
        self.assertEqual(before, seed())
        self.assertEqual(record['number'], 22)
        self.assertEqual(state['next_number'], 23)
        self.assertEqual(state['reservations']['aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'],
                         before['reservations']['aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'])
        self.assertEqual(allocation.host_generation_request(state, 'aap27-test', '2' * 32), request)
        self.assertEqual(allocation.reserve(state, 'aap27-test', request, '2' * 32)[0], state)
        self.assertEqual(allocation.reserve_host_generation(state, 'aap27-test', 'a' * 64, '2' * 32)[0], state)
        # A later full installation consumes the next generation, even if the
        # previous VM was never created. Do not recycle the failed attempt.
        newer, _, new_record = allocation.reserve_host_generation(state, 'aap27-test', 'b' * 64, '3' * 32)
        self.assertEqual(new_record['number'], 23)
        self.assertEqual(newer['next_number'], 24)
        self.assertEqual(newer['reservations'][request], record)

    def test_changed_identity_prefix_or_alternate_uuid_never_consumes_second_generation(self):
        state, request, _ = allocation.reserve_host_generation(seed(), 'aap27-test', 'a' * 64, '2' * 32)
        original = copy.deepcopy(state)
        for operation in (
            lambda: allocation.reserve_host_generation(state, 'aap27-test', 'a' * 64, '3' * 32),
            lambda: allocation.reserve_host_generation(state, 'aap27-test', 'b' * 64, '2' * 32),
            lambda: allocation.reserve_host_generation(state, 'aap28-test', 'a' * 64, '2' * 32),
            lambda: allocation.reserve(state, 'aap27-test', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '2' * 32),
        ):
            with self.assertRaises(ValueError):
                operation()
            self.assertEqual(state, original)
        state['reservations'][request]['decommissioned'] = True
        with self.assertRaises(ValueError):
            allocation.host_generation_request(state, 'aap27-test', '2' * 32)
        with self.assertRaises(ValueError):
            allocation.reserve_host_generation(state, 'aap27-test', 'a' * 64, '2' * 32)

    def test_tampered_marker_and_out_of_range_generation_fail_closed(self):
        state, request, _ = allocation.reserve_host_generation(seed(), 'aap27-test', 'a' * 64, '2' * 32)
        for field, value in [('host_installation_id', 'invalid'), ('number', True), ('vm_name', 'foreign')]:
            bad = copy.deepcopy(state)
            bad['reservations'][request][field] = value
            with self.assertRaises(ValueError):
                allocation.host_generation_request(bad, 'aap27-test', '2' * 32)
        with self.assertRaises(ValueError):
            allocation.reserve_host_generation(dict(seed(), next_number=100), 'aap27-test', 'b' * 64, '3' * 32)


class EncryptedGenerationTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='shared-host-generation-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.path = self.directory / 'allocation.vault.yml'
        self.password = self.directory / 'password'
        self.password.write_text('fixture-vault-password-never-print')
        self.password.chmod(0o600)
        self.secret = VaultSecret(self.password.read_bytes())
        self.vault = VaultLib([('cac', self.secret)])
        self.document = load_repository_yaml("aap_vm_allocation: {}\nunrelated: !unsafe '{{ literal_fixture }}'\n")
        self.document['aap_vm_allocation'] = seed()
        self.write()

    def write(self, label='cac'):
        self.path.write_bytes(self.vault.encrypt(yaml.dump(self.document, Dumper=VaultDumper).encode(),
                                                secret=self.secret, vault_id=label))

    def invoke(self, installation='a', host='2', extra=()):
        env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(self.directory / ('ansible-' + installation)))
        return subprocess.run([sys.executable, str(ROOT / 'src/aap_name_allocation.py'), 'reserve-host',
            '--registry', str(self.path), '--vault-password-file', str(self.password),
            '--prefix', 'aap27-test', '--installation-id', installation * 64,
            '--hypervisor-id', host * 32, *extra], capture_output=True, text=True, env=env, timeout=60)

    def read(self):
        return load_repository_yaml(self.vault.decrypt(self.path.read_bytes()))

    def test_real_vault_repeat_preserves_header_literals_other_data_and_ciphertext_on_retry(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['number'], 22)
        self.assertTrue(json.loads(result.stdout)['changed'])
        encrypted = self.path.read_bytes()
        self.assertEqual(encrypted.splitlines()[0], b'$ANSIBLE_VAULT;1.2;AES256;cac')
        after = self.read()
        self.assertEqual(literal_paths(after), literal_paths(self.document))
        self.assertEqual(after['unrelated'], self.document['unrelated'])
        again = self.invoke()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(json.loads(again.stdout), dict(json.loads(result.stdout), changed=False, reused=True))
        self.assertEqual(self.path.read_bytes(), encrypted)
        self.assertNotIn('fixture-vault-password', result.stdout + result.stderr)
        self.assertNotIn('literal_fixture', result.stdout + result.stderr)

    def test_real_concurrent_installations_and_lost_response_retry_share_one_locked_counter(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda x: self.invoke(*x), [('a', '2'), ('b', '3')]))
        self.assertTrue(all(r.returncode == 0 for r in results), [r.stderr for r in results])
        self.assertEqual({json.loads(r.stdout)['number'] for r in results}, {22, 23})
        self.assertEqual(self.read()['aap_vm_allocation']['next_number'], 24)
        before = self.path.read_bytes()
        retry = self.invoke('a', '2')
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertTrue(json.loads(retry.stdout)['reused'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_same_installation_concurrency_consumes_once(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.invoke(), range(2)))
        self.assertTrue(all(r.returncode == 0 for r in results), [r.stderr for r in results])
        self.assertEqual([json.loads(r.stdout)['changed'] for r in results].count(True), 1)
        self.assertEqual(self.read()['aap_vm_allocation']['next_number'], 23)

    def test_wrong_identity_exposed_password_and_missing_registry_preserve_existing_state(self):
        self.assertEqual(self.invoke().returncode, 0)
        before = self.path.read_bytes()
        self.assertNotEqual(self.invoke('a', '3').returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.password.chmod(0o644)
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.path.unlink()
        self.password.chmod(0o600)
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertFalse(self.path.exists())

    def test_legacy_header_is_preserved(self):
        self.write(label=None)
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.path.read_bytes().splitlines()[0], b'$ANSIBLE_VAULT;1.1;AES256')

    def test_retired_installation_history_cannot_be_consumed_again(self):
        self.assertEqual(self.invoke().returncode, 0)
        self.document = self.read()
        record = next(row for row in self.document['aap_vm_allocation']['reservations'].values()
                      if row.get('host_installation_id') == 'a' * 64)
        record['decommissioned'] = True
        self.write()
        before = self.path.read_bytes()
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.read()['aap_vm_allocation']['next_number'], 23)
        newer = self.invoke('b', '3')
        self.assertEqual(newer.returncode, 0, newer.stderr)
        self.assertEqual(json.loads(newer.stdout)['number'], 23)


if __name__ == '__main__':
    unittest.main()
