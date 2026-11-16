"""Cold snapshots for one registered AAP VM; native metadata is the only store."""
from copy import deepcopy
import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urljoin, parse_qs


CHECKPOINTS = {
    'infra': 'aap-infra-configured-before-install-snapshot',
    'installed': 'aap-up-before-base-snapshot',
    'base': 'aap-base-deployed-snapshot',
}
VOLATILE = {'created', 'modified', 'updated_at', 'checked_at', 'verified_at', 'last_used',
            'last_job_run', 'last_job_failed', 'source_job_id', 'source_project_revision'}


class SnapshotFailure(ValueError):
    def __init__(self, original, restart_error=None, changed=False):
        super().__init__(str(original) + ('; restarting the unchanged original VM also failed: ' + str(restart_error)
                                        if restart_error is not None else ''))
        self.changed = changed


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(stable(value), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def external_state(allocation, shared, capture, selected, projects=None):
    """Hash selected ownership, inventory, access and grants; never hash a whole repo."""
    rows = [r for r in allocation['reservations'].values() if r.get('vm_name') == selected]
    require(len(rows) == 1 and not rows[0].get('decommissioned'), 'Select one active registered instance.')
    record = rows[0]
    route, resources = record['instance_route'], record.get('instance_resources', {})
    number = record['number']
    selected_rows = []
    addresses, macs = {route['vm_ip']}, set()
    names = {selected}
    identities = set()
    for resource in resources.values():
        if not isinstance(resource, dict):
            continue
        if isinstance(resource.get('vm_name'), str): names.add(resource['vm_name'])
        if isinstance(resource.get('uuid'), str): identities.add(resource['uuid'])
        for nic in [resource] + resource.get('interfaces', []) + resource.get('supplemental_interfaces', []):
            addresses.add(nic.get('address')); macs.add(nic.get('mac'))
    policy_rows = []
    for row in shared['host_inventory_configuration']['hosts']:
        values = row.get('variables') or {}
        require(isinstance(values, dict), 'Snapshot readback requires parsed canonical host variables.')
        resource = values.get('vm_resource') or {}
        owned = (resource.get('vm_name') in names or resource.get('uuid') in identities or resource.get('instance_name') == selected or
                 (values.get('aap_instance_number') == number and
                  resource.get('hypervisor_machine_id') == route['hypervisor']['machine_id'] and
                  re.fullmatch(r'[a-z][a-z0-9-]*-v%02d' % number, resource.get('vm_name', ''))))
        if owned:
            selected_rows.append({k: deepcopy(values[k]) for k in (
                'vm_resource', 'vm_uuid', 'ansible_host', 'ansible_fqdn', 'machine_id', 'host_keys',
                'ansible_user', 'ansible_port', 'aap_instance_number', 'hypervisor_host',
                'computer_name', 'computer_uuid', 'zabbix_api_url') if k in values})
            for nic in [resource] + resource.get('interfaces', []) + resource.get('supplemental_interfaces', []):
                addresses.add(nic.get('address')); macs.add(nic.get('mac'))
    for configuration in (shared['host_inventory_configuration'], capture.get('autodeploy_configuration', {})):
        # Group and inventory inheritance are scoped to the actual hypervisor,
        # rather than scanning every other installation's settings.
        members = set()
        for row in configuration.get('hosts', []):
            values = row.get('variables') or {}
            if isinstance(values, dict) and values.get('machine_id') == route['hypervisor']['machine_id']:
                members.add((row.get('inventory'), row['name'])); policy_rows.append(values)
        groups = configuration.get('groups', [])
        require(len(groups) <= 256, 'Require bounded canonical inventory group inheritance.')
        inherited = set()
        for _ in range(len(groups) + 1):
            previous = set(inherited)
            for row in groups:
                inventory = row.get('inventory'); group = (inventory, row['name'])
                if (any((inventory, name) in members for name in row.get('hosts', [])) or
                        any((inventory, child) in inherited for child in row.get('children', []))): inherited.add(group)
            if previous == inherited: break
        for row in groups:
            if (row.get('inventory'), row['name']) in inherited:
                values = row.get('variables') or {}
                require(isinstance(values, dict), 'Parse inherited group variables before snapshot state hashing.')
                policy_rows.append(values)
        inventories = {inventory for inventory, _ in members}
        for row in configuration.get('inventories', []):
            values = row.get('variables') or {}
            require(isinstance(values, dict), 'Parse inventory variables before snapshot state hashing.')
            if row.get('name') in inventories or values.get('aap_hypervisor_pin', {}).get('machine_id') == route['hypervisor']['machine_id']:
                policy_rows.append(values)
    addresses.discard(None); macs.discard(None)
    def owned_grant(item):
        return isinstance(item, dict) and (item.get('ipv4') in addresses or item.get('address') in addresses or item.get('mac') in macs)
    policy = []
    for values in policy_rows:
        for field, value in values.items():
            if field.startswith('aap_hypervisor_isolation_') and isinstance(value, list):
                selected_grants = sorted([stable(x) for x in value if owned_grant(x)], key=digest)
                if selected_grants: policy.append((field, selected_grants))
            elif field in ('isolation_policy', 'hactar_isolation_policy', 'aap_hypervisor_isolation_policy') and isinstance(value, dict):
                policy.extend((key, selected_grants) for key, items in value.items() if isinstance(items, list)
                              and (selected_grants := sorted([stable(x) for x in items if owned_grant(x)], key=digest)))
    access = capture.get('aap_instance_api_credentials', {}).get(selected)
    if access is not None:
        access = {k: access[k] for k in ('hostname', 'token', 'token_id', 'expires', 'mcp') if k in access}
    return {'schema_version': 1, 'ownership': digest({'route': route, 'resources': resources}),
            'inventory': digest(sorted(selected_rows, key=digest)), 'api_access': digest(access),
            'policy': digest(sorted(policy, key=lambda x: (x[0], digest(x[1])))), 'projects': digest(projects)}


def policy(value, checkpoint, instance):
    require(isinstance(value, dict) and set(value) == {
        'enabled', 'minimum_instance_number', 'names', 'shutdown_timeout', 'start_timeout', 'minimum_free_bytes'},
        'Use the complete snapshot policy from encrypted CaC.')
    require(value['enabled'] is True and type(value['minimum_instance_number']) is int and value['minimum_instance_number'] > 0,
            'Snapshots must be explicitly enabled for future allocations.')
    match = re.fullmatch(r'aap[0-9]+-test-([1-9][0-9]*)', instance or '')
    require(match and int(match[1]) >= value['minimum_instance_number'], 'This allocation predates the snapshot policy.')
    require(value['names'] == CHECKPOINTS and checkpoint in CHECKPOINTS,
            'Choose one of the three declared installation checkpoints.')
    for key in ('shutdown_timeout', 'start_timeout'):
        require(type(value[key]) is int and 30 <= value[key] <= 1800, 'Use bounded shutdown and startup deadlines.')
    require(type(value['minimum_free_bytes']) is int and value['minimum_free_bytes'] >= 1073741824,
            'Declare at least one GiB of snapshot free-space reserve.')
    return value['names'][checkpoint]


def canonical(element, root=True, path=()):
    if element.tag == 'seclabel' and element.get('type') == 'dynamic':
        return None
    children = [value for child in element
                if (value := canonical(child, False, path + (element.tag,))) is not None]
    if path == ('domain',) and element.tag == 'devices':
        # Libvirt may serialize the same explicitly addressed controllers in a
        # different declaration order in snapshot XML. Preserve every field and
        # multiplicity; normalize only controller slots, never other devices.
        controllers = iter(sorted(value for value in children if value[0] == 'controller'))
        children = [next(controllers) if value[0] == 'controller' else value for value in children]
    return [element.tag, sorted((k, v) for k, v in element.attrib.items() if not (root and element.tag == 'domain' and k == 'id')),
            (element.text or '').strip(), children]


def domain_plan(xml, route, primary):
    root = ET.fromstring(xml)
    name = route['vm_name']
    require(primary.get('verified') is True and primary.get('hypervisor_machine_id') == route['hypervisor']['machine_id'],
            'Require verified primary ownership on the selected hypervisor.')
    require(root.tag == 'domain' and root.get('type') == 'kvm' and root.findtext('name') == name
            and root.findtext('uuid') == primary.get('uuid'), 'Native VM name and UUID must match the registry.')
    require(root.find('./os/loader') is None and root.find('./os/nvram') is None
            and (root.find('os') is None or root.find('os').get('firmware') in (None, 'bios')),
            'Firmware-backed snapshots need separate NVRAM qualification; this workflow supports BIOS guests.')
    require(not root.findall('./devices/hostdev') and not root.findall('./devices/filesystem') and not root.findall('./devices/tpm')
            and not root.findall('.//{http://libvirt.org/schemas/domain/qemu/1.0}commandline'),
            'Refuse host devices, shared filesystems, unqualified TPM state or custom QEMU arguments.')
    disks = root.findall("./devices/disk[@device='disk']")
    require(len(disks) == 1, 'Snapshot only the one registered AAP system disk.')
    require(all(d.get('device') == 'disk' or
                (d.get('device') == 'cdrom' and d.find('readonly') is not None)
                for d in root.findall('./devices/disk')),
            'Refuse additional writable storage; only a read-only seed CDROM may accompany the system disk.')
    disk = disks[0]
    source, driver, target = disk.find('source'), disk.find('driver'), disk.find('target')
    expected = '/opt/vms/' + name + '.disk.qcow2'
    require(disk.get('type') == 'file' and driver is not None and driver.get('type') == 'qcow2'
            and source is not None and source.get('file') == expected and set(source.attrib) <= {'file', 'index'} and primary.get('disk') == expected
            and target is not None and re.fullmatch(r'[a-z][a-z0-9]*', target.get('dev', ''))
            and disk.find('readonly') is None, 'Require the exact registered local qcow2 disk.')
    expected_nics = [primary] + primary.get('supplemental_interfaces', [])
    nics = root.findall('./devices/interface')
    require(len(nics) == len(expected_nics) and all(n.get('type') == 'network' for n in nics),
            'Native NIC count and transport must match scoped ownership.')
    actual = {(n.find('source').get('network'), n.find('mac').get('address')) for n in nics
              if n.find('source') is not None and n.find('mac') is not None}
    require(actual == {(n['network'], n['mac']) for n in expected_nics}, 'Native network/MAC identity differs.')
    return {'name': name, 'uuid': primary['uuid'], 'disk': expected, 'target': target.get('dev'),
            'configuration': digest(canonical(root))}


def snapshot_record(xml, expected):
    root = ET.fromstring(xml)
    require(root.tag == 'domainsnapshot' and root.findtext('name') == expected['snapshot_name']
            and root.findtext('state') == 'shutoff', 'Require the named cold snapshot, never a live snapshot.')
    record = json.loads(root.findtext('description', ''))
    require(record == expected, 'Snapshot identity or checkpoint-relevant external state changed; reconcile it before rollback.')
    stored = root.find('domain'); memory = root.find('memory'); disks = root.findall('./disks/disk')
    require(stored is not None and stored.findtext('uuid') == expected['native']['uuid']
            and stored.findtext('name') == expected['native']['name']
            and digest(canonical(stored)) == expected['native']['configuration'],
            'Stored native domain configuration differs from its registered checkpoint.')
    require(memory is not None and memory.attrib == {'snapshot': 'no'}
            and len({x.get('name') for x in disks}) == len(disks)
            and [(x.get('name'), x.get('snapshot')) for x in disks if x.get('snapshot') != 'no'] ==
                [(expected['native']['target'], 'internal')],
            'Require one genuine internal disk snapshot and no saved memory or additional writable disk.')
    return record


def eda_next_page(data, origin):
    require(isinstance(data, dict) and isinstance(data.get('results'), list) and len(data['results']) <= 100
            and type(data.get('count')) is int and data['count'] >= len(data['results'])
            and 'next' in data, 'Require a complete bounded EDA activation response.')
    require(all(isinstance(row, dict) and row.get('is_enabled') is False
                and 'current_job_id' in row and row['current_job_id'] is None for row in data['results']),
            'Every activation must be explicitly disabled and have no current job; no activation is changed here.')
    next_page = data['next']
    if next_page is None:
        return ''
    require(isinstance(next_page, str) and next_page, 'Require a valid EDA pagination link or null.')
    target = urlsplit(urljoin(origin + '/', next_page)); selected = urlsplit(origin)
    require(selected.scheme == 'https' and target.scheme == 'https' and target.netloc == selected.netloc
            and not target.username and not target.password and not target.fragment
            and target.path == '/api/eda/v1/activations/' and bool(target.query)
            and (next_page.startswith('https://') or next_page.startswith('/api/eda/v1/activations/?')),
            'EDA pagination must remain on the selected HTTPS activation endpoint.')
    return target.geturl()


def controller_jobs_page(data, origin, state=None):
    """Validate one complete, ordered page without trusting a filtered count."""
    state = {} if state is None else state
    require(isinstance(state, dict) and (not state or set(state) == {
        'count', 'page', 'jobs', 'next', 'complete', 'idle'}), 'Require the current bounded job scan state.')
    require(not state.get('complete', False), 'Do not append pages after a complete job scan.')
    require(isinstance(data, dict) and type(data.get('count')) is int and 0 <= data['count'] <= 2000
            and isinstance(data.get('results'), list) and len(data['results']) <= 100
            and 'next' in data, 'Require bounded complete Controller job-list metadata.')
    page = state.get('page', 0) + 1
    require(page <= 20 and (not state or data['count'] == state['count']),
            'Controller job-list count changed during pagination or exceeded its page bound.')
    jobs = list(state.get('jobs', []))
    for row in data['results']:
        require(isinstance(row, dict) and type(row.get('id')) is int and row['id'] > 0
                and isinstance(row.get('status'), str)
                and row['status'] in {'new', 'pending', 'waiting', 'running', 'successful', 'failed', 'error', 'canceled'},
                'Every Controller job needs a real ID and explicit known status before shutdown.')
        require(not jobs or row['id'] > jobs[-1]['id'],
                'Controller job IDs must be unique and strictly increasing across every page.')
        jobs.append({'id': row['id'], 'status': row['status']})
    require(len(jobs) <= data['count'], 'Controller job results exceed the declared complete count.')
    next_link = data['next']
    if next_link is None:
        require(len(jobs) == data['count'], 'Controller job results are incomplete despite a terminal page.')
        target = ''
    else:
        require(isinstance(next_link, str) and next_link and data['results'] and len(jobs) < data['count']
                and page < 20, 'Require progress within the finite Controller pagination bound.')
        selected = urlsplit(origin)
        target = urlsplit(urljoin(origin.rstrip('/') + '/', next_link))
        require(selected.scheme == 'https' and not selected.username and not selected.password
                and not selected.query and not selected.fragment and selected.path in ('', '/')
                and target.scheme == 'https' and target.netloc == selected.netloc
                and not target.username and not target.password and not target.fragment
                and target.path == '/api/controller/v2/unified_jobs/'
                and (next_link.startswith('https://') or next_link.startswith('/api/controller/v2/unified_jobs/?')),
                'Controller pagination must stay on the selected authenticated HTTPS endpoint.')
        query = parse_qs(target.query, keep_blank_values=True, strict_parsing=True)
        require(query == {'order_by': ['id'], 'page_size': ['100'], 'page': [str(page + 1)]},
                'Controller pagination must preserve the unfiltered ordered query and advance exactly one page.')
        target = target.geturl()
    complete = next_link is None
    return {'count': data['count'], 'page': page, 'jobs': jobs, 'next': target,
            'complete': complete, 'idle': complete and all(row['status'] in {
                'successful', 'failed', 'error', 'canceled'} for row in jobs)}


class Manager:
    def __init__(self, run=None, sleep=time.sleep, monotonic=time.monotonic):
        self.run = run or self.command
        self.sleep, self.monotonic = sleep, monotonic

    @staticmethod
    def command(args):
        result = subprocess.run(args, capture_output=True, text=True, timeout=60,
                                env=dict(os.environ, LC_ALL='C'))
        require(result.returncode == 0, 'Native snapshot command failed (rc=%d): %s' %
                (result.returncode, result.stderr[-4096:]))
        return result.stdout

    def virsh(self, *args):
        return self.run(['virsh', '-c', 'qemu:///system', *args])

    def wait_state(self, name, expected, timeout):
        deadline = self.monotonic() + timeout
        while True:
            if self.virsh('domstate', name).strip() == expected:
                return
            require(self.monotonic() < deadline, 'Guest state deadline expired; no force-power operation is permitted.')
            self.sleep(2)

    def execute(self, route, primary, settings, checkpoint, external, guest_machine_id, operation, check_mode=False):
        name = route['vm_name']; snapshot_name = policy(settings, checkpoint, name)
        require(operation in ('create', 'restore'), 'Choose snapshot creation or explicit rollback.')
        require(isinstance(external, dict) and set(external) == {'schema_version', 'ownership', 'inventory', 'api_access', 'policy', 'projects'}
                and external['schema_version'] == 1 and all(re.fullmatch('[0-9a-f]{64}', external[k] or '') for k in external if k != 'schema_version'),
                'Require freshly read checkpoint-relevant selected external fingerprints.')
        require(re.fullmatch('[0-9a-f]{32}', guest_machine_id or ''), 'Require authenticated guest machine identity.')
        native = domain_plan(self.virsh('dumpxml', name, '--inactive'), route, primary)
        live = domain_plan(self.virsh('dumpxml', name), route, primary)
        require({k:v for k,v in live.items() if k != 'configuration'} ==
                {k:v for k,v in native.items() if k != 'configuration'}, 'Running and persistent native guest identity differ.')
        current = self.virsh('domstate', name).strip()
        require(current == 'running', 'Begin from the running verified guest; do not guess an earlier shutdown outcome.')
        record = dict(schema_version=1, snapshot_name=snapshot_name, checkpoint=checkpoint,
                      native=native, guest_machine_id=guest_machine_id, external_state=external)
        names = self.virsh('snapshot-list', name, '--name').split()
        require(len(names) <= 64 and len(set(names)) == len(names), 'Require bounded native snapshot metadata.')
        if snapshot_name in names:
            existing_xml = self.virsh('snapshot-dumpxml', name, snapshot_name)
            if operation == 'create':
                existing = json.loads(ET.fromstring(existing_xml).findtext('description', ''))
                require(existing.get('schema_version') == 1 and existing.get('snapshot_name') == snapshot_name
                        and existing.get('checkpoint') == checkpoint and existing.get('guest_machine_id') == guest_machine_id
                        and all(existing.get('native', {}).get(k) == native[k] for k in ('name', 'uuid', 'disk', 'target')),
                        'The existing name belongs to another native guest or checkpoint; never overwrite it.')
                snapshot_record(existing_xml, existing)
                return {'changed': False, 'snapshot_name': snapshot_name, 'checkpoint': checkpoint,
                        'existing_checkpoint_preserved': True, 'external_state_matches': existing['external_state'] == external}
            snapshot_record(existing_xml, record)
        else:
            require(operation == 'create', 'The requested checkpoint does not exist.')
        if check_mode:
            return {'changed': True, 'snapshot_name': snapshot_name, 'checkpoint': checkpoint, 'check_mode': True}
        stopped = False
        shutdown_requested = False
        try:
            shutdown_requested = True
            self.virsh('shutdown', name, '--mode', 'acpi')
            self.wait_state(name, 'shut off', settings['shutdown_timeout']); stopped = True
            require(domain_plan(self.virsh('dumpxml', name, '--inactive'), route, primary) == native,
                    'Native configuration changed during shutdown; no disk operation is permitted.')
            image = json.loads(self.run(['qemu-img', 'info', '--output=json', native['disk']]))
            require(image.get('format') == 'qcow2' and not image.get('backing-filename')
                    and not image.get('encrypted', False)
                    and not image.get('format-specific', {}).get('data', {}).get('data-file'),
                    'Cold snapshot qualification requires standalone unencrypted qcow2 storage without an external data file.')
            if operation == 'create':
                root = ET.Element('domainsnapshot'); ET.SubElement(root, 'name').text = snapshot_name
                ET.SubElement(root, 'description').text = json.dumps(record, sort_keys=True, separators=(',', ':'))
                ET.SubElement(root, 'memory', snapshot='no')
                ET.SubElement(ET.SubElement(root, 'disks'), 'disk', name=native['target'], snapshot='internal')
                with tempfile.NamedTemporaryFile(mode='w', prefix='aap-cold-snapshot-', suffix='.xml') as source:
                    os.chmod(source.name, 0o600); source.write(ET.tostring(root, encoding='unicode')); source.flush()
                    self.virsh('snapshot-create', name, source.name, '--atomic')
                snapshot_record(self.virsh('snapshot-dumpxml', name, snapshot_name), record)
            else:
                self.virsh('snapshot-revert', name, '--snapshotname', snapshot_name)
            self.virsh('start', name); stopped = False
            self.wait_state(name, 'running', settings['start_timeout'])
            require(domain_plan(self.virsh('dumpxml', name, '--inactive'), route, primary) == native,
                    'Post-start VM identity or configuration changed.')
            return {'changed': True, 'snapshot_name': snapshot_name, 'checkpoint': checkpoint, 'operation': operation,
                    'native_running': True, 'guest_readiness_requires_playbook_verification': True}
        except Exception as original:
            # Creation is atomic. Recover only the unchanged original VM; a failed
            # restore can have an uncertain disk outcome and deliberately stays off.
            restart_error = None
            if stopped and operation == 'create':
                try:
                    if (self.virsh('domstate', name).strip() == 'shut off' and
                            domain_plan(self.virsh('dumpxml', name, '--inactive'), route, primary) == native):
                        self.virsh('start', name)
                        self.wait_state(name, 'running', settings['start_timeout'])
                except Exception as error:
                    restart_error = error
            raise SnapshotFailure(original, restart_error, changed=shutdown_requested) from None


def native_preflight(route, primary, protected_production_ipv4, minimum_free_bytes):
    require(os.geteuid() == 0 and Path('/etc/machine-id').read_text().strip() == route['hypervisor']['machine_id'],
            'The actual hypervisor must match its independently verified machine pin.')
    addresses = json.loads(Manager.command(['ip', '-j', '-4', 'address', 'show']))
    addresses = {a['local'] for i in addresses for a in i.get('addr_info', []) if a.get('family') == 'inet'}
    require(route['hypervisor']['public_ip'] in addresses and protected_production_ipv4 not in addresses
            and protected_production_ipv4 not in (route['hypervisor']['address'], route['hypervisor']['public_ip']),
            'Refuse the independently excluded production host or an unverified target.')
    for action in ('is-active', 'is-enabled'):
        Manager.command(['systemctl', action, 'hactar-recovery-isolation.service'])
    nics = [primary] + primary.get('supplemental_interfaces', [])
    for nic in nics:
        network = ET.fromstring(Manager.command(['virsh', '-c', 'qemu:///system', 'net-dumpxml', nic['network']]))
        require(network.findtext('name') == nic['network'] and network.find('bridge') is not None
                and network.find('bridge').get('name') == nic['bridge']
                and nic['bridge'] in route['hypervisor']['isolation_bridges'],
                'Every selected NIC must retain its actual registered isolated network and bridge.')
    names = Manager.command(['virsh', '-c', 'qemu:///system', 'list', '--all', '--name']).split()
    require(len(names) <= 64 and len(names) == len(set(names)), 'Require a bounded actual hypervisor VM set.')
    for name in names:
        if name == route['vm_name']: continue
        native = ET.fromstring(Manager.command(['virsh', '-c', 'qemu:///system', 'dumpxml', name, '--inactive']))
        require(not any(d.get('file') == primary['disk'] for d in native.findall('./devices/disk/source'))
                and not {m.get('address') for m in native.findall('./devices/interface/mac')}.intersection(n['mac'] for n in nics),
                'Another VM refers to the selected disk or MAC; no power operation is permitted.')
    require(primary.get('disk') == '/opt/vms/' + route['vm_name'] + '.disk.qcow2', 'Require canonical selected primary storage.')
    path = Path(primary['disk']); info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and info.st_nlink == 1 and str(path.resolve()) == str(path),
            'The exact registered disk must be a non-symlink regular file with one link.')
    filesystem = os.statvfs(path.parent)
    block_info = Manager.command(['virsh', '-c', 'qemu:///system', 'domblkinfo', route['vm_name'], str(path)])
    capacity = re.search(r'^Capacity:\s+([0-9]+)\s*$', block_info, re.M)
    require(capacity is not None, 'Read the current native disk capacity before shutdown.')
    require('--atomic' in Manager.command(['virsh', '-c', 'qemu:///system', 'help', 'snapshot-create']),
            'The installed native snapshot command must support atomic creation.')
    require(filesystem.f_bavail * filesystem.f_frsize >= max(minimum_free_bytes, int(capacity[1])),
            'Snapshot free-space reserve is unavailable; do not stop the VM.')


def native_lock(primary):
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', primary.get('uuid', '')),
            'Require canonical native UUID for the snapshot lock.')
    fd = os.open('/run/lock/aap-cold-snapshot-' + primary['uuid'] + '.lock',
                 os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    info = os.fstat(fd)
    try:
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1,
                'Require a root-owned native per-VM transaction lock.')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        os.close(fd)
        raise
    return fd
