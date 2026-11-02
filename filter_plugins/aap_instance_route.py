"""Bind private guest connections and public APIs to one verified hypervisor."""

from collections.abc import Mapping
from ipaddress import IPv4Address
import re
import shlex
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from ansible.errors import AnsibleFilterError


def require(value, message):
    if not value:
        raise AnsibleFilterError(message)


def ipv4(value):
    try:
        require(
            isinstance(value, str) and str(IPv4Address(value)) == value,
            "Use a normalized IPv4 address.",
        )
    except ValueError:
        raise AnsibleFilterError("Use a normalized IPv4 address.") from None


def host_keys(value):
    require(
        isinstance(value, list)
        and value
        and all(
            isinstance(key, str)
            and re.fullmatch(
                r"(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)) [A-Za-z0-9+/]+={0,2}",
                key,
            )
            for key in value
        ),
        "Supply verified public SSH host keys without comments.",
    )


def public_host_key(value):
    require(isinstance(value, str), "Read the new guest public SSH key.")
    result = " ".join(value.split()[:2])
    host_keys([result])
    return result


def registered_instance(state, name):
    require(
        isinstance(state, Mapping)
        and state.get("schema_version") == 1
        and isinstance(state.get("reservations"), Mapping)
        and isinstance(name, str),
        "Choose an instance from the shared encrypted allocation registry.",
    )
    matches = [
        record["instance_route"]
        for record in state["reservations"].values()
        if record.get("vm_name") == name and "instance_route" in record
    ]
    require(
        len(matches) == 1,
        "The selected instance has no unique verified routing record.",
    )
    return instance_route(matches[0])


def hypervisor_pin(pin):
    require(isinstance(pin, Mapping), "Supply the protected hypervisor connection pin.")
    require(
        set(pin)
        <= {
            "address",
            "public_ip",
            "user",
            "port",
            "machine_id",
            "host_keys",
            "isolation_bridges",
            "isolation_dns_bridges",
            "machine_credential_name",
        },
        "Keep passwords and private keys out of the public connection handoff.",
    )
    for field in ("address", "public_ip"):
        ipv4(pin.get(field))
    require(
        isinstance(pin.get("user"), str)
        and re.fullmatch(r"[a-z_][a-z0-9_-]*[$]?", pin["user"])
        and pin["user"] != "root"
        and type(pin.get("port")) is int
        and 1 <= pin["port"] <= 65535,
        "Pin the managed hypervisor account and SSH port.",
    )
    require(
        isinstance(pin.get("machine_id"), str)
        and re.fullmatch(r"[a-f0-9]{32}", pin["machine_id"]),
        "Pin the selected hypervisor machine identity.",
    )
    host_keys(pin.get("host_keys"))
    require(
        isinstance(pin.get("isolation_bridges"), list)
        and pin["isolation_bridges"]
        and all(
            re.fullmatch(r"[A-Za-z0-9_.:-]{1,15}", item)
            for item in pin["isolation_bridges"]
        )
        and isinstance(pin.get("isolation_dns_bridges"), list)
        and set(pin["isolation_dns_bridges"]) <= set(pin["isolation_bridges"]),
        "Declare the complete enforced recovery isolation bridge set.",
    )
    return pin


def instance_route(route):
    require(
        isinstance(route, Mapping),
        "Supply the verified new-instance handoff; direct private-IP fallback is refused.",
    )
    hypervisor_pin(route.get("hypervisor"))
    require(
        isinstance(route.get("vm_name"), str)
        and re.fullmatch(r"aap[0-9]+-[a-z0-9-]+-[0-9]+", route["vm_name"]),
        "Bind the route to its reserved test VM name.",
    )
    ipv4(route.get("vm_ip"))
    host_keys(route.get("guest_host_keys"))
    parsed = urlsplit(route.get("aap_hostname", ""))
    require(
        parsed.scheme == "https"
        and parsed.hostname
        and re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", parsed.hostname)
        and ".." not in parsed.hostname
        and parsed.hostname.startswith(route["vm_name"] + ".")
        and not parsed.username
        and not parsed.password
        and parsed.port in (None, 443)
        and parsed.path in ("", "/")
        and not parsed.query
        and not parsed.fragment,
        "Use this VM's unique public HTTPS hostname for its API.",
    )
    return route


def safe_instance_dns(records, name, address):
    """Only an absent record or an exact existing binding can be updated."""
    ipv4(address)
    require(
        isinstance(records, list)
        and all(
            isinstance(record, Mapping)
            and record.get("data") == address
            and record.get("name", name) == name
            and record.get("type", "A") == "A"
            for record in records
        ),
        "The reserved hostname has a conflicting or incomplete DNS record.",
    )
    return True


def ssh_args(route, known_hosts):
    route = instance_route(route)
    require(
        isinstance(known_hosts, str)
        and known_hosts.startswith("/")
        and "\n" not in known_hosts,
        "Allocate a private controller-side SSH trust file.",
    )
    pin = route["hypervisor"]
    proxy = (
        "ssh -o BatchMode=yes -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no "
        "-o StrictHostKeyChecking=yes -o UserKnownHostsFile=%s -p %s -W %%h:%%p %s@%s"
        % (shlex.quote(known_hosts), pin["port"], pin["user"], pin["address"])
    )
    return (
        "-o StrictHostKeyChecking=yes -o UserKnownHostsFile=%s -o HostKeyAlias=%s -o ProxyCommand=%s"
        % (
            shlex.quote(known_hosts),
            shlex.quote(urlsplit(route["aap_hostname"]).hostname),
            shlex.quote(proxy),
        )
    )


def observed_floor(domain_names, local_counter=""):
    require(isinstance(domain_names, list), "Read the actual existing domain names.")
    values = [
        int(match.group(1)) + 1
        for name in domain_names
        if (match := re.fullmatch(r"aap[0-9]+-test-([0-9]+)", name))
    ]
    if local_counter:
        require(
            isinstance(local_counter, str)
            and re.fullmatch(r"[0-9]+", local_counter.strip()),
            "The preserved local migration counter is not numeric.",
        )
        values.append(int(local_counter.strip()))
    return max([1] + values)


def network_bridge(xml):
    try:
        root = ET.fromstring(xml)
        bridge = root.find("bridge")
        require(
            bridge is not None and bridge.get("name"),
            "The selected libvirt network needs an enforced bridge.",
        )
        return bridge.get("name")
    except ET.ParseError:
        raise AnsibleFilterError("The live libvirt network XML is invalid.") from None


def guest_ipv4(output):
    values = re.findall(r"\bipv4\s+((?:[0-9]{1,3}\.){3}[0-9]{1,3})/[0-9]+", output)
    require(
        len(set(values)) == 1,
        "Read exactly one IPv4 address for the newly created libvirt domain.",
    )
    ipv4(values[0])
    return values[0]


class FilterModule:
    def filters(self):
        return {
            "aap_hypervisor_pin": hypervisor_pin,
            "aap_instance_route": instance_route,
            "aap_instance_ssh_args": ssh_args,
            "aap_observed_allocation_floor": observed_floor,
            "aap_network_bridge": network_bridge,
            "aap_public_host_key": public_host_key,
            "aap_registered_instance": registered_instance,
            "aap_guest_ipv4": guest_ipv4,
            "aap_safe_instance_dns": safe_instance_dns,
        }
