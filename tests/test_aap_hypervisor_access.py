"""Verify narrowly derived management access, local rollback and encrypted publication."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import yaml
from ansible.errors import AnsibleActionFail
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase
from ansible.utils.unsafe_proxy import AnsibleUnsafeText

from test_instance_keys import retirement_fixture, FakeRetirementSource, saved, load, keys, vault_yaml

ROOT = Path(__file__).resolve().parents[1]
access = load('test_hypervisor_management', 'src/aap_hypervisor_access.py')


def fixture():
    context, _, main, shared, hactar, allocation = retirement_fixture()
    route = context['route']
    primary = allocation['aap_vm_allocation']['reservations']['selected-request']['instance_resources']['aap']
    old = deepcopy(context['previous_policy'])
    old['guest_host_clients'] = [client for client in old['guest_host_clients'] if client['ipv4'] != primary['address']]
    for configuration, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar')):
        if kind == 'autodeploy':
            rows = configuration['autodeploy_configuration']['inventories']
        elif kind == 'shared':
            rows = configuration['host_inventory_configuration']['hosts'][:1]
        else:
            rows = configuration['controller_hosts_hactar_recovery']
        for row in rows:
            values = keys.inventory_variables(row)
            for alias in ('isolation_policy', 'hactar_isolation_policy'):
                if alias in values:
                    values[alias] = deepcopy(old)
            if kind == 'autodeploy':
                values['aap_hypervisor_isolation_host_clients'] = deepcopy(old['guest_host_clients'])
            keys.set_inventory_variables(row, values)
    # Registration sees only the actual shared-inventory instance, without a synthetic foreign-name duplicate.
    shared['host_inventory_configuration']['hosts'] = [row for row in shared['host_inventory_configuration']['hosts'] if row['inventory'] == 'Shared']
    shared['host_inventory_configuration']['groups'][0]['variables'] = {'hypervisor_host': 'fixture-hypervisor'}
    xml = ('<domain><name>%s</name><uuid>%s</uuid><devices><disk device="disk"><source file="%s"/></disk>'
           '<interface type="network"><mac address="%s"/><source network="isolated"/></interface></devices></domain>'
           % (route['vm_name'], primary['uuid'], primary['disk'], primary['mac']))
    probe = {'machine_id': route['hypervisor']['machine_id'], 'addresses': [route['hypervisor']['address']],
        'policy': deepcopy(old), 'autostart': [], 'zone': 'libvirt',
        'networks': {'isolated': '<network><name>isolated</name><bridge name="vmbr0"/></network>'},
        'domains': {route['vm_name']: {'persistent': xml, 'current': xml}},
        'leases': '%s ipv4 %s/24' % (primary['mac'], primary['address'])}
    expected = {'route': route, 'primary': primary, 'declared_policy': old, 'check_mode': False}
    return expected, probe, main, shared, hactar, allocation


class ManagementAccessTests(unittest.TestCase):
    def test_only_selected_management_port_is_added_and_all_old_rules_are_preserved(self):
        expected, probe, *_ = fixture()
        before = deepcopy((expected, probe))
        plan = access.plan(expected, probe)
        self.assertEqual(before, (expected, probe))
        self.assertEqual(plan['client']['ports'], [2222])
        self.assertEqual(plan['client']['destinations'], [expected['route']['hypervisor']['address']])
        self.assertEqual(plan['desired_policy']['guest_host_clients'][:-1], expected['declared_policy']['guest_host_clients'])
        for key in ('bridges', 'dns_bridges', 'https_clients', 'protected_ipv4'):
            self.assertEqual(plan['desired_policy'][key], expected['declared_policy'][key])
        probe['policy'] = plan['desired_policy']
        self.assertFalse(access.plan(expected, probe)['changed'])

    def test_foreign_identity_production_address_autostart_and_drift_fail(self):
        cases = [lambda e, p: p.update(machine_id='2' * 32),
                 lambda e, p: p.update(addresses=[]),
                 lambda e, p: p.update(autostart=['unknown']),
                 lambda e, p: e['primary'].update(uuid='11111111-2222-3333-4444-555555555555'),
                 lambda e, p: e['primary'].update(mac='52:54:00:12:34:aa'),
                 lambda e, p: e['primary'].update(address='192.168.70.99'),
                 lambda e, p: e['primary'].update(bridge='foreign'),
                 lambda e, p: e['primary'].update(disk='/opt/vms/foreign.disk.qcow2'),
                 lambda e, p: e['declared_policy']['protected_ipv4'].append(e['route']['hypervisor']['address']),
                 lambda e, p: e['declared_policy'].update(https_clients=[]),
                 lambda e, p: p['policy'].update(guest_host_clients=[])]
        for index, change in enumerate(cases):
            with self.subTest(index=index):
                expected, probe, *_ = fixture()
                change(expected, probe)
                with self.assertRaises((ValueError, KeyError)):
                    access.plan(expected, probe)

    def test_saved_and_running_domains_cannot_bypass_network_isolation(self):
        for replacement in ('<hostdev/>', '<filesystem/>', '<interface type="direct"><source dev="eth0"/></interface>',
                            '<disk><source protocol="https"><host name="foreign"/></source></disk>'):
            expected, probe, *_ = fixture()
            probe['domains']['other'] = {'persistent': '<domain><name>other</name><devices>' + replacement + '</devices></domain>'}
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                access.plan(expected, probe)
        expected, probe, *_ = fixture()
        duplicate = probe['domains'][expected['route']['vm_name']]['current'].replace(expected['route']['vm_name'], 'other')
        probe['domains']['other'] = {'current': duplicate}
        with self.assertRaises(ValueError):
            access.plan(expected, probe)

    def test_existing_selected_local_permission_cannot_expand_or_be_replaced(self):
        expected, probe, *_ = fixture()
        selected = access.plan(expected, probe)['client']
        for replacement in (dict(selected, ports=[22]), dict(selected, ports=[2222, 443]),
                            dict(selected, destinations=['192.168.70.1'])):
            expected['declared_policy']['guest_host_clients'].append(replacement)
            with self.assertRaises(ValueError):
                access.plan(expected, probe)
            expected['declared_policy']['guest_host_clients'].pop()

    def test_encrypted_capture_authorization_preserves_literals_and_refuses_extra_grants(self):
        expected, _, main, shared, hactar, allocation = fixture()
        requested = access.desired_policy(expected['route'], expected['primary'], expected['declared_policy'])
        record = allocation['aap_vm_allocation']['reservations']['selected-request']
        context = keys.management_access_context(main, record, expected['route']['vm_name'], expected['route'], requested)
        for configuration, kind in ((main, 'autodeploy'), (shared, 'shared'), (hactar, 'hactar')):
            original = deepcopy(configuration)
            updated = keys.management_inventory_capture(configuration, context, kind)
            self.assertEqual(configuration, original)
            self.assertEqual(updated, keys.management_inventory_capture(updated, context, kind))
            if kind == 'autodeploy':
                row = updated['autodeploy_configuration']['inventories'][0]
            elif kind == 'shared':
                row = updated['host_inventory_configuration']['hosts'][0]
            else:
                row = updated['controller_hosts_hactar_recovery'][0]
            self.assertIsInstance(row['variables'], AnsibleUnsafeText)
            self.assertEqual(keys.inventory_variables(row)['hactar_isolation_policy'], requested)
        invalid = deepcopy(requested)
        invalid['guest_host_clients'][-1]['ports'].append(443)
        with self.assertRaises(keys.StoreError):
            keys.management_access_context(main, record, expected['route']['vm_name'], expected['route'], invalid)
        record['decommissioned'] = True
        with self.assertRaises(keys.StoreError):
            keys.management_access_context(main, record, expected['route']['vm_name'], expected['route'], requested)

    def test_source_alias_retry_allows_only_the_exact_same_addition(self):
        expected, _, main, _, _, allocation = fixture()
        desired = access.desired_policy(expected['route'], expected['primary'], expected['declared_policy'])
        record = allocation['aap_vm_allocation']['reservations']['selected-request']
        context = keys.management_access_context(main, record, expected['route']['vm_name'], expected['route'], desired)
        old = {'isolation_policy': expected['declared_policy'], 'keep': '{{ literal }}'}
        result = keys.source_management_variables(old, context)
        self.assertEqual(result['keep'], old['keep'])
        self.assertEqual(result['isolation_policy'], desired)
        self.assertEqual(keys.source_management_variables(result, context), result)
        foreign = deepcopy(old)
        foreign['isolation_policy']['guest_host_clients'][0]['ports'].append(8443)
        with self.assertRaises(keys.StoreError):
            keys.source_management_variables(foreign, context)

    def test_resource_verifier_is_read_only_for_real_and_check_modes(self):
        for check in (False, True):
            expected, state, *_ = fixture()
            expected['check_mode'] = check
            original = deepcopy(state)
            with mock.patch.object(access, 'probe', return_value=state) as probe, \
                 mock.patch.object(access, 'command') as command:
                result = access.reconcile(expected)
                self.assertFalse(result['applied'])
                self.assertEqual(result['desired_policy'], access.desired_policy(expected['route'], expected['primary'], expected['declared_policy']))
                self.assertEqual(probe.call_args.args[1], expected['declared_policy'])
                command.assert_not_called()
                self.assertEqual(state, original)

    def test_connection_tasks_bind_original_host_and_do_not_proxy_hypervisor_through_itself(self):
        tasks = yaml.safe_load((ROOT / 'tasks/aap-hypervisor-access.yml').read_text())
        remote = next(row for row in tasks if 'delegate_to' in row and 'block' in row)
        self.assertIn('hostvars[inventory_hostname].aap_instance_route.hypervisor.port', remote['vars']['ansible_port'])
        self.assertIn('StrictHostKeyChecking=yes', remote['vars']['ansible_ssh_common_args'])
        self.assertNotIn('ProxyCommand', remote['vars']['ansible_ssh_common_args'])
        self.assertTrue(next(row for row in remote['block'] if 'ansible.builtin.command' in row)['no_log'])
        tcp = next(row for row in tasks if 'ansible.builtin.wait_for' in row)
        self.assertIn('hostvars[inventory_hostname].aap_instance_route.vm_ip', tcp['vars']['ansible_host'])
        self.assertIn('hostvars[inventory_hostname].aap_instance_ssh_args', tcp['vars']['ansible_ssh_common_args'])
        self.assertIn('hostvars[inventory_hostname].aap_hypervisor_management_login.password', tcp['vars']['ansible_password'])

    def test_native_delegation_renders_original_route_and_pinned_guest_jump_without_connecting(self):
        expected, _, _, _, _, _ = fixture()
        with tempfile.TemporaryDirectory(prefix='management-delegation-') as temporary:
            directory = Path(temporary)
            plugins = directory / 'action_plugins'; plugins.mkdir()
            plugins.joinpath('connection_proof.py').write_text(
                'import json\nfrom ansible.plugins.action import ActionBase\n'
                'class ActionModule(ActionBase):\n'
                '    TRANSFERS_FILES = False\n'
                '    def run(self, tmp=None, task_vars=None):\n'
                '        route=task_vars["hostvars"][task_vars["inventory_hostname"]]["aap_instance_route"]\n'
                '        original=task_vars["hostvars"][task_vars["inventory_hostname"]]\n'
                '        p=self._play_context\n'
                '        if "stdin" in self._task.args:\n'
                '            request=json.loads(self._task.args["stdin"])\n'
                '            assert request["route"] == route and request["primary"] == original["aap_instance_resources"]["aap"]\n'
                '            assert p.remote_addr == route["hypervisor"]["address"] and p.port == route["hypervisor"]["port"]\n'
                '            assert p.remote_user == route["hypervisor"]["user"]\n'
                '            assert "ProxyCommand" not in self._connection.get_option("ssh_common_args")\n'
                '        else:\n'
                '            assert p.remote_addr == route["vm_ip"] and p.port == 22, repr((p.remote_addr,p.port,route["vm_ip"]))\n'
                '            assert p.remote_user == original["aap_hypervisor_management_login"]["user"], repr(p.remote_user)\n'
                '            assert self._connection.get_option("ssh_common_args") == original["aap_instance_ssh_args"]\n'
                '            assert str(self._task.args["port"]) == str(route["hypervisor"]["port"]), repr(self._task.args["port"])\n'
                '        return {"changed":False,"stdout":json.dumps({"desired_policy":original["fixture_policy"],"changed":False})}\n')
            tasks = yaml.safe_load((ROOT / 'tasks/aap-hypervisor-access.yml').read_text())
            transaction = next(row for row in tasks if 'block' in row)
            verifier = next(row for row in transaction['block'] if 'ansible.builtin.command' in row)
            verifier = deepcopy(verifier)
            verifier['vars'] = transaction['vars']
            verifier['delegate_to'] = transaction['delegate_to']
            verifier['become'] = False
            tasks = [tasks[1], verifier, next(row for row in tasks if 'ansible.builtin.wait_for' in row)]
            for row in tasks:
                row['no_log'] = False  # Synthetic fixture only.
                for module in ('ansible.builtin.command', 'ansible.builtin.wait_for'):
                    if module in row:
                        row['connection_proof'] = row.pop(module)
                        if module == 'ansible.builtin.command':
                            row['connection_proof']['argv'] = ['synthetic-resource-verifier']
            variables = {'aap_instance_route': expected['route'], 'aap_instance_resources': {'aap': expected['primary']},
                'aap_hypervisor_isolation_https_clients': expected['declared_policy']['https_clients'],
                'aap_hypervisor_isolation_protected_ipv4': expected['declared_policy']['protected_ipv4'],
                'aap_hypervisor_isolation_host_clients': expected['declared_policy']['guest_host_clients'],
                'aap_management_native_runtime': {'path': '/tmp/synthetic-runtime'}, 'fixture_policy': expected['declared_policy'], 'aap_instance_trust': {'path': '/tmp/synthetic-trust'},
                'vault_ansible_user': 'guest_operator', 'vault_ansible_password': 'synthetic-password',
                'aap_instance_ssh_args': '-o StrictHostKeyChecking=yes -o ProxyCommand=synthetic-pinned-jump'}
            play = directory / 'play.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'gather_facts': False, 'connection': 'local',
                'vars': variables, 'tasks': [{'ansible.builtin.set_fact': {key: value for key, value in variables.items()
                    if key in ('aap_instance_route', 'aap_instance_resources', 'aap_instance_trust', 'aap_instance_ssh_args', 'fixture_policy')},
                    'no_log': True}] + tasks}], sort_keys=False))
            config = directory / 'ansible.cfg'; config.write_text('[defaults]\n')
            environment = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_ACTION_PLUGINS=str(plugins),
                ANSIBLE_FILTER_PLUGINS=str(ROOT / 'filter_plugins'), ANSIBLE_LOCAL_TEMP=str(directory / 'local'),
                ANSIBLE_REMOTE_TEMP=str(directory / 'remote'))
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                text=True, capture_output=True, env=environment, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_encrypted_git_publication_retries_source_interruption_without_rotating_token(self):
        module = load('test_management_publish_action', 'action_plugins/aap_publish_instance_keys.py')
        expected, _, main, shared, hactar, allocation = fixture()
        desired = access.desired_policy(expected['route'], expected['primary'], expected['declared_policy'])
        class Client(FakeRetirementSource):
            def rows(self, path):
                if path.startswith('groups/?'):
                    return [{'id': 77, 'name': 'guests'}]
                if path == 'groups/77/hosts/':
                    return [{'id': row['id']} for row in self.hosts.values() if row['inventory'] == 1]
                return super().rows(path)
        client = Client(main, shared, hactar)
        secret = VaultSecret(b'synthetic-cac-password')
        environment_secret = VaultSecret(b'synthetic-environment-password')
        vault = VaultLib([('cac', secret), ('default', environment_secret)])
        documents = {'vaults/cac/aap_autodeploy_configascode-cac-vault.yml': main,
            'cac/host_inventory.yml': shared, 'cac/hactar_recovery.yml': hactar,
            'state/aap_vm_allocations_vault.yml': allocation}
        real_run = subprocess.run
        with tempfile.TemporaryDirectory(prefix='encrypted-management-git-') as temporary:
            directory = Path(temporary)
            remote, seed, project = (directory / name for name in ('remote.git', 'seed', 'project'))
            seed.mkdir(); project.mkdir()
            def git(path, *arguments):
                return real_run(['git', '-C', str(path), *arguments], text=True, capture_output=True, check=True)
            real_run(['git', 'init', '--bare', '--initial-branch=main', str(remote)], capture_output=True, check=True)
            git(seed, 'init', '--initial-branch=main')
            for relative, value in documents.items():
                path = seed / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(vault.encrypt(yaml.dump(value, Dumper=vault_yaml.VaultDumper), vault_id='cac'))
            git(seed, 'add', '.')
            git(seed, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Initialize encrypted captures')
            git(seed, 'remote', 'add', 'origin', str(remote)); git(seed, 'push', 'origin', 'main')
            (project / 'myvars').write_bytes(vault.encrypt(yaml.safe_dump({'git_url':
                'https://git.example.invalid/fixture-owner/autodeploy.git'}), vault_id='default'))
            loader = DataLoader(); loader.set_vault_secrets([('cac', secret), ('default', environment_secret)])
            def redirected(command, *args, **kwargs):
                replaced = [str(remote) if value == 'https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git' else value for value in command]
                self.assertFalse(any(value.startswith(('https://', 'http://', 'git@')) for value in replaced))
                return real_run(replaced, *args, **kwargs)
            def run(policy=desired):
                plugin = module.ActionModule.__new__(module.ActionModule)
                plugin._task = SimpleNamespace(args={'instance_name': expected['route']['vm_name'],
                    'record': dict(saved('aap27.v07'), target=expected['route']['aap_hostname']), 'organization': 'Example',
                    'inventory_registration': {'route': expected['route'], 'policy': policy}}, check_mode=False)
                plugin._loader = loader
                return plugin.run(task_vars={'awx_job_id': 123, 'awx_job_template_id': 456, 'awx_project_revision': 'a' * 40})
            with mock.patch.object(ActionBase, 'run', return_value={}), mock.patch.object(module.ActionModule, '_project_root', return_value=project), \
                 mock.patch.object(module, 'SourceClient', return_value=client), \
                 mock.patch.object(module.subprocess, 'run', side_effect=redirected), \
                 mock.patch.dict(os.environ, {'CAC_GIT_TOKEN': 'synthetic-writer-token'}):
                invalid = deepcopy(desired); invalid['guest_host_clients'][-1]['ports'].append(443)
                with self.assertRaises(AnsibleActionFail): run(invalid)
                self.assertEqual(git(remote, 'rev-list', '--count', 'main').stdout.strip(), '1')
                self.assertEqual(client.calls, [])
                existing = next(row for row in client.hosts.values() if row['name'] == expected['route']['vm_name'])
                original_variables = existing['variables']
                existing['variables'] = json.dumps(dict(json.loads(original_variables), vm_uuid='foreign-primary'))
                with self.assertRaises(AnsibleActionFail): run()
                self.assertEqual(git(remote, 'rev-list', '--count', 'main').stdout.strip(), '1')
                self.assertEqual(client.calls, [])
                existing['variables'] = original_variables
                original_request = client.request
                def interrupted(method, path, body=None):
                    if method == 'PATCH' and path.startswith('inventories/'):
                        raise module.keys.StoreError('Synthetic source API interruption')
                    return original_request(method, path, body)
                with mock.patch.object(client, 'request', side_effect=interrupted):
                    with self.assertRaises(AnsibleActionFail) as failure: run()
                self.assertEqual(str(failure.exception), 'Synthetic source API interruption')
                self.assertEqual(git(remote, 'rev-list', '--count', 'main').stdout.strip(), '2')
                self.assertTrue(run()['published'])
                writes = len(client.calls)
                self.assertFalse(run()['changed'])
                self.assertEqual(len(client.calls), writes)
            restored = {}
            for relative in documents:
                restored[relative] = AnsibleLoader(vault.decrypt(git(remote, 'show', 'main:' + relative).stdout.encode())).get_single_data()
            self.assertEqual(restored['state/aap_vm_allocations_vault.yml'], allocation)
            updated = restored['vaults/cac/aap_autodeploy_configascode-cac-vault.yml']
            self.assertEqual(updated['aap_instance_api_credentials'], main['aap_instance_api_credentials'])
            self.assertEqual(updated['autodeploy_configuration']['credentials'], main['autodeploy_configuration']['credentials'])
            self.assertTrue(all(method != 'DELETE' for method, path in client.calls))
            self.assertEqual(len(client.hosts), len(shared['host_inventory_configuration']['hosts']) + 1)
            self.assertEqual(json.loads(next(row for row in client.hosts.values() if row['name'] == expected['route']['vm_name'])['variables'])['vm_resource'],
                             dict(expected['primary'], vm_name=expected['route']['vm_name']))
            self.assertFalse(keys.source_management_operations(client, restored['cac/host_inventory.yml'], updated,
                restored['cac/hactar_recovery.yml'], keys.management_access_context(updated,
                allocation['aap_vm_allocation']['reservations']['selected-request'], expected['route']['vm_name'], expected['route'], desired)))


if __name__ == '__main__':
    unittest.main()
