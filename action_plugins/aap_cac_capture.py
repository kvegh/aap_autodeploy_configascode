"""Preview or publish reviewed encrypted CaC deltas; never apply to source AAP."""

from collections import Counter
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import yaml
from ansible.errors import AnsibleActionFail
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase
from ansible.template import Templar, trust_as_template
from ansible.utils.unsafe_proxy import wrap_var

ROOT = Path(__file__).resolve().parents[1]
for module_name in ("cac_compare", "cac_snapshot", "cac_yaml", "cac_import"):
    spec = importlib.util.spec_from_file_location(
        module_name, ROOT / ("filter_plugins" if module_name == "cac_import" else "src") / (module_name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
core, extraction = sys.modules["cac_compare"], sys.modules["cac_snapshot"]
vault_yaml = sys.modules["cac_yaml"]


def select_path(data, path):
    current = data
    for key in path:
        if not isinstance(current, dict):
            raise core.CaptureError("A declared CaC section is not a mapping.")
        current = current.get(key, {})
    return [] if current == {} else current


def assign_path(data, path, value):
    current = data
    for key in path[:-1]:
        current = current.setdefault(key, {})
    current[path[-1]] = value


def protected_strings(value):
    if isinstance(value, dict):
        return {key: protected_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [protected_strings(item) for item in value]
    return (
        wrap_var(value)
        if isinstance(value, str) and ("{{" in value or "{%" in value)
        else value
    )


def normalized_resource(resource):
    result = deepcopy(resource)
    for key in ("extra_vars", "variables", "extra_data"):
        if key in result and isinstance(result[key], str):
            parsed = AnsibleLoader(io.StringIO(result[key])).get_single_data() or {}
            if not isinstance(parsed, dict):
                raise core.CaptureError(
                    "Resource variable fields must contain YAML/JSON mappings."
                )
            result[key] = parsed
    if isinstance(result.get("workflow_nodes"), list):
        result["workflow_nodes"] = [
            normalized_resource(node) for node in result["workflow_nodes"]
        ]
    return result


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        try:
            return self._capture(tmp, task_vars)
        except AnsibleActionFail as error:
            # Core 2.16 bypasses failed_when for raised ActionFail, hiding even
            # controlled errors under no_log. The entrypoint prints this bounded
            # refusal separately while all protected inputs remain censored.
            return {"changed": False, "capture_failed": True, "msg": str(error)}
        except Exception:
            return {
                "changed": False,
                "capture_failed": True,
                "msg": "Protected capture preflight failed; inspect scoped inputs without logging secrets.",
            }

    def _capture(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        args = self._task.args
        mode = args.get("mode", "preview")
        scope_key = args.get("scope", "")
        if mode not in ("preview", "initialize", "update") or not re.fullmatch(
            r"[a-z][a-z0-9_-]{0,63}", scope_key
        ):
            raise AnsibleActionFail(
                "Choose a declared scope and preview, initialize or update mode."
            )

        def boolean(value):
            if type(value) is bool:
                return value
            if isinstance(value, str) and value.lower() in ("true", "false"):
                return value.lower() == "true"
            raise AnsibleActionFail(
                "Use explicit Boolean true/false Git publication choices."
            )

        commit, push = boolean(args.get("commit", False)), boolean(
            args.get("push", False)
        )
        if push and not commit:
            raise AnsibleActionFail(
                "Git publication requires explicit Boolean commit and push choices."
            )
        repository = os.environ.get("AAP_CAC_CAPTURE_REPOSITORY", "")
        token = os.environ.get("AAP_CAC_CAPTURE_GIT_TOKEN", "")
        if not repository and not token:
            token = os.environ.get("CAC_GIT_TOKEN", "")
            if token:
                try:
                    repository = sys.modules["cac_import"].autodeploy_repository(
                        self._loader, ROOT
                    )
                except Exception:
                    raise AnsibleActionFail(
                        "Load the encrypted AutoDeploy repository configuration with its environment Vault credential."
                    ) from None
        parsed = extraction.urlsplit(repository)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path in ("", "/")
            or not token
        ):
            raise AnsibleActionFail(
                "Attach the scoped CaC repository credential without credentials in its URL."
            )
        working_copy = args.get("working_copy")
        if mode != "preview" and not push and not working_copy:
            raise AnsibleActionFail(
                "For an unpublished update supply a persistent local working_copy; AAP updates require explicit commit/push."
            )
        if self._task.check_mode:
            mode = "preview"
            commit = push = False
        protected_stage = "private repository read"
        try:
            with tempfile.TemporaryDirectory(prefix="aap-cac-review-") as temporary:
                private = Path(temporary)
                helper = private / "git-askpass"
                helper.write_text(
                    '#!/bin/sh\ncase "$1" in\n*Username*) printf "%s\\n" x-access-token ;;\n*Password*) printf "%s\\n" "$AAP_CAC_CAPTURE_GIT_TOKEN" ;;\n*) exit 1 ;;\nesac\n'
                )
                helper.chmod(0o700)
                environment = dict(
                    os.environ,
                    AAP_CAC_CAPTURE_GIT_TOKEN=token,
                    GIT_ASKPASS=str(helper),
                    GIT_TERMINAL_PROMPT="0",
                    LC_ALL="C",
                    GIT_CONFIG_COUNT="3",
                    GIT_CONFIG_KEY_0="credential.helper",
                    GIT_CONFIG_VALUE_0="",
                    GIT_CONFIG_KEY_1="http.followRedirects",
                    GIT_CONFIG_VALUE_1="false",
                    GIT_CONFIG_KEY_2="http.sslVerify",
                    GIT_CONFIG_VALUE_2="true",
                )
                checkout = (
                    Path(working_copy).resolve()
                    if working_copy
                    else private / "repository"
                )

                def git(*arguments):
                    process = subprocess.run(
                        ["git", "-C", str(checkout), *arguments],
                        env=environment,
                        capture_output=True,
                        text=True,
                        timeout=90,
                    )
                    if process.returncode:
                        raise core.CaptureError(
                            "CaC Git operation failed; no force push or source-AAP change was attempted."
                        )
                    return process.stdout.strip()

                if working_copy:
                    if not checkout.is_dir() or git(
                        "remote", "get-url", "origin"
                    ).rstrip("/") != repository.rstrip("/"):
                        raise core.CaptureError(
                            "The local working copy must have the exact credential-bound origin."
                        )
                    if push:
                        git("fetch", "--quiet", "origin", "main")
                        if git("rev-parse", "HEAD") != git("rev-parse", "origin/main"):
                            raise core.CaptureError(
                                "Publish only from current main; reconcile the local branch first."
                            )
                else:
                    checkout.mkdir(mode=0o700)
                    git("init", "--quiet")
                    git("remote", "add", "origin", repository)
                    git("fetch", "--quiet", "--depth=1", "origin", "main")
                    git("checkout", "--quiet", "--detach", "FETCH_HEAD")
                if commit and git("diff", "--cached", "--name-only"):
                    raise core.CaptureError(
                        "Preserve unrelated staged work; use a clean index for publication."
                    )

                def read_vault(relative):
                    path = checkout / relative
                    if (
                        not path.is_file()
                        or path.is_symlink()
                        or not path.read_bytes().startswith(b"$ANSIBLE_VAULT;")
                    ):
                        raise core.CaptureError(
                            "Scope manifests, captures and baselines must be complete Vault-encrypted files."
                        )
                    plaintext, vault_id, secret = (
                        self._loader._vault.decrypt_and_get_vault_id(
                            path.read_bytes()
                        )
                    )
                    return vault_yaml.load_repository_yaml(plaintext), vault_id, secret

                protected_stage = "capture manifest Vault load"
                manifest, _, _ = read_vault("cac/capture_scopes_vault.yml")
                if manifest.get("schema_version") != 1 or scope_key not in manifest.get(
                    "scopes", {}
                ):
                    raise core.CaptureError(
                        "The selected scope has no reviewed encrypted capture adapter."
                    )
                scope = manifest["scopes"][scope_key]
                if scope.get("unavailable"):
                    raise core.CaptureError(
                        "This scope is unavailable: " + scope["unavailable"]
                    )
                configuration_file = scope["configuration_file"]
                if not re.fullmatch(r"(?:cac/[A-Za-z0-9_-]+|vaults/cac/[A-Za-z0-9_-]+-cac-vault)\.yml", configuration_file):
                    raise core.CaptureError(
                        "Only the declared CaC file may be updated; allocator state is excluded."
                    )
                baseline_file = "baselines/" + scope_key + "_vault.yml"
                protected_stage = "CaC Vault load and normalization"
                configuration, vault_id, secret = read_vault(configuration_file)
                baseline_path = checkout / baseline_file
                retained_baseline = (
                    read_vault(baseline_file)[0] if baseline_path.exists() else {}
                )
                current = {
                    kind: core.indexed(
                        [
                            normalized_resource(entry)
                            for entry in select_path(configuration, path)
                        ],
                        scope["organization"],
                    )
                    for kind, path in scope["sections"].items()
                }
                source_origin = os.environ.get("AAP_CAC_SOURCE_URL", "").rstrip("/")
                if source_origin != scope["source_controller"].rstrip("/"):
                    raise core.CaptureError(
                        "The API credential origin differs from the encrypted scope pin."
                    )
                api = extraction.ControllerReader(
                    source_origin,
                    os.environ.get("AAP_CAC_SOURCE_TOKEN", ""),
                    os.environ.get("AAP_CAC_SOURCE_CA_FILE") or None,
                )
                snapshot = extraction.Snapshot(
                    api, scope, lambda value: AnsibleLoader(value).get_single_data()
                )
                snapshot.retained_dependencies = {
                    kind: sorted(
                        set(scope.get("dependency_names", {}).get(kind, []))
                        | set(
                            retained_baseline.get("source_dependency_names", {}).get(
                                kind, []
                            )
                        )
                    )
                    for kind in ("credentials", "execution_environments", "inventories")
                }
                snapshot.retained_labels = [
                    entry["name"]
                    for entry in retained_baseline.get("source", {})
                    .get("labels", {})
                    .values()
                ]
                protected_stage = "source API extraction"
                live = snapshot.collect()
                if any(
                    project.get("scm_url", "").rstrip("/").removesuffix(".git")
                    != scope["code_repository"].rstrip("/").removesuffix(".git")
                    for project in snapshot.raw_by_kind["projects"]
                ):
                    raise core.CaptureError(
                        "A discovered project requires a different reviewed code-checkout adapter."
                    )
                code_metadata = subprocess.run(
                    ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                    text=True,
                    capture_output=True,
                    timeout=15,
                )
                code_revision = (
                    code_metadata.stdout.strip()
                    if code_metadata.returncode == 0
                    else (
                        (task_vars or {}).get("awx_project_revision")
                        or (task_vars or {}).get("tower_project_revision")
                        or ""
                    )
                )
                if not isinstance(code_revision, str) or not re.fullmatch(
                    r"[a-f0-9]{40,64}", code_revision
                ):
                    raise core.CaptureError(
                        "The code checkout revision is unavailable; retain Git metadata or the AAP project revision variable."
                    )
                source_files = [ROOT / "action_plugins/aap_cac_capture.py"]
                for directory in (
                    "src",
                    "tasks",
                    "templates",
                    "filter_plugins",
                    "vars",
                ):
                    source_files.extend(
                        path
                        for path in (ROOT / directory).rglob("*")
                        if path.is_file() and path.suffix in (".py", ".yml", ".j2")
                    )
                source_files.extend(ROOT.glob("*.yml"))
                code_content_fingerprint = core.fingerprint(
                    {
                        str(path.relative_to(ROOT)): core.hashlib.sha256(
                            path.read_bytes()
                        ).hexdigest()
                        for path in sorted(set(source_files))
                    }
                )
                missing_playbooks = [
                    job["playbook"]
                    for job in snapshot.objects["job_templates"]
                    if job.get("playbook")
                    and (
                        Path(job["playbook"]).is_absolute()
                        or ".." in Path(job["playbook"]).parts
                        or not (ROOT / job["playbook"]).is_file()
                    )
                ]
                if missing_playbooks:
                    raise core.CaptureError(
                        "Captured own-project playbooks are missing from this code checkout; code adaptation is required."
                    )
                protected_stage = "code ownership comparison"
                code_current, code_live = {}, {}
                for entry in scope.get("code_owned_workflows", []):
                    if (
                        Path(entry["template"]).is_absolute()
                        or ".." in Path(entry["template"]).parts
                    ):
                        raise core.CaptureError(
                            "Code-owned adapters must use repository-local template paths."
                        )
                    graph = Templar(
                        loader=self._loader,
                        variables=dict(task_vars or {}, **configuration),
                    ).template(trust_as_template((ROOT / entry["template"]).read_text()))
                    expected = AnsibleLoader(graph).get_single_data()
                    for node in expected:
                        node.setdefault("extra_data", {})
                        node.setdefault("all_parents_must_converge", False)
                    code_current[entry["name"]] = {"workflow_nodes": expected}
                    prior = snapshot.scope
                    snapshot.scope = dict(
                        scope,
                        sections={"workflows": []},
                        workflow_names=[entry["name"]],
                        owned_labels=[],
                    )
                    snapshot.collect_workflows()
                    snapshot.scope = prior
                    code_live[entry["name"]] = (
                        {
                            "workflow_nodes": snapshot.objects["workflows"][0][
                                "workflow_nodes"
                            ]
                        }
                        if snapshot.objects["workflows"]
                        else {}
                    )
                protected_stage = "accepted baseline comparison"
                baseline_path = checkout / baseline_file
                if baseline_path.exists():
                    baseline, _, _ = read_vault(baseline_file)
                    if mode == "initialize":
                        raise core.CaptureError(
                            "An accepted baseline already exists; initialization cannot overwrite it."
                        )
                    if baseline.get("schema_version") != 1 or baseline.get(
                        "scope_fingerprint"
                    ) != core.fingerprint(scope):
                        raise core.CaptureError(
                            "The reviewed scope changed; adapt/review its baseline explicitly."
                        )
                    comparison = core.compare(
                        baseline["source"], baseline["desired"], current, live, True
                    )
                    code_comparison = core.compare(
                        baseline.get("code_source", {}),
                        baseline.get("code_desired", {}),
                        code_current,
                        code_live,
                        True,
                    )
                    initialization = False
                else:
                    comparison = core.compare(live, current, current, live, True)
                    code_comparison = core.compare(
                        code_live, code_current, code_current, code_live, True
                    )
                    initialization = True
                    if mode == "update":
                        raise core.CaptureError(
                            "No accepted baseline exists. Review preview, then explicitly initialize; no baseline was guessed."
                        )
                # Required owned labels are desired policy; never PATCH them onto the source.
                for job in comparison["merged"].get("job_templates", {}).values():
                    job["labels"] = sorted(
                        set(job.get("labels", [])) | set(scope["owned_labels"])
                    )
                comparison["desired_changes"] = core.semantic_diff(
                    current, comparison["merged"]
                )
                validation_errors = []
                try:
                    core.validate_dependencies(
                        comparison["merged"], scope.get("external_dependencies", {})
                    )
                except core.CaptureError as error:
                    validation_errors.append(str(error))
                code_blocked = bool(
                    code_comparison["desired_changes"] or code_comparison["conflicts"]
                )
                report = {
                    "schema_version": 1,
                    "scope": scope_key,
                    "initialization_required": initialization,
                    "visibility_evidence": {
                        "controller_superuser_verified": True,
                        "complete_pagination": True,
                        "relationship_reads_complete": True,
                    },
                    "source_code_revision": code_revision,
                    "source_code_content_fingerprint": code_content_fingerprint,
                    "configuration_revision": git("rev-parse", "HEAD"),
                    "comparison": comparison,
                    "source_snapshot": live,
                    "current_desired": current,
                    "code_owned_comparison": code_comparison,
                    "code_owned_source": code_live,
                    "code_owned_desired": code_current,
                    "initial_code_vs_desired": (
                        core.semantic_diff(code_current, code_live)
                        if initialization
                        else []
                    ),
                    "initial_source_vs_desired": (
                        core.semantic_diff(current, live) if initialization else []
                    ),
                    "code_adaptation_required": code_blocked,
                    "validation_errors": validation_errors,
                    "limitations": [
                        "API-masked secret rotation is unobservable; refresh existing vaulted inputs separately.",
                        "No arbitrary Ansible AST reconciliation, Gateway/EDA/PAH settings or unsupported node overrides.",
                    ],
                }
                digest = core.fingerprint(
                    {
                        "scope": scope,
                        "source": live,
                        "desired": current,
                        "code_revision": code_revision,
                        "code_content_fingerprint": code_content_fingerprint,
                        "comparison": comparison,
                        "code": code_comparison,
                        "initialization": initialization,
                    }
                )
                report["review_digest"] = digest

                protected_stage = "encrypted review validation"

                def encrypt(data):
                    protected = protected_strings(data)
                    encoded = yaml.dump(
                        protected,
                        Dumper=vault_yaml.VaultDumper,
                        sort_keys=False,
                        width=110,
                    ).encode()
                    sealed = self._loader._vault.encrypt(
                        encoded, secret=secret, vault_id=vault_id
                    )
                    loaded = vault_yaml.load_repository_yaml(
                        self._loader._vault.decrypt(sealed)
                    )
                    if loaded != data or vault_yaml.literal_paths(
                        loaded
                    ) != vault_yaml.literal_paths(protected):
                        raise core.CaptureError(
                            "Vault roundtrip validation failed before any publication."
                        )
                    return sealed.rstrip(b"\n") + b"\n"

                counts = dict(
                    Counter(item["operation"] for item in comparison["source_changes"])
                )
                result.update(
                    changed=False,
                    mode=mode,
                    scope=scope_key,
                    review_digest=digest,
                    source_change_counts=counts,
                    desired_change_count=len(comparison["desired_changes"]),
                    conflict_count=len(comparison["conflicts"]),
                    validation_error_count=len(validation_errors),
                    initialization_required=initialization,
                    initial_difference_count=len(report["initial_source_vs_desired"]),
                    initial_code_difference_count=len(
                        report["initial_code_vs_desired"]
                    ),
                    code_adaptation_required=code_blocked,
                    encrypted_review=encrypt(report).decode(),
                )
                if mode == "preview":
                    return result
                if (
                    args.get("review_digest") != digest
                    or comparison["conflicts"]
                    or code_blocked
                    or validation_errors
                ):
                    raise core.CaptureError(
                        "A fresh matching review digest and resolved source/repository/code conflicts are required."
                    )
                if initialization and mode != "initialize":
                    raise core.CaptureError(
                        "Choose explicit reviewed initialize for the first accepted baseline."
                    )
                if not initialization:
                    for kind, path in scope["sections"].items():
                        assign_path(
                            configuration,
                            path,
                            list(comparison["merged"][kind].values()),
                        )
                    # Verify all required label definitions exist in the resulting complete capture.
                    defined = {
                        x["name"]
                        for x in comparison["merged"].get("labels", {}).values()
                    }
                    if any(
                        set(job.get("labels", [])) - defined
                        for job in comparison["merged"]
                        .get("job_templates", {})
                        .values()
                    ):
                        raise core.CaptureError(
                            "A referenced label definition is missing; refuse incomplete CaC publication."
                        )
                accepted = {
                    "schema_version": 1,
                    "scope_fingerprint": core.fingerprint(scope),
                    "source": live,
                    "desired": current if initialization else comparison["merged"],
                    "code_source": code_live,
                    "code_desired": code_current,
                    "source_code_revision": code_revision,
                    "source_code_content_fingerprint": code_content_fingerprint,
                    "source_dependency_names": {
                        kind: sorted(set(names))
                        for kind, names in getattr(
                            snapshot, "source_dependency_names", {}
                        ).items()
                    },
                }
                if not initialization and accepted == baseline:
                    return result
                baseline_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                capture_changed = not initialization and comparison["merged"] != current
                if capture_changed:
                    (checkout / configuration_file).write_bytes(encrypt(configuration))
                baseline_path.write_bytes(encrypt(accepted))
                files = [baseline_file] + (
                    [configuration_file] if capture_changed else []
                )
                protected_stage = "reviewed Git publication"
                if commit:
                    git("add", "--", *files)
                    if set(git("diff", "--cached", "--name-only").splitlines()) - set(
                        files
                    ):
                        raise core.CaptureError(
                            "Unrelated staged files appeared; publication was stopped."
                        )
                    git(
                        "-c",
                        "user.name=AAP CaC capture",
                        "-c",
                        "user.email=automation@example.invalid",
                        "commit",
                        "--quiet",
                        "-m",
                        "Accept reviewed encrypted CaC "
                        + ("baseline" if initialization else "changes"),
                    )
                if push:
                    git("push", "origin", "HEAD:refs/heads/main")
                    git("fetch", "--quiet", "origin", "main")
                    if git("rev-parse", "HEAD") != git("rev-parse", "FETCH_HEAD"):
                        raise core.CaptureError(
                            "Remote publication verification failed; inspect accepted commits before retrying."
                        )
                result.update(
                    changed=True,
                    committed=commit,
                    pushed=push,
                    resulting_revision=git("rev-parse", "HEAD"),
                    working_copy=str(checkout) if working_copy else None,
                )
                return result
        except core.CaptureError as error:
            if (
                "api" in locals()
                and getattr(api, "diagnostic", None) is not None
                and "secret" in locals()
            ):
                failure = {"changed": False, "capture_failed": True, "msg": str(error)}
                diagnostic = {
                    "source_network_diagnostic": api.diagnostic,
                    "source_aap_mutations": 0,
                }
                sealed = self._loader._vault.encrypt(
                    yaml.dump(diagnostic, Dumper=vault_yaml.VaultDumper).encode(),
                    secret=secret,
                    vault_id=vault_id,
                )
                failure["encrypted_diagnostic"] = sealed.rstrip(b"\n").decode() + "\n"
                return failure
            raise AnsibleActionFail(str(error)) from None
        except Exception as error:
            raise AnsibleActionFail(
                "Protected capture failed during "
                + protected_stage
                + " ("
                + type(error).__name__
                + "); inspect protected scoped inputs. No source-AAP mutation was attempted."
            ) from None
