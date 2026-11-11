"""Instance API access, source inventory ownership and synchronization."""

from copy import deepcopy
from datetime import datetime, timezone
from ipaddress import IPv4Address, IPv4Network
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import re
import ssl
import yaml
from ansible.utils.unsafe_proxy import AnsibleUnsafeText, wrap_var
from urllib.parse import quote, urlsplit, urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler

TYPE_NAME = "Pseudo Instance Key Store"
CREDENTIAL_NAME = "AAP API/MCP Auth Token Store"

_routing_spec = spec_from_file_location("instance_key_retirement_route", Path(__file__).resolve().parents[1] / "filter_plugins/aap_instance_route.py")
_routing = module_from_spec(_routing_spec)
_routing_spec.loader.exec_module(_routing)
_management_spec = spec_from_file_location("instance_key_management_access", Path(__file__).with_name("aap_hypervisor_access.py"))
_management = module_from_spec(_management_spec)
_management_spec.loader.exec_module(_management)
_allocation_spec = spec_from_file_location('instance_key_allocation', Path(__file__).with_name('aap_name_allocation.py'))
_allocation = module_from_spec(_allocation_spec)
_allocation_spec.loader.exec_module(_allocation)


class StoreError(ValueError):
    """Only fixed, credential-free messages may leave this module."""


def require(condition, message):
    if not condition:
        raise StoreError(message)


def validate_aap_primary(route, resource):
    try:
        return _allocation.validate_primary_resource(route, resource)
    except (ValueError, TypeError, KeyError):
        raise StoreError('Require the exact saved primary AAP ownership and bounded supplemental declaration.') from None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SourceClient:
    """The existing injected source API access, with trusted TLS and no redirects."""
    def __init__(self):
        self.origin = origin(os.environ.get("AAP_CAC_SOURCE_URL", ""))
        self.token = os.environ.get("AAP_CAC_SOURCE_TOKEN", "")
        require(bool(self.token), "Attach the existing source AAP API access credential.")
        context = ssl.create_default_context()
        authority = os.environ.get("AAP_CAC_SOURCE_CA_FILE")
        if authority:
            context.load_verify_locations(cafile=authority)
        self.opener = build_opener(NoRedirect(), HTTPSHandler(context=context))

    def request(self, method, path, body=None):
        relative = path if path.startswith("/") else "/api/controller/v2/" + path
        url = urljoin(self.origin + "/", relative)
        require(urlsplit(url).netloc == urlsplit(self.origin).netloc,
                "Source API pagination must remain on the authenticated source.")
        request = Request(url, data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"}, method=method)
        try:
            with self.opener.open(request, timeout=45) as response:
                raw = response.read()
            return json.loads(raw) if raw else {}
        except Exception:
            raise StoreError("Source AAP API access failed; inspect protected job state before retry.") from None

    def rows(self, path):
        result = []
        while path:
            page = self.request("GET", path)
            result.extend(page["results"])
            path = page.get("next")
        return result


def verify_source_job(client, target, variables):
    require(target is None or client.origin != origin(target), "Source API access must identify the AAP running this deployment job.")
    job_id, template_id, revision = (variables.get(key) for key in ("awx_job_id", "awx_job_template_id", "awx_project_revision"))
    require(str(job_id).isdigit() and str(template_id).isdigit() and bool(revision),
            "Read source ownership only from its authenticated running AAP job.")
    job = client.request("GET", "jobs/%s/" % job_id)
    require(job.get("status") == "running" and job.get("job_template") == int(template_id)
            and job.get("scm_revision") == revision,
            "The source API credential does not identify this running deployment job.")


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


def mcp_connection(value):
    """Validate the optional selected private endpoint and its installed public CA."""
    require(isinstance(value, dict) and set(value) == {"url", "ca_pem"},
            "Keep only the selected private MCP endpoint and public authority.")
    try:
        parsed = urlsplit(value["url"])
        address = IPv4Address(parsed.hostname)
        require(value["url"] == "https://" + str(address) + ":8448/mcp",
                "Use only the selected private AAP MCP HTTPS endpoint.")
        require(any(address in IPv4Network(network) for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")),
                "Use only the selected private AAP address for MCP.")
        authority = value["ca_pem"]
        require(isinstance(authority, str) and len(authority) <= 524288
                and "PRIVATE KEY" not in authority, "Publish only the installed public CA bundle.")
        blocks = re.findall(r"-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----", authority)
        require(bool(blocks), "Require the selected installed PEM certificate authority.")
        normalized = "\n".join(blocks) + "\n"
        ssl.create_default_context(cadata=normalized)
    except (ValueError, TypeError, KeyError, ssl.SSLError):
        raise StoreError("The selected private MCP endpoint or public authority is invalid.") from None
    return {"url": value["url"], "ca_pem": normalized}


def validate_record(record):
    fields = {"hostname", "token", "token_id", "expires"}
    require(isinstance(record, dict) and fields <= set(record) <= fields | {"mcp"},
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
    if "mcp" in record:
        mcp_connection(record["mcp"])
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


def select_mcp(data, selected, inventory_host):
    """Keep public API authentication unchanged and return only selected MCP metadata."""
    select_access(data, selected, inventory_host)
    record = data["instances"][selected]
    return mcp_connection(record["mcp"]) if "mcp" in record else None


def merge_record(configuration, selected, saved):
    instance_name(selected)
    require(isinstance(saved, dict) and saved.get("username") == "admin" and saved.get("scope") == "write",
            "Publish only the verified administrator API/MCP token.")
    record = {"hostname": origin(saved.get("target")), "token": saved.get("token"),
              "token_id": saved.get("id"), "expires": saved.get("expires")}
    if "mcp" in saved:
        record["mcp"] = mcp_connection(saved["mcp"])
    validate_record(record)
    result = deepcopy(configuration)
    records = result.setdefault("aap_instance_api_credentials", {})
    require(isinstance(records, dict), "Require instance-indexed encrypted API access data.")
    if selected in records:
        old = records[selected]
        require(old.get("hostname") == record["hostname"] and old.get("token") == record["token"]
                and old.get("token_id") == record["token_id"],
                "Stored access differs for this instance; review replacement explicitly.")
        if "mcp" in old:
            previous = mcp_connection(old["mcp"])
            require("mcp" not in record or record["mcp"] == previous,
                    "The saved private MCP authority or endpoint changed; review replacement explicitly.")
            record.setdefault("mcp", previous)
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


def source_related_resources(client, shared, allocation, selected, aiops_capture, retained=None):
    """Validate durable application CaC against any present source inventory rows.

    Native/certified inventory modules do not enforce our cross-repository VM
    identity schema; see ../README.md#cac-owned-related-resource-retirement.
    """
    records = [row for row in allocation["reservations"].values() if row.get("vm_name") == selected]
    require(len(records) == 1, "Resolve exactly one selected AAP reservation for source ownership.")
    record = records[0]
    route = _routing.instance_route(record["instance_route"])
    pin = route["hypervisor"]
    number = int(selected.rsplit("-", 1)[1])
    require(record.get("number") == number and record.get("hypervisor_id") == pin["machine_id"]
            and set(record.get("instance_resources", {})) <= {"aap"},
            "The allocation must retain only selected AAP ownership; migrate application data separately.")
    captured = [row for row in shared["host_inventory_configuration"]["hosts"]
                if inventory_variables(row).get("ansible_host") == pin["address"]]
    require(len(captured) == 1, "Resolve the pinned hypervisor in the fixed encrypted shared inventory.")
    hypervisor = captured[0]
    inventories = client.rows("inventories/?name=" + quote(hypervisor["inventory"]))
    require(len(inventories) == 1 and inventories[0].get("name") == hypervisor["inventory"],
            "Resolve exactly the captured source inventory by name.")
    inventory_id = inventories[0]["id"]
    rows = client.rows("hosts/?inventory=%s&page_size=200" % inventory_id)
    require(isinstance(rows, list) and len(rows) <= 256
            and all(row.get("inventory") == inventory_id for row in rows)
            and len({row.get("name") for row in rows}) == len(rows),
            "Source ownership requires bounded unique rows in the exact captured inventory.")
    live_hypervisors = [row for row in rows if row.get("name") == hypervisor["name"]]
    require(len(live_hypervisors) == 1, "Keep the existing pinned source hypervisor entry.")
    for values in (inventory_variables(hypervisor), inventory_variables(live_hypervisors[0])):
        require(values.get("ansible_host") == pin["address"] and values.get("machine_id") == pin["machine_id"]
                and values.get("ansible_port") == pin["port"] and values.get("ansible_user") == pin["user"]
                and values.get("host_keys") == pin["host_keys"],
                "Captured and live source hypervisor identity must match the exact registered pin.")
    names = {role + "-v%02d" % number: role for role in ("zabbix", "testserver1", "tra")}
    require(isinstance(aiops_capture, dict)
            and aiops_capture.get("cac_import_metadata", {}).get("project_id") == "aiops-selfhealing-demo"
            and isinstance(aiops_capture.get("aiops_instances"), dict),
            "Load authoritative application CaC through the existing protected reader before retirement.")
    aap_records = {row["vm_name"]: row for row in allocation["reservations"].values()
                   if row.get("instance_route", {}).get("hypervisor") == pin}
    # Keep all surviving same-hypervisor owners visible even when the external
    # controller has never imported their inventory. Deletion remains selected-only.
    fields = {"vm_name", "address", "uuid", "disk", "mac", "network", "bridge", "machine_id",
              "host_keys", "hypervisor_machine_id", "verified"}
    cac_resources, cac_numbers, cac_names = {}, {}, set(names)
    for instance_name, entry in aap_records.items():
        instance = aiops_capture["aiops_instances"].get(instance_name, {})
        require(isinstance(instance, dict), "Application CaC must contain instance mappings.")
        instance_number = entry["number"]
        require(type(instance_number) is int and instance_number > 0
                and instance_name == entry["instance_route"]["vm_name"]
                and re.fullmatch(r"aap[0-9]+-test-" + str(instance_number), instance_name)
                and entry.get("hypervisor_id") == pin["machine_id"],
                "Application owners must belong to registered numbered test instances on the pinned hypervisor.")
        for role in ("zabbix", "testserver1", "tra"):
            name = role + "-v%02d" % instance_number
            cac_names.add(name)
            resource = instance.get(role)
            if resource is None:
                continue
            if isinstance(resource, dict) and set(resource) == {"configuration"}:
                require(isinstance(resource["configuration"], dict), "Planned VM configuration must be a mapping.")
                continue
            require(isinstance(resource, dict) and fields <= set(resource)
                    and "supplemental_interfaces" not in resource and resource.get("kind") != "windows"
                    and resource.get("instance_name", instance_name) == instance_name
                    and type(resource.get("instance_number", instance_number)) is int
                    and resource.get("instance_number", instance_number) == instance_number,
                    "Application CaC requires complete same-instance VM ownership.")
            # Never copy runtime configuration or credentials into ownership proof.
            cac_resources[name] = {key: deepcopy(resource[key]) for key in fields}
            cac_numbers[name] = instance_number
    for field in ("uuid", "disk", "address", "mac", "machine_id"):
        identities = [resource[field] for resource in cac_resources.values()]
        require(all(isinstance(value, str) for value in identities) and len(set(identities)) == len(identities),
                "Application VM ownership identities must be distinct.")
    for row in rows:
        if row.get("name") not in cac_names:
            continue
        values = inventory_variables(row)
        resource = values.get("vm_resource")
        require(row["name"] in cac_resources and isinstance(resource, dict)
                and "supplemental_interfaces" not in resource and resource.get("kind") != "windows"
                and all(resource.get(key) == value for key, value in cac_resources[row["name"]].items())
                and values.get("hypervisor_host") == hypervisor["name"]
                and type(values.get("aap_instance_number")) is int
                and values["aap_instance_number"] == cac_numbers[row["name"]]
                and values.get("ansible_host") == resource["address"]
                and values.get("vm_uuid") == resource["uuid"]
                and values.get("machine_id") == resource["machine_id"]
                and values.get("host_keys") == resource["host_keys"],
                "Existing inventory ownership disagrees with authoritative application CaC.")
    cac_rows = [{"name": name, "variables": {
        "hypervisor_host": hypervisor["name"], "aap_instance_number": cac_numbers[name],
        "ansible_host": resource["address"], "vm_uuid": resource["uuid"],
        "machine_id": resource["machine_id"], "host_keys": resource["host_keys"],
        "vm_resource": resource}} for name, resource in cac_resources.items()]
    rows = [row for row in rows if row.get("name") not in cac_names] + cac_rows
    related, owners = {}, []

    def add_owner(resource):
        for nic in _management.primary_interfaces(resource, pin):
            identity = {"bridge": nic["bridge"], "ipv4": nic["address"], "mac": nic["mac"]}
            require(not any(old["ipv4"] == identity["ipv4"] or old["mac"] == identity["mac"] for old in owners),
                    "Remaining inventory guest permission ownership must be unique.")
            owners.append(identity)

    for instance_name, entry in aap_records.items():
        present = any(inventory_variables(row).get("vm_resource", {}).get("vm_name", row.get("name")) == instance_name
                      for row in rows)
        if not present and not entry.get("decommissioned") and entry.get("instance_resources", {}).get("aap"):
            primary = entry["instance_resources"]["aap"]
            validate_aap_primary(entry["instance_route"], primary)
            add_owner(primary)
    for row in rows:
        name, values = row.get("name"), inventory_variables(row)
        if name == hypervisor["name"]:
            continue
        if values.get("hypervisor_host") != hypervisor["name"]:
            require(name not in names, "A selected related VM points to a different hypervisor.")
            continue
        physical_name = values.get("vm_resource", {}).get("vm_name", name)
        if physical_name in aap_records:
            entry = aap_records[physical_name]
            resource = entry.get("instance_resources", {}).get("aap")
            validate_aap_primary(entry['instance_route'], resource)
            require(isinstance(resource, dict) and resource.get("verified") is True
                    and resource.get("hypervisor_machine_id") == pin["machine_id"]
                    and resource.get("address") == entry["instance_route"]["vm_ip"]
                    and resource.get("bridge") in pin["isolation_bridges"]
                    and isinstance(resource.get("uuid"), str)
                    and re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", resource["uuid"])
                    and resource.get("disk") == "/opt/vms/" + physical_name + ".disk.qcow2"
                    and isinstance(resource.get("mac"), str)
                    and re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", resource["mac"])
                    and not int(resource["mac"][:2], 16) & 1 and resource["mac"] != "00:00:00:00:00:00"
                    and values.get("ansible_host") == resource["address"]
                    and values.get("host_keys") == entry["instance_route"]["guest_host_keys"]
                    and type(values.get("aap_instance_number")) is int
                    and values["aap_instance_number"] == entry["number"],
                    "Remaining AAP permission ownership requires its verified source placement and resource.")
            if not entry.get("decommissioned"):
                require(values.get('vm_resource', {}).get('supplemental_interfaces') == resource.get('supplemental_interfaces'),
                        'Source and canonical AAP supplemental ownership must remain identical.')
                add_owner(resource)
            continue
        resource = values.get("vm_resource")
        require(name not in names or isinstance(resource, dict),
                "An existing selected related VM requires its complete source vm_resource.")
        if resource is None:
            continue
        require(isinstance(resource, dict) and 'supplemental_interfaces' not in resource,
                'Only a registered AAP primary may own the supplemental Windows interface.')
        if isinstance(resource, dict) and resource.get('kind') == 'windows':
            resource = windows_guest_resource(resource, pin)
            require(name == resource['vm_name'] and name not in names
                    and values.get('ansible_host') == resource['address']
                    and values.get('vm_uuid') == resource['uuid']
                    and values.get('computer_name') == resource['computer_name']
                    and values.get('computer_uuid') == resource['computer_uuid'],
                    'Unrelated Windows permissions require complete native trusted computer ownership.')
            for nic in resource['interfaces']:
                add_owner(nic)
            continue
        required = {"vm_name", "address", "uuid", "disk", "mac", "network", "bridge", "machine_id",
                    "host_keys", "hypervisor_machine_id", "verified"}
        require(isinstance(resource, dict) and required <= set(resource),
                "Source vm_resource must contain the complete verified guest artifact.")
        match = re.fullmatch(r"[a-z][a-z0-9-]*-v([0-9]{2,})", name or "")
        require(match is not None and name.endswith("-v%02d" % int(match[1])) and int(match[1]) > 0
                and resource["vm_name"] == name and resource["verified"] is True
                and resource["hypervisor_machine_id"] == pin["machine_id"]
                and resource["bridge"] in pin["isolation_bridges"]
                and isinstance(resource["network"], str)
                and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", resource["network"])
                and isinstance(resource["uuid"], str)
                and re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", resource["uuid"])
                and resource["uuid"] != "00000000-0000-0000-0000-000000000000"
                and isinstance(resource["disk"], str)
                and re.fullmatch(re.escape("/opt/vms/" + name) + r"(?:\.disk)?\.qcow2", resource["disk"])
                and isinstance(resource["mac"], str)
                and re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", resource["mac"])
                and not int(resource["mac"][:2], 16) & 1 and resource["mac"] != "00:00:00:00:00:00"
                and isinstance(resource["machine_id"], str) and re.fullmatch(r"[a-f0-9]{32}", resource["machine_id"])
                and resource["machine_id"] != pin["machine_id"]
                and type(values.get("aap_instance_number")) is int
                and values["aap_instance_number"] == int(match[1])
                and resource.get("aap_instance_number", int(match[1])) == int(match[1]),
                "Source vm_resource conflicts with its VM name, number, storage or pinned hypervisor.")
        _routing.ipv4(resource["address"])
        address = IPv4Address(resource["address"])
        require(not (address.is_unspecified or address.is_loopback or address.is_multicast or address.is_reserved),
                "Verified VM ownership requires a normalized unicast guest IPv4 address.")
        _routing.host_keys(resource["host_keys"])
        require(values.get("ansible_host") == resource["address"] and values.get("vm_uuid") == resource["uuid"]
                and values.get("machine_id") == resource["machine_id"] and values.get("host_keys") == resource["host_keys"],
                "Source host variables disagree with their verified vm_resource identity.")
        add_owner(resource)
        if name in names:
            require(values["aap_instance_number"] == number, "Selected related VM counter differs from the AAP instance.")
            related[names[name]] = deepcopy(resource)
    proof = {"instance_name": selected, "inventory_name": hypervisor["inventory"], "inventory_id": inventory_id,
             "hypervisor_name": hypervisor["name"], "hypervisor_machine_id": pin["machine_id"],
             "related_resources": related, "policy_owners": owners,
             "missing_roles": sorted(set(names.values()) - set(related))}
    if retained is not None:
        require(all(proof[key] == retained.get(key) for key in ("instance_name", "inventory_name", "inventory_id",
                    "hypervisor_name", "hypervisor_machine_id")), "Source resource scope changed during retirement.")
        require(related == retained["related_resources"],
                "Durable application CaC ownership changed during retirement.")
    return proof


def verify_remaining_guest_grants(policy, proof):
    """A missing optional source row cannot excuse an unowned surviving grant."""
    if proof["missing_roles"]:
        owners = {tuple(owner[key] for key in ("bridge", "ipv4", "mac")) for owner in proof["policy_owners"]}
        require(all(tuple(client[key] for key in ("bridge", "ipv4", "mac")) in owners
                    for client in policy.get("https_clients", []) + policy.get("guest_host_clients", []) + policy.get("released_clients", []) + policy.get("http_clients", [])),
                "Missing related VM rows require every remaining grant to have surviving verified inventory ownership.")


def isolation_retirement_context(record, selected, target, transition, related_resources=None):
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
            policy.get("protected_ipv4"), policy.get("guest_host_clients", []), policy.get("released_clients", []), policy.get("http_clients", [])) == policy,
            "Retirement policies must preserve the registered hypervisor's normalized isolation schema.")
    normalized(previous)
    normalized(desired)
    resources = record.get("instance_resources", {})
    require(isinstance(resources, dict), "Require existing selected guest ownership records.")
    if related_resources is not None:
        require(set(resources) <= {"aap"} and isinstance(related_resources, dict)
                and set(related_resources) <= {"zabbix", "testserver1", "tra"},
                "Keep application ownership in authoritative AIOps CaC, not central allocation.")
        resources = dict(resources, **deepcopy(related_resources))
    guests = []
    for role in ("aap", "zabbix", "testserver1", "tra"):
        metadata = resources.get(role, {})
        require(isinstance(metadata, dict), "Require mapping resource ownership records.")
        require(role == 'aap' or 'supplemental_interfaces' not in metadata,
                'Related application guests cannot borrow AAP supplemental-interface ownership.')
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
        if metadata and role == 'aap':
            validate_aap_primary(route, metadata)
        guests.append({"name": name, "role": role, "address": address, "metadata": deepcopy(metadata)})
    owned_nics = [(guest, nic) for guest in guests for nic in _management.primary_interfaces(guest['metadata'], pin)]
    require(isinstance(identities, list) and len(identities) <= len(owned_nics),
            "Retire only the exact NIC identities of the four selected deployment VMs.")
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
        matches = [(guest, nic) for guest, nic in owned_nics if nic.get('address', guest['address']) == identity['ipv4']]
        require(len(matches) == 1, "An isolation identity does not belong to a selected recorded guest.")
        guest, metadata = matches[0]
        require((guest["role"] == "aap" or metadata)
                and metadata.get("mac", identity["mac"]) == identity["mac"]
                and metadata.get("bridge", identity["bridge"]) == identity["bridge"],
                "An isolation identity differs from its existing selected guest record.")
        require(identity["ipv4"] not in addresses and identity["mac"] not in macs,
                "Selected guest retirement identities must be unique.")
        addresses.add(identity["ipv4"])
        macs.add(identity["mac"])
        key = tuple(identity[field] for field in ("bridge", "ipv4", "mac"))
        for client in previous.get("guest_host_clients", []) + previous.get("https_clients", []) + previous.get("released_clients", []) + previous.get("http_clients", []):
            require(not ((client["ipv4"] == identity["ipv4"] or client["mac"] == identity["mac"])
                         and tuple(client[field] for field in ("bridge", "ipv4", "mac")) != key),
                    "An isolation identity conflicts with an existing guest permission.")
        selected_keys.add(key)
    for client in previous.get("guest_host_clients", []) + previous.get("https_clients", []) + previous.get("released_clients", []) + previous.get("http_clients", []):
        if any(client['ipv4'] == nic.get('address', guest['address']) or client['mac'] == nic.get('mac') for guest, nic in owned_nics):
            require(tuple(client[field] for field in ("bridge", "ipv4", "mac")) in selected_keys,
                    "Retirement must include every existing permission of the selected recorded guests.")
    expected = deepcopy(previous)
    for field in ("https_clients", "guest_host_clients", "released_clients", "http_clients"):
        if field not in expected:
            continue
        retained = [client for client in expected[field]
                    if tuple(client[key] for key in ("bridge", "ipv4", "mac")) not in selected_keys]
        if retained != expected[field]:
            if retained:
                expected[field] = retained
            else:
                expected.pop(field)
                if not expected.get("https_clients") and not expected.get("released_clients") and not expected.get("http_clients"):
                    expected.pop("protected_ipv4", None)
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
            values.get("aap_hypervisor_isolation_host_clients", []), values.get("aap_hypervisor_isolation_released_clients", []), values.get("aap_hypervisor_isolation_http_clients", []))
        require(current in (old, new), "Canonical recovery policy changed beyond this exact retirement.")
        values.update(aap_hypervisor_isolation_https_clients=deepcopy(new.get("https_clients", [])),
            aap_hypervisor_isolation_protected_ipv4=deepcopy(new.get("protected_ipv4", [])),
            aap_hypervisor_isolation_host_clients=deepcopy(new.get("guest_host_clients", [])),
            **({"aap_hypervisor_isolation_released_clients": deepcopy(new.get("released_clients", []))}
               if new.get("released_clients") or "aap_hypervisor_isolation_released_clients" in values else {}))
        if "http_clients" in new or "aap_hypervisor_isolation_http_clients" in values:
            values["aap_hypervisor_isolation_http_clients"] = deepcopy(new.get("http_clients", []))
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


def source_retirement_variables(values, context, pinned=False):
    """Reconcile lagging API aliases only by exact verified identity removal."""
    values = deepcopy(values)
    pin, desired = context["route"]["hypervisor"], context["desired_policy"]
    selected = {tuple(identity[key] for key in ("bridge", "ipv4", "mac")) for identity in context["identities"]}
    policies = []
    if pinned:
        require(values.get("aap_hypervisor_pin") == pin, "Keep the exact registered source inventory pin.")
        policies.append(_routing.isolation_policy(pin, values.get("aap_hypervisor_isolation_https_clients", []),
            values.get("aap_hypervisor_isolation_protected_ipv4", []), values.get("aap_hypervisor_isolation_host_clients", []), values.get("aap_hypervisor_isolation_released_clients", []), values.get("aap_hypervisor_isolation_http_clients", [])))
    policies += [values[key] for key in ("isolation_policy", "hactar_isolation_policy") if key in values]
    removed_rules = set(context["removed_rules"])
    for policy in policies:
        require(isinstance(policy, dict) and _routing.isolation_policy(pin, policy.get("https_clients", []),
            policy.get("protected_ipv4"), policy.get("guest_host_clients", []), policy.get("released_clients", []), policy.get("http_clients", [])) == policy,
            "A lagging source policy must retain the normalized registered schema.")
        reduced = deepcopy(policy)
        for field in ("https_clients", "guest_host_clients", "released_clients", "http_clients"):
            if field not in reduced:
                continue
            retained = [client for client in reduced[field]
                        if tuple(client[key] for key in ("bridge", "ipv4", "mac")) not in selected]
            if retained != reduced[field]:
                if retained:
                    reduced[field] = retained
                else:
                    reduced.pop(field)
                    if not reduced.get("https_clients") and not reduced.get("released_clients") and not reduced.get("http_clients"):
                        reduced.pop("protected_ipv4", None)
        require(reduced == desired, "A source policy cannot change beyond exact selected identity retirement.")
        removed_rules.update('rule family="ipv4" priority="0" source address="%s/32" '
            'destination address="%s/32" port port="%s" protocol="tcp" accept'
            % (client["ipv4"], destination, port) for client in policy.get("guest_host_clients", [])
            if tuple(client[key] for key in ("bridge", "ipv4", "mac")) in selected
            for destination in client["destinations"] for port in client["ports"])
    # All present aliases have been proved above; absent aliases are populated from canonical policy.
    for key in ("isolation_policy", "hactar_isolation_policy"):
        values[key] = deepcopy(desired)
    if pinned:
        values.update(aap_hypervisor_isolation_https_clients=deepcopy(desired.get("https_clients", [])),
            aap_hypervisor_isolation_protected_ipv4=deepcopy(desired.get("protected_ipv4", [])),
            aap_hypervisor_isolation_host_clients=deepcopy(desired.get("guest_host_clients", [])),
            **({"aap_hypervisor_isolation_released_clients": deepcopy(desired.get("released_clients", []))}
               if desired.get("released_clients") or "aap_hypervisor_isolation_released_clients" in values else {}))
        if "http_clients" in desired or "aap_hypervisor_isolation_http_clients" in values:
            values["aap_hypervisor_isolation_http_clients"] = deepcopy(desired.get("http_clients", []))
    if "firewall_additional_zone_rules" in values:
        rules = values["firewall_additional_zone_rules"]
        require(isinstance(rules, list) and all(isinstance(rule, dict) for rule in rules),
                "Require explicit source native rule data before exact retirement.")
        values["firewall_additional_zone_rules"] = [rule for rule in rules
            if not (rule.get("zone") == "libvirt" and rule.get("rule") in removed_rules)]
    return values


def retirement_host_matches(row, guest, route, hypervisor_name):
    values = inventory_variables(row)
    require(values.get("ansible_host") == guest["address"]
            and values.get("hypervisor_host", hypervisor_name) == hypervisor_name,
            "A selected inventory guest has conflicting address or placement data.")
    metadata = guest["metadata"]
    if guest["role"] == "aap":
        require(values.get('vm_resource', {}).get('supplemental_interfaces') == metadata.get('supplemental_interfaces'),
                'Do not retire an AAP inventory row with conflicting supplemental ownership.')
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
        if metadata.get("kind") == "windows":
            require(all(values.get(field) == metadata[field] for field in ("computer_name", "computer_uuid")),
                    "Windows retirement requires the exact recorded trusted computer identity.")


def aap_inventory_owner(row, physical):
    """An inventory label may change; existing VM provenance identifies its owner."""
    resource = inventory_variables(row).get("vm_resource", {})
    return row.get("name") == physical or (isinstance(resource, dict) and resource.get("vm_name") == physical)


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
        removed = set()
        for guest in context["guests"]:
            rows = [row for row in data["hosts"] if (aap_inventory_owner(row, guest["name"])
                    if guest["role"] == "aap" else row.get("name") == guest["name"])
                    and row.get("inventory") == hypervisor["inventory"]]
            require(len(rows) <= 1, "Require unique guest rows in the exact captured shared inventory.")
            for row in rows:
                retirement_host_matches(row, guest, context["route"], hypervisor["name"])
                removed.add(row["name"])
                data["hosts"].remove(row)
        for group in data["groups"]:
            if group.get("inventory") == hypervisor["inventory"]:
                require(not any(guest["name"] in group.get("hosts", []) and guest["name"] not in removed
                                for guest in context["guests"]),
                        "Related group membership requires its existing recorded resource ownership.")
                group["hosts"] = [name for name in group.get("hosts", []) if name not in removed]
    return result


def canonical_api_port(value):
    """Normalize only canonical Controller wire text, retaining the exact port."""
    if isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,4}", value):
        value = int(value)
    require(type(value) is int and 1 <= value <= 65535,
            "The live hypervisor SSH port must be an exact canonical port.")
    return value


def source_inventory_operations(client, shared, autodeploy, hactar, context, policy_variables):
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

    def patch_hypervisor(captured, optional=False):
        if optional:
            matches = client.rows("inventories/?name=" + quote(captured["inventory"]))
            if not matches:
                identity = client.rows("me/")
                require(len(identity) == 1 and identity[0].get("is_superuser") is True,
                        "Verify administrator visibility before treating an optional Hactar alias as undeployed.")
                return None
        live_inventory = inventory(captured["inventory"])
        rows = host_rows(captured["name"], live_inventory["id"])
        require(len(rows) == 1, "Keep the existing pinned hypervisor inventory host.")
        row = rows[0]
        current = inventory_variables(row)
        require(current.get("ansible_host") == pin["address"],
                "The live hypervisor inventory address conflicts with its registered pin.")
        for field, expected in (("machine_id", pin["machine_id"]), ("ansible_port", pin["port"]),
                                ("ansible_user", pin["user"]), ("host_keys", pin["host_keys"])):
            require(field not in current or
                    (canonical_api_port(current[field]) == expected if field == "ansible_port"
                     else current[field] == expected),
                    "The live hypervisor inventory identity conflicts with its registered pin.")
        desired = policy_variables(current, context)
        if desired != current:
            operations[("PATCH", "hosts/%s/" % row["id"])] = {"variables": json.dumps(desired)}
        return live_inventory

    hosts = shared["host_inventory_configuration"]["hosts"]
    selected_hypervisors = [row for row in hosts if inventory_variables(row).get("ansible_host") == pin["address"]]
    require(len(selected_hypervisors) == 1, "Resolve one captured shared hypervisor for source retirement.")
    hypervisor = selected_hypervisors[0]
    shared_inventory = patch_hypervisor(hypervisor)
    for guest in context["guests"]:
        if guest["role"] == "aap":
            candidates = client.rows("hosts/?inventory=%s&page_size=200" % shared_inventory["id"])
            require(len(candidates) <= 256, "Read bounded source inventory before selected AAP retirement.")
            selected_rows = [row for row in candidates if aap_inventory_owner(row, guest["name"])]
            require(len(selected_rows) <= 1, "A physical AAP must have exactly one inventory label.")
        else:
            selected_rows = host_rows(guest["name"], shared_inventory["id"])
        for row in selected_rows:
            retirement_host_matches(row, guest, context["route"], hypervisor["name"])
            if guest["role"] != "aap":
                resource = inventory_variables(row).get("vm_resource")
                require(isinstance(resource, dict) and "supplemental_interfaces" not in resource
                        and all(resource.get(key) == value for key, value in guest["metadata"].items()),
                        "An extant related source VM ownership changed before deletion.")
            operations[("DELETE", "hosts/%s/" % row["id"])] = None

    recovery_rows = [row for row in autodeploy["autodeploy_configuration"]["inventories"]
                     if inventory_variables(row).get("aap_hypervisor_pin") == pin]
    require(len(recovery_rows) == 1, "Resolve one exact pinned recovery inventory for source synchronization.")
    live = inventory(recovery_rows[0]["name"])
    current = inventory_variables(live)
    desired = policy_variables(current, context, True)
    if current != desired:
        operations[("PATCH", "inventories/%s/" % live["id"])] = {"variables": json.dumps(desired)}
    if hactar is not None:
        for captured in hactar.get("controller_hosts_hactar_recovery", []):
            if inventory_variables(captured).get("ansible_host") == pin["address"]:
                patch_hypervisor(captured, optional=True)
    return [(method, path, body) for method in ("PATCH", "DELETE")
            for (operation, path), body in operations.items() if operation == method]


def source_retirement_operations(client, shared, autodeploy, hactar, context):
    return source_inventory_operations(client, shared, autodeploy, hactar, context, source_retirement_variables)


def _installation_policy_with_source_protection(configuration, route, policy):
    """Materialize canonical production protection only for the first installation grant."""
    if policy.get("protected_ipv4"):
        return policy
    source = configuration.get("aap_autodeploy_source_public_ip")
    try:
        address = IPv4Address(source) if isinstance(source, str) else None
    except ValueError:
        address = None
    pin = route["hypervisor"]
    require(address is not None and str(address) == source
            and not (address.is_unspecified or address.is_multicast or address.is_loopback
                     or address.is_link_local or address.is_reserved)
            and source not in (pin["address"], pin["public_ip"], route["vm_ip"]),
            "First installation access requires a distinct canonical source public IPv4 address.")
    declared = deepcopy(policy)
    declared["protected_ipv4"] = [source]
    return declared


def management_access_context(configuration, record, selected, route, requested, mode="management"):
    """Authorize one base-stage addition using existing canonical AAP ownership."""
    require(_routing.instance_route(record.get("instance_route")) == route
            and record.get("vm_name") == selected == route["vm_name"]
            and record.get("hypervisor_id") == route["hypervisor"]["machine_id"]
            and record.get("number") == int(selected.rsplit("-", 1)[1])
            and record.get("decommissioned") is not True
            and set(record.get("instance_resources", {})) == {"aap"},
            "Management publication requires the active exact AAP-only reservation.")
    primary = record["instance_resources"]["aap"]
    validate_aap_primary(route, primary)
    require(isinstance(primary, dict) and isinstance(primary.get("uuid"), str)
            and re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", primary["uuid"])
            and primary.get("vm_name", selected) == selected,
            "Management publication requires the recorded primary UUID and selected name.")
    pin = route["hypervisor"]
    inventories = [row for row in configuration["autodeploy_configuration"]["inventories"]
                   if inventory_variables(row).get("aap_hypervisor_pin") == pin]
    require(len(inventories) == 1, "Resolve the canonical pinned recovery policy before management publication.")
    values = inventory_variables(inventories[0])
    previous = _routing.isolation_policy(pin, values.get("aap_hypervisor_isolation_https_clients", []),
        values.get("aap_hypervisor_isolation_protected_ipv4", []), values.get("aap_hypervisor_isolation_host_clients", []), values.get("aap_hypervisor_isolation_released_clients", []), values.get("aap_hypervisor_isolation_http_clients", []))
    declared = (_installation_policy_with_source_protection(configuration, route, previous)
                if mode == "installation" else previous)
    try:
        desired = _management.desired_policy(route, primary, declared, mode)
    except (ValueError, KeyError):
        raise StoreError("Management publication differs from the existing selected AAP permission.") from None
    require(_routing.isolation_policy(pin, desired.get("https_clients", []), desired.get("protected_ipv4"),
            desired.get("guest_host_clients", []), desired.get("released_clients", []), desired.get("http_clients", [])) == desired
            and (requested is None or requested == desired),
            "Publish only the independently derived selected AAP management grant; preserve all other clients.")
    return {"route": deepcopy(route), "primary": deepcopy(primary), "previous_policy": previous,
            "desired_policy": desired, "guests": [], "removed_rules": set(), "access_mode": mode}


def supplemental_interface_context(configuration, shared, allocation, guest, pin, transition=None):
    """Change one declared Windows NIC without changing route, primary or permissions."""
    fields = {'kind', 'route', 'primary', 'guest_machine_id', 'supplemental_interface',
              'supplemental_state', 'connection_readback'}
    require(isinstance(guest, dict) and set(guest) == fields and guest['kind'] == 'aap',
            'Use only the existing AAP route and bounded supplemental connection request.')
    route, pin = _routing.instance_route(guest['route']), _routing.hypervisor_pin(pin)
    require(route['hypervisor'] == pin and isinstance(guest['guest_machine_id'], str)
            and re.fullmatch(r'[0-9a-f]{32}', guest['guest_machine_id'])
            and guest['guest_machine_id'] not in ('0' * 32, pin['machine_id']),
            'Bind supplemental networking to the pinned existing AAP and authenticated guest.')
    records = [row for row in allocation['aap_vm_allocation']['reservations'].values()
               if row.get('vm_name') == route['vm_name']]
    require(len(records) == 1, 'Resolve one consumed AAP reservation for supplemental networking.')
    record = records[0]
    context = management_access_context(configuration, record, route['vm_name'], route, None)
    current, supplied = context['primary'], guest['primary']
    validate_aap_primary(route, supplied)
    require(_management.same_primary(current, supplied), 'Supplemental networking cannot change primary ownership.')
    declaration = guest['supplemental_interface']
    desired = _management.desired_resource(current, declaration, guest['supplemental_state'], pin)
    _management.desired_resource(supplied, declaration, guest['supplemental_state'], pin)
    previous = current
    if current == desired and supplied != current:
        previous = supplied
    policy = context['previous_policy']
    require(all(nic['address'] not in policy.get('protected_ipv4', []) for nic in _management.primary_interfaces(desired, pin))
            and declaration['address'] not in (pin['address'], pin['public_ip'])
            and declaration['address'] not in policy.get('protected_ipv4', []),
            'Supplemental networking must preserve all hypervisor and production exclusions.')
    if transition is not None:
        require(isinstance(transition, dict) and set(transition) == {
                    'previous_policy', 'desired_policy', 'previous_resource', 'desired_resource'}
                and transition['previous_policy'] == transition['desired_policy'] == policy
                and transition['desired_resource'] == desired
                and current in (transition['previous_resource'], desired)
                and _management.same_primary(transition['previous_resource'], desired)
                and _management.desired_resource(transition['previous_resource'], declaration,
                                                guest['supplemental_state'], pin) == desired,
                'Publish only the planned exact supplemental ownership transition.')
        previous = transition['previous_resource']
        _management.connection_readback(guest)
    context.update(guest=deepcopy(guest), reservation=deepcopy(record), previous_resource=deepcopy(previous),
                   desired_resource=deepcopy(desired), desired_policy=deepcopy(policy), identities=[])
    rows = [row for row in shared['host_inventory_configuration']['hosts']
            if aap_inventory_owner(row, route['vm_name'])]
    require(len(rows) == 1, 'Use the existing uniquely owned main-inventory AAP entry.')
    hypervisors = [row for row in shared['host_inventory_configuration']['hosts']
                   if inventory_variables(row).get('ansible_host') == pin['address']]
    require(len(hypervisors) == 1 and rows[0].get('inventory') == hypervisors[0].get('inventory'),
            'Preserve AAP placement in the captured pinned hypervisor inventory.')
    context['hypervisor_name'] = hypervisors[0]['name']
    context['inventory_host_name'] = rows[0]['name']
    supplemental_host_variables(inventory_variables(rows[0]), context)
    # Every recorded NIC address and MAC must remain exclusive across AAP and
    # ordinary guest rows, including unrelated multi-interface Windows guests.
    for row in shared['host_inventory_configuration']['hosts']:
        if row is rows[0]:
            continue
        values = inventory_variables(row)
        resource = values.get('vm_resource', {})
        others = list(resource.get('interfaces', [resource])) if isinstance(resource, dict) else []
        if isinstance(resource, dict):
            others += resource.get('supplemental_interfaces', [])
        require(values.get('ansible_host') != declaration['address']
                and all(nic.get('address') != declaration['address'] and nic.get('mac') != declaration['mac'] for nic in others),
                'Another captured guest already owns the supplemental address or MAC.')
    for other in allocation['aap_vm_allocation']['reservations'].values():
        if other is record or other.get('decommissioned') or other.get('hypervisor_id') != pin['machine_id']:
            continue
        resource = other.get('instance_resources', {}).get('aap')
        if not resource:
            continue
        require(all(nic.get('address') != declaration['address'] and nic.get('mac') != declaration['mac']
                    and nic.get('connection_uuid') != declaration['connection_uuid']
                    for nic in _management.primary_interfaces(resource)),
                'Another consumed AAP reservation already owns the supplemental identity.')
    return context


def supplemental_host_variables(values, context):
    """Preserve host aliases, keys and unrelated variables while replacing exact NIC ownership."""
    result = deepcopy(values)
    route, primary, guest = context['route'], context['desired_resource'], context['guest']
    resource = result.get('vm_resource')
    require(isinstance(resource, dict) and resource.get('vm_name') == route['vm_name']
            and result.get('ansible_host') == route['vm_ip'] and result.get('vm_uuid') == primary['uuid']
            and result.get('hypervisor_host') == context['hypervisor_name']
            and result.get('host_keys') == route['guest_host_keys']
            and origin('https://' + result.get('ansible_fqdn', '')) == origin(route['aap_hostname']),
            'Keep the existing verified primary inventory placement and public identity.')
    number = result.get('aap_instance_number')
    if isinstance(number, str) and re.fullmatch(r'[1-9][0-9]{0,9}', number):
        number = int(number)
    require(type(number) is int and number == int(route['vm_name'].rsplit('-', 1)[1]),
            'Preserve the exact canonical selected AAP allocation number.')
    core = {key: resource[key] for key in _allocation.ownership.PRIMARY_FIELDS | {'supplemental_interfaces'} if key in resource}
    require(core in (context['previous_resource'], context['desired_resource'], guest['primary']),
            'The inventory supplemental declaration differs from the exact planned resources.')
    for machine_id in (result.get('machine_id'), resource.get('machine_id')):
        require(machine_id is None or machine_id == guest['guest_machine_id'],
                'The authenticated AAP machine identity changed from saved ownership.')
    resource.pop('supplemental_interfaces', None)
    resource.update(deepcopy(primary))
    result['vm_resource'] = resource
    return result


def supplemental_interface_capture(configuration, context, kind):
    result = deepcopy(configuration)
    if kind == 'allocation':
        rows = [row for row in result['aap_vm_allocation']['reservations'].values()
                if row.get('vm_name') == context['route']['vm_name']]
        require(len(rows) == 1 and rows[0] == context['reservation'],
                'The consumed reservation changed before supplemental publication.')
        rows[0]['instance_resources']['aap'] = deepcopy(context['desired_resource'])
    elif kind == 'shared':
        rows = [row for row in result['host_inventory_configuration']['hosts']
                if aap_inventory_owner(row, context['route']['vm_name'])]
        require(len(rows) == 1, 'Preserve one existing supplemental owner in the main inventory.')
        set_inventory_variables(rows[0], supplemental_host_variables(inventory_variables(rows[0]), context))
    else:
        require(kind in ('autodeploy', 'hactar'), 'Use only maintained supplemental ownership captures.')
    return result


def source_supplemental_interface_operations(client, shared, autodeploy, hactar, context):
    def unchanged_policy(values, selected_context, pinned=False):
        source_retirement_variables(values, selected_context, pinned)
        return deepcopy(values)
    operations = source_inventory_operations(client, shared, autodeploy, hactar, context, unchanged_policy)
    host = next(row for row in shared['host_inventory_configuration']['hosts']
                if aap_inventory_owner(row, context['route']['vm_name']))
    inventories = client.rows('inventories/?name=' + quote(host['inventory']))
    require(len(inventories) == 1, 'Keep the existing source inventory for the owned supplemental interface.')
    rows = client.rows('hosts/?inventory=%s&page_size=200' % inventories[0]['id'])
    require(len(rows) <= 256 and all(row.get('inventory') == inventories[0]['id'] for row in rows),
            'Read complete bounded source ownership before supplemental publication.')
    selected = [row for row in rows if aap_inventory_owner(row, context['route']['vm_name'])]
    require(len(selected) == 1 and selected[0].get('name') == host['name'],
            'Keep the same physical AAP and inventory alias during supplemental publication.')
    for row in rows:
        if row is selected[0]:
            continue
        values = inventory_variables(row)
        resource = values.get('vm_resource', {})
        others = list(resource.get('interfaces', [resource])) if isinstance(resource, dict) else []
        if isinstance(resource, dict):
            others += resource.get('supplemental_interfaces', [])
        nic = context['guest']['supplemental_interface']
        require(values.get('ansible_host') != nic['address']
                and all(item.get('address') != nic['address'] and item.get('mac') != nic['mac'] for item in others),
                'Another live source guest already owns the supplemental address or MAC.')
    old = inventory_variables(selected[0])
    updated = supplemental_host_variables(old, context)
    if old != updated:
        operations.append(('PATCH', 'hosts/%s/' % selected[0]['id'], {'variables': json.dumps(updated)}))
    return operations


def management_inventory_capture(configuration, context, kind):
    """Persist the selected policy and native rule without retiring inventory guests."""
    result = retire_inventory_capture(configuration, context, kind)
    pin = context["route"]["hypervisor"]
    if kind == "autodeploy":
        rows = [row for row in result["autodeploy_configuration"]["inventories"]
                if inventory_variables(row).get("aap_hypervisor_pin") == pin]
    else:
        hosts = (result["host_inventory_configuration"]["hosts"] if kind == "shared"
                 else result.get("controller_hosts_hactar_recovery", []))
        rows = [row for row in hosts if inventory_variables(row).get("ansible_host") == pin["address"]]
    for row in rows:
        set_inventory_variables(row, source_management_variables(inventory_variables(row), context, kind == "autodeploy"))
    return result


def source_management_variables(values, context, pinned=False):
    """Accept a lagging source alias only through the same exact management addition."""
    result = deepcopy(values)
    pin, desired = context["route"]["hypervisor"], context["desired_policy"]
    policies = []
    if pinned:
        require(result.get("aap_hypervisor_pin") == pin, "Keep the registered source recovery pin.")
        policies.append(_routing.isolation_policy(pin, result.get("aap_hypervisor_isolation_https_clients", []),
            result.get("aap_hypervisor_isolation_protected_ipv4", []), result.get("aap_hypervisor_isolation_host_clients", []), result.get("aap_hypervisor_isolation_released_clients", []), result.get("aap_hypervisor_isolation_http_clients", [])))
    policies += [result[key] for key in ("isolation_policy", "hactar_isolation_policy") if key in result]
    for policy in policies:
        require(isinstance(policy, dict) and _routing.isolation_policy(pin, policy.get("https_clients", []),
            policy.get("protected_ipv4"), policy.get("guest_host_clients", []), policy.get("released_clients", []), policy.get("http_clients", [])) == policy,
            "A source management policy must use the normalized registered schema.")
        declared = policy
        if context.get("access_mode") == "installation" and not policy.get("protected_ipv4"):
            require(policy in (context["previous_policy"], desired) and desired.get("protected_ipv4"),
                    "First installation source aliases must match the exact validated transition.")
            declared = deepcopy(policy)
            declared["protected_ipv4"] = deepcopy(desired["protected_ipv4"])
        try:
            expected = _management.desired_policy(context["route"], context["primary"], declared,
                context.get("access_mode", "management"))
        except (ValueError, KeyError):
            raise StoreError("A source management alias changed beyond the exact selected grant.") from None
        require(expected == desired, "A source alias cannot add or remove unrelated guest permissions.")
    for alias in ("isolation_policy", "hactar_isolation_policy"):
        result[alias] = deepcopy(desired)
    if pinned:
        result.update(aap_hypervisor_isolation_https_clients=deepcopy(desired["https_clients"]),
            aap_hypervisor_isolation_protected_ipv4=deepcopy(desired["protected_ipv4"]),
            aap_hypervisor_isolation_host_clients=deepcopy(desired["guest_host_clients"]),
            **({"aap_hypervisor_isolation_released_clients": deepcopy(desired["released_clients"])}
               if desired.get("released_clients") else ({"aap_hypervisor_isolation_released_clients": []}
               if "aap_hypervisor_isolation_released_clients" in result else {})))
        if "http_clients" in desired or "aap_hypervisor_isolation_http_clients" in result:
            result["aap_hypervisor_isolation_http_clients"] = deepcopy(desired.get("http_clients", []))
    # firewalld's base playbook consumes this explicit native-rule list, not
    # guest_host_clients. Persist only the current operation's approved pair.
    import shlex
    mode = context.get("access_mode", "management")
    require(mode in ("management", "installation"), "Choose one approved native management or installation grant.")
    primary = context["primary"]
    destination, port = (pin["public_ip"], 443) if mode == "installation" else (pin["address"], pin["port"])
    require(primary.get("verified") is True and primary.get("hypervisor_machine_id") == pin["machine_id"]
            and primary.get("address") == context["route"]["vm_ip"]
            and any(all(client.get(key) == primary.get(field) for key, field in (
                ("bridge", "bridge"), ("ipv4", "address"), ("mac", "mac")))
                and destination in client.get("destinations", []) and port in client.get("ports", [])
                for client in desired.get("guest_host_clients", [])),
            "Persist a native rule only for the verified selected guest's exact approved destination and port.")
    rule = ('rule family="ipv4" priority="0" source address="%s/32" destination address="%s/32" '
            'port port="%s" protocol="tcp" accept' % (primary["address"], destination, port))
    rules = result.setdefault("firewall_additional_zone_rules", [])
    require(isinstance(rules, list) and all(isinstance(row, dict) for row in rules),
            "Preserve explicit native zone-rule declarations before adding the selected grant.")
    tokens = shlex.split(rule)
    matching = []
    for row in rules:
        if row.get("zone") != "libvirt" or not isinstance(row.get("rule"), str):
            continue
        try:
            existing = shlex.split(row["rule"])
        except ValueError:
            raise StoreError("An existing native libvirt rule cannot be interpreted safely.") from None
        selected_source = any(existing[index] == "source" and index + 1 < len(existing)
            and existing[index + 1] in ("address=" + primary["address"], "address=" + primary["address"] + "/32")
            for index in range(len(existing)))
        selected_destination = any(existing[index] == "destination" and index + 1 < len(existing)
            and existing[index + 1] in ("address=" + destination, "address=" + destination + "/32")
            for index in range(len(existing)))
        selected_port = any(existing[index] == "port" and set(existing[index + 1:index + 3]) ==
            {"port=" + str(port), "protocol=tcp"} for index in range(len(existing)))
        if selected_source and selected_destination and selected_port:
            require(existing == tokens and row.get("state", "enabled") == "enabled",
                    "An existing selected native grant has a conflicting action or desired state.")
            matching.append(row)
    require(len(matching) <= 1, "Duplicate selected native rule declarations require review.")
    if not matching:
        rules.append({"zone": "libvirt", "rule": rule})
    return result


def source_management_operations(client, shared, autodeploy, hactar, context):
    operations = source_inventory_operations(client, shared, autodeploy, hactar, context, source_management_variables)
    host = next(row for row in shared["host_inventory_configuration"]["hosts"]
                if aap_inventory_owner(row, context["route"]["vm_name"]))
    inventories = client.rows("inventories/?name=" + quote(host["inventory"]))
    require(len(inventories) == 1, "Keep the exact shared inventory for primary registration.")
    rows = client.rows("hosts/?inventory=%s&name=%s" % (inventories[0]["id"], quote(host["name"])))
    require(len(rows) <= 1 and all(row.get("inventory") == inventories[0]["id"] and row.get("name") == host["name"] for row in rows),
            "Keep unique primary source placement within the captured inventory.")
    for row in rows:
        values = inventory_variables(row)
        require(values.get("ansible_host") == context["route"]["vm_ip"]
            and origin("https://" + values.get("ansible_fqdn", "")) == origin(context["route"]["aap_hostname"])
            and ("vm_uuid" not in values or values["vm_uuid"] == context["primary"]["uuid"])
            and ("vm_resource" not in values or all(values["vm_resource"].get(key) == value
                for key, value in context["primary"].items())),
            "Existing primary source ownership must match before publishing any management policy.")
    return operations


def installation_access_context(configuration, shared, allocation, route, primary, transition=None):
    """Authorize installer HTTPS only from the existing exact consumed reservation."""
    route = _routing.instance_route(route)
    records = [row for row in allocation["aap_vm_allocation"]["reservations"].values()
               if row.get("vm_name") == route["vm_name"]]
    require(len(records) == 1 and records[0].get("instance_resources", {}).get("aap") == primary,
            "Installation access requires the already-published exact primary ownership.")
    context = management_access_context(configuration, records[0], route["vm_name"], route, None, "installation")
    if transition is not None:
        require(isinstance(transition, dict) and set(transition) == {"previous_policy", "desired_policy"}
                and transition["desired_policy"] == context["desired_policy"],
                "Publish only the exact planned installer access transition.")
        old = transition["previous_policy"]
        pin = route["hypervisor"]
        require(_routing.isolation_policy(pin, old.get("https_clients", []), old.get("protected_ipv4"),
                old.get("guest_host_clients", []), old.get("released_clients", []), old.get("http_clients", [])) == old
                and _management.desired_policy(route, primary,
                    _installation_policy_with_source_protection(configuration, route, old),
                    "installation") == context["desired_policy"]
                and context["previous_policy"] in (old, context["desired_policy"]),
                "Installation access cannot replace another guest permission or production exclusion.")
        context["previous_policy"] = deepcopy(old)
    # Resolve a future display name once, while retaining physical registry/token keys.
    planned = merge_inventory(shared, route["vm_name"], route, context["desired_policy"], primary)
    hosts = planned["host_inventory_configuration"]["hosts"]
    selected = next(row for row in hosts if aap_inventory_owner(row, route["vm_name"]))
    context.update(inventory_name=selected["inventory"], inventory_host_name=selected["name"],
                   reservation=deepcopy(records[0]))
    return context


def installation_inventory_capture(configuration, context, kind):
    result = management_inventory_capture(configuration, context, kind)
    if kind == "shared":
        result = merge_inventory(result, context["route"]["vm_name"], context["route"],
                                 context["desired_policy"], context["primary"])
    return result


def source_installation_operations(client, shared, autodeploy, hactar, context):
    """Preflight existing policy aliases and the exact newly verified AAP placement."""
    operations = source_management_operations(client, shared, autodeploy, hactar, context)
    data = shared["host_inventory_configuration"]
    host = next(row for row in data["hosts"] if aap_inventory_owner(row, context["route"]["vm_name"]))
    inventories = client.rows("inventories/?name=" + quote(host["inventory"]))
    require(len(inventories) == 1, "Use the existing shared source inventory for AAP installation access.")
    identity = inventories[0]["id"]
    rows = client.rows("hosts/?inventory=%s&page_size=200" % identity)
    require(len(rows) <= 256 and all(row.get("inventory") == identity for row in rows),
            "Preflight bounded source AAP ownership before publication.")
    selected = [row for row in rows if aap_inventory_owner(row, context["route"]["vm_name"])]
    require(len(selected) <= 1 and all(row.get("name") == host["name"] for row in selected),
            "The same physical AAP cannot be registered under two source inventory labels.")
    primary = context["primary"]
    for row in rows:
        if row in selected:
            continue
        values = inventory_variables(row)
        resource = values.get("vm_resource", {})
        require(values.get("ansible_host") != primary["address"]
                and not any(resource.get(key) == primary[key] for key in ("uuid", "mac")),
                "Another source inventory host already owns the new AAP address, UUID or MAC.")
    desired = inventory_variables(host)
    if selected:
        old = inventory_variables(selected[0])
        merged = dict(old, **desired)
        if merged != old:
            operations.append(("PATCH", "hosts/%s/" % selected[0]["id"], {"variables": json.dumps(merged)}))
    else:
        operations.append(("POST", "hosts/", {"name": host["name"], "inventory": identity,
                           "variables": json.dumps(desired)}))
    groups = [row for row in data["groups"] if row.get("inventory") == identity or
              row.get("inventory") == host["inventory"]]
    captured = [row for row in groups if host["name"] in row.get("hosts", [])]
    require(len(captured) == 1, "Use one existing captured hypervisor placement group for the new AAP.")
    live_groups = client.rows("groups/?inventory=%s" % identity)
    matching = [row for row in live_groups if row.get("name") == captured[0]["name"]]
    require(len(matching) == 1 and inventory_variables(matching[0]).get("hypervisor_host") ==
            desired["hypervisor_host"], "The source placement group must identify the same hypervisor.")
    members = client.rows("groups/%s/hosts/" % matching[0]["id"])
    if not selected or selected[0]["id"] not in {row["id"] for row in members}:
        operations.append(("ASSOCIATE", "groups/%s/hosts/" % matching[0]["id"],
                           {"name": host["name"], "inventory": identity}))
    return operations


def aap_release_host_matches(row, guest, context):
    values = inventory_variables(row)
    route, primary = guest["route"], guest["primary"]
    resource = values.get("vm_resource", {})
    require(values.get("ansible_host") == route["vm_ip"]
            and values.get("hypervisor_host") == context["hypervisor_name"]
            and values.get("vm_uuid") == primary["uuid"]
            and values.get("host_keys") == route["guest_host_keys"]
            and origin("https://" + values.get("ansible_fqdn", "")) == origin(route["aap_hostname"])
            and isinstance(resource, dict) and resource.get("vm_name") == route["vm_name"]
            and all(resource.get(key) == value for key, value in primary.items()),
            "Final AAP release requires the existing published exact primary inventory identity.")
    for recorded in (values.get("machine_id"), resource.get("machine_id")):
        require(recorded is None or recorded == guest["guest_machine_id"],
                "Authenticated AAP machine identity changed from its recorded value.")


def aap_release_context(configuration, shared, allocation, guest, pin, transition=None):
    """Release only the existing consumed AAP primary; never treat it as a clone."""
    require(isinstance(guest, dict) and set(guest) == {"kind", "route", "primary", "guest_machine_id"}
            and guest["kind"] == "aap", "Use only the typed existing AAP route, primary and authenticated machine identity.")
    route, pin = _routing.instance_route(guest["route"]), _routing.hypervisor_pin(pin)
    require(route["hypervisor"] == pin and isinstance(guest["guest_machine_id"], str)
            and re.fullmatch(r"[a-f0-9]{32}", guest["guest_machine_id"])
            and guest["guest_machine_id"] != pin["machine_id"],
            "Final AAP release requires fresh authenticated guest facts on the registered hypervisor.")
    context = installation_access_context(configuration, shared, allocation, route, guest["primary"])
    previous = context["previous_policy"]
    require(previous.get("protected_ipv4") and guest["primary"]["address"] not in previous["protected_ipv4"],
            "Final AAP release must retain independently declared production protection.")
    identity = {key: guest["primary"][field] for key, field in (("bridge", "bridge"), ("ipv4", "address"), ("mac", "mac"))}
    desired = deepcopy(previous)
    matches = [row for row in desired.setdefault("released_clients", [])
               if row["ipv4"] == identity["ipv4"] or row["mac"] == identity["mac"]]
    require(not matches or matches == [identity], "Final AAP release conflicts with another guest's identity.")
    if not matches:
        desired["released_clients"].append(identity)
    require(_routing.isolation_policy(pin, desired.get("https_clients", []), desired.get("protected_ipv4"),
            desired.get("guest_host_clients", []), desired.get("released_clients", []), desired.get("http_clients", [])) == desired,
            "Final AAP release must preserve normalized production protection and all other grants.")
    if transition is not None:
        require(isinstance(transition, dict) and set(transition) == {"previous_policy", "desired_policy"}
                and transition["desired_policy"] == desired, "Publish only the exact planned AAP release.")
        old = transition["previous_policy"]
        require(isinstance(old, dict) and _routing.isolation_policy(pin, old.get("https_clients", []),
                old.get("protected_ipv4"), old.get("guest_host_clients", []), old.get("released_clients", []), old.get("http_clients", [])) == old,
                "Retain the exact normalized policy preceding AAP release.")
        derived = deepcopy(old)
        if identity not in derived.setdefault("released_clients", []):
            derived["released_clients"].append(identity)
        require(derived == desired and previous in (old, desired), "AAP release cannot replace another policy change.")
        previous = old
    hosts = shared["host_inventory_configuration"]["hosts"]
    hypervisors = [row for row in hosts if inventory_variables(row).get("ansible_host") == pin["address"]]
    require(len(hypervisors) == 1, "Resolve one exact published AAP hypervisor.")
    context.update(previous_policy=deepcopy(previous), desired_policy=desired, guest=deepcopy(guest["primary"]),
                   aap_guest=deepcopy(guest), access_mode="aap_release", hypervisor_name=hypervisors[0]["name"])
    selected = [row for row in hosts if row.get("inventory") == context["inventory_name"]
                and aap_inventory_owner(row, route["vm_name"])]
    require(len(selected) == 1, "Final AAP release cannot create a missing primary inventory record.")
    aap_release_host_matches(selected[0], guest, context)
    return context


def source_aap_release_operations(client, shared, autodeploy, hactar, context):
    """Update policy aliases only, requiring the already-published AAP host."""
    operations = source_inventory_operations(client, shared, autodeploy, hactar, context, guest_release_variables)
    inventories = client.rows("inventories/?name=" + quote(context["inventory_name"]))
    require(len(inventories) == 1, "Keep the exact published shared AAP inventory.")
    rows = client.rows("hosts/?inventory=%s&name=%s" % (inventories[0]["id"], quote(context["inventory_host_name"])))
    require(len(rows) == 1 and rows[0].get("inventory") == inventories[0]["id"],
            "Final AAP release requires exactly its existing published source host.")
    aap_release_host_matches(rows[0], context["aap_guest"], context)
    return operations


def merge_inventory(configuration, selected, route, policy, primary=None):
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
    matches = [row for row in data["hosts"] if aap_inventory_owner(row, selected)]
    require(len(matches) <= 1, "Resolve one inventory entry for the selected instance.")
    if matches:
        host = matches[0]
        values = inventory_variables(host)
        require(host["inventory"] == hypervisor["inventory"] and
                origin("https://" + values.get("ansible_fqdn", "")) == origin(route["aap_hostname"]),
                "Do not replace an existing inventory host pointing to a different AAP.")
    else:
        display_name = (selected.split("-", 1)[0] + "-v%02d" % int(match[1])) if primary is not None else selected
        require(not any(row.get("name") == display_name for row in data["hosts"]),
                "The new AAP inventory display name is already owned by another host.")
        host = {"name": display_name, "inventory": hypervisor["inventory"], "enabled": True}
        data["hosts"].append(host)
        values = {}
    values.update(ansible_host=route["vm_ip"], ansible_fqdn=urlsplit(origin(route["aap_hostname"])).hostname,
                  hypervisor_host=hypervisor["name"], aap_instance_number=int(match[1]), vm_ip=route["vm_ip"],
                  host_keys=deepcopy(route["guest_host_keys"]))
    set_inventory_variables(host, values)
    if primary is not None:
        _management.primary_interfaces(primary, pin)
        existing_resource = values.get("vm_resource", {})
        require(existing_resource.get('supplemental_interfaces') == primary.get('supplemental_interfaces'),
                'Only the bounded supplemental transaction may change declared AAP interfaces.')
        require(isinstance(existing_resource, dict) and all(key not in existing_resource or existing_resource[key] == value
                for key, value in primary.items()), "Preserve exact existing primary guest provenance.")
        values.update(vm_uuid=primary["uuid"], vm_resource={**existing_resource, **deepcopy(primary), "vm_name": selected})
        set_inventory_variables(host, values)
    groups = [row for row in data["groups"] if row["inventory"] == hypervisor["inventory"]
              and inventory_variables(row).get("hypervisor_host") == hypervisor["name"]]
    require(len(groups) == 1, "Define one VM inventory group mapped to the selected hypervisor.")
    if host["name"] not in groups[0].setdefault("hosts", []):
        groups[0]["hosts"].append(host["name"])
    return result


def ensure_source_inventory(client, configuration, selected, route):
    data = configuration["host_inventory_configuration"]
    host = next(row for row in data["hosts"] if aap_inventory_owner(row, selected))
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
            if desired is host and "vm_resource" in values:
                require(("vm_uuid" not in current or current["vm_uuid"] == values["vm_uuid"])
                    and ("vm_resource" not in current or all(
                        current["vm_resource"].get(key) == value for key, value in values["vm_resource"].items()
                        if key in current["vm_resource"])),
                    "The selected source AAP ownership differs from the registered primary resource.")
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



def guest_interfaces(guest):
    """Keep Windows NIC provenance explicit; legacy Linux remains one interface."""
    return guest["interfaces"] if guest.get("kind") == "windows" else [guest] + guest.get("supplemental_interfaces", [])


def guest_identities(guest):
    return [{"bridge": nic["bridge"], "ipv4": nic["address"], "mac": nic["mac"]}
            for nic in guest_interfaces(guest)]


def windows_guest_resource(guest, pin):
    required = {"kind", "vm_name", "instance_name", "uuid", "disk", "hypervisor_machine_id", "verified",
                "computer_name", "computer_uuid", "address", "interfaces", "winrm_certificate_validated"}
    require(isinstance(guest, dict) and set(guest) == required and guest["kind"] == "windows"
            and guest["verified"] is True and type(guest["winrm_certificate_validated"]) is bool,
            "Windows release requires complete WinRM identity and a Boolean certificate-validation result.")
    name = generic_retirement_name(guest["vm_name"])
    require(len(name) <= 15 and isinstance(guest["computer_name"], str)
            and re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{0,14}", guest["computer_name"])
            and guest["computer_name"].lower() == name and instance_name(guest["instance_name"])
            and guest["hypervisor_machine_id"] == pin["machine_id"]
            and isinstance(guest["uuid"], str)
            and re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", guest["uuid"])
            and guest["uuid"] != "00000000-0000-0000-0000-000000000000"
            and guest["computer_uuid"] == guest["uuid"]
            and guest["disk"] == "/opt/vms/win-" + name + "-clone.disk.qcow2",
            "Windows computer, native UUID, clone and selected hypervisor identity must agree.")
    interfaces = guest["interfaces"]
    require(isinstance(interfaces, list) and 1 <= len(interfaces) <= 2
            and all(isinstance(nic, dict) and set(nic) == {"network", "bridge", "mac", "address", "dns_name"}
                    for nic in interfaces), "Windows requires one or two exact permanent NIC mappings.")
    for nic in interfaces:
        require(isinstance(nic["network"], str) and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", nic["network"])
                and isinstance(nic["dns_name"], str)
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", nic["dns_name"]),
                "Windows NIC network and DNS reservation names must be exact safe values.")
    require(len({nic["mac"] for nic in interfaces}) == len(interfaces)
            and len({nic["address"] for nic in interfaces}) == len(interfaces)
            and guest["address"] in {nic["address"] for nic in interfaces},
            "Each Windows NIC needs unique verified identity; WinRM must select one of them.")
    _routing.isolation_policy(pin, [], [pin["public_ip"]], [], guest_identities(guest))
    return deepcopy(guest)


def guest_resource_conflicts(old, resource):
    if not isinstance(old, dict):
        return True
    old_nics = guest_interfaces(old)
    new_nics = guest_interfaces(resource)
    return (bool(old.get("uuid") and old["uuid"] == resource["uuid"])
            or bool(old.get("disk") and old["disk"] == resource["disk"])
            or any(left.get(field) == right[field] for left in old_nics for right in new_nics
                   for field in ("mac", "address") if left.get(field))
            or bool(old.get("machine_id") and old["machine_id"] == resource.get("machine_id")))


def released_guest_resource(guest, pin):
    """Keep the strict Linux default or explicitly typed verified Windows fields."""
    if isinstance(guest, dict) and guest.get("kind") == "windows":
        return windows_guest_resource(guest, pin)
    required = {"vm_name", "uuid", "disk", "network", "bridge", "mac", "address", "host_keys",
                "machine_id", "hypervisor_machine_id", "verified"}
    optional = {"user", "port", "source_image_sha256", "vcpus", "memory_mb", "disk_gb", "packages_updated"}
    require(isinstance(guest, dict) and required <= set(guest) and set(guest) <= required | optional,
            "Release only complete verified generic guest provenance without additional inputs.")
    name = guest["vm_name"]
    match = re.fullmatch(r"[a-z][a-z0-9-]*-v([0-9]{2,})", name or "")
    require(match is not None and int(match[1]) > 0 and name.endswith("-v%02d" % int(match[1]))
            and guest["verified"] is True and guest["hypervisor_machine_id"] == pin["machine_id"]
            and guest["bridge"] in pin["isolation_bridges"]
            and isinstance(guest["uuid"], str)
            and re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", guest["uuid"])
            and guest["uuid"] != "00000000-0000-0000-0000-000000000000"
            and isinstance(guest["disk"], str)
            and re.fullmatch(re.escape("/opt/vms/" + name) + r"(?:\.disk)?\.qcow2", guest["disk"])
            and isinstance(guest["network"], str)
            and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", guest["network"])
            and isinstance(guest["machine_id"], str) and re.fullmatch(r"[a-f0-9]{32}", guest["machine_id"])
            and guest["machine_id"] != pin["machine_id"],
            "Release requires the verified versioned guest UUID, disk, network and machine identity.")
    _routing.host_keys(guest["host_keys"])
    identity = {key: guest[field] for key, field in (("bridge", "bridge"), ("ipv4", "address"), ("mac", "mac"))}
    _routing.isolation_policy(pin, [], [pin["public_ip"]], [], [identity])
    return deepcopy(guest)


def guest_release_context(configuration, shared, guest, pin, transition=None, access="release"):
    """Derive one addition from canonical policy; never infer target ownership from an IP."""
    require(access in ("release", "bootstrap_https", "bootstrap_http"),
            "Choose full release or bounded guest bootstrap HTTP or HTTPS.")
    pin = _routing.hypervisor_pin(pin)
    resource = released_guest_resource(guest, pin)
    require(resource.get("kind") != "windows" or access == "release",
            "Windows release follows validated deployment; Windows bootstrap is not authorized here.")
    inventories = [row for row in configuration["autodeploy_configuration"]["inventories"]
                   if inventory_variables(row).get("aap_hypervisor_pin") == pin]
    require(len(inventories) == 1, "Resolve one canonical pinned recovery policy before release.")
    values = inventory_variables(inventories[0])
    previous = _routing.isolation_policy(pin, values.get("aap_hypervisor_isolation_https_clients", []),
        values.get("aap_hypervisor_isolation_protected_ipv4", []), values.get("aap_hypervisor_isolation_host_clients", []),
        values.get("aap_hypervisor_isolation_released_clients", []), values.get("aap_hypervisor_isolation_http_clients", []))
    require(previous.get("protected_ipv4") and pin["address"] not in previous["protected_ipv4"]
            and pin["public_ip"] not in previous["protected_ipv4"]
            and all(nic["address"] not in previous["protected_ipv4"] for nic in guest_interfaces(resource)),
            "Release must preserve independently declared production exclusions.")
    identities = guest_identities(resource)
    desired = deepcopy(previous)
    field = {"release": "released_clients", "bootstrap_https": "https_clients", "bootstrap_http": "http_clients"}[access]
    released = desired.setdefault(field, [])
    for identity in identities:
        matching = [item for item in released if item["ipv4"] == identity["ipv4"] or item["mac"] == identity["mac"]]
        require(not matching or matching == [identity], "An existing released guest identity conflicts with verified provenance.")
        if not matching:
            released.append(identity)
    require(_routing.isolation_policy(pin, desired.get("https_clients", []), desired.get("protected_ipv4"),
            desired.get("guest_host_clients", []), desired.get("released_clients", []), desired.get("http_clients", [])) == desired,
            "The selected release must preserve the complete normalized production-protected policy.")
    if transition is not None:
        require(isinstance(transition, dict) and set(transition) == {"previous_policy", "desired_policy"}
                and transition["desired_policy"] == desired,
                "Publication must match the exact planned and applied guest release.")
        original = transition["previous_policy"]
        require(isinstance(original, dict) and _routing.isolation_policy(pin, original.get("https_clients", []),
            original.get("protected_ipv4"), original.get("guest_host_clients", []), original.get("released_clients", []), original.get("http_clients", [])) == original,
            "Keep the normalized policy captured before the live release.")
        derived = deepcopy(original)
        for identity in identities:
            if identity not in derived.setdefault(field, []):
                derived[field].append(identity)
        require(derived == desired and previous in (original, desired),
                "A release cannot overwrite another guest permission or production exclusion.")
        previous = original
    hosts = shared["host_inventory_configuration"]["hosts"]
    hypervisors = [row for row in hosts if inventory_variables(row).get("ansible_host") == pin["address"]]
    require(len(hypervisors) == 1, "Resolve the exact hypervisor in the fixed shared inventory.")
    hypervisor = hypervisors[0]
    if access == "bootstrap_http":
        owned = [row for row in hosts if row.get("inventory") == hypervisor["inventory"]
                 and row.get("name") == resource["vm_name"]]
        require(len(owned) == 1, "HTTP bootstrap requires an already published guest owner.")
        owner = inventory_variables(owned[0])
        recorded = owner.get("vm_resource", {})
        require(isinstance(recorded, dict) and recorded.get("verified") is True
                and owner.get("hypervisor_host") == hypervisor["name"]
                and owner.get("ansible_host") == resource["address"]
                and owner.get("vm_uuid") == resource["uuid"]
                and ("source_image_sha256" not in resource
                     or recorded.get("source_image_sha256") == resource["source_image_sha256"])
                and all(key in recorded and recorded[key] == resource[key] for key in (
                    "vm_name", "uuid", "disk", "network", "bridge", "mac", "address", "host_keys",
                    "machine_id", "hypervisor_machine_id")),
                "HTTP bootstrap must match the already published complete guest identity.")
    for row in hosts:
        if row.get("inventory") != hypervisor["inventory"] or row.get("name") == resource["vm_name"]:
            continue
        values = inventory_variables(row)
        old = values.get("vm_resource", {})
        require(isinstance(old, dict) and values.get("ansible_host") not in {nic["address"] for nic in guest_interfaces(resource)}
                and not guest_resource_conflicts(old, resource),
                "Another captured host already owns this guest address or machine identity.")
    hypervisor_values = inventory_variables(hypervisor)
    if resource.get("kind") == "windows":
        owners = [row for row in hosts if row.get("inventory") == hypervisor["inventory"]
                  and aap_inventory_owner(row, resource["instance_name"])]
        require(len(owners) == 1 and inventory_variables(owners[0]).get("hypervisor_host") == hypervisor["name"]
                and str(inventory_variables(owners[0]).get("aap_instance_number")) == str(int(resource["vm_name"].rsplit("-v", 1)[1])),
                "The Windows clone must belong to the selected existing AAP instance on this hypervisor.")
    for field, expected in (("machine_id", pin["machine_id"]), ("ansible_user", pin["user"]),
                            ("ansible_port", pin["port"]), ("host_keys", pin["host_keys"])):
        require(hypervisor_values.get(field) == expected, "Shared hypervisor identity conflicts with the release pin.")
    context = {"route": {"hypervisor": deepcopy(pin)}, "previous_policy": deepcopy(previous),
               "desired_policy": desired, "guests": [], "removed_rules": set(), "guest": resource,
               "hypervisor_name": hypervisor["name"], "inventory_name": hypervisor["inventory"],
               "access_mode": access}
    # Validate capture placement and any extant guest identity before returning a plan.
    guest_release_inventory_capture(shared, context, "shared")
    return context


def guest_release_variables(values, context, pinned=False):
    """A lagging alias may differ only by this exact guest's release."""
    result = deepcopy(values)
    pin, previous, desired = context["route"]["hypervisor"], context["previous_policy"], context["desired_policy"]
    policies = [result[key] for key in ("isolation_policy", "hactar_isolation_policy") if key in result]
    if pinned:
        require(result.get("aap_hypervisor_pin") == pin, "Keep the exact recovery pin during release.")
        policies.append(_routing.isolation_policy(pin, result.get("aap_hypervisor_isolation_https_clients", []),
            result.get("aap_hypervisor_isolation_protected_ipv4", []), result.get("aap_hypervisor_isolation_host_clients", []),
            result.get("aap_hypervisor_isolation_released_clients", []), result.get("aap_hypervisor_isolation_http_clients", [])))
    identities = guest_identities(context["guest"])
    if context.get("access_mode") == "aap_release":
        identities = identities[:1]
    field = {"bootstrap_https": "https_clients", "bootstrap_http": "http_clients"}.get(context.get("access_mode"), "released_clients")
    for policy in policies:
        require(isinstance(policy, dict) and _routing.isolation_policy(pin, policy.get("https_clients", []),
            policy.get("protected_ipv4"), policy.get("guest_host_clients", []), policy.get("released_clients", []), policy.get("http_clients", [])) == policy,
            "A source release alias must keep the normalized production-protected schema.")
        derived = deepcopy(policy)
        for identity in identities:
            if identity not in derived.setdefault(field, []):
                derived[field].append(identity)
        require(derived == desired, "A policy alias changed beyond this exact verified guest release.")
    for key in ("isolation_policy", "hactar_isolation_policy"):
        result[key] = deepcopy(desired)
    if pinned:
        result.update(aap_hypervisor_isolation_https_clients=deepcopy(desired.get("https_clients", [])),
            aap_hypervisor_isolation_protected_ipv4=deepcopy(desired["protected_ipv4"]),
            aap_hypervisor_isolation_host_clients=deepcopy(desired.get("guest_host_clients", [])),
            aap_hypervisor_isolation_released_clients=deepcopy(desired.get("released_clients", [])))
        if "http_clients" in desired or "aap_hypervisor_isolation_http_clients" in result:
            result["aap_hypervisor_isolation_http_clients"] = deepcopy(desired.get("http_clients", []))
    return result


def guest_release_host_variables(values, context):
    resource, pin = context["guest"], context["route"]["hypervisor"]
    result = deepcopy(values)
    number = int(resource["vm_name"].rsplit("-v", 1)[1])
    expected = {"ansible_host": resource["address"], "hypervisor_host": context["hypervisor_name"],
                "vm_uuid": resource["uuid"], "aap_instance_number": number}
    if resource.get("kind") == "windows":
        require("machine_id" not in result and "host_keys" not in result,
                "A Windows inventory row cannot substitute for an existing Linux identity.")
        expected.update(computer_name=resource["computer_name"], computer_uuid=resource["computer_uuid"], ansible_connection="winrm")
        fields = tuple(resource)
    else:
        expected.update(machine_id=resource["machine_id"], host_keys=resource["host_keys"])
        # Keep verified SSH inputs for AIOps; no credential or port is inferred.
        # Justification: ../README.md#keep-the-demo-boundaries-clear
        if "user" in resource:
            expected["ansible_user"] = resource["user"]
        if "port" in resource:
            expected["ansible_port"] = resource["port"]
        fields = ("vm_name", "uuid", "disk", "network", "bridge", "mac", "address", "host_keys",
                  "machine_id", "hypervisor_machine_id", "verified")
    for field, value in expected.items():
        require(field not in result or result[field] == value, "An existing guest inventory row conflicts with verified provenance.")
    old = result.get("vm_resource", {})
    require(isinstance(old, dict), "Preserve the existing complete guest ownership mapping.")
    require(not old or (old.get("kind") == "windows") == (resource.get("kind") == "windows"),
            "Guest operating-system provenance cannot change in place.")
    for field in fields:
        require(field not in old or old[field] == resource[field], "An existing vm_resource conflicts with this verified guest.")
    result.update(expected)
    result["vm_resource"] = dict(old, **deepcopy(resource))
    return result


def guest_release_inventory_capture(configuration, context, kind):
    result = retire_inventory_capture(configuration, context, kind)
    if kind == "autodeploy":
        row = next(row for row in result["autodeploy_configuration"]["inventories"]
                   if inventory_variables(row).get("aap_hypervisor_pin") == context["route"]["hypervisor"])
        set_inventory_variables(row, guest_release_variables(inventory_variables(row), context, True))
    elif kind == "shared":
        data = result["host_inventory_configuration"]
        guests = [row for row in data["hosts"] if row.get("name") == context["guest"]["vm_name"]
                  and row.get("inventory") == context["inventory_name"]]
        require(len(guests) <= 1, "Register only one selected guest in the fixed shared inventory.")
        row = guests[0] if guests else {"name": context["guest"]["vm_name"], "inventory": context["inventory_name"], "variables": {}}
        set_inventory_variables(row, guest_release_host_variables(inventory_variables(row), context))
        if not guests:
            data["hosts"].append(row)
        groups = [row for row in data["groups"] if row.get("inventory") == context["inventory_name"]
                  and inventory_variables(row).get("hypervisor_host") == context["hypervisor_name"]]
        require(len(groups) == 1, "Use the existing unique guest placement group for the selected hypervisor.")
        group = groups[0]
        require(isinstance(group.get("hosts", []), list), "Keep explicit existing placement group members.")
        if context["guest"]["vm_name"] not in group.setdefault("hosts", []):
            group["hosts"].append(context["guest"]["vm_name"])
    return result


def source_guest_release_operations(client, shared, autodeploy, hactar, context):
    """Preflight all bounded writes before publication; register only verified guest ownership."""
    operations = source_inventory_operations(client, shared, autodeploy, hactar, context, guest_release_variables)
    inventories = client.rows("inventories/?name=" + quote(context["inventory_name"]))
    require(len(inventories) == 1, "Use exactly the captured shared inventory for guest release.")
    inventory_id = inventories[0]["id"]
    all_rows = client.rows("hosts/?inventory=%s&page_size=200" % inventory_id)
    require(len(all_rows) <= 256 and all(row.get("inventory") == inventory_id for row in all_rows),
            "Preflight the bounded current source guest ownership inventory.")
    name, resource = context["guest"]["vm_name"], context["guest"]
    for row in all_rows:
        values = inventory_variables(row)
        if row.get("name") == name:
            continue
        old = values.get("vm_resource", {})
        require(values.get("ansible_host") not in {nic["address"] for nic in guest_interfaces(resource)}
                and not guest_resource_conflicts(old, resource),
                "Another source host already owns this guest address or machine identity.")
    matches = [row for row in all_rows if row.get("name") == name]
    require(len(matches) <= 1, "The source guest name is not unique in the captured inventory.")
    if matches:
        row = matches[0]
        current = inventory_variables(row)
        desired = guest_release_host_variables(current, context)
        if desired != current:
            operations.append(("PATCH", "hosts/%s/" % row["id"], {"variables": json.dumps(desired)}))
    else:
        operations.append(("POST", "hosts/", {"name": name, "inventory": inventory_id,
            "variables": json.dumps(guest_release_host_variables({}, context))}))
    groups = client.rows("groups/?inventory=%s" % inventory_id)
    captured_groups = [row for row in shared["host_inventory_configuration"]["groups"]
        if row.get("inventory") == context["inventory_name"]
        and inventory_variables(row).get("hypervisor_host") == context["hypervisor_name"]]
    require(len(captured_groups) == 1, "Preserve the selected captured guest placement group.")
    matches_groups = [row for row in groups if row.get("name") == captured_groups[0]["name"]]
    require(len(matches_groups) == 1 and matches_groups[0].get("inventory", inventory_id) == inventory_id,
            "Use only the existing source placement group.")
    group = matches_groups[0]
    require(inventory_variables(group).get("hypervisor_host") == context["hypervisor_name"],
            "Keep the live placement group bound to the verified hypervisor.")
    members = client.rows("groups/%s/hosts/" % group["id"])
    if not matches or matches[0]["id"] not in {row["id"] for row in members}:
        # Resolve a freshly created ID only after the preflighted create completes.
        operations.append(("ASSOCIATE", "groups/%s/hosts/" % group["id"], {"name": name, "inventory": inventory_id}))
    return operations


def generic_retirement_name(name):
    """Use only a canonical generic guest name, never an AAP allocation name."""
    match = re.fullmatch(r"[a-z][a-z0-9-]{0,58}-v([0-9]{2,})", name or "")
    require(match is not None and int(match[1]) > 0 and name.endswith("-v%02d" % int(match[1]))
            and len(name) <= 63, "Select one exact canonical versioned generic guest.")
    return name


def generic_retirement_no_host_grants(values, guest):
    """Unknown selected host-service grants require review before physical deletion."""
    if guest is None:
        return
    addresses = {nic["address"] for nic in guest_interfaces(guest)}
    macs = {nic["mac"] for nic in guest_interfaces(guest)}
    for alias in ("isolation_policy", "hactar_isolation_policy"):
        for row in values.get(alias, {}).get("guest_host_clients", []):
            require(row.get("ipv4") not in addresses and row.get("mac") not in macs,
                    "Selected guest host-service grants require explicit supported cleanup before retirement.")
    for row in values.get("aap_hypervisor_isolation_host_clients", []):
        require(row.get("ipv4") not in addresses and row.get("mac") not in macs,
                "Selected guest host-service grants require explicit supported cleanup before retirement.")
    rules = values.get("firewall_additional_zone_rules", [])
    require(isinstance(rules, list) and all(isinstance(row, dict) for row in rules),
            "Inspect declared native grants before exact guest retirement.")
    for row in rules:
        rule = row.get("rule", "")
        require(isinstance(rule, str), "Inspect declared native rule text before retirement.")
        require(not any(re.search(r'\bsource\s+address="' + re.escape(address) + r'(?:/32)?"', rule) for address in addresses),
                "Selected native host-service rules require explicit supported cleanup before retirement.")


def generic_retirement_policy(policy, guest):
    """Remove this exact guest's HTTPS/full-release entries and no other permission."""
    result = deepcopy(policy)
    if guest is None:
        return result
    identities = guest_identities(guest)
    generic_retirement_no_host_grants({"isolation_policy": result}, guest)
    for field in ("https_clients", "released_clients", "http_clients"):
        retained = []
        for row in result.get(field, []):
            matching = [identity for identity in identities if row["ipv4"] == identity["ipv4"] or row["mac"] == identity["mac"]]
            if matching:
                require(matching == [row], "A selected retirement identity conflicts with another guest permission.")
            else:
                retained.append(row)
        if field in result and retained != result[field]:
            if retained:
                result[field] = retained
            else:
                result.pop(field)
    if not result.get("https_clients") and not result.get("released_clients") and not result.get("http_clients"):
        result.pop("protected_ipv4", None)
    return result


def generic_retirement_context(configuration, shared, client, name, pin, transition=None, guest_kind=None):
    """Resolve persisted exact ownership before deletion; a gone guest needs no SSH."""
    name, pin = generic_retirement_name(name), _routing.hypervisor_pin(pin)
    require(guest_kind in (None, "windows"), "Choose only the default Linux or explicit Windows retirement provenance.")
    require(guest_kind != "windows" or len(name) <= 15, "Windows retirement requires its exact safe computer name.")
    recovery = [row for row in configuration["autodeploy_configuration"]["inventories"]
                if inventory_variables(row).get("aap_hypervisor_pin") == pin]
    require(len(recovery) == 1, "Resolve one canonical pinned recovery inventory before guest retirement.")
    values = inventory_variables(recovery[0])
    previous = _routing.isolation_policy(pin, values.get("aap_hypervisor_isolation_https_clients", []),
        values.get("aap_hypervisor_isolation_protected_ipv4", []), values.get("aap_hypervisor_isolation_host_clients", []),
        values.get("aap_hypervisor_isolation_released_clients", []), values.get("aap_hypervisor_isolation_http_clients", []))
    data = shared["host_inventory_configuration"]
    hypervisors = [row for row in data["hosts"] if inventory_variables(row).get("ansible_host") == pin["address"]]
    require(len(hypervisors) == 1, "Resolve the fixed main-inventory hypervisor before exact guest retirement.")
    hypervisor = hypervisors[0]
    hypervisor_values = inventory_variables(hypervisor)
    for field, expected in (("machine_id", pin["machine_id"]), ("ansible_user", pin["user"]),
                            ("ansible_port", pin["port"]), ("host_keys", pin["host_keys"])):
        require(hypervisor_values.get(field) == expected, "The canonical retirement hypervisor identity changed.")
    captured = [row for row in data["hosts"] if row.get("inventory") == hypervisor["inventory"] and row.get("name") == name]
    require(len(captured) <= 1, "Resolve at most one exact canonical generic guest record.")
    inventories = client.rows("inventories/?name=" + quote(hypervisor["inventory"]))
    require(len(inventories) == 1 and inventories[0].get("name") == hypervisor["inventory"],
            "Resolve exactly the fixed source main inventory before retirement.")
    inventory_id = inventories[0]["id"]
    live = client.rows("hosts/?inventory=%s&page_size=200" % inventory_id)
    require(len(live) <= 256 and all(row.get("inventory") == inventory_id for row in live),
            "Read complete bounded source guest ownership before retirement.")
    matches = [row for row in live if row.get("name") == name]
    require(len(matches) <= 1, "Resolve at most one exact live generic guest record.")
    candidates = [inventory_variables(row).get("vm_resource") for row in captured + matches]
    require(all(isinstance(row, dict) for row in candidates), "Every extant guest record requires saved verified vm_resource.")
    require(not candidates or all(row == candidates[0] for row in candidates),
            "Canonical and source guest ownership disagree; resolve drift before retirement.")
    guest = deepcopy(candidates[0]) if candidates else None
    if transition is not None:
        require(isinstance(transition, dict) and set(transition) == {"previous_policy", "desired_policy", "guest"},
                "Publish only the exact preflighted generic guest retirement transition.")
        retained = transition["guest"]
        require(guest is None or guest == retained, "Guest ownership changed during the retirement transaction.")
        # A successful Git/API removal can precede final readback in this same job.
        # Retain only that already-preflighted resource, never an independently guessed record.
        if guest is None and retained is not None:
            require(previous == transition["desired_policy"], "A missing record cannot authorize a new policy change.")
            guest = deepcopy(retained)
    if guest is not None:
        guest = released_guest_resource(guest, pin)
        require(guest.get("kind") == guest_kind and guest["vm_name"] == name
                and (guest_kind == "windows" or (isinstance(guest.get("source_image_sha256"), str)
                     and re.fullmatch(r"[a-f0-9]{64}", guest["source_image_sha256"]))),
                "Retire only the saved verified guest provenance for this exact name.")
        for row in captured + matches:
            row_values = inventory_variables(row)
            require(row_values.get("ansible_host") == guest["address"]
                    and row_values.get("hypervisor_host") == hypervisor["name"]
                    and row_values.get("vm_uuid") == guest["uuid"]
                    and ((row_values.get("computer_name") == guest["computer_name"]
                          and row_values.get("computer_uuid") == guest["computer_uuid"])
                         if guest_kind == "windows" else
                         (row_values.get("machine_id") == guest["machine_id"]
                          and row_values.get("host_keys") == guest["host_keys"])),
                    "Exact guest ownership and placement must agree before retirement.")
        for row in data["hosts"] + live:
            if row.get("name") == name:
                continue
            row_values = inventory_variables(row)
            metadata = row_values.get("vm_resource", {})
            require(row_values.get("ansible_host") not in {nic["address"] for nic in guest_interfaces(guest)}
                    and not guest_resource_conflicts(metadata, guest),
                    "Another inventory host owns the selected guest identity or disk.")
    elif not captured:
        require(not any(name in row.get("hosts", []) for row in data["groups"]
                        if row.get("inventory") == hypervisor["inventory"]),
                "A missing guest record has orphaned captured group membership requiring review.")
    desired = generic_retirement_policy(previous, guest)
    if transition is not None:
        old = transition["previous_policy"]
        require(isinstance(old, dict) and _routing.isolation_policy(pin, old.get("https_clients", []),
                old.get("protected_ipv4"), old.get("guest_host_clients", []), old.get("released_clients", []), old.get("http_clients", [])) == old
                and generic_retirement_policy(old, guest) == transition["desired_policy"] == desired
                and previous in (old, desired), "A retirement transition changed beyond the exact selected guest.")
        previous = old
    require(_routing.isolation_policy(pin, desired.get("https_clients", []), desired.get("protected_ipv4"),
            desired.get("guest_host_clients", []), desired.get("released_clients", []), desired.get("http_clients", [])) == desired,
            "Retirement must preserve normalized production protection and other guest permissions.")
    identities = guest_identities(guest) if guest is not None else []
    context = {"route": {"hypervisor": deepcopy(pin)}, "guest": guest, "guest_name": name,
        "guests": ([{"name": name, "role": "generic", "address": guest["address"], "metadata": deepcopy(guest)}]
                   if guest is not None else []), "identities": identities, "removed_rules": set(),
        "previous_policy": deepcopy(previous), "desired_policy": deepcopy(desired),
        "inventory_name": hypervisor["inventory"], "hypervisor_name": hypervisor["name"],
        "records_absent": not captured and not matches}
    generic_retirement_no_host_grants(values, guest)
    generic_retirement_no_host_grants(hypervisor_values, guest)
    return context


def generic_retirement_capture(configuration, context, kind):
    """Reuse exact existing capture removal, refusing unsupported native grants."""
    if kind == "autodeploy":
        rows = configuration["autodeploy_configuration"]["inventories"]
    elif kind == "shared":
        rows = configuration["host_inventory_configuration"]["hosts"]
    else:
        rows = configuration.get("controller_hosts_hactar_recovery", [])
    for row in rows:
        values = inventory_variables(row)
        if values.get("ansible_host") == context["route"]["hypervisor"]["address"] or values.get("aap_hypervisor_pin") == context["route"]["hypervisor"]:
            generic_retirement_no_host_grants(values, context["guest"])
    return retire_inventory_capture(configuration, context, kind)


def source_generic_retirement_variables(values, context, pinned=False):
    generic_retirement_no_host_grants(values, context["guest"])
    return source_retirement_variables(values, context, pinned)


def source_generic_retirement_operations(client, shared, autodeploy, hactar, context):
    return source_inventory_operations(client, shared, autodeploy, hactar, context, source_generic_retirement_variables)
