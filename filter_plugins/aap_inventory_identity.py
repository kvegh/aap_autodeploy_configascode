"""Read the physical AAP identity already recorded on its inventory entry."""

from collections.abc import Mapping
from ipaddress import IPv4Address
from urllib.parse import urlsplit
import re

from ansible.errors import AnsibleFilterError


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
    number = host.get('aap_instance_number')
    # Controller may serialize this scalar as text in a nonnative CaC import.
    # Normalize only canonical positive ASCII decimals; never coerce bools/floats.
    if isinstance(number, str) and len(number) <= 63 and re.fullmatch(r'[1-9][0-9]*', number):
        number = int(number)
    if (match is None or type(number) is not int or number <= 0 or number != int(match[2])
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
                 and all(primary.get(key) == resource.get(key) for key in (
                     'vm_name', 'uuid', 'disk', 'address', 'network', 'bridge', 'mac', 'hypervisor_machine_id', 'verified')))
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise AnsibleFilterError('The selected AAP inventory entry differs from its registered VM route.')
    return True


class FilterModule:
    def filters(self):
        return {'aap_inventory_instance_name': inventory_instance_name,
                'aap_inventory_route_matches': inventory_route_matches}
