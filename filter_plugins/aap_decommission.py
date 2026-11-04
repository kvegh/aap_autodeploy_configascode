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
        if any(not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", name)
               for name in names):
            raise ValueError
        return sorted(names)
    except (ValueError, TypeError, ET.ParseError):
        raise AnsibleFilterError("Resolve only the selected guests' recorded libvirt networks.") from None


def guest_access_plan(previous, retirement, route, related, xmls, networks, actual_policy=None):
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
                    policy.get("protected_ipv4"), policy.get("guest_host_clients", [])) != policy:
                raise ValueError

        validate_policy(previous)
        old_clients = previous.get("guest_host_clients", []) + previous.get("https_clients", [])

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
            root = ET.fromstring(networks[network])
            bridge = root.find("bridge")
            if root.findtext("name") != network or bridge is None or bridge.get("name") not in previous["bridges"]:
                raise ValueError
            return bridge.get("name")

        identities = []
        for domain in retirement["domains"]:
            name = domain["name"]
            primary = domain.get("primary", False)
            role = "aap" if primary else name.rsplit("-", 1)[0]
            metadata = related.get(role, {})
            if not isinstance(metadata, dict):
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
            if name in xmls:
                xml = xmls[name]
                if not domain_matches(xml, domain):
                    raise ValueError
                root = ET.fromstring(xml)
                if metadata.get("uuid") and metadata["uuid"] != root.findtext("uuid"):
                    raise ValueError
                interfaces = root.findall("./devices/interface")
                if len(interfaces) != 1:
                    raise ValueError
                interface = interfaces[0]
                source, mac = interface.find("source"), interface.find("mac")
                if source is None or mac is None:
                    raise ValueError
                actual_mac = mac_address(mac.get("address"))
                network = source.get("network") if interface.get("type") == "network" else None
                if network:
                    bridge = bridge_for(network)
                elif interface.get("type") == "bridge":
                    bridge = source.get("bridge")
                else:
                    raise ValueError
                if bridge not in previous["bridges"]:
                    raise ValueError
                if (metadata.get("mac", actual_mac) != actual_mac or metadata.get("bridge", bridge) != bridge
                        or metadata.get("network", network) != network):
                    raise ValueError
                if not address:
                    if any(client["mac"] == actual_mac for client in old_clients):
                        raise ValueError
                    continue
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
                actual_mac = mac_address(metadata["mac"])
                bridge = bridge_for(metadata["network"]) if metadata.get("network") else metadata["bridge"]
                if metadata.get("bridge", bridge) != bridge or bridge not in previous["bridges"]:
                    raise ValueError
            identity = {"bridge": bridge, "ipv4": ipv4(address), "mac": actual_mac}
            for existing in identities:
                if identity["ipv4"] == existing["ipv4"] or identity["mac"] == existing["mac"]:
                    raise ValueError
            for client in old_clients:
                if ((client["ipv4"] == identity["ipv4"] or client["mac"] == identity["mac"])
                        and any(client[key] != identity[key] for key in identity)):
                    raise ValueError
            identities.append(identity)

        selected = {tuple(identity[key] for key in ("bridge", "ipv4", "mac")) for identity in identities}
        desired = deepcopy(previous)
        for field in ("guest_host_clients", "https_clients"):
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
                if field == "https_clients":
                    desired.pop("protected_ipv4")
        validate_policy(desired)
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
                "rich_rules_to_remove": sorted(rules(previous) - rules(desired))}
    except (ValueError, TypeError, KeyError, AttributeError, ET.ParseError, AnsibleFilterError):
        raise AnsibleFilterError("Guest permission retirement requires exact recorded and live VM ownership; no cleanup was planned.") from None


class FilterModule:
    def filters(self):
        return {"aap_decommission_resources": resources, "aap_decommission_domain_matches": domain_matches,
                "aap_decommission_dns_plan": dns_plan,
                "aap_decommission_guest_networks": guest_networks,
                "aap_decommission_guest_access_plan": guest_access_plan}
