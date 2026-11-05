"""Require genuine Windows provenance and exact multi-NIC lifecycle transactions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from ansible.errors import AnsibleFilterError
import test_guest_release as release_tests
import test_guest_retirement as retirement_tests
import test_guest_retirement_role as role_tests
from test_guest_retirement_runtime import runtime

ORIGINAL_FIXTURE = release_tests.fixture


def source_fixture(new=True, nics=2, certificate_validated=True):
    original, pin, main, shared, hactar, allocation = ORIGINAL_FIXTURE(new=True)
    interfaces = [{'network': 'isolated', 'bridge': 'vmbr0', 'mac': original['mac'],
                   'address': original['address'], 'dns_name': 'winvm-v07.example.invalid'}]
    if nics == 2:
        interfaces.append({'network': 'management', 'bridge': 'vmbr0', 'mac': '52:54:00:12:34:98',
                           'address': '192.168.71.99', 'dns_name': 'winvm-v07-mgmt.example.invalid'})
    guest = {'kind': 'windows', 'vm_name': 'winvm-v07', 'instance_name': 'aap27-test-7',
             'uuid': original['uuid'], 'disk': '/opt/vms/win-winvm-v07-clone.disk.qcow2',
             'hypervisor_machine_id': pin['machine_id'], 'verified': True,
             'computer_name': 'WINVM-V07', 'computer_uuid': original['uuid'],
             'address': interfaces[-1]['address'], 'interfaces': interfaces, 'winrm_certificate_validated': certificate_validated}
    return guest, pin, main, shared, hactar, allocation


def retired_fixture():
    guest, pin, main, shared, hactar, allocation = source_fixture()
    context = release_tests.keys.guest_release_context(main, shared, guest, pin)
    documents = {kind: release_tests.keys.guest_release_inventory_capture(value, context, kind)
                 for kind, value in {'autodeploy': main, 'shared': shared, 'hactar': hactar}.items()}
    return guest, pin, documents, allocation


def runtime_fixture(absent=False, nics=2, certificate_validated=True):
    guest, pin, *_ = source_fixture(nics=nics, certificate_validated=certificate_validated)
    if nics == 2:
        guest['interfaces'][1]['bridge'] = 'vmbr1'
        pin['isolation_bridges'].append('vmbr1')
        pin['isolation_dns_bridges'].append('vmbr1')
    before = {'bridges': list(pin['isolation_bridges']), 'dns_bridges': list(pin['isolation_dns_bridges']), 'protected_ipv4': ['203.0.113.99'],
              'https_clients': [{'bridge': 'vmbr0', 'ipv4': '192.168.70.2', 'mac': '52:54:00:00:00:02'}]}
    desired = deepcopy(before)
    desired['released_clients'] = [{'bridge': nic['bridge'], 'ipv4': nic['address'], 'mac': nic['mac']} for nic in guest['interfaces']]
    request = {'operation': 'apply', 'guest': guest, 'hypervisor': pin,
               'transition': {'previous_policy': before, 'desired_policy': desired}, 'check_mode': False}
    interfaces = ''.join('<interface type="network"><source network="%s"/><mac address="%s"/></interface>' %
                         (nic['network'], nic['mac']) for nic in guest['interfaces'])
    xml = ('<domain><name>%s</name><uuid>%s</uuid><description>aap-disconnected-windows-clone</description>'
           '<title>%s:%s</title><devices><disk device="disk"><source file="%s"/></disk>%s</devices></domain>') % (
               guest['vm_name'], guest['uuid'], guest['instance_name'], guest['vm_name'], guest['disk'], interfaces)
    networks = {}
    for index, nic in enumerate(guest['interfaces']):
        gateway = '192.168.%s.1' % (70 + index)
        networks[nic['network']] = ('<network><name>%s</name><bridge name="%s"/><dns><host ip="%s"><hostname>%s</hostname></host></dns>'
            '<ip address="%s" netmask="255.255.255.0"><dhcp><host mac="%s" ip="%s" name="%s"/></dhcp></ip></network>') % (
                nic['network'], nic['bridge'], nic['address'], nic['dns_name'], gateway, nic['mac'], nic['address'], nic['dns_name'])
    state = {'machine_id': pin['machine_id'], 'addresses': [pin['address']], 'autostart': [], 'policy': before,
             'domains': {} if absent else {guest['vm_name']: {'persistent': xml, 'current': xml}},
             'networks': networks, 'network_definitions': {name: {'persistent': xml, 'current': xml} for name, xml in networks.items()},
             'dhcp_leases': {name: '' for name in networks}, 'native_rich_rules': {'runtime': [], 'permanent': []},
             'disk_states': {guest['disk']: {'exists': not absent, 'regular': True, 'symlink': False, 'links': 1},
                 '/opt/vms/' + guest['vm_name'] + '.disk.qcow2': {'exists': False},
                 '/opt/vms/' + guest['vm_name'] + '.qcow2': {'exists': False}}}
    return request, state


def retirement_request(absent=False):
    release, state = runtime_fixture(absent=absent)
    guest, pin = release['guest'], release['hypervisor']
    request = {'operation': 'retire_plan', 'guest_name': guest['vm_name'], 'guest': guest, 'guest_kind': 'windows',
               'hypervisor': pin, 'transition': {'previous_policy': release['transition']['desired_policy'],
                   'desired_policy': release['transition']['previous_policy'], 'guest': guest}, 'check_mode': False}
    state['policy'] = deepcopy(request['transition']['previous_policy'])
    return request, state


class WindowsGuestLifecycleTests(unittest.TestCase):
    def test_lab_exception_preserves_false_in_capture_and_still_requires_native_identity(self):
        keys = release_tests.keys
        for validated in (False, True):
            with self.subTest(certificate_validated=validated):
                guest, pin, main, shared, *_ = source_fixture(certificate_validated=validated)
                context = keys.guest_release_context(main, shared, guest, pin)
                capture = keys.guest_release_inventory_capture(shared, context, 'shared')
                row = next(row for row in capture['host_inventory_configuration']['hosts']
                           if row['name'] == guest['vm_name'])
                self.assertIs(keys.inventory_variables(row)['vm_resource']['winrm_certificate_validated'], validated)
                request, state = runtime_fixture(certificate_validated=validated)
                self.assertTrue(runtime.plan(request, state)['changed'])
                request['guest']['computer_uuid'] = '88888888-2222-3333-4444-555555555555'
                with self.assertRaises(ValueError):
                    runtime.plan(request, state)

    def test_certificate_result_requires_a_real_boolean_in_both_validators(self):
        for value in (None, 0, 1, 'false', 'true', [], {}):
            with self.subTest(value=value):
                guest, pin, main, shared, *_ = source_fixture(certificate_validated=value)
                with self.assertRaises(release_tests.keys.StoreError):
                    release_tests.keys.guest_release_context(main, shared, guest, pin)
                request, state = runtime_fixture(certificate_validated=value)
                with self.assertRaises(ValueError):
                    runtime.plan(request, state)

    def test_native_windows_probe_requires_explicit_absence_and_inspects_only_three_exact_paths(self):
        request, fixture = runtime_fixture(absent=True)
        pin = request['hypervisor'];calls = [];paths = []
        directory = SimpleNamespace(is_dir=lambda: True, is_symlink=lambda: False,
                                    stat=lambda: SimpleNamespace(st_uid=0, st_mode=0o700))
        config = SimpleNamespace(is_file=lambda: True, is_symlink=lambda: False,
            stat=lambda: SimpleNamespace(st_uid=0, st_mode=0o600), read_text=lambda: json.dumps(fixture['policy']))
        def command(arguments, *args, **kwargs):
            calls.append(arguments)
            if arguments[:3] == ['/usr/sbin/ip', '-j', 'address']:
                text = json.dumps([{'addr_info': [{'family': 'inet', 'local': pin['address']}]}])
            elif arguments[0] == 'systemctl': text = 'active'
            elif 'net-list' in arguments: text = '\n'.join(fixture['networks'])
            elif 'net-dumpxml' in arguments: text = fixture['networks'][arguments[4]]
            else: text = ''
            return SimpleNamespace(stdout=text)
        def missing(path): paths.append(path);raise FileNotFoundError
        route = {'vm_name': request['guest']['vm_name'], 'hypervisor': pin}
        with patch.object(runtime.base, 'DIRECTORY', directory), patch.object(runtime.base, 'CONFIG', config), \
             patch.object(runtime.base.os, 'geteuid', return_value=0), patch.object(runtime.base.os, 'lstat', side_effect=missing), \
             patch.object(runtime.base.Path, 'read_text', return_value=pin['machine_id']), patch.object(runtime.base, 'command', side_effect=command):
            state = runtime.base.probe(route, allow_absent_guest=True, guest_kind='windows')
            self.assertEqual(set(state['disk_states']), set(fixture['disk_states']))
            self.assertEqual(set(paths), set(fixture['disk_states']))
            self.assertFalse(any('domifaddr' in call or 'dumpxml' in call for call in calls))
            with self.assertRaises(ValueError): runtime.base.probe(route, guest_kind='windows')
            with patch.object(runtime.base.os, 'lstat', return_value=SimpleNamespace(st_mode=0o100600,
                    st_ino=1, st_dev=1, st_size=1, st_mtime_ns=1, st_nlink=1)):
                with self.assertRaises(ValueError): runtime.base.probe(route, allow_absent_guest=True, guest_kind='windows')

    def test_source_saves_every_exact_nic_without_linux_substitutes_and_retires_only_selected_windows_guest(self):
        guest, pin, main, shared, hactar, allocation = source_fixture()
        original = deepcopy((main, shared, hactar, allocation))
        keys = release_tests.keys
        context = keys.guest_release_context(main, shared, guest, pin)
        self.assertEqual(context['desired_policy']['released_clients'], [
            {'bridge': nic['bridge'], 'ipv4': nic['address'], 'mac': nic['mac']} for nic in guest['interfaces']])
        documents = {kind: keys.guest_release_inventory_capture(value, context, kind)
                     for kind, value in {'autodeploy': main, 'shared': shared, 'hactar': hactar}.items()}
        row = next(row for row in documents['shared']['host_inventory_configuration']['hosts'] if row['name'] == guest['vm_name'])
        values = keys.inventory_variables(row)
        self.assertEqual(values['ansible_connection'], 'winrm')
        self.assertNotIn('machine_id', values); self.assertNotIn('host_keys', values)
        self.assertEqual(values['vm_resource'], guest)
        source = release_tests.Source(documents['autodeploy'], documents['shared'], documents['hactar'])
        retired = keys.generic_retirement_context(documents['autodeploy'], documents['shared'], source,
                                                 guest['vm_name'], pin, guest_kind='windows')
        self.assertEqual(retired['desired_policy'], context['previous_policy'])
        self.assertEqual(len(retired['identities']), 2)
        for kind, value in documents.items(): keys.generic_retirement_capture(value, retired, kind)
        self.assertEqual((main, shared, hactar, allocation), original)
        with self.assertRaises(keys.StoreError): keys.generic_retirement_context(documents['autodeploy'], documents['shared'], source, guest['vm_name'], pin)

    def test_source_rejects_untrusted_incomplete_foreign_and_linux_shaped_windows_records_before_writes(self):
        for variant in ('validation-type', 'unverified', 'computer', 'unicode-computer', 'uuid', 'clone', 'owner', 'missing-nic', 'linux-field', 'duplicate', 'public', 'bootstrap'):
            guest, pin, main, shared, *_ = source_fixture()
            if variant == 'validation-type': guest['winrm_certificate_validated'] = 'false'
            elif variant == 'unverified': guest['verified'] = False
            elif variant == 'computer': guest['computer_name'] = 'FOREIGN'
            elif variant == 'unicode-computer': guest.update(vm_name='k-v07', computer_name='\u212a-V07', disk='/opt/vms/win-k-v07-clone.disk.qcow2')
            elif variant == 'uuid': guest['computer_uuid'] = '88888888-2222-3333-4444-555555555555'
            elif variant == 'clone': guest['disk'] = '/opt/vms/foreign.qcow2'
            elif variant == 'owner': guest['instance_name'] = 'aap27-test-8'
            elif variant == 'missing-nic': guest['interfaces'] = []
            elif variant == 'linux-field': guest['machine_id'] = '2' * 32
            elif variant == 'duplicate': guest['interfaces'][1]['mac'] = guest['interfaces'][0]['mac']
            elif variant == 'public': guest['interfaces'][0]['address'] = '8.8.8.8'
            with self.subTest(variant=variant), self.assertRaises((release_tests.keys.StoreError, AnsibleFilterError)):
                release_tests.keys.guest_release_context(main, shared, guest, pin, access='bootstrap_https' if variant == 'bootstrap' else 'release')

    def test_actual_native_windows_uuid_marker_all_nics_static_network_identity_and_exact_transition_are_required(self):
        for count in (1, 2):
            request, state = runtime_fixture(nics=count)
            self.assertTrue(runtime.plan(request, state)['changed'])
        for variant in ('validation-type', 'unverified', 'computer', 'uuid', 'marker', 'title', 'nic', 'dns', 'dhcp', 'bridge', 'lease', 'extra-policy', 'disk-link', 'bootstrap'):
            request, state = runtime_fixture()
            guest = request['guest']
            if variant == 'validation-type': guest['winrm_certificate_validated'] = 'false'
            elif variant == 'unverified': guest['verified'] = False
            elif variant == 'computer': guest['computer_name'] = 'FOREIGN'
            elif variant == 'uuid': guest['computer_uuid'] = '88888888-2222-3333-4444-555555555555'
            elif variant in ('marker', 'title', 'nic'):
                xml = state['domains'][guest['vm_name']]['persistent']
                state['domains'][guest['vm_name']]['persistent'] = xml.replace(
                    'aap-disconnected-windows-clone' if variant == 'marker' else guest['instance_name'] if variant == 'title' else guest['interfaces'][1]['mac'], 'foreign')
            elif variant in ('dns', 'dhcp', 'bridge'):
                network = guest['interfaces'][1]['network'];xml = state['network_definitions'][network]['persistent']
                if variant == 'dns': xml = xml.replace('<hostname>', '<hostname>foreign-')
                elif variant == 'dhcp': xml = xml.replace('mac="' + guest['interfaces'][1]['mac'], 'mac="52:54:00:00:00:09')
                else: xml = xml.replace('name="' + guest['interfaces'][1]['bridge'] + '"', 'name="foreign"')
                state['network_definitions'][network]['persistent'] = xml
            elif variant == 'lease': state['dhcp_leases'][guest['interfaces'][1]['network']] = '2000-01-01 00:00:00 52:54:00:00:00:09 ipv4 ' + guest['interfaces'][1]['address'] + '/24 x'
            elif variant == 'extra-policy': request['transition']['desired_policy']['protected_ipv4'] = []
            elif variant == 'disk-link': state['disk_states'][guest['disk']]['symlink'] = True
            else: request['mode'] = 'bootstrap_https'
            with self.subTest(variant=variant), self.assertRaises(ValueError): runtime.plan(request, state)

    def test_windows_retirement_requires_explicit_kind_exact_absence_and_all_dhcp_dns_cleanup(self):
        request, state = retirement_request()
        plan = runtime.retirement_plan(request, state)
        self.assertEqual(len(plan['reservations']), 8)
        self.assertEqual({row['kind'] for row in plan['reservations']}, {'dns-host', 'ip-dhcp-host'})
        request['operation'] = 'retire_apply'
        with self.assertRaises(ValueError): runtime.retirement_plan(request, state)
        request, state = retirement_request(absent=True);request['operation'] = 'retire_apply'
        self.assertTrue(runtime.retirement_plan(request, state)['disks_absent'])
        for path in state['disk_states']:
            changed = deepcopy(state);changed['disk_states'][path]['exists'] = True
            with self.subTest(path=path), self.assertRaises(ValueError): runtime.retirement_plan(request, changed)
        request.pop('guest_kind')
        with self.assertRaises((ValueError, KeyError)): runtime.retirement_plan(request, state)

    def test_windows_real_encrypted_release_publication_retry_uses_same_source_transaction(self):
        for validated in (False, True):
            def fixture(*args, **kwargs):
                return source_fixture(*args, certificate_validated=validated, **kwargs)
            with self.subTest(certificate_validated=validated), patch.object(release_tests, 'fixture', side_effect=fixture):
                release_tests.GuestReleaseTests().exercise_action('release_guest')

    def test_native_windows_cleanup_preserves_unrelated_dns_dhcp_and_recovers_failed_policy_apply(self):
        for fail_once in (False, True):
            request, state = retirement_request(absent=True);request['operation'] = 'retire_apply'
            for network, scopes in state['network_definitions'].items():
                for scope, xml in scopes.items():
                    root = ET.fromstring(xml)
                    ET.SubElement(root.find('./ip/dhcp'), 'host', {'mac': '52:54:00:00:00:08', 'ip': '192.168.70.8', 'name': 'other-v08'})
                    dns = ET.SubElement(root.find('dns'), 'host', {'ip': '192.168.70.8'})
                    ET.SubElement(dns, 'hostname').text = 'other-v08.example.invalid'
                    state['network_definitions'][network][scope] = ET.tostring(root, encoding='unicode')
            original_policy = deepcopy(state['policy']);failed = False;calls = []
            with tempfile.TemporaryDirectory(prefix='windows-native-retirement-') as directory:
                root = Path(directory);config = root / 'policy.json';config.write_text(json.dumps(original_policy))
                helper = root / 'helper.py'
                helper.write_text('TABLE="synthetic_isolation"\ndef validate_configuration(value):\n assert value["bridges"]\ndef policy(value):\n return []\n')
                def command(arguments, data=None, allowed=(0,)):
                    nonlocal failed
                    calls.append(arguments)
                    if arguments[0] == 'virsh':
                        network, kind = arguments[4], arguments[6]
                        scope = 'persistent' if arguments[-1] == '--config' else 'current'
                        xml = ET.fromstring(state['network_definitions'][network][scope])
                        parent = xml.find('./ip/dhcp' if kind == 'ip-dhcp-host' else './dns')
                        expected = ET.fromstring(arguments[7])
                        matches = [node for node in parent if runtime._network_shape(node) == runtime._network_shape(expected)]
                        self.assertEqual(len(matches), 1);parent.remove(matches[0])
                        state['network_definitions'][network][scope] = ET.tostring(xml, encoding='unicode')
                        if scope == 'current': state['networks'][network] = state['network_definitions'][network][scope]
                    elif arguments == [str(helper), 'apply']:
                        state['policy'] = json.loads(config.read_text())
                        if fail_once and not failed:
                            failed = True;raise ValueError('Synthetic Windows policy apply interruption')
                    elif arguments == [str(helper), 'check']:
                        self.assertEqual(json.loads(data), state['policy'])
                    else: self.assertEqual(arguments[:2], ['/usr/sbin/nft', '--check'])
                with patch.object(runtime.base, 'DIRECTORY', root), patch.object(runtime.base, 'CONFIG', config), \
                     patch.object(runtime.base, 'HELPER', helper), patch.object(runtime.base, 'command', side_effect=command), \
                     patch.object(runtime.base, 'probe', side_effect=lambda *args, **kwargs: deepcopy(state)):
                    if fail_once:
                        with self.assertRaises(ValueError): runtime.reconcile_retirement(request)
                        self.assertEqual(state['policy'], original_policy)
                    result = runtime.reconcile_retirement(request)
                    self.assertTrue(result['retirement_verified'])
                    self.assertEqual(state['policy'], request['transition']['desired_policy'])
                    self.assertFalse(runtime.reconcile_retirement(request)['changed'])
                    self.assertEqual(sum(command[0] == 'virsh' for command in calls), 8)
                    for scopes in state['network_definitions'].values():
                        for xml in scopes.values():
                            network = ET.fromstring(xml)
                            self.assertEqual([node.get('name') for node in network.findall('./ip/dhcp/host')], ['other-v08'])
                            self.assertEqual([node.text for node in network.findall('./dns/host/hostname')], ['other-v08.example.invalid'])
                    request['guest'] = None;request['transition']['guest'] = None
                    request['transition']['previous_policy'] = deepcopy(request['transition']['desired_policy'])
                    self.assertTrue(runtime.reconcile_retirement(request)['already_absent'])

    def test_windows_real_encrypted_retirement_publication_retry_preserves_tokens_and_allocator(self):
        with patch.object(retirement_tests, 'fixture', side_effect=retired_fixture):
            retirement_tests.GenericRetirementTests().test_native_encrypted_transaction_recovers_api_interruption_without_token_or_allocator_changes()

    def test_windows_native_two_phase_role_carries_explicit_kind_in_both_modes(self):
        with patch.object(role_tests, 'fixture', side_effect=retirement_request):
            for native in (False, True):
                for behavior in ('success', 'unpublished', 'durable', 'runtime-failure'):
                    with self.subTest(native=native, behavior=behavior):
                        role_tests.GenericRetirementRoleTests().run_role(native, behavior)


if __name__ == '__main__': unittest.main()
