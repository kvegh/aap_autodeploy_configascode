"""Release one verified Linux guest from recovery quarantine, retaining production denial.

Runs only on the pinned recovery hypervisor. The sibling management helper owns
the existing protected-file, libvirt readback and atomic-write primitives.
"""

from copy import deepcopy
import fcntl
import importlib.util
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


def plan(request, state):
    require({'operation', 'guest', 'hypervisor', 'transition', 'check_mode'} <= set(request)
            and set(request) <= {'operation', 'guest', 'hypervisor', 'transition', 'check_mode', 'mode'}
            and request['operation'] in {'apply', 'rollback'}
            and type(request['check_mode']) is bool,
            'Choose one exact verified recovery guest transition.')
    mode = request.get('mode', 'release')
    require(mode in {'release', 'bootstrap_https'}, 'Choose full release or bounded guest bootstrap HTTPS.')
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
    field = 'released_clients' if mode == 'release' else 'https_clients'
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


def reconcile(request):
    pin, guest = request['hypervisor'], request['guest']
    route = {'hypervisor': pin, 'vm_name': guest['vm_name']}
    descriptor = os.open(base.DIRECTORY, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
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


if __name__ == '__main__':
    try:
        print(json.dumps(reconcile(json.load(sys.stdin))))
    except Exception:
        print('Protected guest recovery-isolation release failed.', file=sys.stderr)
        raise SystemExit(1)
