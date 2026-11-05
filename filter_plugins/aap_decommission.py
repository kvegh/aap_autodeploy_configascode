"""Only retire resources belonging to an explicitly selected test reservation."""
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from ipaddress import IPv4Address
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from ansible.errors import AnsibleFilterError

_route_spec = spec_from_file_location("decommission_route", Path(__file__).with_name("aap_instance_route.py"))
_routing = module_from_spec(_route_spec)
_route_spec.loader.exec_module(_routing)
_ownership_spec = spec_from_file_location('decommission_interface_ownership', Path(__file__).resolve().parents[1] / 'src/aap_hypervisor_access.py')
_ownership = module_from_spec(_ownership_spec)
_ownership_spec.loader.exec_module(_ownership)


def resources(route, zone, disk_directory, related=None):
    name = route.get("vm_name", "")
    match = re.fullmatch(r"aap[0-9]+-test-([0-9]+)", name)
    hostname = route.get("aap_hostname", "").removeprefix("https://")
    if not match or not hostname.endswith("." + zone) or disk_directory != "/opt/vms":
        raise AnsibleFilterError("Refuse teardown outside a registered test VM and its public zone.")
    dns = hostname[:-(len(zone) + 1)]
    if not re.fullmatch(r"[a-z0-9.-]+", dns):
        raise AnsibleFilterError("Require a bounded instance DNS name.")
    version = "v%02d" % int(match[1])
    website = "redhat." + version
    related = related or {}
    domains = [{"name": name, "disk": disk_directory + "/" + name + ".disk.qcow2", "primary": True}]
    for role in ("zabbix", "testserver1", "tra"):
        guest = role + "-" + version
        metadata = related.get(role, {})
        disk = metadata.get("disk", disk_directory + "/" + guest + ".disk.qcow2")
        if not re.fullmatch(re.escape(disk_directory + "/" + guest) + r"(?:\.disk)?\.qcow2", disk):
            raise AnsibleFilterError("Related guest disks must belong to the same deployment version.")
        domains.append({"name": guest, "disk": disk, "uuid": metadata.get("uuid"), "primary": False})
    return {"name": name, "disk": disk_directory + "/" + name + ".disk.qcow2",
            "version": version, "domains": domains,
            "dns": [dns, website, "zabbix." + version],
            "certificates": [hostname, website + "." + zone, "zabbix." + version + "." + zone],
            "nginx": ["/etc/nginx/conf.d/" + name + ".conf",
                      "/etc/nginx/conf.d/demo-website-" + version + ".conf",
                      "/etc/nginx/conf.d/demo-zabbix-" + version + ".conf"],
            "website_paths": ["/var/www/redhat-" + version,
                "/var/cache/nginx/demo-website-" + version, "/opt/demo-web-src-" + version,
                "/etc/nginx/demo-website-" + version + "-rate-limit.conf",
                "/etc/nginx/demo-zabbix-" + version + ".htpasswd"],
            "authority": "/etc/nginx/aap-upstreams/" + name + ".pem"}


def domain_matches(xml, expected):
    try:
        root = ET.fromstring(xml)
        disks = root.findall("./devices/disk[@device='disk']")
        sources = [disk.find("source") for disk in disks]
        return (root.findtext("name") == expected["name"] and len(disks) == 1
                and sources[0] is not None and sources[0].get("file") == expected["disk"]
                and set(sources[0].attrib) <= {"file", "index"}
                and (expected.get("primary", True) or
                     (expected.get("uuid") and root.findtext("uuid") == expected["uuid"])))
    except ET.ParseError:
        return False


def dns_plan(records, retirement, public_ip, zone):
    """Find all matching version labels, including unknown orphaned role names."""
    if not isinstance(records, list):
        raise AnsibleFilterError("Read the complete DNS record list before retirement.")
    version = retirement["version"]
    exact = set(retirement["dns"])
    chosen = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("name"), str):
            raise AnsibleFilterError("The provider returned an incomplete DNS record list.")
        name = record["name"].lower().removesuffix("." + zone)
        if name not in exact and version not in name.split("."):
            continue
        if not re.fullmatch(r"[a-z0-9_*.-]+", name) or ".." in name:
            raise AnsibleFilterError("Refuse an invalid selected DNS record name.")
        kind, data = record.get("type"), record.get("data")
        if kind == "A":
            valid = data == public_ip
        elif kind == "CNAME":
            target = str(data).lower().rstrip(".")
            valid = target.endswith("." + zone) and (version in target.split(".") or
                    target.removesuffix("." + zone) in exact)
        else:
            valid = kind in ("TXT", "CAA")
        if not valid:
            raise AnsibleFilterError("A selected version DNS record points elsewhere or needs explicit ownership review.")
        chosen.setdefault((kind, name), []).append(record)
    return [{"type": kind, "name": name, "records": values} for (kind, name), values in sorted(chosen.items())]


def guest_networks(xmls, related):
    """Resolve only explicit libvirt network names from selected ownership evidence."""
    try:
        if not isinstance(xmls, dict) or not isinstance(related, dict):
            raise ValueError
        names = {interface.find("source").get("network")
                 for xml in xmls.values() for interface in ET.fromstring(xml).findall("./devices/interface")
                 if interface.get("type") == "network" and interface.find("source") is not None}
        names.update(record["network"] for record in related.values()
                     if isinstance(record, dict) and record.get("network"))
        names.update(nic['network'] for record in related.values() if isinstance(record, dict)
                     for nic in _ownership.primary_interfaces(record)[1:])
        if any(not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", name)
               for name in names):
            raise ValueError
        return sorted(names)
    except (ValueError, TypeError, ET.ParseError):
        raise AnsibleFilterError("Resolve only the selected guests' recorded libvirt networks.") from None


def guest_access_plan(previous, retirement, route, related, xmls, networks, actual_policy=None, source_proof=None,
                      persistent_xmls=None):
    """Remove only proven selected VM identities; never infer ownership from a name/IP alone."""
    try:
        if not all(isinstance(value, dict) for value in (previous, retirement, route, related, xmls, networks)):
            raise ValueError
        pin = _routing.hypervisor_pin(route["hypervisor"])
        match = re.fullmatch(r"aap[0-9]+-test-([0-9]+)", route["vm_name"])
        if not match or int(match[1]) <= 0:
            raise ValueError
        version = "v%02d" % int(match[1])
        expected_names = {route["vm_name"], *(role + "-" + version for role in ("zabbix", "testserver1", "tra"))}
        if (retirement.get("name") != route["vm_name"] or retirement.get("version") != version
                or not isinstance(retirement.get("domains"), list) or len(retirement["domains"]) != 4
                or {domain["name"] for domain in retirement["domains"]} != expected_names
                or set(xmls) - expected_names):
            raise ValueError
        for domain in retirement["domains"]:
            primary = domain["name"] == route["vm_name"]
            suffix = r"\.disk\.qcow2" if primary else r"(?:\.disk)?\.qcow2"
            if (domain.get("primary") is not primary or not re.fullmatch(
                    re.escape("/opt/vms/" + domain["name"]) + suffix, domain["disk"])):
                raise ValueError

        def validate_policy(policy):
            if _routing.isolation_policy(pin, policy.get("https_clients", []),
                    policy.get("protected_ipv4"), policy.get("guest_host_clients", []), policy.get("released_clients", []), policy.get("http_clients", [])) != policy:
                raise ValueError

        validate_policy(previous)
        old_clients = previous.get("guest_host_clients", []) + previous.get("https_clients", []) + previous.get("released_clients", []) + previous.get("http_clients", [])

        def ipv4(address):
            parsed = IPv4Address(address)
            if (not isinstance(address, str) or str(parsed) != address or parsed.is_unspecified
                    or parsed.is_multicast or parsed.is_loopback or parsed.is_reserved):
                raise ValueError
            return address

        def mac_address(value):
            if (not isinstance(value, str) or not re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", value)
                    or int(value[:2], 16) & 1 or value == "00:00:00:00:00:00"):
                raise ValueError
            return value

        def bridge_for(network):
            definitions = networks[network]
            xml = definitions.get('current', definitions.get('persistent')) if isinstance(definitions, dict) else definitions
            root = ET.fromstring(xml)
            bridge = root.find("bridge")
            if root.findtext("name") != network or bridge is None or bridge.get("name") not in previous["bridges"]:
                raise ValueError
            return bridge.get("name")

        identities = []
        live_primary_identity = None
        for domain in retirement["domains"]:
            name = domain["name"]
            primary = domain.get("primary", False)
            role = "aap" if primary else name.rsplit("-", 1)[0]
            metadata = related.get(role, {})
            if not isinstance(metadata, dict):
                raise ValueError
            if role != 'aap' and 'supplemental_interfaces' in metadata:
                raise ValueError
            if metadata and (not isinstance(metadata.get("uuid"), str)
                    or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", metadata["uuid"])
                    or metadata.get("disk") != domain["disk"]):
                raise ValueError
            address = route["vm_ip"] if primary else metadata.get("address")
            if metadata and not primary and not address:
                raise ValueError
            if metadata.get("address") and metadata["address"] != address:
                raise ValueError
            if metadata.get("disk", domain["disk"]) != domain["disk"] or metadata.get("verified", True) is not True:
                raise ValueError
            if metadata.get("hypervisor_machine_id", pin["machine_id"]) != pin["machine_id"]:
                raise ValueError
            recorded_nics = _ownership.primary_interfaces(metadata, pin)
            if name in xmls:
                xml = xmls[name]
                if not domain_matches(xml, domain):
                    raise ValueError
                root = ET.fromstring(xml)
                if metadata.get("uuid") and metadata["uuid"] != root.findtext("uuid"):
                    raise ValueError
                interfaces = root.findall("./devices/interface")
                if len(recorded_nics) > 1:
                    if not isinstance(persistent_xmls, dict) or name not in persistent_xmls:
                        raise ValueError
                    persistent = ET.fromstring(persistent_xmls[name])
                    if (not domain_matches(persistent_xmls[name], domain)
                            or persistent.findtext('uuid') != metadata['uuid']
                            or {(node.get('type'), node.find('source').get('network'), node.find('mac').get('address'))
                                for node in persistent.findall('./devices/interface')}
                            != {(node.get('type'), node.find('source').get('network'), node.find('mac').get('address'))
                                for node in interfaces}
                            or len(persistent.findall('./devices/interface')) != len(recorded_nics)):
                        raise ValueError
                    for definition in (root, persistent):
                        for record in recorded_nics[1:]:
                            matches = [node for node in definition.findall('./devices/interface')
                                       if node.find('mac') is not None and node.find('mac').get('address') == record['mac']]
                            if len(matches) != 1 or not _ownership.supplemental_native_matches(matches[0], record):
                                raise ValueError
                if len(interfaces) != len(recorded_nics):
                    raise ValueError
                live_nics = []
                for interface in interfaces:
                    source, mac = interface.find('source'), interface.find('mac')
                    if source is None or mac is None:
                        raise ValueError
                    network = source.get('network') if interface.get('type') == 'network' else None
                    bridge = bridge_for(network) if network else source.get('bridge') if interface.get('type') == 'bridge' else None
                    live_nics.append({'mac': mac_address(mac.get('address')), 'network': network, 'bridge': bridge})
                if len(recorded_nics) > 1:
                    if {(nic['mac'], nic['network'], nic['bridge']) for nic in recorded_nics} != {
                            (nic['mac'], nic['network'], nic['bridge']) for nic in live_nics}:
                        raise ValueError
                else:
                    actual = live_nics[0]
                    if any(metadata.get(key, actual[key]) != actual[key] for key in actual):
                        raise ValueError
                    recorded_nics = [dict(metadata, **actual, address=address)]
            else:
                # Missing VMs need their original full identity, not DHCP or a policy-derived MAC.
                candidate = any((address and client["ipv4"] == address)
                                or (metadata.get("mac") and client["mac"] == metadata["mac"])
                                for client in old_clients)
                complete = (metadata.get("uuid") and metadata.get("disk") == domain["disk"]
                            and address and metadata.get("mac")
                            and (metadata.get("bridge") or metadata.get("network")))
                if not complete:
                    if candidate or (metadata and previous.get("guest_host_clients")):
                        raise ValueError
                    continue
                if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", metadata["uuid"]):
                    raise ValueError
            for nic in recorded_nics:
                actual_mac = mac_address(nic['mac'])
                bridge = bridge_for(nic['network']) if nic.get('network') else nic['bridge']
                if nic.get('bridge', bridge) != bridge or bridge not in previous['bridges']:
                    raise ValueError
                nic_address = nic.get('address', address)
                if not nic_address:
                    if any(client['mac'] == actual_mac for client in old_clients):
                        raise ValueError
                    continue
                identity = {'bridge': bridge, 'ipv4': ipv4(nic_address), 'mac': actual_mac}
                for existing in identities:
                    if identity['ipv4'] == existing['ipv4'] or identity['mac'] == existing['mac']:
                        raise ValueError
                for client in old_clients:
                    if ((client['ipv4'] == identity['ipv4'] or client['mac'] == identity['mac'])
                            and any(client[key] != identity[key] for key in identity)):
                        raise ValueError
                identities.append(identity)
                if primary and not metadata:
                    if not _ownership.uuid(root.findtext('uuid')):
                        raise ValueError
                    live_primary_identity = {'vm_name': name, 'uuid': root.findtext('uuid'), 'disk': domain['disk'],
                                             'network': nic.get('network'), 'bridge': bridge,
                                             'mac': actual_mac, 'address': identity['ipv4']}

        selected = {tuple(identity[key] for key in ("bridge", "ipv4", "mac")) for identity in identities}
        desired = deepcopy(previous)
        for field in ("guest_host_clients", "https_clients", "released_clients", "http_clients"):
            if field not in desired:
                continue
            retained = [client for client in desired[field]
                        if tuple(client[key] for key in ("bridge", "ipv4", "mac")) not in selected]
            if retained == desired[field]:
                continue
            if retained:
                desired[field] = retained
            else:
                desired.pop(field)
                if not desired.get("https_clients") and not desired.get("released_clients") and not desired.get("http_clients"):
                    desired.pop("protected_ipv4", None)
        validate_policy(desired)
        if source_proof is not None:
            if (not isinstance(source_proof, dict) or source_proof.get("instance_name") != route["vm_name"]
                    or source_proof.get("hypervisor_machine_id") != pin["machine_id"]
                    or not isinstance(source_proof.get("missing_roles"), list)
                    or set(source_proof["missing_roles"]) - {"zabbix", "testserver1", "tra"}
                    or not isinstance(source_proof.get("policy_owners"), list)):
                raise ValueError
            owners = source_proof["policy_owners"]
            for owner in owners:
                if (not isinstance(owner, dict) or set(owner) != {"bridge", "ipv4", "mac"}
                        or owner["bridge"] not in previous["bridges"]):
                    raise ValueError
                ipv4(owner["ipv4"])
                mac_address(owner["mac"])
            if source_proof["missing_roles"]:
                owner_keys = {tuple(owner[key] for key in ("bridge", "ipv4", "mac")) for owner in owners}
                if any(tuple(client[key] for key in ("bridge", "ipv4", "mac")) not in owner_keys
                       for client in desired.get("guest_host_clients", []) + desired.get("https_clients", []) + desired.get("released_clients", []) + desired.get("http_clients", [])):
                    raise ValueError
        actual = previous if actual_policy is None else actual_policy
        validate_policy(actual)
        if actual != previous and actual != desired:
            raise ValueError

        def rules(policy):
            return {'rule family="ipv4" priority="0" source address="%s/32" '
                    'destination address="%s/32" port port="%s" protocol="tcp" accept'
                    % (client["ipv4"], destination, port)
                    for client in policy.get("guest_host_clients", [])
                    for destination in client["destinations"] for port in client["ports"]}

        return {"previous_policy": deepcopy(previous), "desired_policy": desired,
                "identities": identities, "changed": desired != previous,
                "actual_policy": deepcopy(actual), "requires_local_update": actual != desired,
                'live_primary_identity': live_primary_identity,
                "rich_rules_to_remove": sorted(rules(previous) - rules(desired))}
    except (ValueError, TypeError, KeyError, AttributeError, ET.ParseError, AnsibleFilterError):
        raise AnsibleFilterError("Guest permission retirement requires exact recorded and live VM ownership; no cleanup was planned.") from None


def network_shape(xml):
    root = ET.fromstring(xml)
    root.attrib.pop('connections', None)
    def shape(node):
        return (node.tag, tuple(sorted(node.attrib.items())), (node.text or '').strip(), tuple(shape(child) for child in node))
    return shape(root)


def reservation_plan(networks, route, related, live_xmls=None, ownership_plan=None):
    """Remove exact owned libvirt host records, preserving every unrelated XML field."""
    try:
        pin = _routing.hypervisor_pin(route['hypervisor'])
        require_names = {route['vm_name'], *(role + '-v%02d' % int(route['vm_name'].rsplit('-', 1)[1])
                                          for role in ('zabbix', 'testserver1', 'tra'))}
        owned = []
        # A live legacy primary already accepted by guest_access_plan has native
        # ownership even when it predates saved AAP resource metadata. Reuse that
        # exact proof; never manufacture a saved verified resource for it.
        if not related.get('aap') and isinstance(live_xmls, dict) and route['vm_name'] in live_xmls:
            if not isinstance(ownership_plan, dict):
                raise ValueError
            expected = {'name': route['vm_name'], 'disk': '/opt/vms/' + route['vm_name'] + '.disk.qcow2', 'primary': True}
            xml = live_xmls[route['vm_name']]
            root = ET.fromstring(xml)
            interfaces = root.findall('./devices/interface')
            if not domain_matches(xml, expected) or not _ownership.uuid(root.findtext('uuid')) or len(interfaces) != 1:
                raise ValueError
            interface = interfaces[0]
            source, mac = interface.find('source'), interface.find('mac')
            if source is None or mac is None or interface.get('type') not in ('network', 'bridge'):
                raise ValueError
            network = source.get('network') if interface.get('type') == 'network' else None
            if network:
                definitions = networks[network]
                bridge = ET.fromstring(definitions.get('current', definitions.get('persistent'))).find('bridge').get('name')
            else:
                bridge = source.get('bridge')
            actual = {'vm_name': route['vm_name'], 'uuid': root.findtext('uuid'), 'disk': expected['disk'],
                      'network': network, 'bridge': bridge, 'mac': mac.get('address'), 'address': route['vm_ip']}
            identity = {'bridge': bridge, 'mac': actual['mac'], 'ipv4': actual['address']}
            if (actual != ownership_plan.get('live_primary_identity')
                    or identity not in ownership_plan.get('identities', []) or bridge not in pin['isolation_bridges']):
                raise ValueError
            owned.append((route['vm_name'], actual))
        for role, record in related.items():
            if role not in ('aap', 'zabbix', 'testserver1', 'tra'):
                raise ValueError
            if not record:
                continue
            if role != 'aap' and 'supplemental_interfaces' in record:
                raise ValueError
            name = route['vm_name'] if role == 'aap' else role + '-v%02d' % int(route['vm_name'].rsplit('-', 1)[1])
            if (record.get('verified') is not True or not _ownership.uuid(record.get('uuid'))
                    or not re.fullmatch(re.escape('/opt/vms/' + name) + r'(?:\.disk)?\.qcow2', record.get('disk', ''))
                    or record.get('hypervisor_machine_id', pin['machine_id']) != pin['machine_id']):
                raise ValueError
            for nic in _ownership.primary_interfaces(record, pin):
                nic = dict(nic)
                if not nic.get('bridge') and nic.get('network') in networks:
                    definitions = networks[nic['network']]
                    definition = ET.fromstring(definitions.get('persistent', definitions.get('current')))
                    nic['bridge'] = definition.find('bridge').get('name')
                if not all(nic.get(key) for key in ('mac', 'address', 'network', 'bridge')):
                    raise ValueError
                if nic['bridge'] not in pin['isolation_bridges']:
                    raise ValueError
                owned.append((name, nic))
        result = {'before': deepcopy(networks), 'after': deepcopy(networks), 'reservations': []}
        for network, scopes in networks.items():
            if not isinstance(scopes, dict) or not {'persistent'} <= set(scopes) <= {'persistent', 'current'}:
                raise ValueError
            for scope, xml in scopes.items():
                root = ET.fromstring(xml)
                if root.findtext('name') != network or root.find('bridge') is None:
                    raise ValueError
                bridge = root.find('bridge').get('name')
                for parent_path, kind in (('./ip/dhcp', 'ip-dhcp-host'), ('./dns', 'dns-host')):
                    for parent in root.findall(parent_path):
                        for node in list(parent.findall('host')):
                            names = ([node.get('name')] if kind == 'ip-dhcp-host' else [child.text for child in node.findall('hostname')])
                            names = [name for name in names if name]
                            matching = [(name, nic) for name, nic in owned
                                        if node.get('ip') == nic['address'] or node.get('mac', '').lower() == nic['mac']]
                            if not matching:
                                if (any(value.split('.', 1)[0] in require_names
                                        or value == route['aap_hostname'].removeprefix('https://') for value in names)
                                        or (not related.get('aap') and node.get('ip') == route['vm_ip'])):
                                    raise ValueError
                                continue
                            if len(matching) != 1:
                                raise ValueError
                            name, nic = matching[0]
                            allowed_names = {name, route['aap_hostname'].removeprefix('https://')} if name == route['vm_name'] else {name}
                            if network != nic['network'] or bridge != nic['bridge'] or node.get('ip') != nic['address']:
                                raise ValueError
                            if kind == 'ip-dhcp-host':
                                if (node.get('mac', '').lower() != nic['mac'] or set(node.attrib) - {'ip', 'mac', 'name'}
                                        or (names and any(value not in allowed_names for value in names)) or list(node)):
                                    raise ValueError
                            elif (node.attrib != {'ip': nic['address']} or len(names) != 1
                                  or names[0] not in allowed_names or len(list(node)) != 1):
                                raise ValueError
                            result['reservations'].append({'network': network, 'scope': scope, 'kind': kind,
                                                           'xml': ET.tostring(node, encoding='unicode')})
                            parent.remove(node)
                result['after'][network][scope] = ET.tostring(root, encoding='unicode')
        return result
    except (ValueError, TypeError, KeyError, AttributeError, ET.ParseError):
        raise AnsibleFilterError('Libvirt reservation cleanup requires complete exact guest ownership; no deletion was planned.') from None


def reservation_matches(networks, plan, phase='after'):
    try:
        if phase not in ('before', 'after') or set(networks) != set(plan[phase]):
            raise ValueError
        return all(set(scopes) == set(plan[phase][network]) and all(
            network_shape(xml) == network_shape(plan[phase][network][scope]) for scope, xml in scopes.items())
            for network, scopes in networks.items())
    except (ValueError, TypeError, KeyError, AttributeError, ET.ParseError):
        raise AnsibleFilterError('The exact network reservation readback changed; preserve remaining records for review.') from None


class FilterModule:
    def filters(self):
        return {"aap_decommission_resources": resources, "aap_decommission_domain_matches": domain_matches,
                "aap_decommission_dns_plan": dns_plan,
                "aap_decommission_guest_networks": guest_networks,
                "aap_decommission_guest_access_plan": guest_access_plan,
                'aap_decommission_reservation_plan': reservation_plan,
                'aap_decommission_reservation_matches': reservation_matches}
