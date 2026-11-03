"""Only retire resources belonging to an explicitly selected test reservation."""
import re
import xml.etree.ElementTree as ET
from ansible.errors import AnsibleFilterError


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


class FilterModule:
    def filters(self):
        return {"aap_decommission_resources": resources, "aap_decommission_domain_matches": domain_matches,
                "aap_decommission_dns_plan": dns_plan}
