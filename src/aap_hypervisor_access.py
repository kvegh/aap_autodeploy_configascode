"""Verify native AAP guest resources; Ansible owns firewall application and locking."""
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import stat
import sys
import xml.etree.ElementTree as ET

from ipaddress import IPv4Address, IPv4Interface, IPv4Network



OWNER = 'disconnected-windows-patching'
PRIMARY_FIELDS = {'uuid', 'disk', 'address', 'mac', 'network', 'bridge', 'verified', 'hypervisor_machine_id'}
SUPPLEMENTAL_FIELDS = {'owner_project_id', 'network', 'bridge', 'address', 'mac',
                       'connection_uuid', 'connection_name', 'attachment_created', 'connection_created'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uuid(value):
    return (isinstance(value, str) and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value)
            and value != '00000000-0000-0000-0000-000000000000')


def nic(value):
    """Validate a canonical, private, isolated network identity without coercion."""
    require(isinstance(value, dict), 'Require a recorded network identity.')
    address = IPv4Address(value.get('address'))
    require(isinstance(value.get('address'), str) and str(address) == value['address']
            and any(address in IPv4Network(block)
                    for block in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
            and isinstance(value.get('mac'), str)
            and re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', value['mac'])
            and not int(value['mac'][:2], 16) & 1 and value['mac'] != '00:00:00:00:00:00'
            and isinstance(value.get('network'), str)
            and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}', value['network'])
            and isinstance(value.get('bridge'), str)
            and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,14}', value['bridge']),
            'Require a canonical private address, unicast MAC, network and bridge.')
    return value


def supplemental(value, pin=None):
    require(isinstance(value, dict) and set(value) == SUPPLEMENTAL_FIELDS
            and value['owner_project_id'] == OWNER
            and value['attachment_created'] is True and value['connection_created'] is True
            and uuid(value['connection_uuid'])
            and isinstance(value['connection_name'], str)
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,62}', value['connection_name']),
            'Require the exact Windows-owned NIC and newly created persistent connection.')
    nic(value)
    require(pin is None or value['bridge'] in pin['isolation_bridges'],
            'The supplemental NIC must remain on an enforced isolated bridge.')
    return value


def primary_interfaces(primary, pin=None):
    """Preserve the immutable flat primary and, when declared, exactly one extra."""
    require(isinstance(primary, dict), 'Require existing primary guest ownership.')
    extras = primary.get('supplemental_interfaces', [])
    require(isinstance(extras, list) and len(extras) <= 1
            and ('supplemental_interfaces' not in primary or len(extras) == 1),
            'Omit unused supplemental metadata; record only one exact Windows NIC.')
    result = [primary]
    for value in extras:
        supplemental(value, pin)
        require(all(value[field] != primary[field] for field in ('address', 'mac', 'network', 'bridge')),
                'The supplemental identity must be distinct from the immutable primary.')
        result.append(value)
    return result


def supplemental_native_matches(interface, record):
    """The use-case marker belongs only to its exact declared extra interface."""
    source, mac = interface.find('source'), interface.find('mac')
    alias, model = interface.find('alias'), interface.find('model')
    return (interface.get('type') == 'network' and source is not None and mac is not None
            and source.get('network') == record['network'] and mac.get('address') == record['mac']
            and alias is not None and alias.get('name') == 'ua-windows-' + record['connection_uuid']
            and model is not None and model.get('type') == 'virtio')


def same_primary(before, after):
    """Only the bounded supplemental declaration can change."""
    return ({key: value for key, value in before.items() if key != 'supplemental_interfaces'}
            == {key: value for key, value in after.items() if key != 'supplemental_interfaces'})


def desired_resource(primary, declaration, state, pin):
    require(state in ('present', 'absent'), 'Choose exact supplemental NIC addition or removal.')
    supplemental(declaration, pin)
    primary_interfaces(primary, pin)
    extras = primary.get('supplemental_interfaces', [])
    require(not extras or extras == [declaration], 'Never replace another saved supplemental NIC or connection.')
    result = deepcopy(primary)
    if state == 'present':
        result['supplemental_interfaces'] = [deepcopy(declaration)]
    else:
        result.pop('supplemental_interfaces', None)
    primary_interfaces(result, pin)
    return result


def connection_readback(guest):
    """Use actual authenticated RHEL readback, never a caller-supplied verified flag."""
    observed, declaration = guest['connection_readback'], guest['supplemental_interface']
    require(isinstance(observed, dict) and set(observed) == {'machine_id', 'connections'}
            and observed['machine_id'] == guest['guest_machine_id']
            and re.fullmatch(r'[0-9a-f]{32}', observed['machine_id'] or ''),
            'Require fresh authenticated connection and guest-machine readback.')
    rows = observed['connections']
    fields = {'uuid', 'name', 'mac', 'addresses', 'gateway', 'dns', 'never_default', 'autoconnect',
              'ipv4_method', 'ipv4_ignore_auto_dns', 'ipv6_method', 'ipv6_never_default', 'ipv6_ignore_auto_dns'}
    require(isinstance(rows, list) and len(rows) <= 64
            and all(isinstance(row, dict) and set(row) == fields and uuid(row['uuid'])
                    and isinstance(row['name'], str) and isinstance(row['mac'], str)
                    and isinstance(row['addresses'], list) and len(row['addresses']) <= 16
                    and isinstance(row['gateway'], str) and isinstance(row['dns'], list)
                    and type(row['never_default']) is bool and type(row['autoconnect']) is bool
                    and isinstance(row['ipv4_method'], str) and isinstance(row['ipv6_method'], str)
                    and all(type(row[key]) is bool for key in ('ipv4_ignore_auto_dns', 'ipv6_never_default', 'ipv6_ignore_auto_dns'))
                    for row in rows)
            and len({row['uuid'] for row in rows}) == len(rows),
            'Inspect a bounded complete list of persistent NetworkManager profiles.')
    matching = []
    for row in rows:
        addresses = [IPv4Interface(value) for value in row['addresses']]
        require(all(str(address) == value for address, value in zip(addresses, row['addresses'])),
                'Read canonical persistent IPv4 addresses without lossy conversion.')
        if (row['uuid'] == declaration['connection_uuid'] or row['name'] == declaration['connection_name']
                or row['mac'] == declaration['mac'] or any(str(value.ip) == declaration['address'] for value in addresses)):
            matching.append(row)
    if guest['supplemental_state'] == 'absent':
        require(not matching, 'Do not forget a remaining supplemental connection or address.')
        return None
    require(len(matching) == 1, 'Require exactly one authenticated owned persistent connection.')
    row = matching[0]
    require(row['uuid'] == declaration['connection_uuid'] and row['name'] == declaration['connection_name']
            and row['mac'] == declaration['mac'] and len(row['addresses']) == 1
            and str(IPv4Interface(row['addresses'][0]).ip) == declaration['address']
            and not row['gateway'] and not row['dns'] and row['never_default'] is True and row['autoconnect'] is True
            and row['ipv4_method'] == 'manual' and row['ipv4_ignore_auto_dns'] is True
            and row['ipv6_method'] == 'disabled' and row['ipv6_never_default'] is True
            and row['ipv6_ignore_auto_dns'] is True,
            'The exact supplemental connection needs its static address, autoconnect, no gateway and no DNS.')
    return IPv4Interface(row['addresses'][0])


def command(arguments, data=None, allowed=(0,)):
    result = subprocess.run(arguments, input=data, text=True, capture_output=True, timeout=30)
    require(result.returncode in allowed, 'A required protected hypervisor command failed.')
    return result


def isolated(xml, networks, bridges):
    root = ET.fromstring(xml)
    require(not root.findall('./devices/hostdev') and not root.findall('./devices/filesystem')
            and not root.findall('.//{http://libvirt.org/schemas/domain/qemu/1.0}commandline'),
            'Guest devices cannot bypass isolation through host passthrough or custom arguments.')
    for interface in root.findall('./devices/interface'):
        source = interface.find('source')
        require(source is not None and not interface.findall('./virtualport'), 'Require isolated guest interfaces.')
        require((interface.get('type') == 'network' and source.get('network') in networks
                 and networks[source.get('network')] in bridges)
                or (interface.get('type') == 'bridge' and source.get('bridge') in bridges),
                'A guest interface escaped the enforced bridges.')
    for source in root.findall('./devices//source'):
        require(not any(key in source.attrib for key in ('host', 'url', 'protocol', 'address'))
                and source.find('host') is None, 'Remote host-backed guest devices are outside isolation.')


def desired_policy(route, primary, declared, mode='management'):
    """Derive exactly one management permission from an existing HTTPS identity."""
    pin = route['hypervisor']
    require(primary.get('verified') is True and primary['hypervisor_machine_id'] == pin['machine_id']
            and primary['address'] == route['vm_ip']
            and primary['disk'] == '/opt/vms/' + route['vm_name'] + '.disk.qcow2',
            'Require the selected verified primary resource.')
    require(declared.get('protected_ipv4') and pin['address'] not in declared['protected_ipv4']
            and pin['public_ip'] not in declared['protected_ipv4']
            and type(pin['port']) is int and 1 <= pin['port'] <= 65535,
            'Management access must remain on the nonproduction pinned hypervisor.')
    identity = {key: primary[field] for key, field in (('bridge', 'bridge'), ('ipv4', 'address'), ('mac', 'mac'))}
    require(mode in ('management', 'installation'), 'Choose one bounded AAP installation or management permission.')
    desired = deepcopy(declared)
    if mode == 'installation':
        clients = desired.setdefault('https_clients', [])
        matches = [item for item in clients if item['ipv4'] == identity['ipv4'] or item['mac'] == identity['mac']]
        require(not matches or matches == [identity], 'An installation permission conflicts with existing guest ownership.')
        if not matches:
            clients.append(identity)
        destination, port = pin['public_ip'], 443
    else:
        require(identity in declared.get('https_clients', []),
                'Management access requires this exact already-approved HTTPS client.')
        destination, port = pin['address'], pin['port']
    client = dict(identity, destinations=[destination], ports=[port])
    local = desired.setdefault('guest_host_clients', [])
    matching = [item for item in local if item['ipv4'] == identity['ipv4'] or item['mac'] == identity['mac']]
    require(not matching or (len(matching) == 1
        and all(matching[0][key] == identity[key] for key in identity)),
        'An existing primary local permission conflicts with selected guest ownership.')
    if matching:
        old = matching[0]
        requested = {(address, value) for address in old['destinations'] for value in old['ports']} | {(destination, port)}
        destinations = old['destinations'] + ([] if destination in old['destinations'] else [destination])
        ports = old['ports'] + ([] if port in old['ports'] else [port])
        require({(address, value) for address in destinations for value in ports} == requested,
                'Separate management and public addresses require reviewed exact destination-port pairs.')
        old.update(destinations=destinations, ports=ports)
    else:
        local.append(client)
    return desired


def plan(expected, probe):
    route, primary, declared = (expected[key] for key in ('route', 'primary', 'declared_policy'))
    pin = route['hypervisor']
    require(primary.get('verified') is True and primary['hypervisor_machine_id'] == pin['machine_id']
            and primary['address'] == route['vm_ip'] and probe['machine_id'] == pin['machine_id'],
            'Require the exact verified primary guest and pinned hypervisor.')
    require(declared.get('protected_ipv4') and pin['address'] not in declared['protected_ipv4']
            and pin['public_ip'] not in declared['protected_ipv4'] and pin['address'] in probe['addresses']
            and type(pin['port']) is int and 1 <= pin['port'] <= 65535,
            'Management access is confined to the nonproduction hypervisor assigned address and managed port.')
    require(declared['bridges'] == pin['isolation_bridges'] and declared['dns_bridges'] == pin['isolation_dns_bridges']
            and not probe['autostart'], 'Preserve the complete enforced bridges and disabled guest autostart.')
    networks = {}
    for name, xml in probe['networks'].items():
        root = ET.fromstring(xml)
        require(root.findtext('name') == name and root.find('bridge') is not None, 'Read actual network bridge definitions.')
        networks[name] = root.find('bridge').get('name')
    recorded = primary_interfaces(primary, pin)
    require(all(networks.get(nic['network']) == nic['bridge'] and nic['bridge'] in declared['bridges'] for nic in recorded),
            'Every declared AAP NIC must use its recorded enforced network and bridge.')
    for nic in recorded[1:]:
        definitions = probe.get('supplemental_network_definitions', {}).get(nic['network'])
        require(isinstance(definitions, dict) and set(definitions) == {'persistent', 'current'},
                'Inspect both active and persistent supplemental network definitions.')
        for xml in definitions.values():
            root = ET.fromstring(xml)
            require(root.findtext('name') == nic['network'] and root.find('bridge') is not None
                    and root.find('bridge').get('name') == nic['bridge'] and root.find('forward') is None,
                    'The exact supplemental network must remain persistently isolated.')
    mac_owners = {}
    require(route['vm_name'] in probe['domains'], 'Require the actual selected primary domain.')
    for name, states in probe['domains'].items():
        for xml in states.values():
            root = ET.fromstring(xml)
            require(root.findtext('name') == name, 'Domain readback must match its selected identity.')
            isolated(xml, networks, declared['bridges'])
            for mac in root.findall('./devices/interface/mac'):
                address = mac.get('address')
                require(address not in mac_owners or mac_owners[address] == name, 'Guest MAC ownership must be unique.')
                mac_owners[address] = name
    require(set(probe['domains'][route['vm_name']]) == {'persistent', 'current'},
            'Inspect both persistent and current primary domain definitions.')
    expected_nics = {(nic['network'], nic['mac']) for nic in recorded}
    for xml in probe['domains'][route['vm_name']].values():
        root = ET.fromstring(xml)
        disks, interfaces = root.findall("./devices/disk[@device='disk']"), root.findall('./devices/interface')
        require(root.findtext('uuid') == primary['uuid'] and len(disks) == 1 and len(interfaces) == len(recorded),
                'Primary UUID, one disk and the exact declared NIC set must match verified ownership.')
        disk = disks[0].find('source')
        require(disk is not None and disk.get('file') == primary['disk']
                and primary['disk'] == '/opt/vms/' + route['vm_name'] + '.disk.qcow2'
                and all(interface.get('type') == 'network' and interface.find('source') is not None
                        and interface.find('mac') is not None for interface in interfaces)
                and {(interface.find('source').get('network'), interface.find('mac').get('address'))
                     for interface in interfaces} == expected_nics,
                'Primary storage and every declared MAC/network must match actual libvirt ownership.')
        for record in recorded[1:]:
            matching = [interface for interface in interfaces
                        if interface.find('mac').get('address') == record['mac']]
            require(len(matching) == 1 and supplemental_native_matches(matching[0], record),
                    'The supplemental NIC must retain its exact Windows ownership marker and virtio model.')
    leases = re.findall(r'([0-9a-f]{2}(?::[0-9a-f]{2}){5})\s+ipv4\s+([0-9.]+)/[0-9]+', probe['leases'].lower())
    require((primary['mac'], primary['address']) in leases
            and set(leases) <= {(nic['mac'], nic['address']) for nic in recorded},
            'Require the exact primary DHCP identity and no undeclared supplemental lease.')
    mode = expected.get('mode', 'management')
    desired = desired_policy(route, primary, declared, mode)
    client = next(item for item in desired['guest_host_clients'] if item['ipv4'] == primary['address'])
    actual = probe['policy']
    require(actual == declared or actual == desired, 'Live policy must equal declared state or this exact derived management grant.')
    if expected.get('operation', 'apply') == 'rollback':
        require(mode == 'installation' and actual == desired,
                'Installation rollback requires exactly this job\'s applied policy.')
        desired = deepcopy(declared)
    destination, port = (pin['public_ip'], 443) if mode == 'installation' else (pin['address'], pin['port'])
    require(destination in probe['addresses'], 'The exact AAP host destination must belong to this hypervisor.')
    rule = ('rule family="ipv4" priority="0" source address="%s/32" destination address="%s/32" '
            'port port="%s" protocol="tcp" accept' % (primary['address'], destination, port))
    return {'previous_policy': deepcopy(actual), 'desired_policy': desired, 'client': client,
            'rich_rule': rule, 'changed': actual != desired}


def probe(route, policy, allow_absent_guest=False, guest_kind=None, primary=None):
    """Gather native resource facts only; desired policy is supplied from CaC.

    The caller holds the approved temporary Ansible transaction lock and checks
    this supplied policy against complete native nft readback before mutation.
    See ../README.md#native-firewall-transactions.
    """
    require(guest_kind in (None, 'windows'), 'Select only default Linux or explicit Windows native provenance.')
    require(os.geteuid() == 0 and isinstance(policy, dict), 'Require root resource readback and complete CaC policy.')
    data = {'machine_id': Path('/etc/machine-id').read_text().strip(), 'policy': deepcopy(policy)}
    addresses = json.loads(command(['/usr/sbin/ip', '-j', 'address', 'show']).stdout)
    data['addresses'] = [item['local'] for interface in addresses for item in interface.get('addr_info', []) if item.get('family') == 'inet']
    for action in ('is-active', 'is-enabled'):
        command(['systemctl', action, 'hactar-recovery-isolation.service'])
    names = command(['virsh', '-c', 'qemu:///system', 'list', '--all', '--name']).stdout.split()
    require(len(names) <= 64 and len(set(names)) == len(names), 'Require a bounded actual VM set.')
    data['domains'] = {name: {state: command(['virsh', '-c', 'qemu:///system', 'dumpxml', name] + options).stdout
        for state, options in (('persistent', ['--inactive']), ('current', []))} for name in names}
    net_names = command(['virsh', '-c', 'qemu:///system', 'net-list', '--all', '--name']).stdout.split()
    require(len(net_names) <= 64, 'Require bounded actual guest networks.')
    data['networks'] = {name: command(['virsh', '-c', 'qemu:///system', 'net-dumpxml', name]).stdout for name in net_names}
    if primary is not None and primary.get('supplemental_interfaces'):
        data['supplemental_network_definitions'] = {nic['network']: {
            'current': data['networks'][nic['network']],
            'persistent': command(['virsh', '-c', 'qemu:///system', 'net-dumpxml', nic['network'], '--inactive']).stdout}
            for nic in primary_interfaces(primary, route['hypervisor'])[1:]}
    data['autostart'] = command(['virsh', '-c', 'qemu:///system', 'list', '--all', '--autostart', '--name']).stdout.split()
    if allow_absent_guest or guest_kind == 'windows':
        name = route['vm_name']
        require(isinstance(name, str) and re.fullmatch(r'[a-z][a-z0-9-]{0,62}', name),
                'Inspect only the exact selected generic guest disk names.')
        data['disk_states'] = {}
        paths = ['/opt/vms/' + name + '.disk.qcow2', '/opt/vms/' + name + '.qcow2']
        if guest_kind == 'windows':
            paths.append('/opt/vms/win-' + name + '-clone.disk.qcow2')
        for path in paths:
            try:
                info = os.lstat(path)
            except FileNotFoundError:
                data['disk_states'][path] = {'exists': False}
            else:
                data['disk_states'][path] = {'exists': True, 'regular': stat.S_ISREG(info.st_mode),
                    'symlink': stat.S_ISLNK(info.st_mode), 'inode': info.st_ino, 'device': info.st_dev,
                    'size': info.st_size, 'mtime_ns': info.st_mtime_ns, 'links': info.st_nlink}
        if name not in data['domains']:
            require(allow_absent_guest and not any(row['exists'] for row in data['disk_states'].values()),
                    'A missing selected domain with a remaining canonical disk requires explicit recovery review.')
        active = command(['virsh', '-c', 'qemu:///system', 'net-list', '--name']).stdout.split()
        require(set(active) <= set(net_names), 'Retain the complete known libvirt network set.')
        data['network_definitions'] = {network: {'persistent': command(
            ['virsh', '-c', 'qemu:///system', 'net-dumpxml', network, '--inactive']).stdout,
            **({'current': data['networks'][network]} if network in active else {})} for network in net_names}
        data['dhcp_leases'] = {network: command(
            ['virsh', '-c', 'qemu:///system', 'net-dhcp-leases', network]).stdout for network in active}
        data['native_rich_rules'] = {state: command(['firewall-cmd'] + options +
            ['--list-all-zones']).stdout.splitlines()
            for state, options in (('runtime', []), ('permanent', ['--permanent']))}
        # An enforced bridge can be inactive after its guest was removed. No
        # native zone rule is changed here; inspect all zones for owned residue.
        data['zone'] = None
        data['leases'] = ''
        return data
    data['leases'] = command(['virsh', '-c', 'qemu:///system', 'domifaddr', route['vm_name'], '--source', 'lease']).stdout
    selected = ET.fromstring(data['domains'][route['vm_name']]['current'])
    management = [interface for interface in selected.findall('./devices/interface')
                  if interface.find('source') is not None and interface.find('mac') is not None]
    if primary is not None:
        management = [interface for interface in management
                      if interface.find('mac').get('address') == primary['mac']
                      and interface.find('source').get('network') == primary['network']]
        require(len(management) == 1, 'Inspect the declared primary bridge independently of NIC ordering.')
    network = management[0].find('source').get('network')
    bridge = ET.fromstring(data['networks'][network]).find('bridge').get('name')
    data['zone'] = command(['firewall-cmd', '--get-zone-of-interface=' + bridge]).stdout.strip()
    return data



def reconcile(expected):
    """Return the existing native resource plan without changing any firewall."""
    require({'route', 'primary', 'declared_policy', 'check_mode'} <= set(expected)
            and set(expected) <= {'route', 'primary', 'declared_policy', 'check_mode', 'mode', 'operation', 'native_rule_previous'}
            and type(expected['check_mode']) is bool, 'Use only the fixed verified management request.')
    require(expected.get('operation', 'apply') in ('apply', 'rollback'), 'Select the exact planned operation.')
    primary = expected['primary']
    current = probe(expected['route'], expected['declared_policy'],
                    **({'primary': primary} if primary.get('supplemental_interfaces') else {}))
    change = plan(expected, current)
    require(current['zone'] == 'libvirt', 'Use only the existing libvirt zone for the selected bridge.')
    return dict(change, applied=False)


if __name__ == '__main__':
    try:
        print(json.dumps(reconcile(json.load(sys.stdin))))
    except Exception:
        print('Protected hypervisor resource verification failed.', file=sys.stderr)
        raise SystemExit(1)
