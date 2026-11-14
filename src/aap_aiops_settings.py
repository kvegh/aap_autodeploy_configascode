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

from ansible.template import trust_as_template
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
    return (isinstance(value, int) and not isinstance(value, bool)) and value > 0


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
            and (isinstance(value["schema_version"], int) and not isinstance(value["schema_version"], bool)) and value["schema_version"] == 1
            and isinstance(value["instances"], dict), "Preserve the existing runtime Vault document schema.")
    require(all(re.fullmatch(r"aap27-test-[1-9][0-9]*", name or "") and isinstance(row, dict)
                for name, row in value["instances"].items()), "Runtime namespaces must identify existing allocation keys.")
    return deepcopy(value)


def same_material(old, new, label):
    require(old == new, "The existing " + label + " changed; preserve it for explicit review.")


def zabbix_import_binding(data, context):
    """Bind the existing target-local importer and its actual inventory alias."""
    require(isinstance(data, dict) and set(data) == {"importer", "hosts", "groups"},
            "Read the existing AIOps importer and its native inventory before preparing the VM configuration.")
    importer, hosts = data["importer"], data["hosts"]
    require(isinstance(importer, dict) and positive_id(importer.get("id"))
            and positive_id(importer.get("inventory"))
            and importer.get("playbook") == "deploy-cac-project.yml"
            and keys.inventory_variables({"variables": importer.get("extra_vars", {})}).get("aap_cac_project_id") == "aiops-selfhealing-demo"
            and isinstance(hosts, list) and len(hosts) <= 256,
            "Use the existing saved AIOps importer and bounded source inventory.")
    selected = []
    for row in hosts:
        require(isinstance(row, dict) and row.get("inventory") == importer["inventory"],
                "Every source host must belong to the importer's existing inventory.")
        value = keys.inventory_variables(row)
        resource = value.get("vm_resource", {})
        if resource.get("vm_name") == context["instance_name"]:
            require(resource.get("verified") is True and value.get("ansible_fqdn") == context["aap_fqdn"]
                    and value.get("hypervisor_host") == context["hypervisor_name"]
                    and resource.get("hypervisor_machine_id") == context["hypervisor"]["machine_id"],
                    "The importer inventory must identify this exact selected AAP and hypervisor.")
            selected.append(row)
    require(len(selected) == 1 and isinstance(selected[0].get("name"), str),
            "Resolve exactly one native inventory alias for the selected AAP.")
    groups = data["groups"]
    require(isinstance(groups, list) and len(groups) <= 256,
            "Read the existing bounded hypervisor placement groups.")
    placement = [row for row in groups if row.get("inventory") == importer["inventory"]
                 and keys.inventory_variables(row).get("hypervisor_host") == context["hypervisor_name"]]
    require(len(placement) == 1 and positive_id(placement[0].get("id")),
            "Use exactly the existing placement group for this hypervisor.")
    return {"controller_host": context["aap_origin"], "inventory_id": importer["inventory"],
            "job_template_id": importer["id"], "group_id": placement[0]["id"],
            "aap_instance_key": selected[0]["name"]}


def prepare_zabbix_configuration(capture, context, binding=None, new_owners=()):
    """Keep the permission and importer settings inside their existing VM section."""
    instances = capture["aiops_instances"]
    for name, row in instances.items():
        if "firewall" not in row and "zabbix" not in row:
            continue
        vm = row.get("zabbix")
        require(vm is None or isinstance(vm, dict), "Preserve the existing Zabbix VM definition.")
        vm = row.setdefault("zabbix", {}) if vm is not None else {}
        row["zabbix"] = vm
        configuration = vm.setdefault("configuration", {})
        require(isinstance(configuration, dict), "Keep Zabbix configuration inside its VM definition.")
        old = row.pop("firewall", None)
        if old is not None:
            require(isinstance(old, dict) and ("firewall" not in configuration or configuration["firewall"] == old),
                    "Conflicting firewall copies require review; no parallel ownership is retained.")
            configuration["firewall"] = old
        firewall = configuration.setdefault("firewall", {"guest_host_clients": []})
        require(isinstance(firewall, dict) and set(firewall) == {"guest_host_clients"}
                and isinstance(firewall["guest_host_clients"], list) and len(firewall["guest_host_clients"]) <= 1,
                "Keep only this VM's explicit firewall configuration.")
        require(not (vm.get("verified") is True and name in new_owners) or "gateway" in vm,
                "A freshly published Zabbix owner needs its observed native gateway.")
        require(not firewall['guest_host_clients'] or vm.get('verified') is True,
                'Declared Zabbix permissions require its verified VM owner.')
        if vm.get("verified") is True and "gateway" in vm:
            gateway = str(ipaddress.IPv4Address(vm["gateway"]))
            require(gateway == vm["gateway"] and gateway != vm["address"]
                    and ipaddress.IPv4Address(gateway).is_private,
                    "Use the bridge gateway observed with this verified guest.")
            grant = {"bridge": vm["bridge"], "ipv4": vm["address"], "mac": vm["mac"],
                     "destinations": [gateway], "ports": [443]}
            require(not firewall["guest_host_clients"] or firewall["guest_host_clients"] == [grant],
                    "The existing Zabbix grant differs from its verified native resource.")
            if name in new_owners:
                firewall["guest_host_clients"] = [grant]
    if binding is not None:
        row = instances[context["instance_name"]]
        configuration = row.setdefault("zabbix", {}).setdefault("configuration", {})
        configuration.setdefault("firewall", {"guest_host_clients": []})
        require("cac_import" not in configuration or configuration["cac_import"] == binding,
                "The existing Zabbix CaC importer binding changed; preserve it for review.")
        configuration["cac_import"] = deepcopy(binding)
    for row in capture.get("controller_hosts_aiops_demo", []):
        deployment = row.get("variables", {}).get("demo_zabbix_deployment")
        if not isinstance(deployment, dict):
            continue
        deployment.pop("guest_user", None)
        deployment.pop("guest_authorized_public_key", None)
        deployment["cac_import"] = trust_as_template(
            "{{ aiops_instances[hostvars[aap_instance_key].vm_resource.vm_name].zabbix.configuration.cac_import }}")
        policy = deployment.get("isolation_policy")
        if isinstance(policy, str):
            old_path = "map(attribute='firewall.guest_host_clients')"
            new_path = "map(attribute='zabbix.configuration.firewall.guest_host_clients')"
            require(old_path in policy or new_path in policy,
                    "Review the maintained Zabbix policy projection before changing its VM section.")
            policy = policy.replace(old_path, new_path)
            defined = "selectattr('zabbix.hypervisor_machine_id', 'defined')"
            if defined not in policy:
                match = "selectattr('zabbix.hypervisor_machine_id', 'equalto',"
                require(match in policy, "Keep the explicit hypervisor filter in the maintained projection.")
                policy = policy.replace(match, defined + " | " + match)
            # This reviewed projection is executable CaC, rather than a runtime
            # credential. String replacement drops Core 2.20's template trust.
            deployment["isolation_policy"] = trust_as_template(policy)
        deployment["firewall"]["guest"] = trust_as_template(
            "{{ aiops_instances[hostvars[aap_instance_key].vm_resource.vm_name].zabbix | dict2items | rejectattr('key', 'equalto', 'configuration') | items2dict }}")


def zabbix_resource(value, context, source_sha256):
    """Validate Zabbix's native clone provenance without imposing a Linux image schema."""
    require(isinstance(value, dict) and value.get("schema_version") == 2
            and (isinstance(value["schema_version"], int) and not isinstance(value["schema_version"], bool))
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
                and not int(value["mac"][:2], 16) & 1 and value["mac"] != "00:00:00:00:00:00",
                "Keep Zabbix's exact native disk, network, bridge and MAC identity.")
        require(not {"machine_id", "host_keys", "guest_host_keys", "user", "port"}.intersection(value)
                and isinstance(value.get("api_version"), str)
                and re.fullmatch(r"7\.4\.[0-9]+", value["api_version"]),
                "Zabbix appliance ownership requires authenticated API evidence and no guest SSH metadata.")
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
    connections = (("zabbix_api_url", "api_url"), ("vm_uuid", "uuid")) if role == "zabbix" else (
        ("ansible_host", "address"), ("vm_uuid", "uuid"), ("machine_id", "machine_id"),
        ("host_keys", "host_keys"), ("ansible_user", "user"), ("ansible_port", "port"))
    if role == "zabbix":
        require(not {"ansible_host", "ansible_user", "ansible_port", "ansible_connection",
                     "ansible_ssh_common_args", "ansible_ssh_private_key_file", "ansible_python_interpreter",
                     "machine_id", "host_keys"}.intersection(source),
                "The Zabbix appliance source row must contain API metadata, not a guest SSH connection.")
    for field, resource_field in connections:
        require(source.get(field) == resource.get(resource_field),
                "The source guest inventory and its verified native provenance disagree.")
    for owner, row in instances.items():
        for other_role in ("testserver1", "tra", "zabbix"):
            other = row.get(other_role, {})
            if owner == name and other_role == role:
                continue
            require(not any(field in resource and resource[field] == other.get(field)
                            for field in ("uuid", "mac", "machine_id"))
                    and not (resource["address"] == other.get("address")
                             and resource["hypervisor_machine_id"] == other.get("hypervisor_machine_id"))
                    and not set(resource.get("host_keys", [])) & set(other.get("host_keys", [])),
                    "Another allocation or role already owns this guest identity.")
    result = deepcopy(instances)
    current = result[name].get(role)
    if role == "zabbix" and isinstance(current, dict) and set(current) == {"configuration"}:
        current = None
    if current is not None:
        immutable = ("vm_name", "uuid", "disk", "network", "address", "mac", "hypervisor_machine_id", "verified")
        if role != "zabbix":
            immutable += ("machine_id", "host_keys", "user", "port")
        require(isinstance(current, dict) and all(current.get(field) == resource[field] for field in immutable),
                "An existing saved guest differs from native ownership; do not replace it.")
        if role == "zabbix":
            require(not {"machine_id", "host_keys", "guest_host_keys", "user", "port"}.intersection(current),
                    "Remove obsolete appliance SSH metadata through an explicitly verified ownership migration.")
            require(all(resource.get(field) == value for field, value in current.items() if field in resource),
                    "Existing Zabbix provenance changed; preserve its native records for review.")
        result[name][role] = dict(deepcopy(current), **deepcopy(resource))
    else:
        configuration = result[name].get(role, {}).get("configuration") if role == "zabbix" else None
        result[name][role] = deepcopy(resource)
        if configuration is not None:
            result[name][role]["configuration"] = deepcopy(configuration)
    return result


def prepare_documents(capture, runtime, context, credential_name, source_hosts=None, password_factory=None,
                      mcp_access=None, authentication=None, subscription=None, source_git_token=None, source_bindings=None):
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
    if source_git_token is not None:
        require(isinstance(source_git_token, str) and source_git_token.strip()
                and not re.search(r"[\r\n]", source_git_token),
                "Supply the reviewed nonempty single-line Hactar source reader.")
        existing_source_token = settings["instances"][name].get("hactar_source_git_token")
        require(existing_source_token is None or existing_source_token == source_git_token,
                "Existing selected Hactar source authentication differs; review replacement explicitly.")
        settings["instances"][name]["hactar_source_git_token"] = wrap_var(source_git_token)
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
    new_zabbix_owners = {name for name, row in instances.items()
                         if not (row.get("zabbix") or {}).get("verified", False)}
    for role in ("testserver1", "tra", "zabbix"):
        source_name = role + "-v%02d" % context["instance_number"]
        if source_name in (source_hosts or {}):
            instances = merge_source_guest(instances, context, role, source_hosts[source_name],
                result.get("aiops_zabbix_source_image", {}).get("sha256"))
    result["aiops_instances"] = instances
    binding = zabbix_import_binding(source_bindings, context) if source_bindings is not None else None
    prepare_zabbix_configuration(result, context, binding, new_zabbix_owners)
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
