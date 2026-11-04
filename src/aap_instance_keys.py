"""Temporary instance-token storage and source-controller synchronization."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import re
import yaml
from ansible.utils.unsafe_proxy import AnsibleUnsafeText, wrap_var
from urllib.parse import quote, urlsplit

TYPE_NAME = "Pseudo Instance Key Store"
CREDENTIAL_NAME = "AAP API/MCP Auth Token Store"

_routing_spec = spec_from_file_location("instance_key_retirement_route", Path(__file__).resolve().parents[1] / "filter_plugins/aap_instance_route.py")
_routing = module_from_spec(_routing_spec)
_routing_spec.loader.exec_module(_routing)


class StoreError(ValueError):
    """Only fixed, credential-free messages may leave this module."""


def require(condition, message):
    if not condition:
        raise StoreError(message)


def type_definition():
    return {
        "name": TYPE_NAME,
        "kind": "cloud",
        "inputs": {"fields": [{"id": "instance_tokens", "type": "string",
            "label": "Instance API/MCP tokens (JSON)", "secret": True, "multiline": True}],
            "required": ["instance_tokens"]},
        "injectors": {"file": {"template": "{{ instance_tokens }}"},
            "env": {"AAP_INSTANCE_KEY_STORE_FILE": "{{ tower.filename }}"}},
    }


def origin(value):
    require(isinstance(value, str) and not any(c.isspace() for c in value),
            "Require an HTTPS instance URL without credentials.")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise StoreError("Require a valid HTTPS instance URL.") from None
    require(parsed.scheme == "https" and parsed.hostname and not parsed.username
            and not parsed.password and parsed.path in ("", "/")
            and not parsed.query and not parsed.fragment and port in (None, 443),
            "Require an HTTPS instance origin without credentials or alternate ports.")
    return "https://" + parsed.hostname


def instance_name(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,62}", value),
            "Select a valid AAP inventory instance name.")
    return value


def validate_record(record):
    require(isinstance(record, dict) and set(record) == {"hostname", "token", "token_id", "expires"},
            "The stored instance access record is incomplete.")
    origin(record["hostname"])
    require(isinstance(record["token"], str) and record["token"]
            and not any(c.isspace() for c in record["token"])
            and record["token"] not in ("ASK", "$encrypted$", "CHANGEME"),
            "The selected instance has no usable stored API token.")
    require(type(record["token_id"]) is int and record["token_id"] > 0,
            "Retain the original instance token identity.")
    if record["expires"] is not None:
        try:
            expiration = datetime.fromisoformat(record["expires"].replace("Z", "+00:00"))
            require(expiration.tzinfo is not None and expiration > datetime.now(timezone.utc),
                    "The selected instance token has expired; review rotation explicitly.")
        except (ValueError, TypeError, AttributeError):
            raise StoreError("The selected instance token expiry is invalid or expired.") from None
    return record


def document(records):
    require(isinstance(records, dict), "Require instance names mapped to API access records.")
    for key, value in records.items():
        instance_name(key)
        # Expired entries may remain for review; selection validates their expiry.
        require(isinstance(value, dict) and "token" in value and "hostname" in value,
                "The instance token list contains an invalid entry.")
    return {"schema_version": 1, "instances": deepcopy(records)}


def select_access(data, selected, inventory_host):
    instance_name(selected)
    require(isinstance(data, dict) and set(data) == {"schema_version", "instances"}
            and type(data["schema_version"]) is int and data["schema_version"] == 1
            and isinstance(data["instances"], dict), "The injected instance token file has an invalid format.")
    require(selected in data["instances"], "No API token is stored for the selected AAP instance.")
    record = validate_record(data["instances"][selected])
    require(isinstance(inventory_host, dict) and isinstance(inventory_host.get("ansible_fqdn"), str),
            "Set ansible_fqdn explicitly on the selected AAP inventory entry.")
    expected = inventory_host["ansible_fqdn"]
    require(re.fullmatch(r"[A-Za-z0-9.-]+", expected) and "." in expected,
            "Require the selected inventory entry's full DNS name.")
    require(origin(record["hostname"]) == origin("https://" + expected),
            "The stored API URL does not match the selected inventory instance.")
    return {"hostname": origin(record["hostname"]), "token": record["token"],
            "username": "", "password": "", "validate_certs": True}


def merge_record(configuration, selected, saved):
    instance_name(selected)
    require(isinstance(saved, dict) and saved.get("username") == "admin" and saved.get("scope") == "write",
            "Publish only the verified administrator API/MCP token.")
    record = {"hostname": origin(saved.get("target")), "token": saved.get("token"),
              "token_id": saved.get("id"), "expires": saved.get("expires")}
    validate_record(record)
    result = deepcopy(configuration)
    records = result.setdefault("aap_instance_api_credentials", {})
    require(isinstance(records, dict), "Require instance-indexed encrypted API access data.")
    if selected in records:
        old = records[selected]
        require(old.get("hostname") == record["hostname"] and old.get("token") == record["token"]
                and old.get("token_id") == record["token_id"],
                "Stored access differs for this instance; review replacement explicitly.")
    records[selected] = record
    document(records)
    return result


def retire_record(configuration, selected, target):
    instance_name(selected)
    target = origin(target)
    result = deepcopy(configuration)
    records = result.setdefault("aap_instance_api_credentials", {})
    existing = records.get(selected)
    require(existing is None or origin(existing.get("hostname")) == target,
            "Retired instance access must match its registered public URL.")
    records.pop(selected, None)
    definitions = result.get("autodeploy_configuration", {}).get("credentials", [])
    result.get("autodeploy_configuration", {})["credentials"] = [row for row in definitions
        if row.get("name") != selected + " MCP and API token"]
    document(records)
    return result


def inventory_variables(row):
    value = row.get("variables", {})
    value = yaml.safe_load(value) if isinstance(value, str) else deepcopy(value)
    if value is None:
        value = {}
    require(isinstance(value, dict), "Require mapping variables on the selected inventory entries.")
    return value


def set_inventory_variables(row, values):
    """Retain a captured literal JSON field instead of enabling its templates."""
    previous = row.get("variables")
    if isinstance(previous, AnsibleUnsafeText):
        row["variables"] = wrap_var(json.dumps(values))
    elif isinstance(previous, str):
        row["variables"] = json.dumps(values)
    else:
        row["variables"] = values


def isolation_retirement_context(record, selected, target, transition):
    """Validate a bounded removal against the selected consumed reservation."""
    require(isinstance(transition, dict) and set(transition) == {"previous_policy", "desired_policy", "identities"},
            "Supply only both isolation policies and verified selected guest identities.")
    route = _routing.instance_route(record.get("instance_route"))
    require(record.get("vm_name") == selected == route["vm_name"]
            and origin(route["aap_hostname"]) == origin(target),
            "Retirement must match the selected consumed reservation and public URL.")
    match = re.fullmatch(r"aap[0-9]+-test-([0-9]+)", selected)
    require(match is not None and int(match[1]) > 0, "Retire only a numbered test deployment.")
    version = "v%02d" % int(match[1])
    pin = route["hypervisor"]
    require(record.get("hypervisor_id") == pin["machine_id"] and record.get("number") == int(match[1])
            and record.get("prefix") == selected.rsplit("-", 1)[0],
            "Selected isolation retirement must match its consumed allocation number and hypervisor.")
    previous, desired, identities = (transition[key] for key in ("previous_policy", "desired_policy", "identities"))

    def normalized(policy):
        require(isinstance(policy, dict) and _routing.isolation_policy(pin, policy.get("https_clients", []),
            policy.get("protected_ipv4"), policy.get("guest_host_clients", [])) == policy,
            "Retirement policies must preserve the registered hypervisor's normalized isolation schema.")
    normalized(previous)
    normalized(desired)
    resources = record.get("instance_resources", {})
    require(isinstance(resources, dict), "Require existing selected guest ownership records.")
    guests = []
    for role in ("aap", "zabbix", "testserver1", "tra"):
        metadata = resources.get(role, {})
        require(isinstance(metadata, dict), "Require mapping resource ownership records.")
        name = selected if role == "aap" else role + "-" + version
        address = route["vm_ip"] if role == "aap" else metadata.get("address")
        require(metadata.get("vm_name", name) == name and metadata.get("address", address) == address
                and metadata.get("hypervisor_machine_id", pin["machine_id"]) == pin["machine_id"]
                and metadata.get("verified", True) is True,
                "Related resource ownership must belong to this selected verified deployment.")
        if metadata:
            require(isinstance(metadata.get("uuid"), str)
                and re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", metadata["uuid"])
                and isinstance(metadata.get("disk"), str)
                and re.fullmatch(re.escape("/opt/vms/" + name) + r"(?:\.disk)?\.qcow2", metadata["disk"]),
                "Recorded guests require their exact selected UUID and disk.")
        guests.append({"name": name, "role": role, "address": address, "metadata": deepcopy(metadata)})
    require(isinstance(identities, list) and len(identities) <= 4,
            "Retire only the four selected deployment identities.")
    selected_keys = set()
    addresses, macs = set(), set()
    for identity in identities:
        require(isinstance(identity, dict) and set(identity) == {"bridge", "ipv4", "mac"},
                "Retire only exact bridge, IPv4 and MAC identities.")
        require(identity["bridge"] in pin["isolation_bridges"]
                and isinstance(identity["mac"], str)
                and re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", identity["mac"])
                and not int(identity["mac"][:2], 16) & 1
                and identity["mac"] != "00:00:00:00:00:00",
                "Retire only normalized selected bridge and unicast MAC identities.")
        _routing.ipv4(identity["ipv4"])
        matches = [guest for guest in guests if guest["address"] == identity["ipv4"]]
        require(len(matches) == 1, "An isolation identity does not belong to a selected recorded guest.")
        guest = matches[0]
        metadata = guest["metadata"]
        require((guest["role"] == "aap" or metadata)
                and metadata.get("mac", identity["mac"]) == identity["mac"]
                and metadata.get("bridge", identity["bridge"]) == identity["bridge"],
                "An isolation identity differs from its existing selected guest record.")
        require(identity["ipv4"] not in addresses and identity["mac"] not in macs,
                "Selected guest retirement identities must be unique.")
        addresses.add(identity["ipv4"])
        macs.add(identity["mac"])
        key = tuple(identity[field] for field in ("bridge", "ipv4", "mac"))
        for client in previous.get("guest_host_clients", []) + previous.get("https_clients", []):
            require(not ((client["ipv4"] == identity["ipv4"] or client["mac"] == identity["mac"])
                         and tuple(client[field] for field in ("bridge", "ipv4", "mac")) != key),
                    "An isolation identity conflicts with an existing guest permission.")
        selected_keys.add(key)
    for client in previous.get("guest_host_clients", []) + previous.get("https_clients", []):
        if any(client["ipv4"] == guest["address"] or client["mac"] == guest["metadata"].get("mac") for guest in guests):
            require(tuple(client[field] for field in ("bridge", "ipv4", "mac")) in selected_keys,
                    "Retirement must include every existing permission of the selected recorded guests.")
    expected = deepcopy(previous)
    for field in ("https_clients", "guest_host_clients"):
        if field not in expected:
            continue
        retained = [client for client in expected[field]
                    if tuple(client[key] for key in ("bridge", "ipv4", "mac")) not in selected_keys]
        if retained != expected[field]:
            if retained:
                expected[field] = retained
            else:
                expected.pop(field)
                if field == "https_clients":
                    expected.pop("protected_ipv4")
    require(expected == desired, "Desired isolation must be exactly selected identity removal without new grants.")
    removed_rules = {'rule family="ipv4" priority="0" source address="%s/32" '
        'destination address="%s/32" port port="%s" protocol="tcp" accept'
        % (client["ipv4"], destination, port)
        for client in previous.get("guest_host_clients", [])
        if tuple(client[key] for key in ("bridge", "ipv4", "mac")) in selected_keys
        for destination in client["destinations"] for port in client["ports"]}
    return {"route": route, "guests": guests, "previous_policy": deepcopy(previous),
            "desired_policy": deepcopy(desired), "identities": deepcopy(identities), "removed_rules": removed_rules}


def retirement_policy_variables(values, context, pinned=False):
    """Change only the declared policy aliases and exact previous-owned rich rules."""
    values = deepcopy(values)
    old, new = context["previous_policy"], context["desired_policy"]
    if pinned:
        require(values.get("aap_hypervisor_pin") == context["route"]["hypervisor"],
                "Recovery inventory must retain the exact registered hypervisor pin.")
        current = _routing.isolation_policy(values["aap_hypervisor_pin"],
            values.get("aap_hypervisor_isolation_https_clients", []),
            values.get("aap_hypervisor_isolation_protected_ipv4", []),
            values.get("aap_hypervisor_isolation_host_clients", []))
        require(current in (old, new), "Canonical recovery policy changed beyond this exact retirement.")
        values.update(aap_hypervisor_isolation_https_clients=deepcopy(new.get("https_clients", [])),
            aap_hypervisor_isolation_protected_ipv4=deepcopy(new.get("protected_ipv4", [])),
            aap_hypervisor_isolation_host_clients=deepcopy(new.get("guest_host_clients", [])))
    for alias in ("isolation_policy", "hactar_isolation_policy"):
        require(alias not in values or values[alias] in (old, new),
                "An existing hypervisor policy alias conflicts with selected retirement.")
        values[alias] = deepcopy(new)
    if "firewall_additional_zone_rules" in values:
        rules = values["firewall_additional_zone_rules"]
        require(isinstance(rules, list) and all(isinstance(rule, dict) for rule in rules),
                "Require explicit native zone-rule data before removing owned entries.")
        values["firewall_additional_zone_rules"] = [rule for rule in rules
            if not (rule.get("zone") == "libvirt" and rule.get("rule") in context["removed_rules"])]
    return values


def retirement_host_matches(row, guest, route, hypervisor_name):
    values = inventory_variables(row)
    require(values.get("ansible_host") == guest["address"]
            and values.get("hypervisor_host", hypervisor_name) == hypervisor_name,
            "A selected inventory guest has conflicting address or placement data.")
    metadata = guest["metadata"]
    if guest["role"] == "aap":
        require(origin("https://" + values.get("ansible_fqdn", "")) == origin(route["aap_hostname"]),
                "The selected inventory AAP host has a conflicting public URL.")
        for field, expected in (("vm_uuid", metadata.get("uuid")), ("machine_id", metadata.get("machine_id")),
                                ("host_keys", route.get("guest_host_keys"))):
            require(field not in values or expected is None or values[field] == expected,
                    "The selected inventory AAP host conflicts with recorded identity.")
    else:
        require(metadata and metadata.get("uuid") and values.get("vm_uuid") == metadata["uuid"],
                "Related inventory retirement requires its exact recorded UUID.")
        for field in ("machine_id", "host_keys"):
            require(field not in metadata or values.get(field) == metadata[field],
                    "Related inventory retirement requires its exact recorded machine identity.")


def retire_inventory_capture(configuration, context, kind):
    """Retire scoped rows/policy in the fixed existing encrypted capture formats."""
    require(kind in ("autodeploy", "shared", "hactar"), "Use only the fixed maintained retirement captures.")
    result = deepcopy(configuration)
    pin = context["route"]["hypervisor"]
    if kind == "autodeploy":
        inventories = result["autodeploy_configuration"]["inventories"]
        matches = [row for row in inventories if inventory_variables(row).get("aap_hypervisor_pin") == pin]
        require(len(matches) == 1, "Resolve the canonical recovery inventory for the exact registered pin.")
        set_inventory_variables(matches[0], retirement_policy_variables(inventory_variables(matches[0]), context, True))
        return result
    data = result["host_inventory_configuration"] if kind == "shared" else {
        "hosts": result.get("controller_hosts_hactar_recovery", []),
        "groups": result.get("controller_groups_hactar_recovery", [])}
    matches = [row for row in data["hosts"] if inventory_variables(row).get("ansible_host") == pin["address"]]
    require(len(matches) == 1 or (kind == "hactar" and not matches),
            "Resolve only the exact hypervisor in its captured inventory.")
    if not matches:
        return result
    hypervisor = matches[0]
    values = inventory_variables(hypervisor)
    for field, expected in (("machine_id", pin["machine_id"]), ("ansible_port", pin["port"]),
                            ("ansible_user", pin["user"]), ("host_keys", pin["host_keys"])):
        require(field not in values or values[field] == expected,
                "Captured hypervisor identity differs from the selected registered pin.")
    set_inventory_variables(hypervisor, retirement_policy_variables(values, context))
    if kind == "shared":
        removed = {guest["name"] for guest in context["guests"] if guest["role"] == "aap" or guest["metadata"]}
        for guest in context["guests"]:
            rows = [row for row in data["hosts"] if row.get("name") == guest["name"]
                    and row.get("inventory") == hypervisor["inventory"]]
            require(len(rows) <= 1, "Require unique guest rows in the exact captured shared inventory.")
            for row in rows:
                retirement_host_matches(row, guest, context["route"], hypervisor["name"])
                data["hosts"].remove(row)
        for group in data["groups"]:
            if group.get("inventory") == hypervisor["inventory"]:
                require(not any(guest["name"] in group.get("hosts", []) and guest["name"] not in removed
                                for guest in context["guests"]),
                        "Related group membership requires its existing recorded resource ownership.")
                group["hosts"] = [name for name in group.get("hosts", []) if name not in removed]
    return result


def source_retirement_operations(client, shared, autodeploy, hactar, context):
    """Read and validate every exact API target before returning bounded operations."""
    operations = {}
    pin = context["route"]["hypervisor"]

    def inventory(name):
        matches = client.rows("inventories/?name=" + quote(name))
        require(len(matches) == 1 and matches[0].get("name") == name,
                "Resolve exactly the captured source inventory before retirement.")
        return matches[0]

    def host_rows(name, identity):
        rows = client.rows("hosts/?inventory=%s&name=%s" % (identity, quote(name)))
        require(len(rows) <= 1 and all(row.get("inventory") == identity and row.get("name") == name for row in rows),
                "Source retirement must remain in the exact captured inventory and host name.")
        return rows

    def patch_hypervisor(captured):
        live_inventory = inventory(captured["inventory"])
        rows = host_rows(captured["name"], live_inventory["id"])
        require(len(rows) == 1, "Keep the existing pinned hypervisor inventory host.")
        row = rows[0]
        current = inventory_variables(row)
        require(current.get("ansible_host") == pin["address"],
                "The live hypervisor inventory address conflicts with its registered pin.")
        for field, expected in (("machine_id", pin["machine_id"]), ("ansible_port", pin["port"]),
                                ("ansible_user", pin["user"]), ("host_keys", pin["host_keys"])):
            require(field not in current or current[field] == expected,
                    "The live hypervisor inventory identity conflicts with its registered pin.")
        desired = retirement_policy_variables(current, context)
        if desired != current:
            operations[("PATCH", "hosts/%s/" % row["id"])] = {"variables": json.dumps(desired)}
        return live_inventory

    hosts = shared["host_inventory_configuration"]["hosts"]
    selected_hypervisors = [row for row in hosts if inventory_variables(row).get("ansible_host") == pin["address"]]
    require(len(selected_hypervisors) == 1, "Resolve one captured shared hypervisor for source retirement.")
    hypervisor = selected_hypervisors[0]
    shared_inventory = patch_hypervisor(hypervisor)
    for guest in context["guests"]:
        for row in host_rows(guest["name"], shared_inventory["id"]):
            retirement_host_matches(row, guest, context["route"], hypervisor["name"])
            operations[("DELETE", "hosts/%s/" % row["id"])] = None

    recovery_rows = [row for row in autodeploy["autodeploy_configuration"]["inventories"]
                     if inventory_variables(row).get("aap_hypervisor_pin") == pin]
    require(len(recovery_rows) == 1, "Resolve one exact pinned recovery inventory for source synchronization.")
    live = inventory(recovery_rows[0]["name"])
    current = inventory_variables(live)
    desired = retirement_policy_variables(current, context, True)
    if current != desired:
        operations[("PATCH", "inventories/%s/" % live["id"])] = {"variables": json.dumps(desired)}
    if hactar is not None:
        for captured in hactar.get("controller_hosts_hactar_recovery", []):
            if inventory_variables(captured).get("ansible_host") == pin["address"]:
                patch_hypervisor(captured)
    return [(method, path, body) for (method, path), body in operations.items()]


def merge_inventory(configuration, selected, route, policy):
    """Keep VM placement in the existing inventory capture, without any tokens."""
    instance_name(selected)
    require(route.get("vm_name") == selected, "Inventory registration must match the allocated VM.")
    match = re.fullmatch(r"aap[0-9]+-test-([0-9]+)", selected)
    require(match is not None, "Register only the selected globally allocated AAP instance.")
    pin = route["hypervisor"]
    result = deepcopy(configuration)
    data = result["host_inventory_configuration"]
    hypervisors = [row for row in data["hosts"]
                   if inventory_variables(row).get("ansible_host") == pin["address"]]
    require(len(hypervisors) == 1, "Register the pinned hypervisor in the existing shared inventory first.")
    hypervisor = hypervisors[0]
    variables = inventory_variables(hypervisor)
    require(variables.get("machine_id", pin["machine_id"]) == pin["machine_id"],
            "The existing inventory hypervisor has a conflicting machine identity.")
    variables.update(ansible_host=pin["address"], ansible_user=pin["user"], ansible_port=pin["port"],
                     public_ipv4=pin["public_ip"], machine_id=pin["machine_id"],
                     host_keys=pin["host_keys"], isolation_policy=deepcopy(policy))
    set_inventory_variables(hypervisor, variables)
    matches = [row for row in data["hosts"] if row.get("name") == selected]
    require(len(matches) <= 1, "Resolve one inventory entry for the selected instance.")
    if matches:
        host = matches[0]
        values = inventory_variables(host)
        require(host["inventory"] == hypervisor["inventory"] and
                origin("https://" + values.get("ansible_fqdn", "")) == origin(route["aap_hostname"]),
                "Do not replace an existing inventory host pointing to a different AAP.")
    else:
        host = {"name": selected, "inventory": hypervisor["inventory"], "enabled": True}
        data["hosts"].append(host)
        values = {}
    values.update(ansible_host=route["vm_ip"], ansible_fqdn=urlsplit(origin(route["aap_hostname"])).hostname,
                  hypervisor_host=hypervisor["name"], aap_instance_number=int(match[1]), vm_ip=route["vm_ip"],
                  host_keys=deepcopy(route["guest_host_keys"]))
    set_inventory_variables(host, values)
    groups = [row for row in data["groups"] if row["inventory"] == hypervisor["inventory"]
              and inventory_variables(row).get("hypervisor_host") == hypervisor["name"]]
    require(len(groups) == 1, "Define one VM inventory group mapped to the selected hypervisor.")
    if selected not in groups[0].setdefault("hosts", []):
        groups[0]["hosts"].append(selected)
    return result


def ensure_source_inventory(client, configuration, selected, route):
    data = configuration["host_inventory_configuration"]
    host = next(row for row in data["hosts"] if row["name"] == selected)
    hypervisor = next(row for row in data["hosts"]
                      if row["name"] == inventory_variables(host)["hypervisor_host"])
    inventories = client.rows("inventories/?name=" + quote(host["inventory"]))
    require(len(inventories) == 1, "Resolve the maintained shared inventory on the source AAP.")
    identity = inventories[0]["id"]
    changed = False
    host_id = None
    for desired in (hypervisor, host):
        existing = client.rows("hosts/?inventory=%s&name=%s" % (identity, quote(desired["name"])))
        require(len(existing) <= 1, "Require unique source inventory host names.")
        values = inventory_variables(desired)
        if existing:
            current = inventory_variables(existing[0])
            key = "ansible_fqdn" if desired is host else "ansible_host"
            require(current.get(key) == values[key], "The live source inventory has conflicting placement data.")
            merged = dict(current, **values)
            if merged != current:
                client.request("PATCH", "hosts/%s/" % existing[0]["id"], {"variables": json.dumps(merged)})
                changed = True
            row_id = existing[0]["id"]
        else:
            row = client.request("POST", "hosts/", {"name": desired["name"], "inventory": identity,
                "enabled": desired.get("enabled", True), "variables": json.dumps(values)})
            row_id = row["id"]
            changed = True
        if desired is host:
            host_id = row_id
    group = next(row for row in data["groups"] if row["inventory"] == host["inventory"] and
                 inventory_variables(row).get("hypervisor_host") == hypervisor["name"])
    groups = client.rows("groups/?inventory=%s&name=%s" % (identity, quote(group["name"])))
    require(len(groups) == 1, "Resolve the existing source VM placement group.")
    members = client.rows("groups/%s/hosts/" % groups[0]["id"])
    if not any(row["id"] == host_id for row in members):
        client.request("POST", "groups/%s/hosts/" % groups[0]["id"], {"id": host_id})
        changed = True
    return changed


def ensure_source_store(client, records, organization):
    """Use injected source API access; do not change other credentials or grants."""
    payload = json.dumps(document(records), sort_keys=True, separators=(",", ":"))
    desired = type_definition()
    types = client.rows("credential_types/?name=" + quote(TYPE_NAME))
    require(len(types) == 1 and not types[0].get("managed")
            and all(types[0].get(key) == desired[key] for key in ("inputs", "injectors", "kind")),
            "Provision the approved Pseudo Instance Key Store type on the source AAP.")
    orgs = client.rows("organizations/?name=" + quote(organization))
    require(len(orgs) == 1, "Resolve exactly one source organization for the token store.")
    existing = client.rows("credentials/?name=" + quote(CREDENTIAL_NAME))
    require(len(existing) <= 1, "Resolve exactly one source API/MCP token-store credential.")
    description = "Managed per-instance API/MCP access; sha256=" + hashlib.sha256(payload.encode()).hexdigest()
    body = {"name": CREDENTIAL_NAME, "credential_type": types[0]["id"],
            "organization": orgs[0]["id"], "description": description,
            "inputs": {"instance_tokens": payload}}
    if existing:
        row = existing[0]
        require(row["credential_type"] == types[0]["id"] and row["organization"] == orgs[0]["id"],
                "The source token-store credential has unexpected ownership or type.")
        if row.get("description") == description:
            return {"changed": False, "credential_id": row["id"]}
        client.request("PATCH", "credentials/%s/" % row["id"],
                       {"description": description, "inputs": body["inputs"]})
        return {"changed": True, "credential_id": row["id"]}
    created = client.request("POST", "credentials/", body)
    return {"changed": True, "credential_id": created["id"]}
