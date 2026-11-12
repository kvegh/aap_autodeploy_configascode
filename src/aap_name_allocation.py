"""Reserve global test-VM names before provisioning; reservations never roll back."""

from copy import deepcopy
from ipaddress import IPv4Address
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re

_spec = spec_from_file_location('allocation_interface_ownership', Path(__file__).with_name('aap_hypervisor_access.py'))
ownership = module_from_spec(_spec)
_spec.loader.exec_module(ownership)


def reserve(state, prefix, request_id, hypervisor_id, observed_floor=1):
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("Initialize the shared encrypted VM allocation state first.")
    if not isinstance(prefix, str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", prefix
    ):
        raise ValueError("Use a bounded lowercase VM-name prefix.")
    if not isinstance(request_id, str) or not re.fullmatch(
        r"[a-f0-9-]{36}", request_id
    ):
        raise ValueError("Use a unique reservation UUID.")
    if not isinstance(hypervisor_id, str) or not re.fullmatch(
        r"[a-f0-9]{32}", hypervisor_id
    ):
        raise ValueError(
            "Verify the selected hypervisor machine identity before reservation."
        )
    next_number = state.get("next_number")
    records = state.get("reservations")
    if (
        (not isinstance(next_number, int) or isinstance(next_number, bool))
        or next_number < 1
        or next_number >= 2**31
        or not isinstance(records, dict)
        or (not isinstance(observed_floor, int) or isinstance(observed_floor, bool))
        or observed_floor < 1
    ):
        raise ValueError("The shared allocation state is invalid.")
    numbers = [record["number"] for record in records.values()]
    names = [record["vm_name"] for record in records.values()]
    if (
        len(set(numbers)) != len(numbers)
        or len(set(names)) != len(names)
        or any((not isinstance(number, int) or isinstance(number, bool)) or number >= next_number for number in numbers)
    ):
        raise ValueError("Refuse inconsistent or regressed global allocation history.")
    if request_id in records:
        record = records[request_id]
        if record["hypervisor_id"] != hypervisor_id or record["prefix"] != prefix:
            raise ValueError("The reservation UUID is bound to a different request.")
        return deepcopy(state), deepcopy(record)
    number = max(next_number, observed_floor)
    name = "%s-%s" % (prefix, number)
    if len(name) > 63:
        raise ValueError("The allocated hostname would be too long.")
    result = deepcopy(state)
    record = {
        "number": number,
        "vm_name": name,
        "prefix": prefix,
        "hypervisor_id": hypervisor_id,
    }
    result["reservations"][request_id] = record
    result["next_number"] = number + 1
    return result, deepcopy(record)


def validate_primary_resource(route, resource):
    """Bind the existing primary ownership record to this exact verified route."""
    if (not isinstance(resource, dict) or not ownership.PRIMARY_FIELDS <= set(resource)
            or set(resource) - ownership.PRIMARY_FIELDS - {'supplemental_interfaces'}):
        raise ValueError("Publish only the complete verified primary guest ownership fields.")
    if (not isinstance(resource["uuid"], str)
            or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", resource["uuid"])
            or resource["uuid"] == "00000000-0000-0000-0000-000000000000"
            or resource["disk"] != "/opt/vms/" + route["vm_name"] + ".disk.qcow2"
            or resource["address"] != route["vm_ip"]
            or not isinstance(resource["address"], str)
            or str(IPv4Address(resource["address"])) != resource["address"]
            or not isinstance(resource["mac"], str)
            or not re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", resource["mac"])
            or int(resource["mac"][:2], 16) & 1 or resource["mac"] == "00:00:00:00:00:00"
            or not isinstance(resource["network"], str)
            or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", resource["network"])
            or resource["bridge"] not in route["hypervisor"]["isolation_bridges"]
            or resource["hypervisor_machine_id"] != route["hypervisor"]["machine_id"]
            or resource["verified"] is not True):
        raise ValueError("Primary guest ownership must match the exact selected route, disk and pinned hypervisor.")
    ownership.primary_interfaces(resource, route['hypervisor'])
    return resource


def publish_route(state, request_id, route, instance_resources=None):
    if request_id not in state["reservations"]:
        raise ValueError(
            "Reserve the name before publishing its verified instance route."
        )
    record = state["reservations"][request_id]
    if record.get("decommissioned"):
        raise ValueError("A decommissioned reservation cannot publish an active guest route.")
    if (
        route["vm_name"] != record["vm_name"]
        or route["hypervisor"]["machine_id"] != record["hypervisor_id"]
    ):
        raise ValueError("The instance route does not match its consumed reservation.")
    if record.get("instance_route") not in (None, route):
        raise ValueError(
            "An existing verified instance route cannot be silently replaced."
        )
    updated = deepcopy(state)
    updated["reservations"][request_id]["instance_route"] = deepcopy(route)
    if instance_resources is not None:
        if not isinstance(instance_resources, dict) or set(instance_resources) != {"aap"}:
            raise ValueError("Route publication may update only its verified primary AAP resource.")
        resource = validate_primary_resource(route, instance_resources["aap"])
        existing = record.get("instance_resources", {})
        if not isinstance(existing, dict) or set(existing) - {"aap"} or existing.get("aap") not in (None, resource):
            raise ValueError("Existing primary guest ownership cannot be silently replaced.")
        updated["reservations"][request_id].setdefault("instance_resources", {})["aap"] = deepcopy(resource)
    return updated, deepcopy(updated["reservations"][request_id])
