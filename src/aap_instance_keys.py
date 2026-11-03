"""Temporary instance-token storage and source-controller synchronization."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import quote, urlsplit

TYPE_NAME = "Pseudo Instance Key Store"
CREDENTIAL_NAME = "AAP API/MCP Auth Token Store"


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
