"""Prepare one AIOps namespace from selected inventory and native API records.

These functions perform no API writes, VM discovery, Git writes or model calls.
Callers obtain the inventory/API records through the existing trusted importer.
Missing guests remain missing; their identities are never generated here.
"""

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import ipaddress
from pathlib import Path
import re
import secrets
import uuid
from urllib.parse import urlsplit

from ansible.utils.unsafe_proxy import wrap_var


ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = spec_from_file_location(name, ROOT / relative)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lifecycle = load("aiops_api_lifecycle", "src/cac_api_lifecycle.py")
routing = load("aiops_instance_routing", "filter_plugins/aap_instance_route.py")
keys = load("aiops_verified_instance_keys", "src/aap_instance_keys.py")
identity = load("aiops_inventory_identity", "filter_plugins/aap_inventory_identity.py")
require = lifecycle.require


def positive_id(value):
    return type(value) is int and value > 0


def selected_context(instance, hypervisor, hostname, zone, known_instances, selected_alias):
    """Bind names to the selected AAP's physical identity, not its renameable alias."""
    require(isinstance(instance, dict) and isinstance(hypervisor, dict)
            and isinstance(known_instances, dict), "Use the selected native inventory records.")
    resource = instance.get("vm_resource", {})
    name = identity.inventory_instance_name(selected_alias, instance)
    number = identity.inventory_counter(instance.get("aap_instance_number"))
    require(name == "aap27-test-%d" % number
            and resource.get("verified") is True
            and isinstance(instance.get("hypervisor_host"), str),
            "Select one verified AAP allocation and its existing hypervisor group.")
    expected_fqdn = routing.instance_public_name(name, zone)
    actual_fqdn = instance.get("ansible_fqdn")
    # Existing pre-naming-change allocations retain their actual URL. New
    # allocations must use the agreed vNN name; no guessed legacy URL is made.
    require(actual_fqdn == expected_fqdn or (name in known_instances
            and actual_fqdn == name + "." + zone),
            "New AAP names must follow the selected allocation's public naming scheme.")
    require(hostname == "https://" + actual_fqdn,
            "The authenticated target API must match the selected inventory FQDN.")
    managed_port = hypervisor.get("ansible_port")
    if isinstance(managed_port, str) and re.fullmatch(r"[1-9][0-9]{0,4}", managed_port):
        managed_port = int(managed_port)
    pin = routing.hypervisor_pin({
        "address": hypervisor.get("ansible_host"), "public_ip": hypervisor.get("public_ipv4"),
        "user": hypervisor.get("ansible_user"), "port": managed_port,
        "machine_id": hypervisor.get("machine_id"), "host_keys": hypervisor.get("host_keys"),
        "isolation_bridges": hypervisor.get("isolation_policy", {}).get("bridges"),
        "isolation_dns_bridges": hypervisor.get("isolation_policy", {}).get("dns_bridges"),
    })
    require(resource.get("hypervisor_machine_id") == pin["machine_id"]
            and resource.get("address") == instance.get("ansible_host")
            and resource.get("uuid") == instance.get("vm_uuid"),
            "Selected AAP placement and its native VM ownership must agree.")
    try:
        require(str(uuid.UUID(resource["uuid"])) == resource["uuid"], "Use the actual selected AAP UUID.")
        address = ipaddress.IPv4Address(resource["address"])
        require(address.is_private and not address.is_loopback and not address.is_link_local,
                "Use the verified private AAP address.")
    except (KeyError, TypeError, ValueError):
        raise lifecycle.LifecycleError("The selected AAP ownership record is incomplete.") from None
    version = "v%02d" % number
    return {"instance_name": name, "instance_number": number, "version": version,
            "aap_fqdn": actual_fqdn, "aap_origin": hostname, "aap_private_address": str(address), "zone": zone,
            "hypervisor_name": instance["hypervisor_host"], "hypervisor": pin,
            "website_fqdn": "redhat." + version + "." + zone,
            "zabbix_fqdn": "zabbix." + version + "." + zone}


def base_machine_credential(client, name):
    """Read exactly the configured existing native Machine credential; create nothing."""
    require(isinstance(name, str) and name.strip() == name and bool(name),
            "Configure the existing target base Machine credential name explicitly.")
    row = lifecycle.one(client.rows("/api/controller/v2/credentials/" + lifecycle.query(name=name)),
                        "configured target base Machine credential")
    require(row.get("name") == name and positive_id(row.get("id"))
            and positive_id(row.get("credential_type")), "The base Machine credential identity is incomplete.")
    kind = client.request("GET", "/api/controller/v2/credential_types/%s/" % row["credential_type"])
    require(kind.get("id") == row["credential_type"] and kind.get("kind") == "ssh"
            and kind.get("managed") is True, "Use the existing built-in Machine credential type.")
    return name


def runtime_document(value):
    require(isinstance(value, dict) and set(value) == {"schema_version", "instances"}
            and type(value["schema_version"]) is int and value["schema_version"] == 1
            and isinstance(value["instances"], dict), "Preserve the existing runtime Vault document schema.")
    require(all(re.fullmatch(r"aap27-test-[1-9][0-9]*", name or "") and isinstance(row, dict)
                for name, row in value["instances"].items()), "Runtime namespaces must identify existing allocation keys.")
    return deepcopy(value)


def same_material(old, new, label):
    require(old == new, "The existing " + label + " changed; preserve it for explicit review.")


def zabbix_resource(value, context, source_sha256):
    """Validate Zabbix's native clone provenance without imposing a Linux image schema."""
    require(isinstance(value, dict) and value.get("schema_version") == 1
            and type(value["schema_version"]) is int
            and value.get("instance_name") == context["instance_name"]
            and identity.inventory_counter(value.get("instance_number")) == context["instance_number"]
            and value.get("vm_name") == "zabbix-" + context["version"]
            and value.get("verified") is True
            and value.get("hypervisor_machine_id") == context["hypervisor"]["machine_id"],
            "Use Zabbix's verified native clone record for the same instance and hypervisor.")
    require(isinstance(source_sha256, str) and re.fullmatch(r"[a-f0-9]{64}", source_sha256)
            and value.get("source_sha256") == source_sha256
            and "source_image_sha256" not in value,
            "Zabbix must retain its own saved-image provenance, not a generic Linux image record.")
    try:
        address = ipaddress.IPv4Address(value["address"])
        require(str(address) == value["address"] and address.is_private and not address.is_loopback
                and not address.is_link_local and not address.is_multicast
                and value.get("ip") == str(address), "Use the native private Zabbix address.")
        require(str(uuid.UUID(value["uuid"])) == value["uuid"]
                and uuid.UUID(value["uuid"]).int > 0, "Use the native nonzero Zabbix domain UUID.")
        require(value.get("disk") == "/opt/vms/" + value["vm_name"] + ".disk.qcow2"
                and isinstance(value.get("network"), str)
                and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}", value["network"])
                and value.get("bridge") in context["hypervisor"]["isolation_bridges"]
                and re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", value.get("mac", ""))
                and not int(value["mac"][:2], 16) & 1 and value["mac"] != "00:00:00:00:00:00"
                and re.fullmatch(r"[a-f0-9]{32}", value.get("machine_id", ""))
                and value["machine_id"] != context["hypervisor"]["machine_id"],
                "Keep Zabbix's exact native disk, network, bridge and machine identity.")
        routing.host_keys(value.get("host_keys"))
        require(value.get("guest_host_keys") == value["host_keys"]
                and isinstance(value.get("user"), str) and re.fullmatch(r"[a-z_][a-z0-9_-]*", value["user"])
                and value["user"] != "root" and type(value.get("port")) is int and 1 <= value["port"] <= 65535,
                "Keep Zabbix's generated SSH public keys and existing management account.")
        version = context["version"]
        require(value.get("public_hostname") == context["zabbix_fqdn"]
                and value.get("certificate") == context["zabbix_fqdn"]
                and value.get("api_url") == "http://" + str(address) + "/api_jsonrpc.php"
                and value.get("nginx_file") == "/etc/nginx/conf.d/demo-zabbix-" + version + ".conf"
                and value.get("auth_file") == "/etc/nginx/demo-zabbix-" + version + ".htpasswd",
                "Keep only the selected Zabbix frontend, certificate and private API references.")
        for field in ("host_id", "item_id", "trigger_id", "mediatype_id", "action_id"):
            if field in value:
                require((positive_id(value[field]) or isinstance(value[field], str)
                        and len(value[field]) <= 63 and re.fullmatch(r"[1-9][0-9]*", value[field])),
                        "Retain native Zabbix API identifiers without fabricating or relabelling them.")
    except (KeyError, TypeError, ValueError):
        raise lifecycle.LifecycleError("Zabbix's native provenance is incomplete; preserve it for review.") from None
    return deepcopy(value)


def merge_source_guest(instances, context, role, source, zabbix_source_sha256=None):
    """Accept only an actual native inventory row for this exact created guest.

    The caller must pass the existing source inventory record, not launch data.
    This validates its saved provenance and prevents copying another allocation;
    it does not claim to discover or establish live identity by itself.
    """
    require(role in ("testserver1", "tra", "zabbix") and isinstance(source, dict),
            "Accept only one reviewed auxiliary VM role from native source inventory.")
    number, name = context["instance_number"], context["instance_name"]
    resource = source.get("vm_resource")
    expected_name = role + "-v%02d" % number
    require(isinstance(resource, dict) and resource.get("vm_name") == expected_name
            and source.get("hypervisor_host") == context["hypervisor_name"]
            and identity.inventory_counter(source.get("aap_instance_number")) == number,
            "A guest must belong to this allocation and selected hypervisor.")
    resource = (zabbix_resource(resource, context, zabbix_source_sha256) if role == "zabbix"
                else keys.released_guest_resource(resource, context["hypervisor"]))
    for field, resource_field in (("ansible_host", "address"), ("vm_uuid", "uuid"),
                                  ("machine_id", "machine_id"), ("host_keys", "host_keys"),
                                  ("ansible_user", "user"), ("ansible_port", "port")):
        require(source.get(field) == resource.get(resource_field),
                "The source guest inventory and its verified native provenance disagree.")
    for owner, row in instances.items():
        for other_role in ("testserver1", "tra", "zabbix"):
            other = row.get(other_role, {})
            if owner == name and other_role == role:
                continue
            require(not any(resource.get(field) == other.get(field)
                            for field in ("uuid", "mac", "machine_id"))
                    and not (resource["address"] == other.get("address")
                             and resource["hypervisor_machine_id"] == other.get("hypervisor_machine_id"))
                    and not set(resource["host_keys"]) & set(other.get("host_keys", [])),
                    "Another allocation or role already owns this guest identity.")
    result = deepcopy(instances)
    current = result[name].get(role)
    if current is not None:
        require(isinstance(current, dict) and all(current.get(field) == resource[field]
                for field in ("vm_name", "uuid", "disk", "network", "address", "mac", "machine_id",
                              "host_keys", "hypervisor_machine_id", "user", "port", "verified")),
                "An existing saved guest differs from native ownership; do not replace it.")
        if role == "zabbix":
            require(all(resource.get(field) == value for field, value in current.items() if field in resource),
                    "Existing Zabbix provenance changed; preserve its native records for review.")
        result[name][role] = dict(deepcopy(current), **deepcopy(resource))
    else:
        result[name][role] = deepcopy(resource)
    return result


def prepare_documents(capture, runtime, context, credential_name, source_hosts=None, password_factory=None,
                      mcp_access=None, authentication=None, subscription=None):
    """Seed only missing selected data and preserve every existing instance/secret."""
    require(isinstance(capture, dict) and isinstance(capture.get("aiops_instances"), dict),
            "Keep the reviewed AIOps capture and existing instance mapping.")
    result, settings = deepcopy(capture), runtime_document(runtime)
    instances = result["aiops_instances"]
    require(all(re.fullmatch(r"aap27-test-[1-9][0-9]*", name or "") and isinstance(row, dict)
                for name, row in instances.items()), "Existing instance settings must remain allocation mappings.")
    legacy = capture.get("aiops_event_stream_password")
    for existing_name, row in instances.items():
        if "event_stream_password" not in row:
            recorded = settings["instances"].get(existing_name, {}).get("demo_zabbix_event_stream", {})
            require(isinstance(recorded, dict), "Keep existing Event Stream runtime data as a mapping.")
            if not recorded:
                # A prepared but not-yet-imported namespace has no legacy
                # secret to inherit. Never copy the old environment's password
                # merely because someone created an empty mapping for it.
                continue
            require(isinstance(legacy, str) and len(legacy) >= 16 and recorded.get("password") == legacy,
                    "The existing runtime Event Stream password conflicts with the reviewed legacy material.")
            row["event_stream_password"] = wrap_var(legacy)
    name = context["instance_name"]
    if name not in instances:
        instances[name] = {"guest_machine_credential_name": credential_name, "testserver_monitoring_enabled": False}
    selected = instances[name]
    require(selected.get("guest_machine_credential_name") == credential_name,
            "The selected instance uses a different base Machine credential; preserve it for review.")
    if "event_stream_password" not in selected:
        require(not any(selected.get(role, {}).get("verified") is True for role in ("testserver1", "tra", "zabbix")),
                "An already deployed instance needs its known Event Stream password; never rotate it during preparation.")
        password = (password_factory or (lambda: secrets.token_urlsafe(48)))()
        require(isinstance(password, str) and len(password) >= 48 and not re.search(r"\s", password),
                "Generate one strong per-instance Event Stream password.")
        require(all(row.get("event_stream_password") != password for key, row in instances.items() if key != name),
                "A new allocation must not reuse another instance's Event Stream password.")
        selected["event_stream_password"] = wrap_var(password)
    require(isinstance(selected["event_stream_password"], str) and len(selected["event_stream_password"]) >= 16,
            "Keep the selected instance's persisted Event Stream password.")
    settings["instances"].setdefault(name, {})
    if subscription is not None:
        require(isinstance(subscription, dict) and set(subscription) == {"organization", "activation_keys"}
                and isinstance(subscription["organization"], str) and subscription["organization"].strip()
                and isinstance(subscription["activation_keys"], list) and subscription["activation_keys"]
                and all(isinstance(key, str) and key.strip() for key in subscription["activation_keys"]),
                "Use the existing protected RHSM organization and activation keys.")
        desired_subscription = wrap_var({
            "instance_name": name, "organization": subscription["organization"],
            "activation_keys": deepcopy(subscription["activation_keys"]),
            "repositories": [
                {"name": "rhel-9-for-x86_64-baseos-rpms", "state": "enabled"},
                {"name": "rhel-9-for-x86_64-appstream-rpms", "state": "enabled"},
            ],
        })
        existing_subscription = settings["instances"][name].get("demo_mcp_subscription")
        require(existing_subscription is None or existing_subscription == desired_subscription,
                "Existing selected RHSM inputs differ; review replacement explicitly without rotating credentials.")
        settings["instances"][name]["demo_mcp_subscription"] = desired_subscription
    if mcp_access is not None:
        connection = keys.mcp_connection(mcp_access)
        require(connection["url"] == "https://" + context["aap_private_address"] + ":8448/mcp"
                and isinstance(authentication, dict) and authentication.get("hostname") == context["aap_origin"]
                and isinstance(authentication.get("token"), str) and authentication["token"],
                "Bind private MCP access only to this selected verified AAP instance.")
        desired_access = wrap_var(dict(connection, instance_name=name, token=authentication["token"]))
        existing_access = settings["instances"][name].get("demo_aap_mcp")
        require(existing_access is None or existing_access == desired_access,
                "Existing selected AAP MCP access differs; review token or CA replacement explicitly.")
        settings["instances"][name]["demo_aap_mcp"] = desired_access
    for role in ("testserver1", "tra", "zabbix"):
        source_name = role + "-v%02d" % context["instance_number"]
        if source_name in (source_hosts or {}):
            instances = merge_source_guest(instances, context, role, source_hosts[source_name],
                result.get("aiops_zabbix_source_image", {}).get("sha256"))
    result["aiops_instances"] = instances
    return result, settings


def target_readbacks(client, context, resources):
    """Read generated target identifiers and secret material without creating/rotating anything."""
    require(client.hostname == context["aap_origin"], "Read generated resources only from the authenticated selected AAP.")
    definition = lifecycle.one([row for row in resources["controller_templates"]
                               if row.get("playbook") == "playbooks/inject_website_fault.yml"],
                              "reviewed website fault template definition")
    require(definition.get("webhook_service") == "gitlab", "The reviewed fault template needs its existing GitLab webhook.")
    project = lifecycle.one(client.rows("/api/controller/v2/projects/" + lifecycle.query(name=definition["project"])),
                           "selected fault-template SCM project")
    template = lifecycle.one(client.rows("/api/controller/v2/job_templates/" + lifecycle.query(
        name=definition["name"], project=project["id"])), "selected native website fault template")
    require(positive_id(template.get("id")) and template.get("project") == project["id"]
            and template.get("name") == definition["name"] and template.get("playbook") == definition["playbook"]
            and template.get("webhook_service") == "gitlab", "The target fault template conflicts with its reviewed definition.")
    webhook = client.request("GET", "/api/controller/v2/job_templates/%d/webhook_key/" % template["id"])
    require(isinstance(webhook, dict) and isinstance(webhook.get("webhook_key"), str)
            and re.fullmatch(r"[A-Za-z0-9_-]{16,256}", webhook["webhook_key"]),
            "Read the existing generated webhook key; never rotate or synthesize it.")
    stream_definition = lifecycle.one(resources["eda_event_streams"], "reviewed AIOps Event Stream definition")
    stream = lifecycle.one(client.rows("/api/eda/v1/event-streams/" + lifecycle.query(name=stream_definition["name"])),
                           "selected native AIOps Event Stream")
    organization = stream_definition.get("organization", stream_definition.get("organization_name"))
    require(stream.get("name") == stream_definition["name"]
            and stream.get("organization", {}).get("name") == organization,
            "The target Event Stream belongs to another reviewed organization.")
    try:
        identity = str(uuid.UUID(stream["uuid"]))
        path = "/eda-event-streams/api/eda/v1/external_event_stream/" + identity + "/post/"
        endpoint = context["aap_origin"] + path
        native_url = stream.get("url")
        require(isinstance(native_url, str) and not any(char.isspace() for char in native_url),
                "Read the target-native HTTPS Event Stream endpoint without control characters.")
        native = urlsplit(native_url)
        require(stream["uuid"] == identity and native.scheme == "https"
                and native.netloc in (context["aap_fqdn"], context["aap_fqdn"] + ":443")
                and native.path == path and not native.username and not native.password
                and not native.query and not native.fragment,
                "Read the target-native Event Stream UUID and its selected-instance HTTPS URL.")
    except (KeyError, TypeError, ValueError):
        raise lifecycle.LifecycleError("The target Event Stream has no verified native endpoint.") from None
    credential_name = stream_definition["credential_name"]
    credential = lifecycle.one([row for row in resources["eda_credentials"] if row.get("name") == credential_name],
                               "reviewed Event Stream authentication definition")
    inputs = credential.get("inputs", {})
    require(inputs.get("auth_type") == "basic" and isinstance(inputs.get("username"), str)
            and inputs["username"] and isinstance(inputs.get("password"), str)
            and len(inputs["password"]) >= 16
            and stream.get("eda_credential", {}).get("name") == credential_name
            and stream["eda_credential"].get("inputs", {}).get("username") == inputs["username"],
            "Bind Event Stream delivery only to its reviewed target Basic credential.")
    return {"demo_website_fault_template_id": template["id"],
            "demo_website_webhook_key": wrap_var(webhook["webhook_key"]),
            "demo_zabbix_event_stream": wrap_var({"url": endpoint, "username": inputs["username"],
                                                  "password": inputs["password"]})}


def complete_documents(capture, runtime, context, readbacks):
    """Persist native target data only when it agrees with saved credentials/identities."""
    result, settings = deepcopy(capture), runtime_document(runtime)
    name = context["instance_name"]
    require(name in capture["aiops_instances"] and name in settings["instances"],
            "Persist pre-import settings before accepting target-generated resources.")
    require(set(readbacks) == {"demo_website_fault_template_id", "demo_website_webhook_key", "demo_zabbix_event_stream"},
            "Accept only reviewed target-native resource readbacks.")
    same_material(capture["aiops_instances"][name]["event_stream_password"],
                  readbacks["demo_zabbix_event_stream"]["password"], "selected Event Stream password")
    selected = settings["instances"][name]
    for field, value in readbacks.items():
        if field in selected:
            if field == "demo_zabbix_event_stream":
                old = selected[field]
                require(isinstance(old, dict) and set(old) == set(value) == {"url", "username", "password"},
                        "Keep only the reviewed saved Event Stream endpoint and Basic credential fields.")
                same_material({key: old[key] for key in ("username", "password")},
                              {key: value[key] for key in ("username", "password")}, "target Event Stream credentials")
                canonical = value["url"]
                require(canonical.startswith(context["aap_origin"] + "/")
                        and old["url"] in (canonical, canonical.replace(context["aap_origin"],
                            "https://" + context["aap_fqdn"] + ":443", 1)),
                        "The existing Event Stream URL changed beyond an equivalent default HTTPS port.")
                # The API serializes :443 explicitly. Keep an already saved
                # equivalent URL verbatim so a repeat import changes no secret
                # material or runtime ciphertext merely to normalize the port.
            else:
                same_material(selected[field], value, "target-native runtime value")
        else:
            selected[field] = deepcopy(value)
    return result, settings
