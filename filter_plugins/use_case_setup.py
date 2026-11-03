"""Bound selected configuration imports to reviewed umbrella submodules."""

from collections.abc import Mapping
import re
from urllib.parse import urlsplit

from ansible.errors import AnsibleFilterError


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def project_display_name(project_id):
    """Derive deployment template names from IDs, preserving their word order."""
    require(isinstance(project_id, str)
            and bool(re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", project_id)),
            "Use a lowercase project ID with hyphen or underscore word separators.")
    acronyms = {"aiops": "AIOps", "aap": "AAP"}
    return "Deploy " + " ".join(acronyms.get(word, word.capitalize())
                                for word in re.split(r"[-_]", project_id)) + " CaC"


def https_origin(value):
    require(
        isinstance(value, str) and not any(c.isspace() for c in value),
        "Supply an explicit HTTPS AAP origin.",
    )
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise AnsibleFilterError("The AAP URL is invalid.") from None
    require(
        parsed.scheme == "https"
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and parsed.path in ("", "/")
        and not parsed.query
        and not parsed.fragment,
        "AAP URLs must be HTTPS origins without credentials or extra paths.",
    )
    return parsed.hostname.lower(), port or 443


def git_url(value):
    require(
        isinstance(value, str) and not any(c.isspace() for c in value),
        "Supply an explicit HTTPS Git URL.",
    )
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise AnsibleFilterError("The Git URL is invalid.") from None
    require(
        parsed.scheme == "https"
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and parsed.path not in ("", "/")
        and not parsed.query
        and not parsed.fragment,
        "Use HTTPS Git URLs without embedded credentials, query or fragment.",
    )
    return value.rstrip("/").removesuffix(".git")


def setup_plan(selected, catalog, protected, seed, target):
    require(isinstance(protected, Mapping)
            and https_origin(seed) == https_origin(protected.get('seed_hostname')),
            'The orchestration seed must match the reviewed protected controller origin.')
    require(
        https_origin(seed) != https_origin(target),
        "The fresh target must differ from the seed AAP.",
    )
    require(
        isinstance(selected, list)
        and selected
        and all(isinstance(key, str) for key in selected)
        and len(set(selected)) == len(selected),
        "Choose a nonempty unique list of use-case submodules.",
    )
    require(
        isinstance(catalog, Mapping) and isinstance(protected, Mapping),
        "Load the reviewed use-case catalog from encrypted configuration.",
    )
    modules = protected.get("umbrella_modules", {})
    repositories = protected.get("configuration_repositories", {})
    require(
        isinstance(modules, Mapping) and set(modules) == set(catalog),
        "Refresh the reviewed umbrella submodule catalog before setup.",
    )
    source = git_url(modules["aap_autodeploy_configascode"])
    importers = []
    for key in selected:
        require(key in catalog, "An unknown use-case submodule was selected.")
        entry = catalog[key]
        require(
            "unavailable" not in entry,
            "Selected submodule %s is unavailable: %s"
            % (key, entry.get("unavailable", "")),
        )
        git_url(modules[key])
        repository = repositories.get(entry["configuration"])
        git_url(repository)
        importers.append(
            {
                "key": key,
                "name": project_display_name(entry["project_id"]),
                "playbook": entry["playbook"],
                "project_id": entry["project_id"],
                "repository": repository,
            }
        )
    return {
        "importers": importers,
        "source_project_url": source,
        "organization": protected["organization"],
        "preparation": {
            "name": "Deploy Test AAP - 05 Prepare Use-Case Prerequisites",
            "playbook": "05-prepare-use-cases.yml",
            "repository": repositories["base"],
        },
    }


def distinct_controllers(seed_instances, target_instances):
    require(
        isinstance(seed_instances, list) and isinstance(target_instances, list),
        "Read both controllers before starting any configuration import.",
    )
    seed = {x.get("uuid") for x in seed_instances if isinstance(x, Mapping)}
    target = {x.get("uuid") for x in target_instances if isinstance(x, Mapping)}
    require(
        seed
        and target
        and None not in seed
        and None not in target
        and "" not in seed
        and "" not in target
        and not seed.intersection(target),
        "The fresh target and seed must have distinct verified controller instances.",
    )
    return True


def instance_store_credentials(credentials):
    """Forward the shared store already attached to the source job."""
    require(isinstance(credentials, list), "Read this source job's credential associations.")
    selected = [entry for entry in credentials if entry.get("summary_fields", {})
                .get("credential_type", {}).get("name") == "Pseudo Instance Key Store"
                and entry.get("name") == "AAP API/MCP Auth Token Store"]
    require(len(selected) == 1 and type(selected[0].get("id")) is int
            and type(selected[0].get("credential_type")) is int,
            "Attach exactly one AAP API/MCP Auth Token Store to this job.")
    return selected


def api_launch_credentials(original, expected_names, destination_credentials,
                           organization, destination, shared_seed_credentials=None):
    """Keep the saved repository credentials and the same shared instance store."""
    require(isinstance(original, list) and isinstance(expected_names, list)
            and all(entry.get("kind") != "ssh" for entry in original)
            and sorted(entry.get("name", "") for entry in original) == sorted(expected_names),
            "The generic importer's saved repository credentials differ from the reviewed capture.")
    pins = shared_seed_credentials or {}
    require(isinstance(pins, Mapping), "Declare shared source credential pins as a mapping.")
    for entry in original:
        owner = entry.get("summary_fields", {}).get("organization") or {}
        pin = pins.get(entry.get("name"), {})
        pinned = (isinstance(pin, Mapping) and type(pin.get("id")) is int
                  and type(pin.get("credential_type")) is int
                  and "organization" in entry and entry["organization"] is None
                  and entry.get("summary_fields", {}).get("organization") is None
                  and entry.get("id") == pin.get("id")
                  and entry.get("credential_type") == pin.get("credential_type")
                  and entry.get("summary_fields", {}).get("credential_type", {}).get("name")
                  == pin.get("credential_type_name"))
        require(type(entry.get("id")) is int and (owner.get("name") == organization or pinned),
                "Repository credential ownership must match the organization or exact reviewed source pins.")
    store = instance_store_credentials(destination_credentials)[0]
    saved_store = instance_store_credentials(original)[0]
    require(len(destination_credentials) == 1
            and saved_store["id"] == store["id"]
            and saved_store["credential_type"] == store["credential_type"],
            "Parent and child must use the same reviewed instance token store.")
    https_origin(destination)
    combined = original
    vault_ids = [entry.get("inputs", {}).get("vault_id", "") for entry in original
                 if entry.get("kind") == "vault"]
    identities = [entry["id"] for entry in combined]
    require(len(vault_ids) == len(set(vault_ids)) and len(identities) == len(set(identities)),
            "Duplicate Vault identities or launch credentials are refused.")
    return identities


def scoped_launch_credentials(
    original, expected_names, route_credentials, organization, machine_name,
    shared_seed_credentials=None,
):
    require(
        isinstance(original, list)
        and isinstance(expected_names, list)
        and isinstance(route_credentials, list)
        and len(route_credentials) == 1,
        "Resolve the exact saved and registered route credential identities.",
    )
    preserved = [entry for entry in original if entry.get("kind") != "ssh"]
    require(
        sorted(entry.get("name", "") for entry in preserved) == sorted(expected_names),
        "The importer credential associations differ from the reviewed capture.",
    )
    machine = route_credentials[0]
    require(
        machine.get("kind") == "ssh"
        and machine.get("name") == machine_name,
        "The selected route requires its bound Machine credential.",
    )
    require(
        len([entry for entry in preserved
             if entry.get("name") == "aap_autodeploy_configascode-secrets CaC repo read token"
             and entry.get("summary_fields", {}).get("credential_type", {}).get("name")
             == "Cac_git_token_type"]) == 1,
        "Retain the saved AutoDeploy repository read token for registry reads.",
    )
    require(
        len([entry for entry in preserved if entry.get("kind") == "vault"
             and entry.get("inputs", {}).get("vault_id") == "cac"]) == 1,
        "Retain the saved AutoDeploy CaC Vault credential for registry encryption and decryption.",
    )
    combined = preserved + route_credentials
    pins = {} if shared_seed_credentials is None else shared_seed_credentials
    require(isinstance(pins, Mapping), "Declare shared seed credential pins as a mapping.")

    def in_organization(entry):
        owner = entry.get("summary_fields", {}).get("organization") or {}
        return owner.get("name") == organization

    def pinned_source_entry(entry):
        pin = pins.get(entry.get("name"))
        return (
            isinstance(pin, Mapping)
            and type(pin.get("id")) is int
            and type(pin.get("credential_type")) is int
            and isinstance(pin.get("credential_type_name"), str)
            and bool(pin["credential_type_name"])
            and "organization" in entry
            and entry["organization"] is None
            and entry.get("summary_fields", {}).get("organization") is None
            and entry.get("id") == pin.get("id")
            and entry.get("credential_type") == pin.get("credential_type")
            and entry.get("summary_fields", {}).get("credential_type", {}).get("name")
            == pin.get("credential_type_name")
        )

    require(
        all(
            type(entry.get("id")) is int
            and (in_organization(entry) or pinned_source_entry(entry))
            for entry in preserved
        ) and all(type(entry.get("id")) is int and in_organization(entry)
                  for entry in route_credentials),
        "Credential ownership must match the organization or exact reviewed source-only pins.",
    )
    vault_ids = [
        entry.get("inputs", {}).get("vault_id", "")
        for entry in combined
        if entry.get("kind") == "vault"
    ]
    require(
        len(vault_ids) == len(set(vault_ids)),
        "Use one saved CaC Vault credential and distinct environment Vault identities.",
    )
    identities = [entry["id"] for entry in combined]
    require(
        len(identities) == len(set(identities)),
        "Duplicate launch credentials are refused.",
    )
    return identities


def selected_prerequisites(definitions, selected):
    require(
        isinstance(definitions, Mapping)
        and isinstance(selected, list)
        and selected
        and all(isinstance(key, str) and key in definitions for key in selected),
        "Select supported use cases with reviewed prerequisite definitions.",
    )
    merged = {}
    for key in selected:
        entry = definitions[key]
        require(
            isinstance(entry, Mapping) and entry.get("reviewed") is True,
            "Review the selected use-case prerequisites before synchronization.",
        )
        for repository in entry["repositories"]:
            require(
                repository["name"] in ("rh-certified", "validated", "community"),
                "Declare a supported PAH repository for every prerequisite.",
            )
            pins = merged.setdefault(repository["name"], [])
            for pin in repository["collections"]:
                if pin not in pins:
                    pins.append(pin)
    return {
        "reviewed": True,
        "repositories": [
            {"name": name, "collections": merged[name]}
            for name in ("rh-certified", "validated", "community")
            if merged.get(name)
        ],
    }


class FilterModule:
    def filters(self):
        return {
            "aap_use_case_setup_plan": setup_plan,
            "aap_cac_project_display_name": project_display_name,
            "aap_distinct_controllers": distinct_controllers,
            "aap_normalized_git_url": git_url,
            "aap_https_origin": https_origin,
            "aap_scoped_launch_credentials": scoped_launch_credentials,
            "aap_instance_store_credentials": instance_store_credentials,
            "aap_api_launch_credentials": api_launch_credentials,
            "aap_selected_use_case_prerequisites": selected_prerequisites,
        }
