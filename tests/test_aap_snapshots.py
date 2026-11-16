"""Exercise snapshot identity, scoped external drift and cold power transitions."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_snapshot', ROOT / 'module_utils/aap_snapshot.py')
snap = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(snap)


def fixture():
    name = 'aap27-test-23'
    primary = {'uuid': '11111111-2222-3333-4444-555555555555', 'verified': True,
               'disk': '/opt/vms/' + name + '.disk.qcow2', 'address': '192.168.70.10',
               'network': 'isolated', 'mac': '52:54:00:12:34:56', 'hypervisor_machine_id': 'a' * 32}
    route = {'vm_name': name, 'vm_ip': primary['address'], 'hypervisor': {'machine_id': 'a' * 32}}
    xml = ('<domain type="kvm"><name>' + name + '</name><uuid>' + primary['uuid'] + '</uuid>'
           '<os><type>hvm</type></os><devices><disk type="file" device="disk">'
           '<driver name="qemu" type="qcow2"/><source file="' + primary['disk'] + '"/>'
           '<target dev="vda"/></disk>'
           '<controller type="usb" index="0" model="ich9-ehci1">'
           '<address type="pci" domain="0x0000" bus="0x00" slot="0x03" function="0x7"/></controller>'
           '<controller type="pci" index="0" model="pci-root"/>'
           '<controller type="ide" index="0">'
           '<address type="pci" domain="0x0000" bus="0x00" slot="0x01" function="0x1"/></controller>'
           '<interface type="network"><source network="isolated"/>'
           '<mac address="' + primary['mac'] + '"/></interface></devices></domain>')
    policy = {'enabled': True, 'minimum_instance_number': 23, 'names': deepcopy(snap.CHECKPOINTS),
              'shutdown_timeout': 30, 'start_timeout': 30, 'minimum_free_bytes': 1073741824}
    external = {'schema_version': 1, **{k: snap.digest(k) for k in ('ownership', 'inventory', 'api_access', 'policy', 'projects')}}
    return route, primary, xml, policy, external


class Native:
    def __init__(self, xml):
        self.xml = xml; self.state = 'running'; self.snapshots = {}; self.calls = []
        self.fail_create = self.fail_restore = self.fail_start = self.stuck = False

    def __call__(self, args):
        self.calls.append(args)
        if args[0] == 'qemu-img': return json.dumps({'format': 'qcow2', 'virtual-size': 1073741824})
        command = args[3]
        if command == 'dumpxml': return self.xml
        if command == 'domstate': return self.state
        if command == 'snapshot-list': return '\n'.join(self.snapshots)
        if command == 'snapshot-dumpxml': return self.snapshots[args[5]]
        if command == 'shutdown':
            if not self.stuck: self.state = 'shut off'
            return ''
        if command == 'snapshot-create':
            if self.fail_create: raise ValueError('original snapshot creation failure')
            assert self.state == 'shut off' and args[-1] == '--atomic'
            root = ET.parse(args[5]).getroot(); ET.SubElement(root, 'state').text = 'shutoff'
            root.append(ET.fromstring(self.xml))
            self.snapshots[root.findtext('name')] = ET.tostring(root, encoding='unicode'); return ''
        if command == 'snapshot-revert':
            assert self.state == 'shut off'
            if self.fail_restore: raise ValueError('original snapshot restore failure')
            return ''
        if command == 'start':
            if self.fail_start: raise ValueError('restart failure')
            self.state = 'running'; return ''
        raise AssertionError(args)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.route, self.primary, self.xml, self.policy, self.external = fixture()
        self.native = Native(self.xml); self.clock = 0
        self.manager = snap.Manager(self.native, self.sleep, lambda: self.clock)

    def sleep(self, seconds): self.clock += seconds

    def execute(self, operation='create', **kw):
        return self.manager.execute(self.route, self.primary, self.policy, 'base', self.external,
                                    'b' * 32, operation, **kw)

    def test_cold_create_and_immutable_idempotence(self):
        self.assertTrue(self.execute()['changed']); self.assertEqual(self.native.state, 'running')
        first = deepcopy(self.native.snapshots); self.native.calls.clear()
        self.assertFalse(self.execute()['changed']); self.assertEqual(self.native.snapshots, first)
        self.assertFalse(any(x[3] in ('shutdown', 'snapshot-create') for x in self.native.calls))

    def test_restore_preserves_generation_and_restores_only_named_checkpoint(self):
        self.execute(); route = deepcopy(self.route); primary = deepcopy(self.primary)
        self.assertTrue(self.execute('restore')['changed'])
        self.assertEqual(self.route, route); self.assertEqual(self.primary, primary)
        commands = [x[3] for x in self.native.calls]
        self.assertEqual(commands.count('snapshot-revert'), 1)
        self.assertNotIn('destroy', commands); self.assertNotIn('undefine', commands)

    def test_wrong_uuid_disk_nic_and_firmware_refused_before_shutdown(self):
        for old, new in [('11111111-2222-3333-4444-555555555555', '99999999-2222-3333-4444-555555555555'),
                         ('.disk.qcow2', '-other.qcow2'), ('52:54:00:12:34:56', '52:54:00:12:34:99'),
                         ('<os>', '<os><nvram>/firmware</nvram>')]:
            with self.subTest(change=old):
                self.native.xml = self.xml.replace(old, new); self.native.calls.clear()
                with self.assertRaises(ValueError): self.execute()
                self.assertNotIn('shutdown', [x[3] for x in self.native.calls])

    def test_changed_selected_external_state_refuses_restore_before_shutdown(self):
        self.execute(); self.native.calls.clear(); self.external['api_access'] = snap.digest('rotated selected token')
        with self.assertRaisesRegex(ValueError, 'external state changed'): self.execute('restore')
        self.assertNotIn('shutdown', [x[3] for x in self.native.calls])

    def test_repeated_creation_preserves_original_checkpoint_after_selected_state_changes(self):
        self.execute(); original=deepcopy(self.native.snapshots); self.external['projects']=snap.digest('later project import')
        self.native.calls.clear(); result=self.execute()
        self.assertFalse(result['changed']); self.assertFalse(result['external_state_matches'])
        self.assertEqual(self.native.snapshots,original); self.assertNotIn('shutdown',[x[3]for x in self.native.calls])

    def test_missing_or_live_snapshot_refused_before_shutdown(self):
        with self.assertRaisesRegex(ValueError, 'does not exist'): self.execute('restore')
        self.execute(); key = self.policy['names']['base']
        self.native.snapshots[key] = self.native.snapshots[key].replace('<state>shutoff</state>', '<state>running</state>')
        self.native.calls.clear()
        with self.assertRaisesRegex(ValueError, 'cold snapshot'): self.execute('restore')
        self.assertNotIn('shutdown', [x[3] for x in self.native.calls])

    def test_tampered_native_snapshot_domain_disks_and_memory_are_rejected(self):
        self.execute(); key = self.policy['names']['base']; original = self.native.snapshots[key]
        for field in ('domain', 'disk', 'memory'):
            with self.subTest(field=field):
                root = ET.fromstring(original)
                if field == 'domain': root.find('./domain/uuid').text = '99999999-2222-3333-4444-555555555555'
                elif field == 'disk': root.find('./disks/disk').set('snapshot', 'external')
                else: root.find('memory').set('snapshot', 'internal')
                self.native.snapshots[key] = ET.tostring(root, encoding='unicode'); self.native.calls.clear()
                with self.assertRaises(ValueError): self.execute('restore')
                self.assertNotIn('shutdown', [x[3] for x in self.native.calls])

    def test_canonical_preserves_device_ids_but_ignores_root_runtime_id(self):
        root = ET.fromstring(self.xml); original = snap.digest(snap.canonical(root))
        root.set('id', '22'); self.assertEqual(snap.digest(snap.canonical(root)), original)
        root.find('./devices/disk').set('id', 'disk-id'); self.assertNotEqual(snap.digest(snap.canonical(root)), original)

    def test_native_reordered_controllers_validate_the_immutable_legacy_checkpoint(self):
        def legacy(element, root=True):
            if element.tag == 'seclabel' and element.get('type') == 'dynamic': return None
            return [element.tag, sorted((k, v) for k, v in element.attrib.items()
                    if not (root and element.tag == 'domain' and k == 'id')),
                    (element.text or '').strip(),
                    [value for child in element if (value := legacy(child, False)) is not None]]
        # The observed native inactive order is USB, PCI root, IDE. Snapshot XML
        # moves IDE before PCI root without changing either addressed controller.
        self.execute(); key = self.policy['names']['base']
        root = ET.fromstring(self.native.snapshots[key]); devices = root.find('./domain/devices')
        controllers = devices.findall('controller'); pci, ide = controllers[-2:]
        pci_position, ide_position = list(devices).index(pci), list(devices).index(ide)
        devices.remove(pci); devices.remove(ide)
        devices.insert(pci_position, ide); devices.insert(ide_position, pci)
        record = json.loads(root.findtext('description'))
        original_digest = snap.digest(legacy(ET.fromstring(self.xml)))
        self.assertEqual(record['native']['configuration'], original_digest)
        self.assertNotEqual(snap.digest(legacy(root.find('domain'))), original_digest)
        self.assertEqual(snap.snapshot_record(ET.tostring(root, encoding='unicode'), record), record)
        self.native.snapshots[key] = ET.tostring(root, encoding='unicode')
        original = deepcopy(self.native.snapshots); self.native.calls.clear()
        self.assertFalse(self.execute()['changed'])
        self.assertEqual(self.native.snapshots, original)
        self.assertFalse(any(call[3] in ('shutdown', 'snapshot-create', 'snapshot-revert', 'start')
                             for call in self.native.calls))

    def test_controller_normalization_retains_every_address_model_and_occurrence(self):
        self.execute(); key = self.policy['names']['base']; original = self.native.snapshots[key]
        for change in ('address', 'model', 'missing', 'duplicate'):
            with self.subTest(change=change):
                root = ET.fromstring(original); devices = root.find('./domain/devices')
                controller = devices.findall('controller')[0]
                if change == 'address': controller.find('address').set('slot', '0x09')
                elif change == 'model': controller.set('model', 'another-controller')
                elif change == 'missing': devices.remove(controller)
                else: devices.append(deepcopy(controller))
                self.native.snapshots[key] = ET.tostring(root, encoding='unicode'); self.native.calls.clear()
                with self.assertRaisesRegex(ValueError, 'Stored native domain configuration'):
                    self.execute()
                self.assertNotIn('shutdown', [call[3] for call in self.native.calls])

    def test_normalization_preserves_other_device_order_and_nested_controller_order(self):
        root = ET.fromstring(self.xml); original = snap.digest(snap.canonical(root))
        devices = root.find('devices'); disk, interface = devices.find('disk'), devices.find('interface')
        disk_position, nic_position = list(devices).index(disk), list(devices).index(interface)
        devices.remove(disk); devices.remove(interface)
        devices.insert(disk_position, interface); devices.insert(nic_position, disk)
        self.assertNotEqual(snap.digest(snap.canonical(root)), original)
        first = ET.fromstring('<domain><metadata><devices><controller index="0"/>'
                              '<controller index="1"/></devices></metadata></domain>')
        second = ET.fromstring('<domain><metadata><devices><controller index="1"/>'
                               '<controller index="0"/></devices></metadata></domain>')
        self.assertNotEqual(snap.canonical(first), snap.canonical(second))

    def test_extra_writable_storage_and_efi_firmware_are_rejected(self):
        for addition in ('<disk device="lun"/>', '<disk device="floppy"/>', '<disk device="cdrom"/>'):
            with self.subTest(addition=addition), self.assertRaises(ValueError):
                snap.domain_plan(self.xml.replace('</devices>', addition + '</devices>'), self.route, self.primary)
        with self.assertRaises(ValueError): snap.domain_plan(self.xml.replace('<os>', '<os firmware="efi">'), self.route, self.primary)
        self.assertTrue(snap.domain_plan(self.xml.replace('</devices>', '<disk device="cdrom"><readonly/></disk></devices>'), self.route, self.primary))

    def test_creation_failure_restarts_original_and_retains_failure(self):
        self.native.fail_create = True
        with self.assertRaisesRegex(snap.SnapshotFailure, 'original snapshot creation failure') as failure: self.execute()
        self.assertTrue(failure.exception.changed); self.assertEqual(self.native.state, 'running')

    def test_creation_and_restart_failures_are_both_retained(self):
        self.native.fail_create = self.native.fail_start = True
        with self.assertRaises(snap.SnapshotFailure) as failure: self.execute()
        self.assertIn('original snapshot creation failure', str(failure.exception))
        self.assertIn('restart failure', str(failure.exception)); self.assertEqual(self.native.state, 'shut off')

    def test_restore_failure_is_not_automatically_restarted(self):
        self.execute(); self.native.fail_restore = True; self.native.calls.clear()
        with self.assertRaisesRegex(snap.SnapshotFailure, 'original snapshot restore failure'): self.execute('restore')
        self.assertEqual(self.native.state, 'shut off'); self.assertNotIn('start', [x[3] for x in self.native.calls])

    def test_graceful_deadline_never_force_stops(self):
        self.native.stuck = True
        with self.assertRaisesRegex(snap.SnapshotFailure, 'deadline'): self.execute()
        self.assertEqual(self.native.state, 'running'); self.assertNotIn('destroy', [x[3] for x in self.native.calls])

    def test_check_mode_never_stops_or_changes_native_snapshots(self):
        self.assertTrue(self.execute(check_mode=True)['changed'])
        self.assertFalse(self.native.snapshots); self.assertNotIn('shutdown', [x[3] for x in self.native.calls])

    def test_future_policy_and_exact_names(self):
        self.assertLess(max(map(len, snap.CHECKPOINTS.values())), 64)
        for change in ({'enabled': False}, {'minimum_instance_number': 24}, {'names': dict(snap.CHECKPOINTS, base='../bad')}):
            altered = dict(self.policy, **change)
            with self.assertRaises(ValueError): snap.policy(altered, 'base', self.route['vm_name'])


class ExternalStateTests(unittest.TestCase):
    def setUp(self):
        route, primary, *_ = fixture(); primary['vm_name'] = route['vm_name']
        self.selected = route['vm_name']; self.record = {'vm_name': self.selected, 'number': 23,
            'instance_route': route, 'instance_resources': {'aap': primary}}
        self.allocation = {'next_number': 24, 'reservations': {'selected': self.record}}
        self.host = {'name': 'display-alias', 'variables': {'aap_instance_number': 23,
            'vm_resource': primary, 'machine_id': 'b' * 32, 'ansible_host': primary['address']}}
        self.shared = {'host_inventory_configuration': {'hosts': [self.host]}}
        self.capture = {'aap_instance_api_credentials': {self.selected: {'hostname': 'https://aap.example.invalid',
            'token': 'synthetic-token', 'token_id': 4, 'last_used': 'before'}}}

    def read(self): return snap.external_state(self.allocation, self.shared, self.capture, self.selected)

    def test_counters_unrelated_instances_and_timestamps_do_not_block_restore(self):
        before = self.read(); self.allocation['next_number'] = 25
        self.allocation['reservations']['unrelated'] = {'vm_name': 'aap27-test-24', 'number': 24}
        self.capture['aap_instance_api_credentials']['aap27-test-24'] = {'token': 'other'}
        self.capture['aap_instance_api_credentials'][self.selected]['last_used'] = 'after'
        self.host['variables']['vm_resource']['verified_at'] = 'later'
        self.assertEqual(self.read(), before)

    def test_selected_token_rotation_changes_only_access_fingerprint(self):
        before = self.read(); self.capture['aap_instance_api_credentials'][self.selected]['token'] = 'changed'
        after = self.read(); self.assertNotEqual(before['api_access'], after['api_access'])
        self.assertEqual({k:v for k,v in before.items() if k != 'api_access'},
                         {k:v for k,v in after.items() if k != 'api_access'})
        self.assertNotIn('changed', json.dumps(after))

    def test_selected_new_project_guest_changes_ownership_fingerprint(self):
        before = self.read(); self.record['instance_resources']['managed-v23'] = {'vm_name': 'managed-v23', 'uuid': 'new'}
        self.assertNotEqual(self.read()['ownership'], before['ownership'])

    def test_selected_policy_grant_changes_but_other_instance_grant_does_not(self):
        self.shared['host_inventory_configuration']['hosts'].append({'name': 'hypervisor', 'variables': {
            'machine_id': 'a' * 32, 'isolation_policy': {'guest_host_clients': []}}})
        before = self.read(); grants = self.shared['host_inventory_configuration']['hosts'][-1]['variables']['isolation_policy']['guest_host_clients']
        grants.append({'ipv4': '192.168.70.99', 'ports': [443]}); self.assertEqual(self.read(), before)
        grants.append({'ipv4': self.record['instance_route']['vm_ip'], 'ports': [443]})
        self.assertNotEqual(self.read()['policy'], before['policy'])

    def test_primary_without_vm_name_does_not_capture_unrelated_hosts(self):
        self.record['instance_resources']['aap'].pop('vm_name')
        other = {'name': 'other', 'variables': {'vm_resource': {'uuid': 'other'}, 'ansible_host': '192.0.2.99'}}
        self.shared['host_inventory_configuration']['hosts'].append(other)
        before = self.read(); other['variables']['ansible_host'] = '192.0.2.100'
        self.assertEqual(self.read(), before)
        self.host['variables']['machine_id'] = 'c' * 32
        self.assertNotEqual(self.read()['inventory'], before['inventory'])

    def test_group_and_parent_group_owned_grants_are_inherited(self):
        data = self.shared['host_inventory_configuration']
        data['hosts'].append({'name': 'hv', 'inventory': 'native', 'variables': {'machine_id': 'a' * 32}})
        data['groups'] = [
            {'name': 'child', 'inventory': 'native', 'hosts': ['hv'], 'variables': {}},
            {'name': 'parent', 'inventory': 'native', 'children': ['child'], 'variables': {
                'isolation_policy': {'guest_host_clients': [{'ipv4': self.record['instance_route']['vm_ip'], 'ports': [443]}]}}}]
        before = self.read(); data['groups'][1]['variables']['isolation_policy']['guest_host_clients'][0]['ports'] = [8448]
        self.assertNotEqual(self.read()['policy'], before['policy'])


class EdaPaginationTests(unittest.TestCase):
    def test_relative_and_absolute_same_origin_query_links(self):
        origin = 'https://aap.example.invalid'
        for link in ('/api/eda/v1/activations/?page=2', origin + '/api/eda/v1/activations/?page=2'):
            self.assertEqual(snap.eda_next_page({'count': 101, 'results': [], 'next': link}, origin), origin + '/api/eda/v1/activations/?page=2')

    def test_foreign_links_and_incomplete_or_running_activation_records_fail_closed(self):
        origin = 'https://aap.example.invalid'
        base = {'count': 1, 'results': [{'is_enabled': False, 'current_job_id': None}], 'next': None}
        for row in ({'is_enabled': True, 'current_job_id': None}, {'current_job_id': None},
                    {'is_enabled': False}, {'is_enabled': None, 'current_job_id': None},
                    {'is_enabled': False, 'current_job_id': 17}):
            with self.subTest(row=row), self.assertRaises(ValueError): snap.eda_next_page(dict(base, results=[row]), origin)
        for link in ('https://foreign.example.invalid/api/eda/v1/activations/?page=2',
                     '//foreign.example.invalid/api/eda/v1/activations/?page=2',
                     '/api/controller/v2/jobs/?page=2', 'http://aap.example.invalid/api/eda/v1/activations/?page=2'):
            with self.subTest(link=link), self.assertRaises(ValueError): snap.eda_next_page(dict(base, next=link), origin)


if __name__ == '__main__': unittest.main()
