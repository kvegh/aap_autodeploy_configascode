"""Release or retire one verified guest, retaining production denial.

Runs only on the pinned recovery hypervisor. The sibling management helper owns
the existing protected-file, libvirt readback and atomic-write primitives.
Linux remains the default; Windows requires its own explicit trusted provenance.
"""

from copy import deepcopy
from datetime import datetime
import fcntl
import importlib.util
import ipaddress
from importlib.machinery import SourceFileLoader
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import aap_hypervisor_access as base


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _interfaces(guest):
    return guest['interfaces'] if guest.get('kind') == 'windows' else [guest]


def _identities(guest):
    return [{'bridge': nic['bridge'], 'ipv4': nic['address'], 'mac': nic['mac']} for nic in _interfaces(guest)]


def _windows_guest(guest, pin):
    fields = {'kind', 'vm_name', 'instance_name', 'uuid', 'disk', 'hypervisor_machine_id', 'verified',
              'computer_name', 'computer_uuid', 'address', 'interfaces', 'winrm_certificate_validated'}
    require(isinstance(guest, dict) and set(guest) == fields and guest['kind'] == 'windows'
            and guest['verified'] is True and type(guest['winrm_certificate_validated']) is bool,
            'Require explicit Windows provenance and a truthful Boolean certificate-validation result.')
    name = guest['vm_name']
    version = re.fullmatch(r'[a-z][a-z0-9-]*-v([0-9]{2,})', name or '')
    require(version is not None and len(name) <= 15 and int(version[1]) > 0
            and name.endswith('-v%02d' % int(version[1]))
            and isinstance(guest['computer_name'], str) and guest['computer_name'].lower() == name
            and re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{0,14}', guest['computer_name'])
            and isinstance(guest['instance_name'], str) and re.fullmatch(r'[a-z][a-z0-9-]{0,62}', guest['instance_name'])
            and guest['computer_uuid'] == guest['uuid']
            and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', guest['uuid'])
            and guest['uuid'] != '00000000-0000-0000-0000-000000000000'
            and guest['hypervisor_machine_id'] == pin['machine_id']
            and guest['disk'] == '/opt/vms/win-' + name + '-clone.disk.qcow2',
            'Windows trusted computer, exact clone and native UUID must agree.')
    nics = guest['interfaces']
    require(isinstance(nics, list) and 1 <= len(nics) <= 2
            and all(isinstance(nic, dict) and set(nic) == {'network', 'bridge', 'mac', 'address', 'dns_name'} for nic in nics),
            'Bind every one or two permanent Windows NICs explicitly.')
    for nic in nics:
        address = ipaddress.IPv4Address(nic['address'])
        require(str(address) == nic['address'] and any(address in ipaddress.IPv4Network(value)
                for value in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')) and not address.is_loopback
                and not address.is_link_local and not address.is_unspecified and not address.is_multicast
                and re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', nic['mac'])
                and int(nic['mac'].split(':')[0], 16) & 1 == 0 and nic['mac'] != '00:00:00:00:00:00'
                and nic['bridge'] in pin['isolation_bridges']
                and re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}', nic['network'])
                and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', nic['dns_name']),
                'Windows NICs require canonical private IPv4, MAC, bridge and network/DNS identity.')
    require(len({nic['mac'] for nic in nics}) == len(nics)
            and len({nic['address'] for nic in nics}) == len(nics)
            and guest['address'] in {nic['address'] for nic in nics},
            'Use distinct Windows NIC identities and select WinRM from the verified interfaces.')


def _windows_native(guest, pin, state, present):
    _windows_guest(guest, pin)
    require(state['machine_id'] == pin['machine_id'] and pin['address'] in state['addresses']
            and not state['autostart'] and all(nic['address'] not in state['addresses'] for nic in guest['interfaces']),
            'Retain the exact pinned hypervisor and disabled guest autostart.')
    networks = {}
    for name, xml in state['networks'].items():
        root = ET.fromstring(xml)
        require(root.findtext('name') == name and root.find('bridge') is not None, 'Inspect the actual libvirt network identity.')
        networks[name] = root.find('bridge').get('name')
    for nic in guest['interfaces']:
        require(networks.get(nic['network']) == nic['bridge'], 'The Windows NIC bridge must match the actual network.')
    mac_owners = {}
    for name, scopes in state['domains'].items():
        for scope, xml in scopes.items():
            root = ET.fromstring(xml)
            require(root.findtext('name') == name, 'Read each exact native domain without substitution.')
            base.isolated(xml, networks, pin['isolation_bridges'])
            for mac in root.findall('./devices/interface/mac'):
                value = mac.get('address')
                require(value not in mac_owners or mac_owners[value] == name, 'Every Windows MAC requires a unique native owner.')
                mac_owners[value] = name
            if name != guest['vm_name']:
                require(root.findtext('uuid') != guest['uuid']
                        and not any(node.get('file') == guest['disk'] for node in root.findall('./devices/disk/source'))
                        and not any(node.get('address') in {nic['mac'] for nic in guest['interfaces']}
                                    for node in root.findall('./devices/interface/mac')),
                        'Another guest owns selected Windows UUID, clone or NIC identity.')
    if present:
        paths = {'/opt/vms/' + guest['vm_name'] + '.disk.qcow2', '/opt/vms/' + guest['vm_name'] + '.qcow2', guest['disk']}
        require(set(state['disk_states']) == paths and all(not state['disk_states'][path]['exists']
                for path in paths if path != guest['disk']), 'Inspect only the exact exclusive Windows clone, without Linux disk aliases.')
        disk = state['disk_states'][guest['disk']]
        require(disk['exists'] and disk.get('regular') and not disk.get('symlink') and disk.get('links') == 1,
                'The Windows clone must be a regular, non-symlinked, exclusively owned file.')
        require(set(state['domains'][guest['vm_name']]) == {'persistent', 'current'}, 'Read both Windows native definitions.')
        for xml in state['domains'][guest['vm_name']].values():
            root = ET.fromstring(xml)
            disks = root.findall("./devices/disk[@device='disk']")
            interfaces = root.findall('./devices/interface')
            actual = []
            for nic in interfaces:
                require(nic.get('type') == 'network' and nic.find('source') is not None and nic.find('mac') is not None,
                        'Every Windows interface must be an explicit libvirt network NIC.')
                actual.append({'network': nic.find('source').get('network'), 'mac': nic.find('mac').get('address')})
            expected = [{'network': nic['network'], 'mac': nic['mac']} for nic in guest['interfaces']]
            require(root.findtext('uuid') == guest['uuid']
                    and root.findtext('description') == 'aap-disconnected-windows-clone'
                    and root.findtext('title') == guest['instance_name'] + ':' + guest['vm_name']
                    and len(disks) == 1 and disks[0].find('source') is not None
                    and disks[0].find('source').get('file') == guest['disk'] and actual == expected,
                    'Windows UUID, clone marker/title, exclusive disk and every native NIC must match trusted provenance.')


def _windows_reservations(state, guest, require_present=False):
    selected = []
    for nic in guest['interfaces']:
        network = nic['network']
        scopes = state['network_definitions'].get(network, {})
        require('persistent' in scopes and (not require_present or 'current' in scopes),
                'Read every Windows NIC network persistent and active ownership.')
        for scope, xml in scopes.items():
            root = ET.fromstring(xml)
            subnets = [node for node in root.findall('ip') if node.get('address')
                       and ipaddress.IPv4Address(nic['address']) in ipaddress.ip_network(node.get('address') + '/' +
                           (node.get('prefix') or node.get('netmask')), strict=False)]
            require(root.findtext('name') == network and root.find('bridge') is not None
                    and root.find('bridge').get('name') == nic['bridge'] and len(subnets) == 1
                    and subnets[0].get('address') != nic['address'], 'Windows IPv4 must belong to its exact native bridge/subnet.')
            expected = {'mac': nic['mac'], 'ip': nic['address'], 'name': nic['dns_name']}
            dhcp = [node for node in root.findall('./ip/dhcp/host') if node.get('ip') == nic['address']
                    or node.get('mac', '').lower() == nic['mac'] or node.get('name') == nic['dns_name']]
            dns = [node for node in root.findall('./dns/host') if node.get('ip') == nic['address']
                   or nic['dns_name'] in [item.text for item in node.findall('hostname')]]
            dns_enabled = root.find('dns') is None or root.find('dns').get('enable', 'yes') != 'no'
            require(len(dhcp) <= 1 and all(node.attrib == expected for node in dhcp)
                    and len(dns) <= 1 and all(node.attrib == {'ip': nic['address']}
                        and [item.text for item in node.findall('hostname')] == [nic['dns_name']] for node in dns)
                    and (dns_enabled or not dns)
                    and (not require_present or
                         (len(dhcp) == 1 and len(dns) == (1 if dns_enabled else 0))),
                    'Windows DHCP and DNS tuples must belong exclusively to this exact verified NIC.')
            for kind, nodes in (('ip-dhcp-host', dhcp), ('dns-host', dns)):
                selected.extend({'network': network, 'scope': scope, 'kind': kind,
                                 'xml': ET.tostring(node, encoding='unicode')} for node in nodes)
        for line in state.get('dhcp_leases', {}).get(network, '').lower().splitlines():
            match = re.search(r'([0-9a-f]{2}(?::[0-9a-f]{2}){5})\s+ipv4\s+([0-9.]+)/[0-9]+', line)
            if match and (match[1] == nic['mac'] or match[2] == nic['address']):
                require((match[1], match[2]) == (nic['mac'], nic['address']), 'A Windows NIC has a conflicting live lease owner.')
    return selected


def windows_plan(request, state):
    require(set(request) <= {'operation', 'guest', 'hypervisor', 'transition', 'check_mode', 'mode'}
            and {'operation', 'guest', 'hypervisor', 'transition', 'check_mode'} <= set(request)
            and request['operation'] in {'apply', 'rollback'} and type(request['check_mode']) is bool
            and request.get('mode', 'release') == 'release', 'Windows supports only final verified deployment release.')
    guest, pin, transition = (request[key] for key in ('guest', 'hypervisor', 'transition'))
    require(guest['vm_name'] in state['domains'], 'Release only a present verified Windows guest.')
    _windows_native(guest, pin, state, True)
    _windows_reservations(state, guest, True)
    require(isinstance(transition, dict) and set(transition) == {'previous_policy', 'desired_policy'},
            'Use the exact preflighted Windows transition.')
    previous, desired = transition['previous_policy'], transition['desired_policy']
    require(previous.get('protected_ipv4') and previous['protected_ipv4'] == desired.get('protected_ipv4')
            and pin['address'] not in previous['protected_ipv4'] and pin['public_ip'] not in previous['protected_ipv4']
            and all(nic['address'] not in previous['protected_ipv4'] for nic in guest['interfaces'])
            and previous['bridges'] == desired['bridges'] == pin['isolation_bridges']
            and previous['dns_bridges'] == desired['dns_bridges'] == pin['isolation_dns_bridges']
            and state['policy'] in (previous, desired), 'Retain canonical production denial and exact enforced policy.')
    expected = deepcopy(previous)
    for identity in _identities(guest):
        matches = [row for row in expected.setdefault('released_clients', [])
                   if row['ipv4'] == identity['ipv4'] or row['mac'] == identity['mac']]
        require(not matches or matches == [identity], 'A Windows release conflicts with another guest identity.')
        if not matches:
            expected['released_clients'].append(identity)
    require(desired == expected, 'Windows release may add only all exact verified NIC identities.')
    if request['operation'] == 'rollback':
        require(state['policy'] == desired, 'Windows rollback cannot overwrite a later policy change.')
    target = previous if request['operation'] == 'rollback' else desired
    return {'previous_policy': deepcopy(state['policy']), 'desired_policy': deepcopy(target), 'changed': state['policy'] != target}


def aap_plan(request, state):
    require(set(request) <= {'operation', 'guest', 'hypervisor', 'transition', 'check_mode', 'mode'}
            and {'operation', 'guest', 'hypervisor', 'transition', 'check_mode'} <= set(request)
            and request['operation'] in {'apply', 'rollback'} and type(request['check_mode']) is bool
            and request.get('mode', 'release') == 'release', 'AAP supports only final verified base-configuration release.')
    guest, pin, transition = (request[key] for key in ('guest', 'hypervisor', 'transition'))
    require(isinstance(guest, dict) and set(guest) == {'kind', 'route', 'primary', 'guest_machine_id'}
            and guest['kind'] == 'aap' and guest['route']['hypervisor'] == pin
            and isinstance(guest['guest_machine_id'], str) and re.fullmatch(r'[a-f0-9]{32}', guest['guest_machine_id'])
            and guest['guest_machine_id'] != pin['machine_id'], 'Require the existing AAP route and fresh authenticated guest machine identity.')
    route, primary = guest['route'], guest['primary']
    require(primary.get('machine_id', guest['guest_machine_id']) == guest['guest_machine_id'],
            'The authenticated AAP machine identity conflicts with saved primary facts.')
    require(isinstance(transition, dict) and set(transition) == {'previous_policy', 'desired_policy'},
            'Use only the exact source-preflighted AAP release transition.')
    previous, desired = transition['previous_policy'], transition['desired_policy']
    require(state['policy'] in (previous, desired)
            and previous.get('protected_ipv4') and previous['protected_ipv4'] == desired.get('protected_ipv4')
            and primary['address'] not in previous['protected_ipv4'], 'AAP release must retain all production exclusions and exact canonical policy.')
    identity = {'bridge': primary['bridge'], 'ipv4': primary['address'], 'mac': primary['mac']}
    expected = deepcopy(previous)
    matches = [row for row in expected.setdefault('released_clients', [])
               if row['ipv4'] == identity['ipv4'] or row['mac'] == identity['mac']]
    require(not matches or matches == [identity], 'An AAP release conflicts with another guest identity.')
    if not matches:
        expected['released_clients'].append(identity)
    require(desired == expected, 'AAP release may add only its exact consumed primary identity.')
    # Reuse the actual AAP native guard, without applying its bounded permission
    # or requiring the unrelated generic-image provenance description.
    base.plan({'route': route, 'primary': primary, 'declared_policy': state['policy'], 'mode': 'installation'}, state)
    require(set(state['domains'][route['vm_name']]) == {'persistent', 'current'}, 'Inspect both actual AAP domain definitions.')
    for name, scopes in state['domains'].items():
        if name == route['vm_name']:
            continue
        for xml in scopes.values():
            root = ET.fromstring(xml)
            require(root.findtext('uuid') != primary['uuid']
                    and not any(node.get('file') == primary['disk'] for node in root.findall('./devices/disk/source')),
                    'Another native domain owns the consumed AAP UUID or disk.')
    if request['operation'] == 'rollback':
        require(state['policy'] == desired, 'AAP rollback cannot overwrite a later policy change.')
    target = previous if request['operation'] == 'rollback' else desired
    return {'previous_policy': deepcopy(state['policy']), 'desired_policy': deepcopy(target), 'changed': state['policy'] != target}


def plan(request, state):
    if request.get('mode') == 'supplemental_interface':
        return supplemental_plan(request, state)
    if isinstance(request.get('guest'), dict) and request['guest'].get('kind') == 'aap':
        return aap_plan(request, state)
    if isinstance(request.get('guest'), dict) and request['guest'].get('kind') == 'windows':
        return windows_plan(request, state)
    require({'operation', 'guest', 'hypervisor', 'transition', 'check_mode'} <= set(request)
            and set(request) <= {'operation', 'guest', 'hypervisor', 'transition', 'check_mode', 'mode'}
            and request['operation'] in {'apply', 'rollback'}
            and type(request['check_mode']) is bool,
            'Choose one exact verified recovery guest transition.')
    mode = request.get('mode', 'release')
    require(mode in {'release', 'bootstrap_https', 'bootstrap_http'},
            'Choose full release or bounded guest bootstrap HTTP or HTTPS.')
    guest, pin, transition = (request[key] for key in ('guest', 'hypervisor', 'transition'))
    require(isinstance(guest, dict) and guest.get('verified') is True
            and re.fullmatch(r'[a-z][a-z0-9-]{0,62}', guest.get('vm_name', ''))
            and re.fullmatch(r'[a-f0-9]{32}', guest.get('machine_id', ''))
            and guest.get('machine_id') != pin['machine_id']
            and guest.get('hypervisor_machine_id') == pin['machine_id'] == state['machine_id'],
            'Require authenticated guest facts and this exact recovery hypervisor.')
    require(isinstance(transition, dict) and set(transition) == {'previous_policy', 'desired_policy'},
            'Use only the source-preflighted old and desired policy.')
    previous, desired = transition['previous_policy'], transition['desired_policy']
    require(previous.get('protected_ipv4') and previous['protected_ipv4'] == desired.get('protected_ipv4')
            and pin['address'] not in previous['protected_ipv4']
            and pin['public_ip'] not in previous['protected_ipv4']
            and previous['bridges'] == desired['bridges'] == pin['isolation_bridges']
            and previous['dns_bridges'] == desired['dns_bridges'] == pin['isolation_dns_bridges']
            and not state['autostart'],
            'Retain production denial, all enforced bridges and disabled autostart.')
    identity = {'bridge': guest['bridge'], 'ipv4': guest['address'], 'mac': guest['mac']}
    expected = deepcopy(previous)
    field = {'release': 'released_clients', 'bootstrap_https': 'https_clients', 'bootstrap_http': 'http_clients'}[mode]
    released = expected.setdefault(field, [])
    matching = [row for row in released if row['ipv4'] == identity['ipv4'] or row['mac'] == identity['mac']]
    require(not matching or matching == [identity], 'An existing conflicting release requires review.')
    if not matching:
        released.append(identity)
    require(desired == expected, 'The transition must add exactly this one verified release.')
    require(state['policy'] in (previous, desired), 'Live policy drift requires a fresh source preflight.')
    networks = {}
    for name, xml in state['networks'].items():
        network = ET.fromstring(xml)
        require(network.findtext('name') == name and network.find('bridge') is not None,
                'Read actual network bridge definitions.')
        networks[name] = network.find('bridge').get('name')
    require(guest['network'] in networks and networks[guest['network']] == guest['bridge']
            and guest['bridge'] in previous['bridges'], 'The selected guest must use its enforced bridge.')
    require(guest['vm_name'] in state['domains'], 'Require the actual verified guest domain.')
    mac_owners = {}
    for name, states in state['domains'].items():
        for xml in states.values():
            domain = ET.fromstring(xml)
            require(domain.findtext('name') == name, 'Read actual selected domain names.')
            base.isolated(xml, networks, previous['bridges'])
            for mac in domain.findall('./devices/interface/mac'):
                address = mac.get('address')
                require(address not in mac_owners or mac_owners[address] == name,
                        'A released MAC must have exactly one owner.')
                mac_owners[address] = name
    selected_states = state['domains'][guest['vm_name']]
    require(set(selected_states) == {'persistent', 'current'}, 'Inspect both persistent and live guest ownership.')
    for kind, xml in selected_states.items():
        domain = ET.fromstring(xml)
        disks, interfaces = domain.findall("./devices/disk[@device='disk']"), domain.findall('./devices/interface')
        require(domain.findtext('uuid') == guest['uuid'] and len(disks) == len(interfaces) == 1,
                'The exact verified UUID must own one disk and one interface.')
        disk, interface = disks[0].find('source'), interfaces[0]
        require(disk is not None and disk.get('file') == guest['disk']
                and guest['disk'] == '/opt/vms/' + guest['vm_name'] + '.disk.qcow2'
                and interface.get('type') == 'network' and interface.find('source') is not None
                and interface.find('source').get('network') == guest['network']
                and interface.find('mac') is not None and interface.find('mac').get('address') == guest['mac'],
                'Disk, MAC and network must match actual verified guest ownership.')
        # Bootstrap records public provenance with `virsh desc --config` after
        # start. Libvirt therefore need not expose that metadata in live XML.
        # Both XMLs still need the exact UUID, disk, MAC and network above;
        # persistent provenance is mandatory and any live copy must also match.
        if kind == 'persistent' or domain.find('description') is not None:
            description = json.loads(domain.findtext('description') or '{}')
            require(description.get('schema_version') == 1 and description.get('deployment_type') == 'generic-recovery'
                    and all(description.get(key) == guest[key] for key in (
                        'vm_name', 'uuid', 'hypervisor_machine_id', 'source_image_sha256', 'host_keys')),
                    'Require the native generic-clone public provenance from guest bootstrap.')
    leases = re.findall(r'([0-9a-f]{2}(?::[0-9a-f]{2}){5})\s+ipv4\s+([0-9.]+)/[0-9]+', state['leases'].lower())
    require(set(leases) == {(guest['mac'], guest['address'])}, 'The DHCP identity must match the verified guest.')
    if request['operation'] == 'rollback':
        # Do not undo a later or independently changed policy.
        require(state['policy'] == desired, 'Rollback requires exactly the transition applied by this job.')
        target = previous
    else:
        target = desired
    return {'previous_policy': deepcopy(state['policy']), 'desired_policy': deepcopy(target),
            'changed': state['policy'] != target}


def supplemental_plan(request, state):
    """Verify intended hardware and authenticated connection without granting access."""
    require(set(request) == {'operation', 'guest', 'hypervisor', 'transition', 'check_mode', 'mode'}
            and request['operation'] == 'apply' and type(request['check_mode']) is bool,
            'Supplemental ownership verification cannot change or roll back networking.')
    guest, pin, transition = request['guest'], request['hypervisor'], request['transition']
    require(isinstance(guest, dict) and set(guest) == {'kind', 'route', 'primary', 'guest_machine_id',
                'supplemental_interface', 'supplemental_state', 'connection_readback'}
            and guest['kind'] == 'aap' and guest['route']['hypervisor'] == pin
            and isinstance(guest['guest_machine_id'], str)
            and re.fullmatch(r'[0-9a-f]{32}', guest['guest_machine_id'])
            and guest['guest_machine_id'] not in ('0' * 32, pin['machine_id']),
            'Use the existing AAP route and authenticated guest identity.')
    require(isinstance(transition, dict) and set(transition) == {
                'previous_policy', 'desired_policy', 'previous_resource', 'desired_resource'}
            and transition['previous_policy'] == transition['desired_policy'] == state['policy'],
            'Supplemental networking must leave all live and declared permissions unchanged.')
    previous, desired = transition['previous_resource'], transition['desired_resource']
    require(base.same_primary(previous, desired) and guest['primary'] in (previous, desired)
            and base.desired_resource(previous, guest['supplemental_interface'], guest['supplemental_state'], pin) == desired,
            'Verify only the planned optional interface; never replace primary ownership.')
    observed_address = base.connection_readback(guest)
    base.plan({'route': guest['route'], 'primary': desired,
               'declared_policy': state['policy'], 'mode': 'installation'}, state)
    if guest['supplemental_state'] == 'present':
        declaration = guest['supplemental_interface']
        definitions = state['supplemental_network_definitions'][declaration['network']]
        for xml in definitions.values():
            definition = ET.fromstring(xml)
            require(definition.find('forward') is None, 'The Windows supplemental network must remain isolated.')
            subnets = [ipaddress.IPv4Network('%s/%s' % (node.get('address'), node.get('prefix', node.get('netmask'))), strict=False)
                       for node in definition.findall('./ip') if node.get('family', 'ipv4') == 'ipv4']
            require(observed_address.network in subnets and observed_address.ip not in {
                        value for subnet in subnets for value in (subnet.network_address, subnet.broadcast_address)}
                    and declaration['address'] not in state['addresses'],
                    'The static supplemental address must match its actual network and not the hypervisor.')
            for node in definition.findall('./ip/dhcp/range'):
                require(not (ipaddress.IPv4Address(node.get('start')) <= observed_address.ip <= ipaddress.IPv4Address(node.get('end'))),
                        'The supplemental static address must remain outside dynamic DHCP pools.')
            for node in definition.findall('./ip/dhcp/host'):
                require(node.get('ip') != declaration['address'] and node.get('mac') != declaration['mac'],
                        'A supplemental static connection cannot claim an existing DHCP reservation.')
            require(all(node.get('ip') != declaration['address'] for node in definition.findall('./dns/host')),
                    'A supplemental static connection cannot claim an existing DNS host record.')
    return {'previous_policy': deepcopy(state['policy']), 'desired_policy': deepcopy(state['policy']),
            'changed': False, 'ownership_verified': True}


def reconcile(request):
    if request.get('operation') in {'retire_plan', 'retire_apply', 'retire_rollback'}:
        return reconcile_retirement(request)
    pin, guest = request['hypervisor'], request['guest']
    route = guest['route'] if guest.get('kind') == 'aap' else {'hypervisor': pin, 'vm_name': guest['vm_name']}
    descriptor = os.open(base.DIRECTORY, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if guest.get('kind') == 'windows':
            state = base.probe(route, guest_kind='windows')
        elif guest.get('kind') == 'aap' and (guest['primary'].get('supplemental_interfaces') or request.get('mode') == 'supplemental_interface'):
            primary = request['transition'].get('desired_resource', guest['primary'])
            state = base.probe(route, primary=primary)
        else:
            state = base.probe(route)
        change = plan(request, state)
        base.command([str(base.HELPER), 'check'], json.dumps(state['policy']))
        spec = importlib.util.spec_from_loader('installed_guest_release_isolation',
            SourceFileLoader('installed_guest_release_isolation', str(base.HELPER)))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        helper.validate_configuration(change['desired_policy'])
        commands = [{'delete': {'table': {'family': 'inet', 'name': helper.TABLE}}}]
        commands += [{'add': {kind: value}} for kind, value in helper.policy(change['desired_policy'])]
        base.command(['/usr/sbin/nft', '--check', '-j', '-f', '-'], json.dumps({'nftables': commands}))
        if request['check_mode']:
            return dict(change, applied=False)
        original = base.CONFIG.read_bytes()
        try:
            if change['changed']:
                base.save(json.dumps(change['desired_policy']).encode())
                base.command([str(base.HELPER), 'apply'])
            base.command([str(base.HELPER), 'check'], json.dumps(change['desired_policy']))
        except Exception:
            base.save(original)
            base.command([str(base.HELPER), 'apply'])
            base.command([str(base.HELPER), 'check'], json.dumps(state['policy']))
            raise
        return dict(change, applied=True)
    finally:
        os.close(descriptor)


def _retirement_policy(policy, guest):
    result = deepcopy(policy)
    if guest is None:
        return result
    identities = _identities(guest)
    require(not any(row['ipv4'] == identity['ipv4'] or row['mac'] == identity['mac']
                    for row in policy.get('guest_host_clients', []) for identity in identities),
            'Selected host-service grants require supported exact cleanup before retirement.')
    for field in ('https_clients', 'released_clients', 'http_clients'):
        retained = []
        for row in result.get(field, []):
            matching = [identity for identity in identities if row['ipv4'] == identity['ipv4'] or row['mac'] == identity['mac']]
            if matching:
                require(matching == [row], 'A selected permission conflicts with another guest identity.')
            else:
                retained.append(row)
        if field in result and retained != result[field]:
            if retained:
                result[field] = retained
            else:
                result.pop(field)
    if not result.get('https_clients') and not result.get('released_clients') and not result.get('http_clients'):
        result.pop('protected_ipv4', None)
    return result


def _retirement_dhcp(state, name, guest):
    if guest is not None and guest.get('kind') == 'windows':
        return _windows_reservations(state, guest)
    selected = []
    for network, scopes in state['network_definitions'].items():
        for scope, xml in scopes.items():
            root = ET.fromstring(xml)
            require(root.findtext('name') == network, 'Read exact persistent and live DHCP network ownership.')
            for item in root.findall('./ip/dhcp/host'):
                mac, address = item.get('mac', '').lower(), item.get('ip', '')
                hostname = item.get('name', '').split('.', 1)[0]
                matching = hostname == name or (guest is not None and (mac == guest['mac'] or address == guest['address']))
                if not matching:
                    continue
                require(guest is not None and network == guest['network'] and mac == guest['mac']
                        and address == guest['address'] and (not hostname or hostname == name),
                        'A selected DHCP name, address or MAC has conflicting ownership.')
                selected.append({'network': network, 'scope': scope, 'xml': ET.tostring(item, encoding='unicode')})
    return selected


def _retirement_lease_cache(state, name, guest):
    result = {'rows': 0, 'expired': 0, 'unexpired': 0}
    for text in state.get('dhcp_leases', {}).values():
        for line in text.splitlines():
            match = re.search(r'([0-9a-f]{2}(?::[0-9a-f]{2}){5})\s+ipv4\s+([0-9.]+)/[0-9]+\s+(\S+)', line.lower())
            if not match:
                continue
            mac, address, hostname = match.groups()
            nics = _interfaces(guest) if guest is not None else []
            for nic in nics:
                if address == nic['address']:
                    require(mac == nic['mac'], 'The selected address has a foreign DHCP lease owner.')
            matching = hostname.split('.', 1)[0] == name or any(mac == nic['mac'] for nic in nics)
            if not matching:
                continue
            result['rows'] += 1
            try:
                expired = datetime.strptime(line.strip()[:19], '%Y-%m-%d %H:%M:%S') <= datetime.now()
            except ValueError:
                expired = False
            result['expired' if expired else 'unexpired'] += 1
    return result


def retirement_plan(request, state):
    if request.get('guest_kind') == 'windows':
        return windows_retirement_plan(request, state)
    require(set(request) == {'operation', 'guest_name', 'guest', 'hypervisor', 'transition', 'check_mode'}
            and request['operation'] in {'retire_plan', 'retire_apply', 'retire_rollback'}
            and type(request['check_mode']) is bool, 'Use only an exact generic guest retirement request.')
    name, guest, pin, transition = (request[key] for key in ('guest_name', 'guest', 'hypervisor', 'transition'))
    version = re.fullmatch(r'[a-z][a-z0-9-]*-v([0-9]{2,})', name or '')
    require(version is not None and int(version[1]) > 0 and name.endswith('-v%02d' % int(version[1]))
            and len(name) <= 63 and state['machine_id'] == pin['machine_id']
            and pin['address'] in state['addresses'] and not state['autostart'],
            'Pin one canonical generic guest and the actual nonproduction hypervisor.')
    require(isinstance(transition, dict) and set(transition) == {'previous_policy', 'desired_policy', 'guest'}
            and transition['guest'] == guest, 'Retire only the source-preflighted saved guest provenance.')
    previous, desired = transition['previous_policy'], transition['desired_policy']
    require(previous['bridges'] == desired['bridges'] == pin['isolation_bridges']
            and previous['dns_bridges'] == desired['dns_bridges'] == pin['isolation_dns_bridges']
            and pin['address'] not in previous.get('protected_ipv4', [])
            and pin['public_ip'] not in previous.get('protected_ipv4', [])
            and state['policy'] in (previous, desired),
            'Retain canonical production exclusions, enforced networks and exact live policy.')
    require(_retirement_policy(previous, guest) == desired,
            'Retirement may remove only the selected guest permission entries.')
    paths = {'/opt/vms/' + name + '.disk.qcow2', '/opt/vms/' + name + '.qcow2'}
    require(set(state['disk_states']) == paths, 'Inspect both exact canonical guest disk paths without following links.')
    present = name in state['domains']
    if guest is None:
        require(not present and not any(row['exists'] for row in state['disk_states'].values()) and previous == desired,
                'Missing managed ownership permits only verified physical absence and no policy change.')
    else:
        require(guest.get('verified') is True and guest.get('vm_name') == name and guest.get('disk') in paths
                and guest.get('hypervisor_machine_id') == pin['machine_id']
                and guest.get('machine_id') != pin['machine_id']
                and re.fullmatch(r'[a-f0-9]{32}', guest.get('machine_id', ''))
                and re.fullmatch(r'[a-f0-9]{64}', guest.get('source_image_sha256', '')),
                'Require complete saved generic-clone machine and source provenance.')
        for rules in state['native_rich_rules'].values():
            require(not any(re.search(r'\bsource\s+address="' + re.escape(guest['address']) + r'(?:/32)?"', rule)
                            for rule in rules), 'Selected native host-service rules require explicit cleanup before retirement.')
        alternate = next(path for path in paths if path != guest['disk'])
        require(not state['disk_states'][alternate]['exists'], 'An additional canonical disk requires explicit ownership review.')
        if present:
            disk = state['disk_states'][guest['disk']]
            require(disk['exists'] and disk.get('regular') and not disk.get('symlink') and disk.get('links') == 1,
                    'The exact selected clone must remain a regular exclusively owned disk.')
        else:
            require(not any(row['exists'] for row in state['disk_states'].values()),
                    'A missing domain with remaining storage requires explicit recovery review.')
    networks = {}
    for network, xml in state['networks'].items():
        root = ET.fromstring(xml)
        require(root.findtext('name') == network and root.find('bridge') is not None,
                'Read actual enforced guest network bridges before retirement.')
        networks[network] = root.find('bridge').get('name')
    if guest is not None:
        require(networks.get(guest['network']) == guest['bridge'] and guest['bridge'] in previous['bridges'],
                'The saved guest network must match its actual enforced bridge.')
    mac_owners = {}
    for domain_name, scopes in state['domains'].items():
        for scope, xml in scopes.items():
            root = ET.fromstring(xml)
            require(root.findtext('name') == domain_name, 'Inspect the exact current domain set without name substitution.')
            base.isolated(xml, networks, previous['bridges'])
            for item in root.findall('./devices/interface/mac'):
                mac = item.get('address')
                require(mac not in mac_owners or mac_owners[mac] == domain_name, 'A guest MAC has conflicting domain ownership.')
                mac_owners[mac] = domain_name
            if guest is not None and domain_name != name:
                require(root.findtext('uuid') != guest['uuid']
                        and not any(item.get('file') in paths for item in root.findall('./devices/disk/source'))
                        and not any(item.get('address') == guest['mac'] for item in root.findall('./devices/interface/mac')),
                        'Another domain owns the selected UUID, storage or MAC.')
    if present:
        require(guest is not None and set(state['domains'][name]) == {'persistent', 'current'},
                'A present guest requires both saved and current native ownership.')
        for scope, xml in state['domains'][name].items():
            root = ET.fromstring(xml)
            disks, interfaces = root.findall("./devices/disk[@device='disk']"), root.findall('./devices/interface')
            require(root.findtext('uuid') == guest['uuid'] and len(disks) == len(interfaces) == 1,
                    'The exact saved UUID must own one disk and one guest interface.')
            disk, interface = disks[0].find('source'), interfaces[0]
            require(disk is not None and disk.get('file') == guest['disk']
                    and interface.get('type') == 'network' and interface.find('source') is not None
                    and interface.find('source').get('network') == guest['network']
                    and interface.find('mac') is not None and interface.find('mac').get('address') == guest['mac'],
                    'Native disk, MAC and network differ from saved generic guest ownership.')
            if scope == 'persistent' or root.find('description') is not None:
                description = json.loads(root.findtext('description') or '{}')
                require(description.get('schema_version') == 1 and description.get('deployment_type') == 'generic-recovery'
                        and all(description.get(key) == guest[key] for key in (
                            'vm_name', 'uuid', 'hypervisor_machine_id', 'source_image_sha256', 'host_keys')),
                        'Native generic-clone provenance changed before retirement.')
    if request['operation'] in {'retire_apply', 'retire_rollback'}:
        require(not present and not any(row['exists'] for row in state['disk_states'].values()),
                'Publish retirement only after the selected domain and both canonical disks are absent.')
    reservations = _retirement_dhcp(state, name, guest)
    lease_cache = _retirement_lease_cache(state, name, guest)
    return {'guest_name': name, 'domain_present': present, 'disks_absent': not any(
        row['exists'] for row in state['disk_states'].values()), 'already_absent': guest is None,
        'disk_identity': deepcopy(state['disk_states'][guest['disk']]) if present and guest is not None else None,
        'reservations': reservations, 'dynamic_lease_cache': lease_cache,
        'previous_policy': deepcopy(state['policy']), 'desired_policy': deepcopy(desired),
        'changed': state['policy'] != desired or bool(reservations)}


def windows_retirement_plan(request, state):
    require(set(request) == {'operation', 'guest_name', 'guest', 'guest_kind', 'hypervisor', 'transition', 'check_mode'}
            and request['guest_kind'] == 'windows' and request['operation'] in {'retire_plan', 'retire_apply', 'retire_rollback'}
            and type(request['check_mode']) is bool, 'Use the explicit exact Windows retirement interface.')
    name, guest, pin, transition = (request[key] for key in ('guest_name', 'guest', 'hypervisor', 'transition'))
    version = re.fullmatch(r'[a-z][a-z0-9-]*-v([0-9]{2,})', name or '')
    require(version is not None and len(name) <= 15 and int(version[1]) > 0
            and name.endswith('-v%02d' % int(version[1])) and state['machine_id'] == pin['machine_id']
            and pin['address'] in state['addresses'] and not state['autostart'], 'Retire only one exact Windows guest on its pinned hypervisor.')
    require(isinstance(transition, dict) and set(transition) == {'previous_policy', 'desired_policy', 'guest'}
            and transition['guest'] == guest, 'Use the exact persisted Windows retirement provenance.')
    previous, desired = transition['previous_policy'], transition['desired_policy']
    require(previous['bridges'] == desired['bridges'] == pin['isolation_bridges']
            and previous['dns_bridges'] == desired['dns_bridges'] == pin['isolation_dns_bridges']
            and pin['address'] not in previous.get('protected_ipv4', [])
            and pin['public_ip'] not in previous.get('protected_ipv4', [])
            and state['policy'] in (previous, desired) and _retirement_policy(previous, guest) == desired,
            'Windows retirement may remove only its exact NIC permissions while retaining production protection.')
    disk = '/opt/vms/win-' + name + '-clone.disk.qcow2'
    paths = {disk, '/opt/vms/' + name + '.disk.qcow2', '/opt/vms/' + name + '.qcow2'}
    require(set(state['disk_states']) == paths, 'Inspect the exact Windows clone and both incompatible Linux disk aliases.')
    present = name in state['domains']
    absent = not any(row['exists'] for row in state['disk_states'].values())
    if guest is None:
        require(not present and absent and previous == desired, 'Missing Windows ownership permits only complete physical absence and no policy change.')
        networks = {}
        for network, xml in state['networks'].items():
            root = ET.fromstring(xml)
            require(root.findtext('name') == network and root.find('bridge') is not None, 'Retain every exact native network identity.')
            networks[network] = root.find('bridge').get('name')
        owners = {}
        for domain, scopes in state['domains'].items():
            for xml in scopes.values():
                root = ET.fromstring(xml)
                require(root.findtext('name') == domain, 'Inspect every remaining exact native domain.')
                base.isolated(xml, networks, pin['isolation_bridges'])
                for node in root.findall('./devices/interface/mac'):
                    mac = node.get('address')
                    require(mac not in owners or owners[mac] == domain, 'A remaining guest MAC has conflicting native ownership.')
                    owners[mac] = domain
        reservations = _retirement_dhcp(state, name, None)
        require(not reservations, 'Missing Windows provenance cannot authorize unknown static DHCP cleanup.')
        for scopes in state['network_definitions'].values():
            for xml in scopes.values():
                require(not any((item.text or '').split('.', 1)[0] == name
                                for item in ET.fromstring(xml).findall('./dns/host/hostname')),
                        'Missing Windows provenance cannot authorize unknown static DNS cleanup.')
    else:
        require(guest.get('kind') == 'windows' and guest.get('vm_name') == name, 'Preserve the selected Windows resource kind and exact name.')
        _windows_native(guest, pin, state, present)
        require(present or absent, 'A missing Windows domain with remaining clone storage requires recovery review.')
        for rules in state['native_rich_rules'].values():
            require(not any(re.search(r'\bsource\s+address="' + re.escape(nic['address']) + r'(?:/32)?"', rule)
                            for rule in rules for nic in guest['interfaces']),
                    'Selected Windows host-service grants require explicit cleanup before retirement.')
        reservations = _windows_reservations(state, guest, present)
    if request['operation'] in {'retire_apply', 'retire_rollback'}:
        require(not present and absent, 'Publish Windows retirement only after domain and all canonical clone paths are absent.')
    return {'guest_name': name, 'domain_present': present, 'disks_absent': absent, 'already_absent': guest is None,
            'disk_identity': deepcopy(state['disk_states'][disk]) if present else None,
            'reservations': reservations, 'dynamic_lease_cache': _retirement_lease_cache(state, name, guest),
            'previous_policy': deepcopy(state['policy']), 'desired_policy': deepcopy(desired),
            'changed': state['policy'] != desired or bool(reservations)}


def _network_shape(root):
    return (root.tag, sorted(root.attrib.items()), (root.text or '').strip(),
            tuple(_network_shape(child) for child in root))


def reconcile_retirement(request):
    route = {'hypervisor': request['hypervisor'], 'vm_name': request['guest_name']}
    descriptor = os.open(base.DIRECTORY, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        probe_args = {'allow_absent_guest': True}
        if request.get('guest_kind') == 'windows':
            probe_args['guest_kind'] = 'windows'
        state = base.probe(route, **probe_args)
        change = retirement_plan(request, state)
        base.command([str(base.HELPER), 'check'], json.dumps(state['policy']))
        if request['operation'] == 'retire_plan':
            return dict(change, applied=False, retirement_verified=True)
        target = (request['transition']['previous_policy'] if request['operation'] == 'retire_rollback'
                  else request['transition']['desired_policy'])
        if request['operation'] == 'retire_rollback':
            require(state['policy'] == request['transition']['desired_policy'],
                    'Retirement rollback cannot overwrite a later policy change.')
        spec = importlib.util.spec_from_loader('installed_guest_retirement_isolation',
            SourceFileLoader('installed_guest_retirement_isolation', str(base.HELPER)))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        helper.validate_configuration(target)
        commands = [{'delete': {'table': {'family': 'inet', 'name': helper.TABLE}}}]
        commands += [{'add': {kind: value}} for kind, value in helper.policy(target)]
        base.command(['/usr/sbin/nft', '--check', '-j', '-f', '-'], json.dumps({'nftables': commands}))
        if request['check_mode']:
            return dict(change, applied=False, retirement_verified=True)
        expected_networks = deepcopy(state['network_definitions'])
        removed = 0
        if request['operation'] == 'retire_apply':
            for reservation in change['reservations']:
                network, scope = reservation['network'], reservation['scope']
                root = ET.fromstring(expected_networks[network][scope])
                kind = reservation.get('kind', 'ip-dhcp-host')
                require(kind in {'ip-dhcp-host', 'dns-host'}, 'Remove only exact native guest DHCP or DNS records.')
                parent_path = './ip/dhcp' if kind == 'ip-dhcp-host' else './dns'
                matching = [item for item in root.findall(parent_path + '/host')
                            if ET.tostring(item, encoding='unicode') == reservation['xml']]
                require(len(matching) == 1, 'Remove only one exact selected static DHCP reservation.')
                for parent in root.findall(parent_path):
                    if matching[0] in list(parent):
                        parent.remove(matching[0])
                expected_networks[network][scope] = ET.tostring(root, encoding='unicode')
                flag = '--config' if scope == 'persistent' else '--live'
                base.command(['virsh', '-c', 'qemu:///system', 'net-update', network,
                              'delete', kind, reservation['xml'], flag])
                removed += 1
            observed = base.probe(route, **probe_args)
            retirement_plan(request, observed)
            require(set(observed['domains']) == set(state['domains'])
                    and set(observed['network_definitions']) == set(expected_networks),
                    'Other domain or network identities changed during exact DHCP cleanup.')
            for network, scopes in expected_networks.items():
                require(set(observed['network_definitions'][network]) == set(scopes)
                        and all(_network_shape(ET.fromstring(observed['network_definitions'][network][scope]))
                                == _network_shape(ET.fromstring(xml)) for scope, xml in scopes.items()),
                        'DHCP cleanup must preserve every unrelated network field and reservation.')
            require(not _retirement_dhcp(observed, request['guest_name'], request['guest']),
                    'A selected static DHCP reservation remains after exact cleanup.')
        original = base.CONFIG.read_bytes()
        try:
            if state['policy'] != target:
                base.save(json.dumps(target).encode())
                base.command([str(base.HELPER), 'apply'])
            base.command([str(base.HELPER), 'check'], json.dumps(target))
        except Exception:
            base.save(original)
            base.command([str(base.HELPER), 'apply'])
            base.command([str(base.HELPER), 'check'], json.dumps(state['policy']))
            raise
        return dict(change, applied=True, retirement_verified=True, dhcp_reservations_removed=removed,
                    desired_policy=deepcopy(target), changed=state['policy'] != target or bool(removed))
    finally:
        os.close(descriptor)


if __name__ == '__main__':
    try:
        print(json.dumps(reconcile(json.load(sys.stdin))))
    except Exception:
        print('Protected guest recovery-isolation release failed.', file=sys.stderr)
        raise SystemExit(1)
