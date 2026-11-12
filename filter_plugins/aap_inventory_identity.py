"""Read the physical AAP identity already recorded on its inventory entry."""

from collections.abc import Mapping
from ipaddress import IPv4Address
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import urlsplit
import re

from ansible.errors import AnsibleFilterError

_spec = spec_from_file_location('inventory_primary_interfaces', Path(__file__).resolve().parents[1] / 'src/aap_hypervisor_access.py')
_ownership = module_from_spec(_spec)
_spec.loader.exec_module(_ownership)


def inventory_counter(value):
    """Normalize only the canonical positive decimal scalar Controller may serialize."""
    if isinstance(value, str) and len(value) <= 63 and re.fullmatch(r'[1-9][0-9]*', value):
        value = int(value)
    if (not isinstance(value, int) or isinstance(value, bool)) or value <= 0:
        raise AnsibleFilterError('Use a positive inventory counter or canonical ASCII decimal text.')
    return value


def inventory_instance_name(selected, host=None):
    """Keep renamed display entries separate from immutable VM/token/registry keys."""
    if not isinstance(selected, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', selected):
        raise AnsibleFilterError('Select an explicit AAP inventory entry or registered instance.')
    if host is None:
        return selected
    if not isinstance(host, Mapping):
        raise AnsibleFilterError('Read AAP identity from its selected inventory entry.')
    resource = host.get('vm_resource')
    if resource is None:
        # Existing ordinary entries and registry-only stage inventories retain
        # their current keys. Never guess a physical name from an alias.
        return selected
    if not isinstance(resource, Mapping):
        raise AnsibleFilterError('Require the existing verified AAP ownership record.')
    physical = resource.get('vm_name')
    match = re.fullmatch(r'(aap[0-9]+)-test-([0-9]+)', physical if isinstance(physical, str) else '')
    # Controller may serialize this scalar as text in a nonnative CaC import.
    # Normalize only canonical positive ASCII decimals; never coerce bools/floats.
    number = inventory_counter(host.get('aap_instance_number'))
    if (match is None or number != int(match[2])
            or resource.get('verified') is not True
            or selected not in (physical, match[1] + '-v%02d' % number)
            or resource.get('address') != host.get('ansible_host')
            or resource.get('address') != host.get('vm_ip', resource.get('address'))
            or not isinstance(resource.get('uuid'), str)
            or not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', resource['uuid'])
            or resource['uuid'] == '00000000-0000-0000-0000-000000000000'
            or resource['uuid'] != host.get('vm_uuid')
            or resource.get('disk') != '/opt/vms/' + physical + '.disk.qcow2'):
        raise AnsibleFilterError('The selected AAP entry conflicts with its verified physical identity.')
    try:
        _ownership.primary_interfaces(resource)
        address = resource.get('address')
        if not isinstance(address, str) or str(IPv4Address(address)) != address:
            raise ValueError
    except ValueError:
        raise AnsibleFilterError('The selected AAP entry has no normalized physical address.') from None
    return physical


def inventory_route_matches(selected, host, route, resources):
    """A renamed inventory entry must still describe the exact registered VM."""
    if not isinstance(host, Mapping) or host.get('vm_resource') is None:
        return True
    physical = inventory_instance_name(selected, host)
    resource = host['vm_resource']
    primary = resources.get('aap') if isinstance(resources, Mapping) else None
    try:
        url = urlsplit(route['aap_hostname'])
        valid = (route['vm_name'] == physical and route['vm_ip'] == resource['address']
                 and route['hypervisor']['machine_id'] == resource['hypervisor_machine_id']
                 and url.scheme == 'https' and url.hostname == host['ansible_fqdn']
                 and not url.username and not url.password and url.port in (None, 443)
                 and not url.query and not url.fragment and url.path in ('', '/')
                 and route['guest_host_keys'] == host['host_keys']
                 and isinstance(primary, Mapping)
                 and primary.get('vm_name', physical) == physical
                 and all(primary.get(key) == resource.get(key) for key in (
                     'uuid', 'disk', 'address', 'network', 'bridge', 'mac', 'hypervisor_machine_id', 'verified',
                     'supplemental_interfaces')))
        if valid:
            _ownership.primary_interfaces(dict(primary), route['hypervisor'])
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise AnsibleFilterError('The selected AAP inventory entry differs from its registered VM route.')
    return True


class FilterModule:
    def filters(self):
        return {'aap_inventory_instance_name': inventory_instance_name,
                'aap_inventory_route_matches': inventory_route_matches}
