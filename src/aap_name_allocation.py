"""Reserve global test-VM names before provisioning; reservations never roll back."""

from copy import deepcopy
import re


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
        type(next_number) is not int
        or next_number < 1
        or next_number >= 2**31
        or not isinstance(records, dict)
        or type(observed_floor) is not int
        or observed_floor < 1
    ):
        raise ValueError("The shared allocation state is invalid.")
    numbers = [record["number"] for record in records.values()]
    names = [record["vm_name"] for record in records.values()]
    if (
        len(set(numbers)) != len(numbers)
        or len(set(names)) != len(names)
        or any(type(number) is not int or number >= next_number for number in numbers)
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


def publish_route(state, request_id, route):
    if request_id not in state["reservations"]:
        raise ValueError(
            "Reserve the name before publishing its verified instance route."
        )
    record = state["reservations"][request_id]
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
    return updated, deepcopy(updated["reservations"][request_id])
