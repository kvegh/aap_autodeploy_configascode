"""Prove exact generic retirement, canonical/API recovery and encrypted retry."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase

from test_guest_release import fixture as release_fixture, Source, load, keys, vault_yaml


def fixture():
    guest, pin, main, shared, hactar, allocation = release_fixture(new=True)
    guest['source_image_sha256'] = 'c' * 64
    documents = {'autodeploy': main, 'shared': shared, 'hactar': hactar}
    for access in ('bootstrap_https', 'release'):
        context = keys.guest_release_context(documents['autodeploy'], documents['shared'], guest, pin, access=access)
        documents = {kind: keys.guest_release_inventory_capture(value, context, kind) for kind, value in documents.items()}
    return guest, pin, documents, allocation


class GenericRetirementTests(unittest.TestCase):
    def test_resolves_saved_exact_ownership_and_removes_only_one_guest(self):
        guest, pin, documents, allocation = fixture()
        original = deepcopy((documents, allocation))
        source = Source(documents['autodeploy'], documents['shared'], documents['hactar'])
        context = keys.generic_retirement_context(documents['autodeploy'], documents['shared'], source, guest['vm_name'], pin)
        self.assertEqual(context['guest'], guest)
        for field in ('https_clients', 'released_clients'):
            self.assertFalse(any(row['mac'] == guest['mac'] for row in context['desired_policy'].get(field, [])))
        self.assertEqual(context['desired_policy']['protected_ipv4'], context['previous_policy']['protected_ipv4'])
        desired = {kind: keys.generic_retirement_capture(value, context, kind) for kind, value in documents.items()}
        self.assertEqual((documents, allocation), original)
        self.assertFalse(any(row['name'] == guest['vm_name'] for row in desired['shared']['host_inventory_configuration']['hosts']))
        self.assertTrue(all(guest['vm_name'] not in row.get('hosts', []) for row in desired['shared']['host_inventory_configuration']['groups']))
        self.assertEqual(desired['autodeploy']['aap_instance_api_credentials'], documents['autodeploy']['aap_instance_api_credentials'])
        self.assertEqual(vault_yaml.literal_paths(desired['autodeploy']), vault_yaml.literal_paths(documents['autodeploy']))
        operations = keys.source_generic_retirement_operations(source, desired['shared'], desired['autodeploy'], desired['hactar'], context)
        self.assertEqual(source.calls, [])
        self.assertEqual(sum(method == 'DELETE' for method, *_ in operations), 1)
        for method, path, body in operations:
            source.request(method, path, body)
        repeated = keys.generic_retirement_context(desired['autodeploy'], desired['shared'], source, guest['vm_name'], pin)
        self.assertIsNone(repeated['guest'])
        self.assertTrue(repeated['records_absent'])
        self.assertFalse(keys.source_generic_retirement_operations(source, desired['shared'], desired['autodeploy'], desired['hactar'], repeated))

    def test_source_record_recovers_ownership_after_git_already_removed_it(self):
        guest, pin, documents, _ = fixture()
        source = Source(documents['autodeploy'], documents['shared'], documents['hactar'])
        first = keys.generic_retirement_context(documents['autodeploy'], documents['shared'], source, guest['vm_name'], pin)
        desired = {kind: keys.generic_retirement_capture(value, first, kind) for kind, value in documents.items()}
        recovered = keys.generic_retirement_context(desired['autodeploy'], desired['shared'], source, guest['vm_name'], pin)
        self.assertEqual(recovered['guest'], guest)
        self.assertEqual(recovered['previous_policy'], recovered['desired_policy'])
        self.assertFalse(recovered['records_absent'])

    def test_foreign_records_aap_names_and_unknown_host_service_grants_refuse_preflight(self):
        for variant in ('foreign-api', 'aap-name', 'host-service', 'native-rule', 'source-native-rule'):
            guest, pin, documents, _ = fixture()
            source = Source(documents['autodeploy'], documents['shared'], documents['hactar'])
            name = guest['vm_name']
            if variant == 'foreign-api':
                row = next(row for row in source.hosts.values() if row['name'] == name)
                values = keys.inventory_variables(row)
                values['vm_resource']['uuid'] = '88888888-2222-3333-4444-555555555555'
                keys.set_inventory_variables(row, values)
            elif variant == 'aap-name':
                name = 'aap27-test-7'
            elif variant in ('host-service', 'native-rule'):
                row = next(row for row in documents['shared']['host_inventory_configuration']['hosts']
                           if keys.inventory_variables(row).get('ansible_host') == pin['address'])
                values = keys.inventory_variables(row)
                if variant == 'host-service':
                    values['isolation_policy']['guest_host_clients'].append({'bridge': guest['bridge'],
                        'ipv4': guest['address'], 'mac': guest['mac'], 'destinations': [pin['address']], 'ports': [2222]})
                else:
                    values.setdefault('firewall_additional_zone_rules', []).append({'zone': 'libvirt',
                        'rule': 'rule family="ipv4" source address="%s/32" port port="2222" protocol="tcp" accept' % guest['address']})
                keys.set_inventory_variables(row, values)
            else:
                row = next(row for row in source.hosts.values()
                           if keys.inventory_variables(row).get('ansible_host') == pin['address'])
                values = keys.inventory_variables(row)
                values.setdefault('firewall_additional_zone_rules', []).append({'zone': 'libvirt',
                    'rule': 'rule family="ipv4" source address="%s/32" port port="2222" protocol="tcp" accept' % guest['address']})
                keys.set_inventory_variables(row, values)
            with self.subTest(variant=variant), self.assertRaises(keys.StoreError):
                context = keys.generic_retirement_context(documents['autodeploy'], documents['shared'], source, name, pin)
                desired = {kind: keys.generic_retirement_capture(value, context, kind) for kind, value in documents.items()}
                keys.source_generic_retirement_operations(source, desired['shared'], desired['autodeploy'], desired['hactar'], context)
            self.assertEqual(source.calls, [])

    def test_native_encrypted_transaction_recovers_api_interruption_without_token_or_allocator_changes(self):
        module = load('test_generic_retirement_action', 'action_plugins/aap_publish_instance_keys.py')
        guest, pin, documents, allocation = fixture()
        source = Source(documents['autodeploy'], documents['shared'], documents['hactar'])
        secret, environment_secret = VaultSecret(b'synthetic-cac-key'), VaultSecret(b'synthetic-environment-key')
        vault = VaultLib([('cac', secret), ('default', environment_secret)])
        paths = {'autodeploy': 'vaults/cac/aap_autodeploy_configascode-cac-vault.yml',
                 'shared': 'cac/host_inventory.yml', 'hactar': 'cac/hactar_recovery.yml'}
        original_run = subprocess.run
        with tempfile.TemporaryDirectory(prefix='generic-retirement-action-') as directory:
            root = Path(directory)
            remote, seed, project = root / 'remote.git', root / 'seed', root / 'project'
            seed.mkdir(); project.mkdir()
            def git(path, *arguments):
                return original_run(['git', '-C', str(path), *arguments], capture_output=True, text=True, check=True)
            original_run(['git', 'init', '--bare', '--initial-branch=main', str(remote)], capture_output=True, check=True)
            git(seed, 'init', '--initial-branch=main')
            for kind, path in paths.items():
                target = seed / path; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(vault.encrypt(yaml.dump(documents[kind], Dumper=vault_yaml.VaultDumper), vault_id='cac'))
            target = seed / 'state/aap_vm_allocations_vault.yml'; target.parent.mkdir(parents=True)
            target.write_bytes(vault.encrypt(yaml.dump(allocation, Dumper=vault_yaml.VaultDumper), vault_id='cac'))
            git(seed, 'add', '.')
            git(seed, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Seed encrypted fixture')
            git(seed, 'remote', 'add', 'origin', str(remote)); git(seed, 'push', 'origin', 'main')
            (project / 'myvars').write_bytes(vault.encrypt(yaml.safe_dump({'git_url':
                'https://git.example.invalid/fixture-owner/autodeploy.git'}), vault_id='default'))
            loader = DataLoader(); loader.set_vault_secrets(vault.secrets)
            def redirected(arguments, *args, **kwargs):
                arguments = [str(remote) if item == 'https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git' else item for item in arguments]
                self.assertFalse(any(item.startswith(('https://', 'http://', 'git@')) for item in arguments))
                return original_run(arguments, *args, **kwargs)
            def run(phase, transition=None, check=False):
                action = module.ActionModule.__new__(module.ActionModule)
                arguments = {'operation': 'retire_guest', 'phase': phase, 'guest_name': guest['vm_name'], 'hypervisor': pin}
                if guest.get('kind') == 'windows': arguments['guest_kind'] = 'windows'
                if transition is not None: arguments['transition'] = transition
                action._task = SimpleNamespace(args=arguments, check_mode=check); action._loader = loader
                return action.run(task_vars={'awx_job_id': 123, 'awx_job_template_id': 456, 'awx_project_revision': 'a' * 40})
            with mock.patch.object(ActionBase, 'run', side_effect=lambda *a, **kw: {}), mock.patch.object(module, 'ROOT', project), \
                 mock.patch.object(module, 'SourceClient', return_value=source), \
                 mock.patch.object(module.subprocess, 'run', side_effect=redirected), \
                 mock.patch.dict(os.environ, {'CAC_GIT_TOKEN': 'synthetic-retirement-token'}):
                planned = run('plan', check=True)
                self.assertFalse(planned.get('failed'), planned)
                self.assertEqual(planned['guest'], guest)
                self.assertEqual(source.calls, [])
                request = source.request
                def interrupted(method, path, body=None):
                    if method == 'PATCH' and path.startswith('inventories/'):
                        raise keys.StoreError('Synthetic API publication interruption')
                    return request(method, path, body)
                with mock.patch.object(source, 'request', side_effect=interrupted):
                    failed = run('publish', planned['transition'])
                self.assertTrue(failed['failed'], failed)
                self.assertTrue(failed['durable_policy_published'])
                self.assertEqual(git(remote, 'rev-list', '--count', 'main').stdout.strip(), '2')
                retried = run('plan')
                self.assertFalse(retried.get('failed'), retried)
                self.assertEqual(retried['guest'], guest)
                published = run('publish', retried['transition'])
                self.assertTrue(published.get('published'), published)
                repeated = run('publish', retried['transition'])
                self.assertFalse(repeated.get('failed'), repeated)
                self.assertFalse(repeated['changed'])
                absent = run('plan')
                self.assertIsNone(absent['guest'])
                self.assertTrue(absent['records_absent'])
                self.assertEqual(git(remote, 'rev-list', '--count', 'main').stdout.strip(), '2')
                self.assertFalse(any('credentials/' in path for _, path in source.calls))
            after = AnsibleLoader(vault.decrypt(git(remote, 'show', 'main:' + paths['autodeploy']).stdout.encode())).get_single_data()
            self.assertEqual(after['aap_instance_api_credentials'], documents['autodeploy']['aap_instance_api_credentials'])
            after_allocation = AnsibleLoader(vault.decrypt(git(remote, 'show', 'main:state/aap_vm_allocations_vault.yml').stdout.encode())).get_single_data()
            self.assertEqual(after_allocation, allocation)


if __name__ == '__main__':
    unittest.main()
