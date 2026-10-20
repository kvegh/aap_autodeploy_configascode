#!/usr/bin/python
"""Set PAH selection limits and preview/apply requirement-aware release retention."""

DOCUMENTATION = r"""
module: pah_collection_retention
short_description: Configure PAH selection limits and curate reviewed collection releases
description:
  - Configure remote selection and repository snapshot limits without syncing content.
  - Preview collection release removal using a complete externally reviewed requirements audit.
  - Apply only an unchanged previously reviewed plan against an idle target.
options:
  operation:
    description: Configure selection limits, preview retention, or apply a reviewed plan.
    type: str
    choices: [configure, plan, apply]
    default: plan
  hub_host:
    description: Target AAP HTTPS origin.
    type: str
    required: true
  hub_token:
    description: Target API bearer token, protected from module output.
    type: str
    required: true
  validate_certs:
    description: Validate the target TLS certificate.
    type: bool
    default: true
  policy:
    description: Declared managed repositories and independent selection/snapshot limits.
    type: dict
    required: true
  requirements_audit:
    description: Reviewed source files, project revisions, EE references and collection requirements.
    type: dict
    default: {}
  expected_plan:
    description: Complete previously reviewed preview required by apply.
    type: dict
    default: {}
"""

from collections import defaultdict
import hashlib
import json
import re
import ssl
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener


class PolicyError(Exception):
    """A retention precondition or API operation could not be verified."""


class RefuseRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise PolicyError("PAH API redirects require review; credentials are never forwarded.")


def release_key(version):
    """Fail closed for releases whose ordering this policy cannot prove."""
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise PolicyError("A nonstable or unsupported collection version requires review.")
    return tuple(map(int, version.split(".")))


def satisfies(version, requirement):
    if requirement in (None, "", "*"):
        return True
    if not isinstance(requirement, str):
        raise PolicyError("A collection requirement must be a string.")
    for expression in requirement.split(","):
        match = re.fullmatch(r"\s*(>=|<=|>|<|==|=|!=)?\s*(\d+\.\d+\.\d+)\s*", expression)
        if not match:
            raise PolicyError("An unsupported dependency constraint requires review.")
        operator, target = match.groups()
        left, right = release_key(version), release_key(target)
        comparisons = {">=": left >= right, "<=": left <= right, ">": left > right,
                       "<": left < right, "==": left == right, "=": left == right,
                       "!=": left != right, None: left == right}
        if not comparisons[operator]:
            return False
    return True


def validate_policy(policy):
    if policy.get("mode") != "latest_installed_plus_requirements":
        raise PolicyError("Declare the latest-installed-plus-requirements policy explicitly.")
    for setting in ("sync_highest_versions", "retain_repo_versions"):
        if type(policy.get(setting)) is not int or policy[setting] != 1:
            raise PolicyError("Remote selection and repository snapshot limits must each be one.")
    repositories = policy.get("repositories")
    if not isinstance(repositories, list) or not repositories or len(set(repositories)) != len(repositories):
        raise PolicyError("Declare a nonempty, unique list of managed PAH repositories.")
    if any(not isinstance(name, str) or not name for name in repositories):
        raise PolicyError("Managed repository names must be nonempty strings.")
    if policy.get("require_complete_requirements_audit") is not True:
        raise PolicyError("Release pruning requires a complete requirements audit.")


class Client:
    def __init__(self, hostname, token, validate_certs=True):
        parsed = urlsplit(hostname)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise PolicyError("Supply an HTTPS AAP origin without credentials or an extra path.")
        self.origin = hostname.rstrip("/")
        self.token = token
        self.context = ssl.create_default_context() if validate_certs else ssl._create_unverified_context()
        self.opener = build_opener(HTTPSHandler(context=self.context), RefuseRedirect())

    def path(self, path):
        if not isinstance(path, str) or not path.startswith(("/api/", "/pulp/")) or "\\" in path or any(c.isspace() for c in path):
            raise PolicyError("An unexpected PAH API reference requires review.")
        return "/api/galaxy" + path if path.startswith("/pulp/") else path

    def request(self, method, path, body=None, expected=(200,)):
        path = self.path(path)
        request = Request(self.origin + path, method=method,
                          data=json.dumps(body).encode() if body is not None else None,
                          headers={"Authorization": "Bearer " + self.token,
                                   "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with self.opener.open(request, timeout=45) as response:
                status, data = response.status, response.read()
        except PolicyError:
            raise
        except HTTPError as error:
            raise PolicyError("PAH API operation returned HTTP " + str(error.code) + ".") from None
        except Exception:
            raise PolicyError("PAH API connection failed; inspect TLS and access configuration.") from None
        if status not in expected:
            raise PolicyError("PAH API operation returned an unexpected status.")
        try:
            return json.loads(data) if data else None
        except ValueError:
            raise PolicyError("PAH API returned an unexpected document.") from None

    def pages(self, path):
        result = []
        for _ in range(100):
            page = self.request("GET", path)
            if not isinstance(page, dict) or not isinstance(page.get("results"), list):
                raise PolicyError("PAH API returned an invalid paginated document.")
            result.extend(page["results"])
            path = page.get("next")
            if not path:
                return result
            if path.startswith("http"):
                parsed, origin = urlsplit(path), urlsplit(self.origin)
                if (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc):
                    raise PolicyError("Pagination points to another API origin.")
                path = parsed.path + ("?" + parsed.query if parsed.query else "")
        raise PolicyError("PAH API pagination exceeded its bound.")

    def wait(self, response):
        if not response or not response.get("task"):
            return
        task = response["task"]
        self.path(task)
        for _ in range(150):
            current = self.request("GET", task)
            state = current.get("state")
            if state == "completed":
                return
            if state in ("failed", "canceled", "canceling"):
                raise PolicyError("A PAH policy task did not complete successfully.")
            time.sleep(2)
        raise PolicyError("A PAH policy task is still running; inspect it before rerunning.")


def configure(client, policy, check_mode=False):
    validate_policy(policy)
    changes = []
    updates = []
    for name in policy["repositories"]:
        selected = {}
        for kind, field, desired in (("remotes", "sync_highest_versions", policy["sync_highest_versions"]),
                                     ("repositories", "retain_repo_versions", policy["retain_repo_versions"])):
            suffix = "collection" if kind == "remotes" else "ansible"
            path = "/api/galaxy/pulp/api/v3/" + kind + "/ansible/" + suffix + "/?" + urlencode({"name": name, "limit": 100})
            matches = client.pages(path)
            if len(matches) != 1 or matches[0].get("name") != name or field not in matches[0]:
                raise PolicyError("The named PAH source or its supported retention setting is unavailable.")
            item = matches[0]
            selected[kind] = item
            if item[field] != desired:
                changes.append({"repository": name, "setting": field, "value": desired})
                updates.append((item["pulp_href"], field, desired))
        if selected["repositories"].get("remote") != selected["remotes"]["pulp_href"]:
            raise PolicyError("A managed repository refers to an unexpected remote.")
    if not check_mode:
        for path, field, desired in updates:
            response = client.request("PATCH", path, {field: desired}, expected=(200, 202))
            client.wait(response)
            verified = client.request("GET", path)
            if verified.get(field) != desired:
                raise PolicyError("A PAH retention setting could not be verified after update.")
    return {"changed": bool(changes), "settings": changes, "content_synced": False,
            "collection_releases_removed": 0}


def audit_requirements(projects, environments, audit):
    """Require a source audit covering the current deployed project and EE set."""
    if audit.get("complete") is not True:
        raise PolicyError("A complete project, playbook, and execution-environment requirements audit is required.")
    definitions = audit.get("projects", [])
    if len({item.get("name") for item in definitions}) != len(definitions):
        raise PolicyError("The requirements audit contains duplicate project names.")
    if {item["name"] for item in projects} != {item.get("name") for item in definitions}:
        raise PolicyError("The live project set differs from the requirements audit.")
    requirements = []
    for project in projects:
        definition = next(item for item in definitions if item["name"] == project["name"])
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", project.get("scm_revision", "")) or project["scm_revision"] != definition.get("scm_revision"):
            raise PolicyError("A project revision is unknown or changed since its requirements audit.")
        files = definition.get("files", [])
        if not files and definition.get("no_requirements_verified") is not True:
            raise PolicyError("A project has no reviewed requirements or verified absence of requirements.")
        for source in files:
            if not source.get("path") or not re.fullmatch(r"[0-9a-f]{64}", source.get("sha256", "")):
                raise PolicyError("Each requirements source needs its relative path and reviewed SHA-256 digest.")
            if source.get("kind") not in ("project", "playbook", "execution_environment"):
                raise PolicyError("A requirements source has an unknown ownership kind.")
            if not isinstance(source.get("collections"), list):
                raise PolicyError("A reviewed requirements source must explicitly list its collections.")
            for requirement in source["collections"]:
                requirements.append({**requirement, "reason": "project " + project["name"] + ": " + source["path"]})
    definitions = audit.get("execution_environments", [])
    if len({item.get("name") for item in definitions}) != len(definitions):
        raise PolicyError("The requirements audit contains duplicate execution-environment names.")
    if {(item["name"], item["image"]) for item in environments} != {(item.get("name"), item.get("image")) for item in definitions}:
        raise PolicyError("The live execution-environment set differs from the requirements audit.")
    for item in definitions:
        provenance = item.get("requirements_source")
        image_audit = item.get("image_inventory")
        if image_audit is not None:
            digest = image_audit.get("digest", "")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) or not item["image"].endswith("@" + digest):
                raise PolicyError("An image inventory requires the exact immutable image digest on the live execution environment.")
            if not re.fullmatch(r"[0-9a-f]{64}", image_audit.get("sha256", "")) or not isinstance(image_audit.get("collections"), list):
                raise PolicyError("An image inventory needs its reviewed inventory SHA-256 digest and explicit collection requirements.")
            for requirement in image_audit["collections"]:
                requirements.append({**requirement, "reason": "execution environment " + item["name"] + ": " + digest})
            continue
        if not isinstance(provenance, dict) or not provenance.get("project") or not provenance.get("path"):
            raise PolicyError("Each execution environment needs reviewed requirements-source provenance.")
        project = next((entry for entry in audit["projects"] if entry["name"] == provenance["project"]), None)
        source = next((entry for entry in (project or {}).get("files", []) if entry["path"] == provenance["path"] and entry.get("kind") == "execution_environment"), None)
        if source is None:
            raise PolicyError("An execution environment's requirements source is absent from the project audit.")
    return requirements


def make_plan(repositories, requirements):
    """Keep each newest installed release and actual requirements plus closure."""
    available = defaultdict(list)
    for repository in repositories:
        for item in repository["collections"]:
            release_key(item["version"])
            if not isinstance(item.get("dependencies"), dict):
                raise PolicyError("Collection dependency metadata is unavailable.")
            available[item["namespace"] + "." + item["name"]].append(item)
    keep = set()
    required_versions = set()
    newest_by_repository = {}
    reasons = defaultdict(list)
    for repository in repositories:
        grouped = defaultdict(list)
        newest_by_repository[repository["name"]] = set()
        for item in repository["collections"]:
            grouped[item["namespace"] + "." + item["name"]].append(item)
        for name, items in grouped.items():
            latest = max(items, key=lambda entry: release_key(entry["version"]))
            identity = (name, latest["version"])
            newest_by_repository[repository["name"]].add(identity)
            keep.add(identity)
            reasons[identity].append("Newest installed release in repository " + repository["name"])
    for requirement in requirements:
        name, constraint = requirement.get("name"), requirement.get("version", "*")
        if set(requirement) - {"name", "version", "reason"}:
            raise PolicyError("A requirements entry with an external source or unsupported fields requires review.")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", name):
            raise PolicyError("A requirements source contains an unsupported collection identity.")
        if not requirement.get("reason"):
            raise PolicyError("A retained requirement needs reviewed source provenance.")
        matches = [item for item in available[name] if satisfies(item["version"], constraint)]
        if not matches:
            raise PolicyError("A declared project requirement is unavailable in the managed PAH repositories.")
        version = max((item["version"] for item in matches), key=release_key)
        keep.add((name, version))
        required_versions.add((name, version))
        reasons[(name, version)].append(requirement["reason"] + " requires " + str(constraint))
    visited = set()
    while keep - visited:
        name, version = min(keep - visited)
        visited.add((name, version))
        copies = [item for item in available[name] if item["version"] == version]
        if len({json.dumps(item.get("dependencies", {}), sort_keys=True) for item in copies}) != 1:
            raise PolicyError("Collection copies disagree about dependency metadata.")
        for dependency, constraint in (copies[0].get("dependencies") or {}).items():
            if any(other == dependency and satisfies(release, constraint) for other, release in keep):
                continue
            matches = [item["version"] for item in available[dependency] if satisfies(item["version"], constraint)]
            if not matches:
                raise PolicyError("A retained collection has an unavailable dependency.")
            chosen = max(matches, key=release_key)
            keep.add((dependency, chosen))
            required_versions.add((dependency, chosen))
            reasons[(dependency, chosen)].append(name + " " + version + " requires " + str(constraint))
    result = []
    for repository in repositories:
        retained, removed = [], []
        for item in repository["collections"]:
            identity = (item["namespace"] + "." + item["name"], item["version"])
            (retained if identity in newest_by_repository[repository["name"]] or identity in required_versions else removed).append(item)
        result.append({"name": repository["name"], "repository_href": repository["pulp_href"],
                       "baseline_version_href": repository["latest_version_href"],
                       "keep": retained, "remove": removed})
    return {"repositories": result, "retained": [{"name": name, "version": version, "reasons": reasons[(name, version)]} for name, version in sorted(keep)],
            "remove_count": sum(len(item["remove"]) for item in result)}


def collect_plan(client, policy, audit):
    validate_policy(policy)
    for state in ("waiting", "running"):
        if client.pages("/api/galaxy/pulp/api/v3/tasks/?" + urlencode({"state": state, "limit": 100})):
            raise PolicyError("PAH has active tasks; wait before planning or applying retention.")
    if client.pages("/api/controller/v2/jobs/?status__in=new,pending,waiting,running&page_size=200"):
        raise PolicyError("The target Controller has active jobs; use an idle target before collection pruning.")
    if client.pages("/api/controller/v2/project_updates/?status__in=new,pending,waiting,running&page_size=200"):
        raise PolicyError("The target has active project updates; wait before collection pruning.")
    projects = client.pages("/api/controller/v2/projects/?page_size=200")
    environments = client.pages("/api/controller/v2/execution_environments/?page_size=200")
    requirements = audit_requirements(projects, environments, audit)
    repositories = []
    for name in policy["repositories"]:
        matches = client.pages("/api/galaxy/pulp/api/v3/repositories/ansible/ansible/?" + urlencode({"name": name, "limit": 100}))
        if len(matches) != 1 or matches[0].get("retain_repo_versions") != 1:
            raise PolicyError("A managed repository or its single-snapshot policy needs review.")
        item = matches[0]
        if not item.get("latest_version_href"):
            raise PolicyError("A managed repository has no readable current version.")
        item["collections"] = client.pages("/api/galaxy/pulp/api/v3/content/ansible/collection_versions/?" + urlencode({"repository_version": item["latest_version_href"], "limit": 200}))
        repositories.append(item)
    plan = make_plan(repositories, requirements)
    plan["requirements_audit_sha256"] = hashlib.sha256(json.dumps(audit, sort_keys=True).encode()).hexdigest()
    return plan


def apply_plan(client, policy, audit, expected_plan):
    current = collect_plan(client, policy, audit)
    if current != expected_plan:
        raise PolicyError("Repository contents, baselines, or requirements changed after preview; review a fresh plan.")
    for repository in current["repositories"]:
        if not repository["remove"]:
            continue
        live = client.request("GET", repository["repository_href"])
        if live.get("latest_version_href") != repository["baseline_version_href"] or live.get("retain_repo_versions") != 1:
            raise PolicyError("A repository changed immediately before retention apply.")
        response = client.request("POST", repository["repository_href"] + "modify/", {
            "base_version": repository["baseline_version_href"], "add_content_units": [],
            "remove_content_units": [item["pulp_href"] for item in repository["remove"]]}, expected=(202,))
        client.wait(response)
        live = client.request("GET", repository["repository_href"])
        content = client.pages("/api/galaxy/pulp/api/v3/content/ansible/collection_versions/?" + urlencode({"repository_version": live["latest_version_href"], "limit": 200}))
        if {item["pulp_href"] for item in content} != {item["pulp_href"] for item in repository["keep"]}:
            raise PolicyError("Retention apply did not produce exactly the reviewed retained content.")
    return {"changed": current["remove_count"] > 0, "collection_releases_removed": current["remove_count"]}


def main():
    from ansible.module_utils.basic import AnsibleModule

    module = AnsibleModule(argument_spec={
        "operation": {"type": "str", "choices": ["configure", "plan", "apply"], "default": "plan"},
        "hub_host": {"type": "str", "required": True},
        "hub_token": {"type": "str", "required": True, "no_log": True},
        "validate_certs": {"type": "bool", "default": True},
        "policy": {"type": "dict", "required": True},
        "requirements_audit": {"type": "dict", "default": {}},
        "expected_plan": {"type": "dict", "default": {}},
    }, supports_check_mode=True)
    parameters = module.params
    try:
        client = Client(parameters["hub_host"], parameters["hub_token"], parameters["validate_certs"])
        operation = parameters["operation"]
        if operation == "configure":
            result = configure(client, parameters["policy"], module.check_mode)
        elif operation == "plan" or module.check_mode:
            result = {"changed": False, "plan": collect_plan(client, parameters["policy"], parameters["requirements_audit"])}
        else:
            if not parameters["expected_plan"]:
                raise PolicyError("Apply requires the complete previously reviewed preview plan.")
            result = apply_plan(client, parameters["policy"], parameters["requirements_audit"], parameters["expected_plan"])
    except PolicyError as error:
        module.fail_json(msg=str(error))
    except Exception:
        module.fail_json(msg="PAH retention could not be verified; no connection values are logged.")
    module.exit_json(**result)


if __name__ == "__main__":
    main()
