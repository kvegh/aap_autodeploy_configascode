"""Reconcile one already-approved AAP guest's access using existing host tools."""
from copy import deepcopy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

DIRECTORY = Path('/etc/hactarconfig')
CONFIG = DIRECTORY / 'replacement-isolation.json'
HELPER = Path('/usr/local/sbin/hactar-recovery-isolation')


def require(condition, message):
    if not condition:
        raise ValueError(message)


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


def desired_policy(route, primary, declared):
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
    require(identity in declared.get('https_clients', []),
            'Management access requires this exact already-approved HTTPS client.')
    client = dict(identity, destinations=[pin['address']], ports=[pin['port']])
    desired = deepcopy(declared)
    local = desired.setdefault('guest_host_clients', [])
    matching = [item for item in local if item['ipv4'] == identity['ipv4'] or item['mac'] == identity['mac']]
    require(not matching or matching == [client],
            'An existing primary local permission needs explicit review before expansion.')
    if not matching:
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
    require(primary['network'] in networks and networks[primary['network']] == primary['bridge']
            and primary['bridge'] in declared['bridges'], 'Primary network must use its recorded enforced bridge.')
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
    for xml in probe['domains'][route['vm_name']].values():
        root = ET.fromstring(xml)
        disks, interfaces = root.findall("./devices/disk[@device='disk']"), root.findall('./devices/interface')
        require(root.findtext('uuid') == primary['uuid'] and len(disks) == len(interfaces) == 1,
                'Primary UUID and single disk/interface must match verified ownership.')
        disk, interface = disks[0].find('source'), interfaces[0]
        require(disk is not None and disk.get('file') == primary['disk']
                and primary['disk'] == '/opt/vms/' + route['vm_name'] + '.disk.qcow2'
                and interface.get('type') == 'network' and interface.find('source') is not None
                and interface.find('source').get('network') == primary['network']
                and interface.find('mac') is not None and interface.find('mac').get('address') == primary['mac'],
                'Primary storage, MAC and network must match actual libvirt ownership.')
    leases = re.findall(r'([0-9a-f]{2}(?::[0-9a-f]{2}){5})\s+ipv4\s+([0-9.]+)/[0-9]+', probe['leases'].lower())
    require(set(leases) == {(primary['mac'], primary['address'])}, 'Require the exact selected guest DHCP identity.')
    desired = desired_policy(route, primary, declared)
    client = next(item for item in desired['guest_host_clients'] if item['ipv4'] == primary['address'])
    actual = probe['policy']
    require(actual == declared or actual == desired, 'Live policy must equal declared state or this exact derived management grant.')
    rule = ('rule family="ipv4" priority="0" source address="%s/32" destination address="%s/32" '
            'port port="%s" protocol="tcp" accept' % (primary['address'], pin['address'], pin['port']))
    return {'previous_policy': deepcopy(actual), 'desired_policy': desired, 'client': client,
            'rich_rule': rule, 'changed': actual != desired}


def probe(route):
    require(os.geteuid() == 0 and DIRECTORY.is_dir() and not DIRECTORY.is_symlink()
            and DIRECTORY.stat().st_uid == 0 and DIRECTORY.stat().st_mode & 0o777 == 0o700
            and CONFIG.is_file() and not CONFIG.is_symlink() and CONFIG.stat().st_uid == 0
            and CONFIG.stat().st_mode & 0o777 == 0o600, 'Require existing protected root-owned isolation configuration.')
    data = {'machine_id': Path('/etc/machine-id').read_text().strip(), 'policy': json.loads(CONFIG.read_text())}
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
    data['autostart'] = command(['virsh', '-c', 'qemu:///system', 'list', '--all', '--autostart', '--name']).stdout.split()
    data['leases'] = command(['virsh', '-c', 'qemu:///system', 'domifaddr', route['vm_name'], '--source', 'lease']).stdout
    selected = ET.fromstring(data['domains'][route['vm_name']]['current'])
    network = selected.find('./devices/interface/source').get('network')
    bridge = ET.fromstring(data['networks'][network]).find('bridge').get('name')
    data['zone'] = command(['firewall-cmd', '--get-zone-of-interface=' + bridge]).stdout.strip()
    return data


def save(content):
    descriptor, name = tempfile.mkstemp(prefix='.management-policy-', dir=str(DIRECTORY))
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o600)
        os.replace(name, CONFIG)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def reconcile(expected):
    require(set(expected) == {'route', 'primary', 'declared_policy', 'check_mode'}
            and type(expected['check_mode']) is bool, 'Use only the fixed verified management request.')
    lock = os.open(DIRECTORY, os.O_RDONLY | os.O_DIRECTORY)
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                require(time.monotonic() < deadline, 'Another hypervisor policy transaction is active; retry safely.')
                time.sleep(0.1)
        current = probe(expected['route'])
        change = plan(expected, current)
        require(current['zone'] == 'libvirt', 'Use only the existing libvirt zone for the selected bridge.')
        command([str(HELPER), 'check'], json.dumps(current['policy']))
        spec = importlib.util.spec_from_file_location('installed_recovery_isolation', HELPER)
        # The installed helper has no .py suffix.
        if spec is None:
            from importlib.machinery import SourceFileLoader
            spec = importlib.util.spec_from_loader('installed_recovery_isolation', SourceFileLoader('installed_recovery_isolation', str(HELPER)))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        helper.validate_configuration(change['desired_policy'])
        commands = [{'delete': {'table': {'family': 'inet', 'name': helper.TABLE}}}]
        commands += [{'add': {kind: value}} for kind, value in helper.policy(change['desired_policy'])]
        command(['/usr/sbin/nft', '--check', '-j', '-f', '-'], json.dumps({'nftables': commands}))
        states = {}
        for permanent in (False, True):
            prefix = ['firewall-cmd'] + (['--permanent'] if permanent else []) + ['--zone=libvirt']
            states[permanent] = command(prefix + ['--query-rich-rule=' + change['rich_rule']], allowed=(0, 1)).returncode == 0
        changed = change['changed'] or not all(states.values())
        if expected['check_mode']:
            return dict(change, changed=changed, applied=False)
        original = CONFIG.read_bytes()
        added = []
        try:
            for permanent, present in states.items():
                prefix = ['firewall-cmd'] + (['--permanent'] if permanent else []) + ['--zone=libvirt']
                if not present:
                    command(prefix + ['--add-rich-rule=' + change['rich_rule']])
                    added.append(prefix)
                command(prefix + ['--query-rich-rule=' + change['rich_rule']])
            command([str(HELPER), 'check'], json.dumps(current['policy']))
            if change['changed']:
                save(json.dumps(change['desired_policy']).encode())
                command([str(HELPER), 'apply'])
            command([str(HELPER), 'check'], json.dumps(change['desired_policy']))
        except Exception:
            save(original)
            command([str(HELPER), 'apply'])
            for prefix in reversed(added):
                command(prefix + ['--remove-rich-rule=' + change['rich_rule']])
            command([str(HELPER), 'check'], json.dumps(current['policy']))
            raise
        return dict(change, changed=changed, applied=True)
    finally:
        os.close(lock)


if __name__ == '__main__':
    try:
        print(json.dumps(reconcile(json.load(sys.stdin))))
    except Exception:
        print('Protected hypervisor management reconciliation failed.', file=sys.stderr)
        raise SystemExit(1)
