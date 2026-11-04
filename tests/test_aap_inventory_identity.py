"""Preserve immutable registry/token identities when an AAP inventory entry is renamed."""
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
from ansible.errors import AnsibleFilterError
from ansible.plugins.action import ActionBase

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


identity = load('test_inventory_identity', 'filter_plugins/aap_inventory_identity.py')


def fixture():
    physical = 'aap27-test-07'
    resource = {'vm_name': physical, 'uuid': '11111111-2222-3333-4444-555555555555',
                'disk': '/opt/vms/' + physical + '.disk.qcow2', 'address': '192.168.70.7',
                'network': 'isolated', 'bridge': 'vmbr0', 'mac': '52:54:00:12:34:07',
                'hypervisor_machine_id': 'a' * 32, 'verified': True}
    host = {'ansible_host': resource['address'], 'ansible_fqdn': 'api.v07.example.invalid',
            'vm_ip': resource['address'], 'vm_uuid': resource['uuid'], 'vm_resource': resource,
            'aap_instance_number': 7, 'host_keys': ['ssh-ed25519 AAAA']}
    route = {'vm_name': physical, 'vm_ip': resource['address'], 'aap_hostname': 'https://' + host['ansible_fqdn'],
             'hypervisor': {'machine_id': resource['hypervisor_machine_id']}, 'guest_host_keys': host['host_keys']}
    return physical, host, route, {'aap': resource}


class InventoryIdentityTests(unittest.TestCase):
    def test_alias_uses_only_existing_verified_vm_resource_without_rekeying_or_guessing(self):
        physical, host, *_ = fixture()
        before = deepcopy(host)
        self.assertEqual(identity.inventory_instance_name('aap27-v07', host), physical)
        self.assertEqual(identity.inventory_instance_name(physical, host), physical)
        self.assertEqual(identity.inventory_instance_name(physical, {}), physical)
        self.assertEqual(identity.inventory_instance_name('aap27-v07', {}), 'aap27-v07')
        self.assertEqual(host, before)
        for mutation in [lambda h: h['vm_resource'].update(verified=False),
                         lambda h: h['vm_resource'].update(vm_name='aap27-test-08'),
                         lambda h: h['vm_resource'].update(vm_name={'bad': True}),
                         lambda h: h.update(aap_instance_number=8),
                         lambda h: h.update(vm_uuid='foreign'),
                         lambda h: h['vm_resource'].update(disk='/opt/vms/foreign.disk.qcow2'),
                         lambda h: h.update(ansible_host='192.168.70.99')]:
            bad = deepcopy(host); mutation(bad)
            with self.assertRaises(AnsibleFilterError): identity.inventory_instance_name('aap27-v07', bad)

    def test_existing_inventory_provenance_must_match_every_registered_route_identity(self):
        _, host, route, resources = fixture()
        self.assertTrue(identity.inventory_route_matches('aap27-v07', host, route, resources))
        self.assertTrue(identity.inventory_route_matches('aap27-test-07', {}, route, resources))
        cases = [('route', lambda r: r.update(vm_name='aap27-test-08')),
                 ('route', lambda r: r.update(vm_ip='192.168.70.99')),
                 ('route', lambda r: r.update(aap_hostname='https://foreign.example.invalid')),
                 ('route', lambda r: r.update(guest_host_keys=['ssh-ed25519 BBBB'])),
                 ('resources', lambda r: r['aap'].update(uuid='99999999-2222-3333-4444-555555555555'))]
        for category, mutate in cases:
            bad_route, bad_resources = deepcopy(route), deepcopy(resources)
            mutate(bad_route if category == 'route' else bad_resources)
            with self.subTest(category=category), self.assertRaises(AnsibleFilterError):
                identity.inventory_route_matches('aap27-v07', host, bad_route, bad_resources)

    def test_existing_token_action_selects_original_store_record_and_still_checks_trusted_fqdn(self):
        action = load('test_inventory_instance_access', 'action_plugins/aap_instance_access.py')
        physical, host, *_ = fixture()
        data = {'schema_version': 1, 'instances': {physical: {'hostname': 'https://' + host['ansible_fqdn'],
                'token': 'synthetic-private-token', 'token_id': 7, 'expires': '2030-01-01T00:00:00Z'}}}
        with tempfile.TemporaryDirectory(prefix='inventory-token-') as temporary:
            path = Path(temporary) / 'token.json'; path.write_text(json.dumps(data)); path.chmod(0o600)
            original = path.read_bytes()
            plugin = action.ActionModule.__new__(action.ActionModule)
            plugin._task = SimpleNamespace(args={'instance_name': identity.inventory_instance_name('aap27-v07', host),
                                                'fqdn': host['ansible_fqdn']})
            environment = {'AAP_INSTANCE_KEY_STORE_FILE': str(path), 'AAP_HOSTNAME': '', 'AAP_TOKEN': '',
                           'AAP_USERNAME': '', 'AAP_PASSWORD': ''}
            with mock.patch.object(ActionBase, 'run', side_effect=lambda *a, **k: {}), mock.patch.dict(os.environ, environment):
                result = plugin.run()
                self.assertEqual(result['authentication']['token'], data['instances'][physical]['token'])
                self.assertTrue(result['authentication']['validate_certs'])
                plugin._task.args['fqdn'] = 'foreign.example.invalid'
                failed = plugin.run()
                self.assertIn('access_error', failed)
                self.assertNotIn(data['instances'][physical]['token'], json.dumps(failed))
            self.assertEqual(path.read_bytes(), original)

    def test_actual_select_tasks_keep_main_inventory_alias_but_registry_only_stages_keep_physical_key(self):
        physical, host, route, resources = fixture()
        for native in ('true', 'false'):
            for selected, has_entry in [('aap27-v07', True), (physical, False), ('', False)]:
                with self.subTest(native=native, selected=selected), tempfile.TemporaryDirectory(prefix='inventory-route-') as temporary:
                    directory = Path(temporary)
                    plugins = directory / 'action_plugins'; plugins.mkdir()
                    plugins.joinpath('aap_read_instance.py').write_text(
                        'from ansible.plugins.action import ActionBase\n'
                        'class ActionModule(ActionBase):\n'
                        ' def run(self,tmp=None,task_vars=None):\n'
                        '  assert self._task.args["instance_key"]==task_vars["fixture_physical"]\n'
                        '  return {"changed":False,"instance_route":task_vars["fixture_route"],"instance_resources":task_vars["fixture_resources"]}\n')
                    tasks = []
                    if has_entry:
                        tasks.append({'ansible.builtin.add_host': dict(host, name=selected)})
                    supplied = {'aap_instance_key': selected}
                    if not selected:
                        supplied['aap_instance_route'] = route
                    tasks += [{'ansible.builtin.set_fact': supplied},
                              {'ansible.builtin.include_tasks': str(ROOT / 'tasks/aap-instance-select.yml')},
                              {'ansible.builtin.assert': {'that': ["aap_instance_key == fixture_selected",
                                  "vm_name == fixture_physical", "vm_ip == fixture_route.vm_ip"]}}]
                    play = directory / 'play.yml'
                    play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                        'vars': {'fixture_physical': physical, 'fixture_selected': selected or physical,
                                 'fixture_route': route, 'fixture_resources': resources}, 'tasks': tasks}], sort_keys=False))
                    cfg = directory / 'ansible.cfg'; cfg.write_text('[defaults]\n')
                    env = dict(os.environ, ANSIBLE_CONFIG=str(cfg), ANSIBLE_JINJA2_NATIVE=native,
                               ANSIBLE_ACTION_PLUGINS=str(plugins), ANSIBLE_FILTER_PLUGINS=str(ROOT / 'filter_plugins'),
                               ANSIBLE_LOCAL_TEMP=str(directory / 'local'), ANSIBLE_REMOTE_TEMP=str(directory / 'remote'))
                    result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(play)],
                                            capture_output=True, text=True, env=env, timeout=40)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__': unittest.main()
