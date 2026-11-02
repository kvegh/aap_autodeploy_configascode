"""Three-way CaC reconciliation. This module has no network or AAP mutations."""

from copy import deepcopy
import hashlib
import json
from collections.abc import Mapping

MISSING = object()
MASK = "$encrypted$"
UNORDERED = {
    "labels",
    "credentials",
    "instance_groups",
    "success_nodes",
    "failure_nodes",
    "always_nodes",
    "hosts",
    "groups",
}
VOLATILE = {
    "id",
    "url",
    "created",
    "modified",
    "related",
    "summary_fields",
    "last_job_run",
    "last_job_failed",
    "last_job_id",
    "status",
    "scm_revision",
    "current_job",
    "last_update_failed",
}


class CaptureError(ValueError):
    pass


def canonical(value, field=""):
    if isinstance(value, Mapping):
        return {
            str(key): canonical(item, str(key)) for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        result = [canonical(item) for item in value]
        if field in UNORDERED:
            result.sort(key=lambda item: json.dumps(item, sort_keys=True))
        if field == "workflow_nodes":
            result.sort(key=lambda item: item["identifier"])
        return result
    if isinstance(value, str):
        return str(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise CaptureError("The capture contains an unsupported value type.")


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(canonical(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def identity(resource, organization):
    if not isinstance(resource, Mapping) or not isinstance(resource.get("name"), str):
        raise CaptureError("Every resource needs a stable name.")
    parent = resource.get("inventory", "")
    owner = resource.get("organization", organization)
    if not isinstance(parent, str) or not isinstance(owner, str):
        raise CaptureError(
            "Use stable inventory and organization names, never runtime IDs."
        )
    return json.dumps([owner, parent, resource["name"]], separators=(",", ":"))


def indexed(resources, organization):
    result = {}
    for resource in resources:
        key = identity(resource, organization)
        if key in result:
            raise CaptureError("Ambiguous duplicate resource identities are refused.")
        result[key] = canonical(resource)
    return result


def preserve_masks(source, desired, path=()):
    """Keep existing secret inputs; an opaque new secret requires owner input."""
    if source == MASK:
        if desired is MISSING or desired in (None, "", MASK, "ASK", "CHANGEME"):
            raise CaptureError(
                "A new or incomplete credential has an unrecoverable secret input."
            )
        return deepcopy(desired)
    if isinstance(source, Mapping):
        return {
            key: preserve_masks(
                item,
                desired.get(key, MISSING) if isinstance(desired, Mapping) else MISSING,
                path + (key,),
            )
            for key, item in source.items()
        }
    if isinstance(source, list):
        key = next(
            (
                name
                for name in ("variable", "identifier", "name")
                if source
                and all(isinstance(item, Mapping) and name in item for item in source)
            ),
            None,
        )
        lookup = (
            {item.get(key): item for item in desired if isinstance(item, Mapping)}
            if key and isinstance(desired, list)
            else {}
        )
        return [
            preserve_masks(
                item,
                (
                    lookup.get(item[key], MISSING)
                    if key
                    else (
                        desired[index]
                        if isinstance(desired, list) and index < len(desired)
                        else MISSING
                    )
                ),
                path + (str(index),),
            )
            for index, item in enumerate(source)
        ]
    return deepcopy(source)


def semantic_diff(before, after, path=()):
    if before == after:
        return []
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        result = []
        for key in sorted(set(before) | set(after)):
            result.extend(
                semantic_diff(
                    before.get(key, MISSING), after.get(key, MISSING), path + (key,)
                )
            )
        return result
    if isinstance(before, list) and isinstance(after, list):
        records = before + after
        field = next(
            (
                key
                for key in ("variable", "identifier", "name")
                if records
                and all(isinstance(item, Mapping) and key in item for item in records)
            ),
            None,
        )

        def key(item):
            return str(item[field]) if field else json.dumps(item, sort_keys=True)

        first, second = {key(item): item for item in before}, {
            key(item): item for item in after
        }
        if len(first) == len(before) and len(second) == len(after):
            result = semantic_diff(first, second, path)
            if not result and path and path[-1] not in UNORDERED and before != after:
                result.append({"path": list(path) + ["$order"], "operation": "change"})
            return result
    change = (
        "addition" if before is MISSING else "removal" if after is MISSING else "change"
    )
    return [{"path": list(path), "operation": change}]


def merge_value(
    source_before, desired_before, current, live, conflicts, excluded, path=()
):
    # Unchanged source never rewrites pending desired edits or desired deletions.
    if source_before == live:
        return deepcopy(current) if current is not MISSING else MISSING
    if live == MASK:
        return preserve_masks(live, current, path)
    if (
        source_before is MISSING
        and desired_before is MISSING
        and isinstance(current, Mapping)
        and isinstance(live, Mapping)
    ):
        return merge_value({}, {}, current, live, conflicts, excluded, path)
    if current == live:
        return deepcopy(current) if current is not MISSING else MISSING
    # The accepted desired baseline explicitly excluded this source resource/field.
    if (
        source_before is not MISSING
        and desired_before is MISSING
        and current is MISSING
    ):
        excluded.append(list(path))
        return MISSING
    # A live addition must not overwrite an already-planned desired object.
    if source_before is MISSING and desired_before is not MISSING:
        conflicts.append(list(path))
        return deepcopy(current) if current is not MISSING else MISSING
    if current == desired_before:
        if live is MISSING:
            return MISSING
        if (
            isinstance(source_before, Mapping)
            and isinstance(live, Mapping)
            and isinstance(current, Mapping)
        ):
            pass
        else:
            return preserve_masks(live, current, path)
    elif not all(
        isinstance(value, Mapping)
        for value in (source_before, desired_before, current, live)
    ):
        conflicts.append(list(path))
        return deepcopy(current) if current is not MISSING else MISSING
    if all(
        isinstance(value, Mapping)
        for value in (source_before, desired_before, current, live)
    ):
        result = {}
        for key in sorted(
            set(source_before) | set(desired_before) | set(current) | set(live)
        ):
            item = merge_value(
                source_before.get(key, MISSING),
                desired_before.get(key, MISSING),
                current.get(key, MISSING),
                live.get(key, MISSING),
                conflicts,
                excluded,
                path + (key,),
            )
            if item is not MISSING:
                result[key] = item
        return result
    conflicts.append(list(path))
    return deepcopy(current) if current is not MISSING else MISSING


def compare(source_before, desired_before, current, live, visibility_complete):
    if not visibility_complete:
        raise CaptureError(
            "Complete authorized visibility and all pagination/relationships are required before comparison."
        )
    values = [
        canonical(value) for value in (source_before, desired_before, current, live)
    ]
    source_before, desired_before, current, live = values
    conflicts, excluded = [], []
    merged = merge_value(
        source_before, desired_before, current, live, conflicts, excluded
    )
    result = {
        "source_changes": semantic_diff(source_before, live),
        "desired_changes": semantic_diff(current, merged),
        "conflicts": conflicts,
        "preserved_exclusions": excluded,
        "merged": merged,
    }
    result["review_digest"] = fingerprint({"inputs": values, "result": result})
    return result


def approved_update(result, digest):
    if result["conflicts"]:
        raise CaptureError(
            "Conflicting source/repository edits require owner resolution."
        )
    if not digest or digest != result["review_digest"]:
        raise CaptureError(
            "The preview digest changed or was not supplied; review a fresh extraction."
        )
    return deepcopy(result["merged"])


def validate_dependencies(model, external=None):
    external = external or {}
    known = {
        kind: {entry["name"] for entry in resources.values()}
        | set(external.get(kind, []))
        for kind, resources in model.items()
    }
    for kind in (
        "projects",
        "inventories",
        "credentials",
        "execution_environments",
        "labels",
    ):
        known.setdefault(kind, set(external.get(kind, [])))
    for job in model.get("job_templates", {}).values():
        for field, kind in [
            ("project", "projects"),
            ("inventory", "inventories"),
            ("execution_environment", "execution_environments"),
        ]:
            if job.get(field) is not None and job[field] not in known[kind]:
                raise CaptureError(
                    "A template has an uncaptured or undeclared external dependency."
                )
        for field, kind in [("credentials", "credentials"), ("labels", "labels")]:
            if set(job.get(field, [])) - known[kind]:
                raise CaptureError(
                    "A template association lacks its captured or declared external definition."
                )
    hosts = {
        (entry["inventory"], entry["name"]) for entry in model.get("hosts", {}).values()
    }
    groups = {
        (entry["inventory"], entry["name"])
        for entry in model.get("groups", {}).values()
    }
    for kind in ("hosts", "groups"):
        for entry in model.get(kind, {}).values():
            if entry["inventory"] not in known["inventories"]:
                raise CaptureError(
                    "A host/group has no captured or declared external inventory."
                )
            if kind == "groups" and (
                any(
                    (entry["inventory"], name) not in hosts
                    for name in entry.get("hosts", [])
                )
                or any(
                    (entry["inventory"], name) not in groups
                    for name in entry.get("children", [])
                )
            ):
                raise CaptureError(
                    "An inventory-group relationship escapes its captured membership boundary."
                )
    for workflow in model.get("workflows", {}).values():
        if set(workflow.get("labels", [])) - known["labels"]:
            raise CaptureError("A workflow label definition is missing.")
        for node in workflow.get("workflow_nodes", []):
            reference = node.get("unified_job_template", {})
            kind = {
                "job_template": "job_templates",
                "workflow_job_template": "workflows",
            }.get(reference.get("type"))
            if kind is None or reference.get("name") not in known.get(kind, set()):
                raise CaptureError(
                    "A workflow node references an uncaptured or undeclared external template."
                )
