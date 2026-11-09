"""Verify native exact-guest presence/absence and isolated policy/DHCP cleanup."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from test_guest_release_runtime import fixture as release_fixture, runtime


def fixture(absent=False):
    source, state = release_fixture()
    guest, pin = source['guest'], source['hypervisor']
    pin.update(user='fixture', port=2222, host_keys=['ssh-ed25519 AAAA'])
    before = deepcopy(source['transition']['desired_policy'])
    other = {'bridge': 'virbr0', 'ipv4': '192.168.10.6', 'mac': '52:54:00:00:00:08'}
    before['https_clients'].append(other)
    desired = deepcopy(before)
    desired['https_clients'] = [other]
    desired.pop('released_clients')
    request = {'operation': 'retire_plan', 'guest_name': guest['vm_name'], 'guest': guest,
        'hypervisor': pin, 'transition': {'previous_policy': before, 'desired_policy': desired, 'guest': guest},
        'check_mode': False}
    selected = '<host mac="%s" ip="%s" name="%s"/>' % (guest['mac'], guest['address'], guest['vm_name'])
    network = ('<network><name>isolated</name><bridge name="virbr0"/><ip address="192.168.10.1">'
        '<dhcp>' + selected + '<host mac="52:54:00:00:00:08" ip="192.168.10.6" name="other-v07"/>'
        '</dhcp></ip></network>')
    state.update(policy=before, addresses=[pin['address']], zone='libvirt',
        disk_states={guest['disk']: {'exists': True, 'regular': True, 'symlink': False, 'links': 1},
                     '/opt/vms/' + guest['vm_name'] + '.qcow2': {'exists': False}},
        native_rich_rules={'runtime': [], 'permanent': []}, networks={'isolated': network},
        network_definitions={'isolated': {'persistent': network, 'current': network}},
        dhcp_leases={'isolated': '2000-01-01 00:00:00 %s ipv4 %s/24 %s -' %
                     (guest['mac'], guest['address'], guest['vm_name'])})
    if absent:
        state['domains'].pop(guest['vm_name'])
        state['disk_states'][guest['disk']] = {'exists': False}
    return request, state


class GenericRetirementRuntimeTests(unittest.TestCase):
    def test_optional_absence_probe_never_substitutes_another_domain_and_keeps_default_strict(self):
        self.probe_fixture()

    def test_optional_absence_probe_refuses_any_remaining_canonical_disk(self):
        self.probe_fixture(disk_exists=True)

    def probe_fixture(self, disk_exists=False):
        request, _ = fixture()
        pin = request['hypervisor']
        calls = []
        directory = SimpleNamespace(is_dir=lambda: True, is_symlink=lambda: False,
                                    stat=lambda: SimpleNamespace(st_uid=0, st_mode=0o700))
        config = SimpleNamespace(is_file=lambda: True, is_symlink=lambda: False,
            stat=lambda: SimpleNamespace(st_uid=0, st_mode=0o600),
            read_text=lambda: json.dumps(request['transition']['previous_policy']))
        network = '<network><name>isolated</name><bridge name="virbr0"/></network>'
        def command(arguments, *args, **kwargs):
            calls.append(arguments)
            if arguments[:3] == ['/usr/sbin/ip', '-j', 'address']:
                value = json.dumps([{'addr_info': [{'family': 'inet', 'local': pin['address']}]}])
            elif arguments[0] == 'systemctl': value = 'active'
            elif 'domifaddr' in arguments: raise ValueError('The selected domain is absent')
            elif 'net-list' in arguments: value = 'isolated\n'
            elif 'net-dumpxml' in arguments: value = network
            elif 'net-dhcp-leases' in arguments: value = ''
            elif arguments[0] == 'firewall-cmd': value = 'libvirt' if '--get-zone-of-interface=virbr0' in arguments else ''
            else: value = ''
            return SimpleNamespace(stdout=value)
        file_info = SimpleNamespace(st_mode=0o100600, st_ino=1, st_dev=1, st_size=1, st_mtime_ns=1, st_nlink=1)
        with patch.object(runtime.base.os, 'geteuid', return_value=0), \
             patch.object(runtime.base.os, 'lstat', **({'return_value': file_info} if disk_exists else {'side_effect': FileNotFoundError})), \
             patch.object(runtime.base.Path, 'read_text', return_value='1' * 32), \
             patch.object(runtime.base, 'command', side_effect=command):
            route = {'vm_name': request['guest_name'], 'hypervisor': pin}
            if disk_exists:
                with self.assertRaises(ValueError): runtime.base.probe(route, request['transition']['previous_policy'], allow_absent_guest=True)
            else:
                state = runtime.base.probe(route, request['transition']['previous_policy'], allow_absent_guest=True)
                self.assertEqual(state['domains'], {})
                self.assertTrue(all(not row['exists'] for row in state['disk_states'].values()))
                self.assertFalse(any('domifaddr' in arguments or 'dumpxml' in arguments for arguments in calls))
                with self.assertRaises(ValueError): runtime.base.probe(route, request['transition']['previous_policy'])

    def test_plan_proves_exact_domain_storage_and_static_reservations_without_changes(self):
        request, state = fixture()
        original = deepcopy((request, state))
        plan = runtime.retirement_plan(request, state)
        self.assertTrue(plan['domain_present'])
        self.assertFalse(plan['disks_absent'])
        self.assertEqual(len(plan['reservations']), 2)
        self.assertEqual(plan['dynamic_lease_cache'], {'rows': 1, 'expired': 1, 'unexpired': 0})
        self.assertEqual((request, state), original)
        request['operation'] = 'retire_apply'
        with self.assertRaises(ValueError): runtime.retirement_plan(request, state)

    def test_gone_vm_uses_saved_resource_and_requires_both_canonical_disks_absent(self):
        request, state = fixture(absent=True)
        request['operation'] = 'retire_apply'
        result = runtime.retirement_plan(request, state)
        self.assertFalse(result['domain_present'])
        self.assertTrue(result['disks_absent'])
        for path in state['disk_states']:
            changed = deepcopy(state)
            changed['disk_states'][path] = {'exists': True, 'regular': True, 'symlink': False, 'links': 1}
            with self.subTest(path=path), self.assertRaises(ValueError):
                runtime.retirement_plan(request, changed)

    def test_unknown_records_allow_only_physical_absence_and_no_policy_or_dhcp_removal(self):
        request, state = fixture(absent=True)
        request['guest'] = None
        request['transition']['guest'] = None
        request['transition']['previous_policy'] = deepcopy(request['transition']['desired_policy'])
        state['policy'] = deepcopy(request['transition']['desired_policy'])
        with self.assertRaises(ValueError): runtime.retirement_plan(request, state)
        for scope, text in state['network_definitions']['isolated'].items():
            root = ET.fromstring(text)
            dhcp = root.find('./ip/dhcp')
            dhcp.remove(dhcp.find('host'))
            state['network_definitions']['isolated'][scope] = ET.tostring(root, encoding='unicode')
        result = runtime.retirement_plan(request, state)
        self.assertTrue(result['already_absent'])
        self.assertFalse(result['changed'])

    def test_foreign_identity_native_grants_and_policy_drift_refuse_preflight(self):
        for variant in ('machine', 'uuid', 'mac', 'disk-link', 'other-disk', 'native-rule', 'dhcp-owner', 'policy', 'autostart'):
            request, state = fixture()
            guest = request['guest']
            if variant == 'machine': state['machine_id'] = '3' * 32
            elif variant in ('uuid', 'mac'):
                root = ET.fromstring(state['domains'][guest['vm_name']]['persistent'])
                if variant == 'uuid': root.find('uuid').text = 'foreign'
                else: root.find('./devices/interface/mac').set('address', '52:54:00:00:00:99')
                state['domains'][guest['vm_name']]['persistent'] = ET.tostring(root, encoding='unicode')
            elif variant == 'disk-link': state['disk_states'][guest['disk']]['symlink'] = True
            elif variant == 'other-disk': state['disk_states']['/opt/vms/' + guest['vm_name'] + '.qcow2'] = {'exists': True}
            elif variant == 'native-rule': state['native_rich_rules']['permanent'] = [
                'rule family="ipv4" source address="%s/32" port port="443" protocol="tcp" accept' % guest['address']]
            elif variant == 'dhcp-owner': state['network_definitions']['isolated']['persistent'] = state['network_definitions']['isolated']['persistent'].replace('name="' + guest['vm_name'] + '"', 'name="foreign-v07"')
            elif variant == 'policy': request['transition']['desired_policy']['https_clients'] = []
            else: state['autostart'] = ['other-v07']
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                runtime.retirement_plan(request, state)

    def test_native_apply_removes_only_exact_static_hosts_and_does_not_write_firewall(self):
        request, state = fixture(absent=True)
        request['operation'] = 'retire_apply'
        original_policy = deepcopy(state['policy'])
        calls = []
        def command(arguments, data=None, allowed=(0,)):
            calls.append(arguments)
            self.assertEqual(arguments[:6], ['virsh', '-c', 'qemu:///system', 'net-update', 'isolated', 'delete'])
            scope = 'persistent' if arguments[-1] == '--config' else 'current'
            network = ET.fromstring(state['network_definitions']['isolated'][scope])
            dhcp = network.find('./ip/dhcp')
            selected = [item for item in dhcp.findall('host') if item.get('name') == request['guest_name']]
            self.assertEqual(len(selected), 1)
            dhcp.remove(selected[0])
            state['network_definitions']['isolated'][scope] = ET.tostring(network, encoding='unicode')
            if scope == 'current':
                state['networks']['isolated'] = state['network_definitions']['isolated'][scope]
        with patch.object(runtime.base, 'command', side_effect=command), \
             patch.object(runtime.base, 'probe', side_effect=lambda *args, **kwargs: deepcopy(state)):
            first = runtime.reconcile_retirement(request)
            self.assertTrue(first['retirement_verified'])
            self.assertFalse(first['applied'])
            self.assertEqual(first['dhcp_reservations_removed'], 2)
            self.assertEqual(state['policy'], original_policy)
            # Native Ansible applies nft separately after the retained resource proof.
            state['policy'] = deepcopy(request['transition']['desired_policy'])
            repeated = runtime.reconcile_retirement(request)
            self.assertFalse(repeated['changed'])
            self.assertEqual(repeated['dhcp_reservations_removed'], 0)
            self.assertEqual(first['dynamic_lease_cache']['expired'], 1)
        for text in state['network_definitions']['isolated'].values():
            names = [item.get('name') for item in ET.fromstring(text).findall('./ip/dhcp/host')]
            self.assertEqual(names, ['other-v07'])
        self.assertEqual(len(calls), 2)


if __name__ == '__main__':
    unittest.main()
