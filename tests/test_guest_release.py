"""Prove bounded guest release, encrypted publication and safe interrupted retries."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import yaml
from ansible.errors import AnsibleFilterError
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase
from ansible.utils.unsafe_proxy import AnsibleUnsafeText

from test_instance_keys import retirement_fixture, FakeRetirementSource, load, keys, vault_yaml

ROOT = Path(__file__).resolve().parents[1]


def fixture(new=False):
    context, _, main, shared, hactar, allocation = retirement_fixture()
    shared['host_inventory_configuration']['groups'][0]['variables'] = {'hypervisor_host': 'fixture-hypervisor'}
    shared['host_inventory_configuration']['hosts'] = [row for row in shared['host_inventory_configuration']['hosts']
        if row['inventory'] == 'Shared']
    guest = deepcopy(context['guests'][2]['metadata'])
    if new:
        guest.update(vm_name='extra-v07', uuid='99999999-2222-3333-4444-555555555555',
                     address='192.168.70.99', mac='52:54:00:12:34:99', machine_id='9' * 32,
                     disk='/opt/vms/extra-v07.disk.qcow2')
    pin = context['route']['hypervisor']
    return guest, pin, main, shared, hactar, allocation


class Source(FakeRetirementSource):
    def __init__(self, main, shared, hactar):
        super().__init__(main, shared, hactar)
        self.members = {row['id'] for row in self.hosts.values() if row['inventory'] == 1}

    def rows(self, path):
        if path.startswith('groups/?'):
            return [{'id': 77, 'name': 'guests', 'inventory': 1, 'variables': {'hypervisor_host': 'fixture-hypervisor'}}]
        if path == 'groups/77/hosts/':
            return [{'id': identity} for identity in self.members]
        return super().rows(path)

    def request(self, method, path, body=None):
        if method == 'POST' and path == 'hosts/':
            identity = max(self.hosts) + 1
            self.hosts[identity] = dict(deepcopy(body), id=identity)
            self.calls.append((method, path))
            return deepcopy(self.hosts[identity])
        if method == 'POST' and path == 'groups/77/hosts/':
            self.members.add(body['id'])
            self.calls.append((method, path))
            return {}
        return super().request(method, path, body)


class GuestReleaseTests(unittest.TestCase):
    def test_derives_only_one_exact_guest_release_and_preserves_production_exclusions(self):
        guest, pin, main, shared, *_ = fixture()
        baseline = deepcopy((guest, pin, main, shared))
        context = keys.guest_release_context(main, shared, guest, pin)
        expected = deepcopy(context['previous_policy'])
        expected['released_clients'] = [{'bridge': guest['bridge'], 'ipv4': guest['address'], 'mac': guest['mac']}]
        self.assertEqual(context['desired_policy'], expected)
        self.assertEqual((guest, pin, main, shared), baseline)
        context['desired_policy']['protected_ipv4'] = []
        with self.assertRaises(keys.StoreError):
            keys.guest_release_context(main, shared, guest, pin, {key: context[key] for key in ('previous_policy', 'desired_policy')})

    def test_foreign_identity_incomplete_provenance_or_capture_conflict_is_refused(self):
        for field, value in [('verified', False), ('uuid', 'invalid'), ('disk', '/opt/vms/foreign.qcow2'),
            ('machine_id', 'invalid'), ('hypervisor_machine_id', '0' * 32), ('address', '127.0.0.1'),
            ('bridge', 'foreign'), ('mac', '01:00:00:00:00:01'), ('extra_secret', 'synthetic-canary')]:
            guest, pin, main, shared, *_ = fixture()
            guest[field] = value
            with self.subTest(field=field), self.assertRaises((keys.StoreError, AnsibleFilterError)):
                keys.guest_release_context(main, shared, guest, pin)
        guest, pin, main, shared, *_ = fixture()
        selected = next(row for row in shared['host_inventory_configuration']['hosts'] if row['name'] == guest['vm_name'])
        selected['variables']['vm_resource']['uuid'] = '11111111-2222-3333-4444-555555555555'
        with self.assertRaises(keys.StoreError): keys.guest_release_context(main, shared, guest, pin)

    def test_registers_new_guest_without_altering_other_hosts_credentials_or_tokens(self):
        guest, pin, main, shared, hactar, _ = fixture(new=True)
        context = keys.guest_release_context(main, shared, guest, pin)
        for configuration, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar')):
            original = deepcopy(configuration)
            updated = keys.guest_release_inventory_capture(configuration, context, kind)
            self.assertEqual(configuration, original)
            self.assertEqual(keys.guest_release_inventory_capture(updated, context, kind), updated)
            if kind == 'autodeploy':
                self.assertEqual(updated['aap_instance_api_credentials'], original['aap_instance_api_credentials'])
                self.assertEqual(updated['autodeploy_configuration']['credentials'], original['autodeploy_configuration']['credentials'])
                self.assertIsInstance(updated['autodeploy_configuration']['inventories'][0]['variables'], AnsibleUnsafeText)
            if kind == 'shared':
                data = updated['host_inventory_configuration']
                self.assertEqual(len(data['hosts']), len(original['host_inventory_configuration']['hosts']) + 1)
                self.assertEqual(data['hosts'][-1]['name'], guest['vm_name'])
                self.assertEqual(keys.inventory_variables(data['hosts'][-1])['vm_resource'], guest)
                self.assertEqual(data['groups'][0]['hosts'][-1], guest['vm_name'])

    def test_source_preflight_rejects_conflicting_live_ownership_before_any_mutation(self):
        guest, pin, main, shared, hactar, _ = fixture(new=True)
        source = Source(main, shared, hactar)
        context = keys.guest_release_context(main, shared, guest, pin)
        row = next(iter(source.hosts.values()))
        original = row['variables']
        row['variables'] = json.dumps(dict(json.loads(original), ansible_host=guest['address']))
        with self.assertRaises(keys.StoreError):
            keys.source_guest_release_operations(source, shared, main, hactar, context)
        self.assertEqual(source.calls, [])

    def test_release_only_policy_normalizes_and_last_https_retirement_keeps_production_block(self):
        guest, pin, main, shared, *_ = fixture()
        context = keys.guest_release_context(main, shared, guest, pin)
        identity = context['desired_policy']['released_clients'][0]
        normalized = keys._routing.isolation_policy(pin, [], ['203.0.113.99'], [], [identity])
        self.assertNotIn('https_clients', normalized)
        self.assertEqual(normalized['protected_ipv4'], ['203.0.113.99'])
        for bad in ([dict(identity, ipv4='8.8.8.8')], [identity, identity], [dict(identity, mac='00:00:00:00:00:00')]):
            with self.subTest(bad=bad), self.assertRaises(AnsibleFilterError):
                keys._routing.isolation_policy(pin, [], ['203.0.113.99'], [], bad)
        old = deepcopy(context['previous_policy'])
        old['released_clients'] = [identity]
        primary = old['https_clients'][0]
        old['https_clients'] = [primary]
        desired = deepcopy(old)
        desired.pop('https_clients')
        desired['guest_host_clients'] = [item for item in desired['guest_host_clients'] if item['ipv4'] != primary['ipv4']]
        transition = {'previous_policy': old, 'desired_policy': desired}
        # Exact removal path leaves protected IPv4 present because an unrelated release survives.
        retirement = dict(context, previous_policy=old, desired_policy=desired, identities=[primary])
        variables = {'isolation_policy': old, 'keep': '{{ literal }}'}
        result = keys.source_retirement_variables(variables, retirement)
        self.assertEqual(result['isolation_policy'], desired)
        self.assertEqual(result['keep'], variables['keep'])

    def test_native_decommission_removes_only_selected_releases_and_retains_other_production_block(self):
        from test_decommission_guest_access import fixture as retirement_inputs
        retire = load('release_native_decommission', 'filter_plugins/aap_decommission.py')
        policy, retirement, route, resources, xmls, networks = retirement_inputs()
        selected = deepcopy(policy['https_clients'][0])
        other = deepcopy(policy['https_clients'][1])
        policy['released_clients'] = [selected, other]
        planned = retire.guest_access_plan(policy, retirement, route, resources, xmls, networks)
        self.assertEqual(planned['desired_policy']['released_clients'], [other])
        self.assertEqual(planned['desired_policy']['protected_ipv4'], policy['protected_ipv4'])
        self.assertNotIn(selected, planned['desired_policy'].get('https_clients', []))
        policy.pop('https_clients')
        planned = retire.guest_access_plan(policy, retirement, route, resources, xmls, networks)
        self.assertEqual(planned['desired_policy']['released_clients'], [other])
        self.assertEqual(planned['desired_policy']['protected_ipv4'], policy['protected_ipv4'])

    def test_native_action_real_encrypted_git_plan_publish_api_interruption_retry_and_idempotence(self):
        module = load('test_guest_release_action', 'action_plugins/aap_publish_instance_keys.py')
        guest, pin, main, shared, hactar, allocation = fixture(new=True)
        source = Source(main, shared, hactar)
        secret = VaultSecret(b'synthetic-cac-password')
        environment_secret = VaultSecret(b'synthetic-environment-password')
        vault = VaultLib([('cac', secret), ('default', environment_secret)])
        docs = {'vaults/cac/aap_autodeploy_configascode-cac-vault.yml': main, 'cac/host_inventory.yml': shared,
                'cac/hactar_recovery.yml': hactar, 'state/aap_vm_allocations_vault.yml': allocation}
        real_run = subprocess.run
        with tempfile.TemporaryDirectory(prefix='guest-release-action-') as temporary:
            directory = Path(temporary)
            remote, seed, project = (directory / name for name in ('remote.git', 'seed', 'project'))
            seed.mkdir(); project.mkdir()
            def git(path, *args):
                return real_run(['git', '-C', str(path), *args], text=True, capture_output=True, check=True)
            real_run(['git', 'init', '--bare', '--initial-branch=main', str(remote)], capture_output=True, check=True)
            git(seed, 'init', '--initial-branch=main')
            for relative, value in docs.items():
                path = seed / relative; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(vault.encrypt(yaml.dump(value, Dumper=vault_yaml.VaultDumper), vault_id='cac'))
            git(seed, 'add', '.')
            git(seed, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Initialize encrypted fixture')
            git(seed, 'remote', 'add', 'origin', str(remote)); git(seed, 'push', 'origin', 'main')
            (project / 'myvars').write_bytes(vault.encrypt(yaml.safe_dump({'git_url':
                'https://git.example.invalid/fixture-owner/autodeploy.git'}), vault_id='default'))
            loader = DataLoader(); loader.set_vault_secrets([('cac', secret), ('default', environment_secret)])
            def redirected(command, *args, **kwargs):
                command = [str(remote) if value == 'https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git' else value for value in command]
                self.assertFalse(any(value.startswith(('https://', 'http://', 'git@')) for value in command))
                return real_run(command, *args, **kwargs)
            def run(phase, transition=None, check=False):
                plugin = module.ActionModule.__new__(module.ActionModule)
                args = {'operation': 'release_guest', 'phase': phase, 'guest': guest, 'hypervisor': pin}
                if transition is not None: args['transition'] = transition
                plugin._task = SimpleNamespace(args=args, check_mode=check); plugin._loader = loader
                return plugin.run(task_vars={'awx_job_id': 123, 'awx_job_template_id': 456, 'awx_project_revision': 'a' * 40})
            with mock.patch.object(ActionBase, 'run', side_effect=lambda *a, **k: {}), mock.patch.object(module, 'ROOT', project), \
                 mock.patch.object(module, 'SourceClient', return_value=source), \
                 mock.patch.object(module.subprocess, 'run', side_effect=redirected), \
                 mock.patch.dict(os.environ, {'CAC_GIT_TOKEN': 'synthetic-writer-token'}):
                planned = run('plan', check=True)
                self.assertFalse(planned.get('failed'), planned)
                transition = planned['transition']
                self.assertEqual(source.calls, [])
                self.assertEqual(git(remote, 'rev-list', '--count', 'main').stdout.strip(), '1')
                original_request = source.request
                def interrupted(method, path, body=None):
                    if method == 'PATCH' and path.startswith('inventories/'):
                        raise module.keys.StoreError('Synthetic API interruption')
                    return original_request(method, path, body)
                with mock.patch.object(source, 'request', side_effect=interrupted):
                    failed = run('publish', transition)
                self.assertTrue(failed['failed'], failed)
                self.assertTrue(failed['durable_policy_published'])
                self.assertEqual(git(remote, 'rev-list', '--count', 'main').stdout.strip(), '2')
                fresh_plan = run('plan')
                self.assertFalse(fresh_plan.get('failed'), fresh_plan)
                transition = fresh_plan['transition']
                finished = run('publish', transition)
                self.assertTrue(finished.get('published'), finished)
                self.assertFalse(finished.get('failed'), finished)
                count = len(source.calls)
                repeated = run('publish', transition)
                self.assertFalse(repeated['changed'], repeated)
                self.assertEqual(len(source.calls), count)
                self.assertEqual(git(remote, 'rev-list', '--count', 'main').stdout.strip(), '2')
                self.assertEqual(source.credential, None)
            restored = {relative: AnsibleLoader(vault.decrypt(git(remote, 'show', 'main:' + relative).stdout.encode())).get_single_data()
                        for relative in docs}
            self.assertEqual(restored['state/aap_vm_allocations_vault.yml'], allocation)
            self.assertEqual(restored['vaults/cac/aap_autodeploy_configascode-cac-vault.yml']['aap_instance_api_credentials'], main['aap_instance_api_credentials'])
            self.assertFalse(any(method == 'DELETE' or 'credentials/' in path for method, path in source.calls))


if __name__ == '__main__': unittest.main()
