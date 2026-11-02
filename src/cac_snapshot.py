"""Bounded Controller GET extraction with proved administrator visibility."""

from copy import deepcopy
import json
import os
import ssl
import socket
import hashlib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit, unquote
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

from cac_compare import CaptureError, indexed, MASK

API_PREFIX = "/api/controller/v2/"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CaptureError("Controller redirects are refused.")


class ControllerReader:
    def __init__(self, origin, token):
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or not token
        ):
            raise CaptureError(
                "Bind a trusted HTTPS Controller origin and API credential."
            )
        self.origin = origin.rstrip("/")
        self.token = token
        self.opener = build_opener(
            NoRedirect(), HTTPSHandler(context=ssl.create_default_context())
        )

    def tls_diagnostic(self):
        """No HTTP or credentials: verify TLS/SNI on resolved peers for diagnosis."""
        parsed = urlsplit(self.origin)
        hostname = parsed.hostname
        port = parsed.port or 443
        context = ssl.create_default_context()
        report = {
            "source_origin": self.origin,
            "default_verify_paths": ssl.get_default_verify_paths()._asdict(),
            "trust_store_counts": context.cert_store_stats(),
            "http_requests_sent": 0,
            "proxy_environment_present": any(
                os.environ.get(name) for name in ("HTTPS_PROXY", "https_proxy")
            ),
        }
        hosts = Path("/etc/hosts")
        report["matching_hosts_entries"] = []
        if hosts.is_file():
            for line in hosts.read_text().splitlines():
                parts = line.split("#", 1)[0].split()
                if len(parts) > 1 and hostname in parts[1:]:
                    report["matching_hosts_entries"].append(
                        {"address": parts[0], "hostname": hostname}
                    )
        addresses = sorted(
            {
                record[4][0]
                for record in socket.getaddrinfo(
                    hostname, port, type=socket.SOCK_STREAM
                )
            }
        )
        report["resolved_addresses"] = addresses
        report["verified_probes"] = []
        for address in addresses[:8]:
            proof = {"address": address, "tls_verified": False}
            try:
                with socket.create_connection((address, port), timeout=4) as raw:
                    proof["peer_address"] = raw.getpeername()[0]
                    with context.wrap_socket(raw, server_hostname=hostname) as secure:
                        proof["tls_verified"] = True
                        proof["certificate_sha256"] = hashlib.sha256(
                            secure.getpeercert(binary_form=True)
                        ).hexdigest()
            except ssl.SSLCertVerificationError as error:
                proof.update(
                    error_type=type(error).__name__,
                    verify_code=getattr(error, "verify_code", None),
                    verify_message=getattr(
                        error, "verify_message", "verification failed"
                    ),
                )
            except Exception as error:
                proof["error_type"] = type(error).__name__
            report["verified_probes"].append(proof)
        return report

    def get(self, path):
        absolute = urljoin(self.origin + API_PREFIX, path)
        parsed, expected = urlsplit(absolute), urlsplit(self.origin)
        if (parsed.scheme, parsed.netloc) != (
            expected.scheme,
            expected.netloc,
        ) or not parsed.path.startswith(API_PREFIX):
            raise CaptureError(
                "A paginated/related URL escaped the exact source Controller API."
            )
        if (
            parsed.fragment
            or parsed.username
            or parsed.password
            or "/../" in parsed.path
            or ".." in unquote(parsed.path).split("/")
            or "\\" in unquote(parsed.path)
        ):
            raise CaptureError("The Controller returned an invalid related URL.")
        request = Request(
            absolute,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/json",
            },
            method="GET",
        )
        family = parsed.path[len(API_PREFIX) :].split("/", 1)[0]
        allowed_families = set(FIELDS) | {
            "me",
            "organizations",
            "workflow_job_templates",
            "workflow_job_template_nodes",
            "credential_types",
        }
        if family not in allowed_families:
            family = "relationship"
        try:
            with self.opener.open(request, timeout=60) as response:
                if response.status != 200:
                    raise CaptureError("A required Controller GET did not succeed.")
                return json.load(response)
        except CaptureError:
            raise
        except HTTPError as error:
            raise CaptureError(
                "Controller GET "
                + family
                + " failed with HTTP "
                + str(error.code)
                + "; absence is not deletion evidence."
            ) from None
        except URLError as error:
            reason = error.reason
            if isinstance(reason, ssl.SSLCertVerificationError):
                category = "TLS certificate trust verification"
                try:
                    self.diagnostic = self.tls_diagnostic()
                except Exception as diagnostic_error:
                    self.diagnostic = {
                        "source_origin": self.origin,
                        "diagnostic_error_type": type(diagnostic_error).__name__,
                        "http_requests_sent": 0,
                    }
            elif isinstance(reason, socket.gaierror):
                category = "hostname resolution"
            elif isinstance(reason, (TimeoutError, socket.timeout)):
                category = "connection timeout"
            elif isinstance(reason, ConnectionRefusedError):
                category = "connection refused"
            else:
                category = "connection transport (" + type(reason).__name__ + ")"
            raise CaptureError(
                "Controller GET "
                + family
                + " failed during "
                + category
                + "; existing TLS and access controls remain enforced."
            ) from None
        except Exception as error:
            raise CaptureError(
                "Controller GET "
                + family
                + " returned an unreadable response ("
                + type(error).__name__
                + "); absence is not deletion evidence."
            ) from None

    def all(self, path):
        result, visited, identities = [], set(), set()
        expected = None
        while path:
            if path in visited:
                raise CaptureError("Controller pagination repeated a page.")
            visited.add(path)
            page = self.get(path)
            if (
                not isinstance(page.get("count"), int)
                or not isinstance(page.get("results"), list)
                or "next" not in page
            ):
                raise CaptureError(
                    "A required paginated Controller response is incomplete."
                )
            if expected is None:
                expected = page["count"]
            if page["count"] != expected:
                raise CaptureError(
                    "Controller objects changed during pagination; retry a fresh preview."
                )
            for entry in page["results"]:
                if type(entry.get("id")) is not int or entry["id"] in identities:
                    raise CaptureError("A paginated resource is missing or duplicated.")
                identities.add(entry["id"])
                result.append(entry)
            path = page["next"]
        if len(result) != expected:
            raise CaptureError(
                "Controller pagination did not prove complete visibility."
            )
        return result


FIELDS = {
    "credential_types": "name description kind inputs injectors",
    "projects": "name description scm_type scm_url scm_branch scm_refspec scm_clean scm_delete_on_update scm_track_submodules scm_update_on_launch scm_update_cache_timeout allow_override timeout",
    "job_templates": "name description playbook job_type timeout verbosity forks limit job_tags skip_tags start_at_task scm_branch become_enabled allow_simultaneous use_fact_cache diff_mode force_handlers job_slice_count prevent_instance_group_fallback survey_enabled webhook_service",
    "credentials": "name description inputs",
    "execution_environments": "name description image pull",
    "inventories": "name description variables prevent_instance_group_fallback",
    "hosts": "name description variables enabled",
    "groups": "name description variables",
    "labels": "name",
    "workflows": "name description allow_simultaneous ask_inventory_on_launch ask_limit_on_launch ask_variables_on_launch ask_scm_branch_on_launch survey_enabled extra_vars limit scm_branch",
}


class Snapshot:
    def __init__(self, api, scope, load_yaml):
        self.api, self.scope, self.load_yaml = api, scope, load_yaml
        self.owner = scope["organization"]
        self.aliases = scope.get("aliases", {})
        self.objects, self.cache = {}, {}
        self.raw_by_kind = {}
        self.retained_dependencies = deepcopy(scope.get("dependency_names", {}))
        self.retained_labels = []
        self.source_dependency_names = {}

    def alias(self, kind, name):
        return self.aliases.get(kind, {}).get(name, name)

    def detail(self, kind, identity):
        endpoint = {"workflows": "workflow_job_templates"}.get(kind, kind)
        key = (endpoint, identity)
        if key not in self.cache:
            self.cache[key] = self.api.get("%s/%s/" % key)
        return self.cache[key]

    def reference(self, kind, identity):
        return (
            self.alias(kind, self.detail(kind, identity)["name"])
            if identity is not None
            else None
        )

    def related(self, raw, field):
        path = raw.get("related", {}).get(field)
        if not path:
            raise CaptureError("A required relationship endpoint is unavailable.")
        return self.api.all(path)

    def fields(self, kind, raw):
        result = {key: deepcopy(raw[key]) for key in FIELDS[kind].split() if key in raw}
        result["name"] = self.alias(kind, raw["name"])
        if kind not in ("hosts", "groups", "credential_types"):
            result["organization"] = self.owner
        for key in ("extra_vars", "variables"):
            if key in result and isinstance(result[key], str):
                result[key] = self.load_yaml(result[key]) or {}
        return result

    def collect(self):
        me = self.api.all("me/?page_size=200")
        if len(me) != 1 or me[0].get("is_superuser") is not True:
            raise CaptureError(
                "A live Controller administrator read is required to prove complete scope visibility."
            )
        organizations = self.api.all(
            "organizations/?" + urlencode({"name": self.owner, "page_size": 200})
        )
        if len(organizations) != 1 or organizations[0]["name"] != self.owner:
            raise CaptureError(
                "The declared source organization cannot be identified uniquely."
            )
        self.organization_id = organizations[0]["id"]
        projects = self.api.all(
            "projects/?"
            + urlencode({"organization": self.organization_id, "page_size": 200})
        )
        selected_projects = {
            p["id"]: p for p in projects if p["name"] in self.scope["project_names"]
        }
        jobs = {}
        for project in selected_projects:
            for job in self.api.all(
                "job_templates/?" + urlencode({"project": project, "page_size": 200})
            ):
                if job.get("project") != project:
                    raise CaptureError(
                        "The API did not honor the selected project filter."
                    )
                jobs[job["id"]] = job
        # Label families discover new definitions, rather than iterating a saved ID list.
        for label in self.scope["owned_labels"]:
            for job in self.api.all(
                "job_templates/?"
                + urlencode(
                    {
                        "labels__name": label,
                        "organization": self.organization_id,
                        "page_size": 200,
                    }
                )
            ):
                labels = self.related(job, "labels")
                if (
                    label not in {x["name"] for x in labels}
                    or job.get("organization") != self.organization_id
                ):
                    raise CaptureError(
                        "The API did not honor the owned label/organization filter."
                    )
                jobs[job["id"]] = job
                if job.get("project") is not None:
                    selected_projects[job["project"]] = self.detail(
                        "projects", job["project"]
                    )
        if len(jobs) > self.scope.get("max_job_templates", 250):
            raise CaptureError("The discovered scope exceeds its reviewed size bound.")
        self.raw_by_kind["projects"] = list(selected_projects.values())
        self.raw_by_kind["job_templates"] = list(jobs.values())
        dependencies = {
            "credentials": set(),
            "execution_environments": set(),
            "inventories": set(),
        }
        labels = set(self.scope["owned_labels"]) | set(self.retained_labels)
        self.objects["projects"], self.objects["job_templates"] = [], []
        for project in selected_projects.values():
            value = self.fields("projects", project)
            for field, kind in [
                ("credential", "credentials"),
                ("default_environment", "execution_environments"),
            ]:
                if project.get(field) is not None:
                    value[field] = self.reference(kind, project[field])
                    dependencies[kind].add(project[field])
            self.objects["projects"].append(value)
        for job in jobs.values():
            value = self.fields("job_templates", job)
            value["extra_vars"] = self.load_yaml(job["extra_vars"]) or {}
            value.update(
                {
                    k: item
                    for k, item in job.items()
                    if k.startswith("ask_") and k.endswith("_on_launch")
                }
            )
            for field, kind in [
                ("project", "projects"),
                ("inventory", "inventories"),
                ("execution_environment", "execution_environments"),
            ]:
                if job.get(field) is not None:
                    value[field] = self.reference(kind, job[field])
                    if kind in dependencies:
                        dependencies[kind].add(job[field])
            associated = self.related(job, "credentials")
            dependencies["credentials"].update(x["id"] for x in associated)
            value["credentials"] = [
                self.alias("credentials", x["name"]) for x in associated
            ]
            value["labels"] = [x["name"] for x in self.related(job, "labels")]
            labels.update(value["labels"])
            if job["survey_enabled"]:
                survey = self.api.get(job["related"]["survey_spec"])
                for question in survey.get("spec", []):
                    if question.get("type") == "password" and question.get("default"):
                        question["default"] = MASK
                value["survey_spec"] = survey
            for field in (
                "instance_groups",
                "notification_templates_started",
                "notification_templates_success",
                "notification_templates_error",
            ):
                if field in job.get("related", {}):
                    entries = self.related(job, field)
                    if entries:
                        raise CaptureError(
                            "This scope has unsupported instance-group/notification associations; extend its reviewed schema first."
                        )
            if "schedules" in job.get("related", {}) and self.related(job, "schedules"):
                raise CaptureError(
                    "Owned schedules need a reviewed adapter; refuse an incomplete baseline or update."
                )
            self.objects["job_templates"].append(value)
        self.collect_workflows()
        for workflow in self.objects.get("workflows", []):
            labels.update(workflow.get("labels", []))
        self.objects["labels"] = []
        for name in sorted(labels):
            entries = self.api.all(
                "labels/?"
                + urlencode(
                    {
                        "organization": self.organization_id,
                        "name": name,
                        "page_size": 200,
                    }
                )
            )
            if len(entries) > 1:
                raise CaptureError("A referenced label is ambiguous.")
            if entries:
                if entries[0]["name"] != name:
                    raise CaptureError("The API did not honor the label name filter.")
                self.objects["labels"].append(self.fields("labels", entries[0]))
        external = self.scope.get("external_dependencies", {})
        custom_types = {}
        for kind, identifiers in dependencies.items():
            for name in self.retained_dependencies.get(kind, []):
                retained = self.api.all(
                    kind + "/?" + urlencode({"name": name, "page_size": 200})
                )
                if len(retained) > 1 or any(
                    entry["name"] != name
                    or entry.get("organization") not in (None, self.organization_id)
                    for entry in retained
                ):
                    raise CaptureError(
                        "A retained dependency no longer has a unique approved organization/name identity."
                    )
                for entry in retained:
                    identifiers.add(entry["id"])
                    self.cache[(kind, entry["id"])] = entry
            self.objects[kind] = []
            self.source_dependency_names[kind] = []
            for identifier in sorted(identifiers):
                raw = self.detail(kind, identifier)
                if raw["name"] in external.get(kind, []) or self.alias(
                    kind, raw["name"]
                ) in external.get(kind, []):
                    continue
                self.source_dependency_names[kind].append(raw["name"])
                value = self.fields(kind, raw)
                if kind == "inventories" and raw["name"] in self.scope.get(
                    "reference_only_inventories", []
                ):
                    value = {
                        "name": self.alias(kind, raw["name"]),
                        "organization": self.owner,
                    }
                if kind == "credentials":
                    if "input_sources" in raw.get("related", {}) and self.related(
                        raw, "input_sources"
                    ):
                        raise CaptureError(
                            "Dynamic credential input sources need a reviewed secret/dependency adapter."
                        )
                    credential_type = (
                        self.api.get(raw["related"]["credential_type"])
                        if raw.get("related", {}).get("credential_type")
                        else self.api.get(
                            "credential_types/%s/" % raw["credential_type"]
                        )
                    )
                    value["credential_type"] = credential_type["name"]
                    if credential_type.get("managed") is False:
                        custom_types[credential_type["name"]] = self.fields(
                            "credential_types", credential_type
                        )
                    # Masked rotations cannot be observed; existing encrypted values stay authoritative.
                    for field in credential_type.get("inputs", {}).get("fields", []):
                        if field.get("secret") and field["id"] in value["inputs"]:
                            value["inputs"][field["id"]] = MASK
                if (
                    kind == "execution_environments"
                    and raw.get("credential") is not None
                ):
                    value["credential"] = self.reference(
                        "credentials", raw["credential"]
                    )
                    if value["credential"] not in external.get("credentials", []):
                        raise CaptureError(
                            "Review execution-environment registry credential capture before updating this scope."
                        )
                self.objects[kind].append(value)
        self.objects["credential_types"] = list(custom_types.values())
        self.collect_inventory_members()
        result = {}
        for kind in self.scope["sections"]:
            try:
                result[kind] = indexed(self.objects.get(kind, []), self.owner)
            except CaptureError:
                raise CaptureError(
                    "Ambiguous duplicate resource identities in "
                    + kind
                    + "; review the namespace adapter."
                ) from None
        return result

    def collect_inventory_members(self):
        self.objects["hosts"], self.objects["groups"] = [], []
        for selection in self.scope.get("inventory_members", []):
            entries = self.api.all(
                "inventories/?"
                + urlencode(
                    {
                        "name": selection["inventory"],
                        "organization": self.organization_id,
                        "page_size": 200,
                    }
                )
            )
            if not entries:
                continue  # A proved-admin complete absence is a real removal.
            if len(entries) != 1 or entries[0]["name"] != selection["inventory"]:
                raise CaptureError("An inventory-member boundary is ambiguous.")
            inventory = entries[0]
            if "inventories" in self.scope["sections"]:
                value = self.fields("inventories", inventory)
                if inventory["name"] in self.scope.get(
                    "reference_only_inventories", []
                ):
                    value = {
                        "name": self.alias("inventories", inventory["name"]),
                        "organization": self.owner,
                    }
                if not any(
                    entry["name"] == value["name"]
                    for entry in self.objects["inventories"]
                ):
                    self.objects["inventories"].append(value)
                if inventory["name"] not in self.source_dependency_names["inventories"]:
                    self.source_dependency_names["inventories"].append(
                        inventory["name"]
                    )
            for kind in ("hosts", "groups"):
                for raw in self.api.all(
                    "inventories/%s/%s/?page_size=200" % (inventory["id"], kind)
                ):
                    if selection.get(kind) != "all" and raw[
                        "name"
                    ] not in selection.get(kind, []):
                        continue
                    value = self.fields(kind, raw)
                    value["inventory"] = self.alias("inventories", inventory["name"])
                    if kind == "groups":
                        value["hosts"] = [
                            self.alias("hosts", x["name"])
                            for x in self.related(raw, "hosts")
                        ]
                        children = self.related(raw, "children")
                        if children:
                            value["children"] = [x["name"] for x in children]
                    self.objects[kind].append(value)

    def collect_workflows(self):
        self.objects["workflows"] = []
        if "workflows" not in self.scope["sections"]:
            return
        selected = {}
        for label in self.scope["owned_labels"]:
            for raw in self.api.all(
                "workflow_job_templates/?"
                + urlencode(
                    {
                        "organization": self.organization_id,
                        "labels__name": label,
                        "page_size": 200,
                    }
                )
            ):
                selected[raw["id"]] = raw
        for name in self.scope.get("workflow_names", []):
            for raw in self.api.all(
                "workflow_job_templates/?"
                + urlencode(
                    {
                        "organization": self.organization_id,
                        "name": name,
                        "page_size": 200,
                    }
                )
            ):
                if raw["name"] != name:
                    raise CaptureError("The workflow name filter was not honored.")
                selected[raw["id"]] = raw
        for raw in selected.values():
            value = self.fields("workflows", raw)
            value.update(
                {
                    key: item
                    for key, item in raw.items()
                    if key.startswith("ask_") and key.endswith("_on_launch")
                }
            )
            value["extra_vars"] = self.load_yaml(raw["extra_vars"]) or {}
            value["labels"] = [x["name"] for x in self.related(raw, "labels")]
            if raw["name"] not in self.scope.get("workflow_names", []) and not set(
                value["labels"]
            ).intersection(self.scope["owned_labels"]):
                raise CaptureError("The workflow ownership filter was not honored.")
            if raw.get("inventory") is not None:
                value["inventory"] = self.reference("inventories", raw["inventory"])
            if raw["survey_enabled"]:
                value["survey_spec"] = self.api.get(raw["related"]["survey_spec"])
            for relation in (
                "notification_templates_started",
                "notification_templates_success",
                "notification_templates_error",
            ):
                if relation in raw.get("related", {}) and self.related(raw, relation):
                    raise CaptureError(
                        "Workflow notification associations require a reviewed serializer."
                    )
            nodes = self.related(raw, "workflow_nodes")
            if "schedules" in raw.get("related", {}) and self.related(raw, "schedules"):
                raise CaptureError(
                    "Owned workflow schedules need a reviewed adapter before acceptance."
                )
            identifiers = {node["id"]: node["identifier"] for node in nodes}
            if len(set(identifiers.values())) != len(nodes):
                raise CaptureError("Workflow node identifiers are ambiguous.")
            value["workflow_nodes"] = []
            for node in nodes:
                if node.get("unified_job_template") is None:
                    raise CaptureError(
                        "Approval/empty workflow nodes require a reviewed serializer."
                    )
                unified_type = (
                    node.get("summary_fields", {})
                    .get("unified_job_template", {})
                    .get("type")
                )
                if unified_type is None:
                    unified_type = {
                        "job": "job_template",
                        "workflow_job": "workflow_job_template",
                    }.get(
                        node.get("summary_fields", {})
                        .get("unified_job_template", {})
                        .get("unified_job_type")
                    )
                endpoint = {
                    "job_template": "job_templates",
                    "workflow_job_template": "workflow_job_templates",
                }.get(unified_type)
                if endpoint is None:
                    raise CaptureError(
                        "Unsupported workflow unified template type; no redirect fallback is allowed."
                    )
                unified = self.api.get(
                    "%s/%s/" % (endpoint, node["unified_job_template"])
                )
                if unified["type"] not in ("job_template", "workflow_job_template"):
                    raise CaptureError("Unsupported workflow node resource type.")
                record = {
                    "identifier": node["identifier"],
                    "unified_job_template": {
                        "name": unified["name"],
                        "type": unified["type"],
                        "organization": {"name": self.owner},
                    },
                    "extra_data": (
                        (self.load_yaml(node.get("extra_data", "{}")) or {})
                        if isinstance(node.get("extra_data", "{}"), str)
                        else deepcopy(node.get("extra_data") or {})
                    ),
                    "all_parents_must_converge": node["all_parents_must_converge"],
                    "related": {},
                }
                for relation in ("success_nodes", "failure_nodes", "always_nodes"):
                    edges = self.related(node, relation)
                    if any(x["id"] not in identifiers for x in edges):
                        raise CaptureError(
                            "A workflow edge escaped its complete node graph."
                        )
                    record["related"][relation] = [
                        {"identifier": identifiers[x["id"]]} for x in edges
                    ]
                # Refuse silently dropping per-node credentials/inventory/branch overrides.
                if (
                    node.get("inventory") is not None
                    or node.get("scm_branch")
                    or node.get("limit")
                    or node.get("job_tags")
                    or node.get("skip_tags")
                ):
                    raise CaptureError(
                        "Workflow node overrides require an extended reviewed serializer."
                    )
                if "credentials" in node.get("related", {}) and self.related(
                    node, "credentials"
                ):
                    raise CaptureError(
                        "Workflow node credentials require an extended reviewed serializer."
                    )
                for relation in ("labels", "instance_groups"):
                    if relation in node.get("related", {}) and self.related(
                        node, relation
                    ):
                        raise CaptureError(
                            "Workflow node label/instance-group overrides need an extended reviewed serializer."
                        )
                value["workflow_nodes"].append(record)
            self.objects["workflows"].append(value)
