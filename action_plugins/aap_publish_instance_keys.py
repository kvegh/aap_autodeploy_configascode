"""Publish one saved token to encrypted CaC and the source AAP token store."""

from importlib.util import module_from_spec, spec_from_file_location
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import tempfile

import yaml
from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = spec_from_file_location(name, path)
    result = module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


keys = load("publish_instance_keys", ROOT / "src/aap_instance_keys.py")
contract = load("publish_cac_contract", ROOT / "filter_plugins/cac_import.py")
vault_yaml = load("publish_cac_yaml", ROOT / "src/cac_yaml.py")
routing = load("publish_inventory_routing", ROOT / "filter_plugins/aap_instance_route.py")


SourceClient = keys.SourceClient

class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def _project_root(self):
        """Read settings from this invocation; the native module cache may outlive a checkout."""
        path = getattr(self, '_original_path', None)
        keys.require(isinstance(path, str) and Path(path).is_absolute(),
                     'Resolve the publisher from its current native action-plugin path.')
        source = Path(path).resolve(strict=True)
        keys.require(source.is_file() and source.name == 'aap_publish_instance_keys.py'
                     and source.parent.name == 'action_plugins',
                     'Require the current native publisher source before reading encrypted settings.')
        return source.parents[1]

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        try:
            if self._task.args.get("operation") in ("release_guest", "guest_bootstrap_https", "guest_bootstrap_http", "installation_access", "retire_guest", "aap_supplemental_interface"):
                return self.release_guest(result, task_vars or {})
            if self._task.check_mode:
                result.update(changed=False, published=False)
                return result
            args = self._task.args
            keys.require(set(args) >= {"instance_name", "record", "organization"} and
                         set(args) <= {"instance_name", "record", "organization", "operation", "inventory_registration",
                                      "isolation_retirement"},
                         "Publish only the selected instance's verified saved token.")
            retiring = args.get("operation", "publish") == "retire"
            keys.require(args.get("operation", "publish") in ("publish", "retire"),
                         "Choose instance access publication or retirement.")
            isolation_retirement = args.get("isolation_retirement")
            keys.require("isolation_retirement" not in args or (retiring and isinstance(isolation_retirement, dict)),
                         "Isolation retirement is permitted only during final selected instance retirement.")
            registration = args.get("inventory_registration")
            if registration:
                keys.require(not retiring and set(registration) == {"route", "policy"},
                             "Publish inventory placement only with a fresh instance token.")
                registered_route = routing.instance_route(registration["route"])
                keys.require(registered_route["vm_name"] == args["instance_name"] and
                             keys.origin(registered_route["aap_hostname"]) == keys.origin(args["record"]["target"]),
                             "Inventory placement must identify the same verified token destination.")
                declared = registration["policy"]
                keys.require(routing.isolation_policy(registered_route["hypervisor"],
                    declared.get("https_clients", []), declared.get("protected_ipv4"),
                    declared.get("guest_host_clients", []), declared.get("released_clients", []), declared.get("http_clients", [])) == declared,
                    "Publish the current declared recovery isolation policy without changing its scope.")
            token = os.environ.get("CAC_GIT_TOKEN", "")
            keys.require(bool(token), "Attach VM allocation git Pseudo CMDB writer for token publication.")
            repository = contract.autodeploy_repository(self._loader, self._project_root())
            source = SourceClient()
            keys.require(source.origin != keys.origin(args["record"].get("target")),
                         "Source API access must identify the AAP running this fresh deployment.")
            variables = task_vars or {}
            preflight_ownership = variables.get("aap_registered_target", {}).get("related_resource_proof")
            job_id = variables.get("awx_job_id")
            template_id = variables.get("awx_job_template_id")
            revision = variables.get("awx_project_revision")
            keys.require(str(job_id).isdigit() and str(template_id).isdigit() and bool(revision),
                         "Publish instance access from its source AAP deployment job.")
            current_job = source.request("GET", "jobs/%s/" % job_id)
            keys.require(current_job.get("status") == "running"
                         and current_job.get("job_template") == int(template_id)
                         and current_job.get("scm_revision") == revision,
                         "The source API credential does not identify this running deployment job.")
            relative = "vaults/cac/aap_autodeploy_configascode-cac-vault.yml"
            with tempfile.TemporaryDirectory(prefix="aap-instance-token-publish-") as temporary:
                workspace = Path(temporary)
                helper = workspace / "askpass"
                helper.write_text('#!/bin/sh\ncase "$1" in\n*Username*) printf "%s\\n" x-access-token ;;\n*Password*) printf "%s\\n" "$CAC_GIT_TOKEN" ;;\n*) exit 1 ;;\nesac\n')
                helper.chmod(0o700)
                environment = dict(os.environ, GIT_ASKPASS=str(helper), GIT_TERMINAL_PROMPT="0",
                    GIT_CONFIG_COUNT="3", GIT_CONFIG_KEY_0="credential.helper", GIT_CONFIG_VALUE_0="",
                    GIT_CONFIG_KEY_1="http.followRedirects", GIT_CONFIG_VALUE_1="false",
                    GIT_CONFIG_KEY_2="http.sslVerify", GIT_CONFIG_VALUE_2="true", LC_ALL="C")
                published = False
                source_ownership_snapshot = None
                retirement_counter = None
                for attempt in range(8):
                    checkout = workspace / str(attempt)
                    checkout.mkdir(mode=0o700)

                    def git(*arguments, optional=False):
                        response = subprocess.run(["git", "-C", str(checkout), *arguments],
                            env=environment, text=True, capture_output=True, timeout=60)
                        if response.returncode and not optional:
                            raise keys.StoreError("Protected instance-token Git publication failed; no force push was attempted.")
                        return response

                    git("init", "--quiet")
                    git("remote", "add", "origin", repository)
                    git("fetch", "--quiet", "--depth=1", "origin", "main")
                    git("checkout", "--quiet", "--detach", "FETCH_HEAD")
                    retirement_context = None
                    management_context = None
                    if isolation_retirement is not None:
                        allocation_path = checkout / "state/aap_vm_allocations_vault.yml"
                        keys.require(allocation_path.is_file() and not allocation_path.is_symlink(),
                                     "Read the selected encrypted reservation before planning source retirement.")
                        allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(allocation_path.read_bytes()))
                        selected_records = [row for row in allocation["aap_vm_allocation"]["reservations"].values()
                                            if row.get("vm_name") == args["instance_name"]]
                        keys.require(len(selected_records) == 1, "Resolve exactly one consumed selected reservation.")
                        ownership_path = checkout / "cac/host_inventory.yml"
                        keys.require(ownership_path.is_file() and not ownership_path.is_symlink(),
                                     "Use the fixed encrypted shared inventory for source ownership lookup.")
                        ownership_capture = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(ownership_path.read_bytes()))
                        source_ownership_snapshot = keys.source_related_resources(source, ownership_capture,
                            allocation["aap_vm_allocation"], args["instance_name"],
                            variables.get("aap_isolation_app_capture", {}).get("ansible_facts"), source_ownership_snapshot)
                        if attempt == 0:
                            keys.require(isinstance(preflight_ownership, dict)
                                and preflight_ownership.get("source_job_id") == str(job_id)
                                and preflight_ownership.get("source_project_revision") == revision
                                and all(preflight_ownership.get(key) == source_ownership_snapshot[key] for key in (
                                    "instance_name", "inventory_name", "inventory_id", "hypervisor_name",
                                    "hypervisor_machine_id", "related_resources")),
                                "Final source ownership differs from this running job's verified preflight.")
                        retirement_context = keys.isolation_retirement_context(selected_records[0], args["instance_name"],
                            args["record"].get("target"), isolation_retirement, source_ownership_snapshot["related_resources"])
                        keys.verify_remaining_guest_grants(retirement_context["desired_policy"], source_ownership_snapshot)
                    path = checkout / relative
                    keys.require(path.is_file() and not path.is_symlink(), "Require the existing encrypted AutoDeploy CaC file.")
                    plain, label, secret = self._loader._vault.decrypt_and_get_vault_id(path.read_bytes())
                    before = vault_yaml.load_repository_yaml(plain)
                    after = (keys.retire_record(before, args["instance_name"], args["record"].get("target"))
                             if retiring else keys.merge_record(before, args["instance_name"], args["record"]))
                    if retirement_context is not None:
                        after = keys.retire_inventory_capture(after, retirement_context, "autodeploy")
                    changes = [(relative, path, before, after, label, secret)]
                    retirement_shared = retirement_hactar = None
                    if registration:
                        allocation_path = checkout / "state/aap_vm_allocations_vault.yml"
                        keys.require(allocation_path.is_file() and not allocation_path.is_symlink(),
                                     "Read existing primary ownership before publishing management access.")
                        allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(allocation_path.read_bytes()))
                        selected_records = [row for row in allocation["aap_vm_allocation"]["reservations"].values()
                                            if row.get("vm_name") == args["instance_name"]]
                        keys.require(len(selected_records) == 1, "Resolve one active primary reservation for management access.")
                        management_context = keys.management_access_context(before, selected_records[0],
                            args["instance_name"], registered_route, declared)
                        after = keys.management_inventory_capture(after, management_context, "autodeploy")
                        changes[0] = (relative, path, before, after, label, secret)
                        extra = "cac/host_inventory.yml"
                        extra_path = checkout / extra
                        keys.require(extra_path.is_file() and not extra_path.is_symlink(),
                                     "Require the maintained encrypted shared inventory capture.")
                        raw, extra_label, extra_secret = self._loader._vault.decrypt_and_get_vault_id(
                            extra_path.read_bytes())
                        old = vault_yaml.load_repository_yaml(raw)
                        updated = keys.management_inventory_capture(old, management_context, "shared")
                        updated = keys.merge_inventory(updated, args["instance_name"], registered_route, management_context["desired_policy"],
                            management_context["primary"])
                        management_shared = updated
                        changes.append((extra, extra_path, old, updated, extra_label, extra_secret))
                        management_hactar = None
                        extra = "cac/hactar_recovery.yml"
                        extra_path = checkout / extra
                        if extra_path.exists():
                            keys.require(extra_path.is_file() and not extra_path.is_symlink(),
                                         "Use the existing encrypted Hactar rebuild capture.")
                            raw, extra_label, extra_secret = self._loader._vault.decrypt_and_get_vault_id(
                                extra_path.read_bytes())
                            old = vault_yaml.load_repository_yaml(raw)
                            management_hactar = keys.management_inventory_capture(old, management_context, "hactar")
                            changes.append((extra, extra_path, old, management_hactar, extra_label, extra_secret))
                        keys.source_management_operations(source, management_shared, after, management_hactar, management_context)
                    if retiring:
                        for extra in ("state/aap_vm_allocations_vault.yml", "cac/host_inventory.yml"):
                            extra_path = checkout / extra
                            keys.require(extra_path.is_file() and not extra_path.is_symlink(),
                                         "Require maintained encrypted allocation and inventory definitions for retirement.")
                            raw, extra_label, extra_secret = self._loader._vault.decrypt_and_get_vault_id(
                                extra_path.read_bytes())
                            old = vault_yaml.load_repository_yaml(raw)
                            updated = deepcopy(old)
                            if extra.startswith("state/"):
                                state = updated["aap_vm_allocation"]
                                current_counter = state.get("next_number")
                                keys.require((isinstance(current_counter, int) and not isinstance(current_counter, bool)) and 0 < current_counter < 2**31
                                    and (retirement_counter is None or current_counter >= retirement_counter)
                                    and all((isinstance(row.get("number"), int) and not isinstance(row.get("number"), bool)) and 0 < row["number"] < current_counter
                                            for row in state["reservations"].values()),
                                    "Keep a valid monotonic allocation counter during retirement.")
                                retirement_counter = current_counter
                                matches = [row for row in updated["aap_vm_allocation"]["reservations"].values()
                                           if row.get("vm_name") == args["instance_name"]]
                                keys.require(len(matches) == 1 and
                                    keys.origin(matches[0]["instance_route"]["aap_hostname"]) ==
                                    keys.origin(args["record"].get("target")),
                                    "Retirement must match exactly one consumed allocation and public URL.")
                                matches[0]["decommissioned"] = True
                                retirement_record = deepcopy(matches[0])
                            else:
                                if retirement_context is not None:
                                    updated = keys.retire_inventory_capture(updated, retirement_context, "shared")
                                    retirement_shared = updated
                                else:
                                    inventory = updated["host_inventory_configuration"]
                                    inventory["hosts"] = [row for row in inventory["hosts"]
                                        if row.get("name") != args["instance_name"]]
                                    for group in inventory["groups"]:
                                        group["hosts"] = [name for name in group.get("hosts", [])
                                                          if name != args["instance_name"]]
                            changes.append((extra, extra_path, old, updated, extra_label, extra_secret))
                    if retirement_context is not None:
                        extra = "cac/hactar_recovery.yml"
                        extra_path = checkout / extra
                        if extra_path.exists():
                            keys.require(extra_path.is_file() and not extra_path.is_symlink(),
                                         "Use only the maintained encrypted Hactar rebuild capture.")
                            raw, extra_label, extra_secret = self._loader._vault.decrypt_and_get_vault_id(
                                extra_path.read_bytes())
                            old = vault_yaml.load_repository_yaml(raw)
                            retirement_hactar = keys.retire_inventory_capture(old, retirement_context, "hactar")
                            changes.append((extra, extra_path, old, retirement_hactar, extra_label, extra_secret))
                        # Validate every current API target before any encrypted publication or source write.
                        keys.source_retirement_operations(source, retirement_shared, after, retirement_hactar, retirement_context)
                    changed_files = []
                    for changed_relative, changed_path, old, desired, changed_label, changed_secret in changes:
                        if old == desired:
                            continue
                        sealed = self._loader._vault.encrypt(yaml.dump(desired, Dumper=vault_yaml.VaultDumper,
                            sort_keys=False, width=110), secret=changed_secret, vault_id=changed_label)
                        restored = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(sealed))
                        keys.require(restored == desired and
                            vault_yaml.literal_paths(restored) == vault_yaml.literal_paths(desired),
                            "Instance updates must preserve literal templates and unrelated definitions.")
                        changed_path.write_bytes(sealed)
                        changed_files.append(changed_relative)
                    if not changed_files:
                        break
                    git("add", "--", *changed_files)
                    git("-c", "user.name=AAP AutoDeploy", "-c", "user.email=automation@example.invalid",
                        "commit", "--quiet", "-m", "Retire encrypted instance access" if retiring
                        else "Update encrypted instance API access")
                    pushed = git("push", "origin", "HEAD:refs/heads/main", optional=True)
                    if pushed.returncode == 0:
                        published = True
                        break
                else:
                    raise keys.StoreError("Competing Git updates prevented token publication; retry without replacing the saved target token.")
                api_changed = False
                # Another deployment may publish while this job updates AAP.
                # Reread Git after the API write so an older writer cannot leave
                # the shared credential missing a concurrently added instance.
                for _ in range(8):
                    git("fetch", "--quiet", "--depth=1", "origin", "main")
                    latest = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                        git("show", "FETCH_HEAD:" + relative).stdout.encode()))
                    if retiring:
                        keys.require(args["instance_name"] not in latest.get("aap_instance_api_credentials", {}),
                                     "The retired access entry was concurrently restored; review before continuing.")
                    else:
                        keys.require(args["instance_name"] in latest.get("aap_instance_api_credentials", {}),
                                     "The published instance entry is missing; review concurrent CaC changes.")
                        keys.merge_record(latest, args["instance_name"], args["record"])
                    records = latest["aap_instance_api_credentials"]
                    synchronized = keys.ensure_source_store(source, records, args["organization"])
                    api_changed = api_changed or synchronized["changed"]
                    if registration:
                        inventory = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:cac/host_inventory.yml").stdout.encode()))
                        latest_allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml").stdout.encode()))
                        latest_records = [row for row in latest_allocation["aap_vm_allocation"]["reservations"].values()
                                          if row.get("vm_name") == args["instance_name"]]
                        keys.require(len(latest_records) == 1, "Keep the exact primary reservation during source synchronization.")
                        management_context = keys.management_access_context(latest, latest_records[0],
                            args["instance_name"], registered_route, declared)
                        keys.require(keys.management_inventory_capture(latest, management_context, "autodeploy") == latest,
                            "Canonical rebuild management declaration changed during source synchronization.")
                        keys.require(keys.management_inventory_capture(inventory, management_context, "shared") == inventory,
                            "Canonical shared management declaration changed during source synchronization.")
                        hactar_file = git("show", "FETCH_HEAD:cac/hactar_recovery.yml", optional=True)
                        management_hactar = (vault_yaml.load_repository_yaml(self._loader._vault.decrypt(hactar_file.stdout.encode()))
                                              if hactar_file.returncode == 0 else None)
                        if management_hactar is not None:
                            keys.require(keys.management_inventory_capture(management_hactar, management_context, "hactar") == management_hactar,
                                         "Canonical Hactar management declaration changed during synchronization.")
                        operations = keys.source_management_operations(source, inventory, latest, management_hactar, management_context)
                        for method, api_path, body in operations:
                            source.request(method, api_path, body)
                            api_changed = True
                        keys.require(not keys.source_management_operations(source, inventory, latest,
                            management_hactar, management_context), "Verify every source management policy alias before registration.")
                        api_changed = keys.ensure_source_inventory(source, inventory,
                            args["instance_name"], registered_route) or api_changed
                    if retiring:
                        if retirement_context is not None:
                            latest_allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                                git("show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml").stdout.encode()))
                            latest_records = [row for row in latest_allocation["aap_vm_allocation"]["reservations"].values()
                                              if row.get("vm_name") == args["instance_name"]]
                            ownership_capture = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                                git("show", "FETCH_HEAD:cac/host_inventory.yml").stdout.encode()))
                            source_ownership_snapshot = keys.source_related_resources(source, ownership_capture,
                                latest_allocation["aap_vm_allocation"], args["instance_name"],
                                variables.get("aap_isolation_app_capture", {}).get("ansible_facts"), source_ownership_snapshot)
                            keys.verify_remaining_guest_grants(retirement_context["desired_policy"], source_ownership_snapshot)
                            keys.require(len(latest_records) == 1 and latest_records[0].get("decommissioned") is True
                                and keys.isolation_retirement_context(latest_records[0], args["instance_name"],
                                    args["record"].get("target"), isolation_retirement,
                                    source_ownership_snapshot["related_resources"]) == retirement_context,
                                "Selected retirement ownership changed during source synchronization.")
                            keys.require(keys.retire_inventory_capture(latest, retirement_context, "autodeploy") == latest,
                                         "Canonical rebuild inventory changed after retirement publication.")
                            retirement_shared = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                                git("show", "FETCH_HEAD:cac/host_inventory.yml").stdout.encode()))
                            keys.require(keys.retire_inventory_capture(retirement_shared, retirement_context, "shared") == retirement_shared,
                                         "Canonical shared inventory changed after retirement publication.")
                            retirement_hactar = None
                            hactar_file = git("show", "FETCH_HEAD:cac/hactar_recovery.yml", optional=True)
                            if hactar_file.returncode == 0:
                                retirement_hactar = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(hactar_file.stdout.encode()))
                                keys.require(keys.retire_inventory_capture(retirement_hactar, retirement_context, "hactar") == retirement_hactar,
                                             "Canonical Hactar capture changed after retirement publication.")
                            source_operations = keys.source_retirement_operations(source, retirement_shared,
                                latest, retirement_hactar, retirement_context)
                            for method, api_path, body in source_operations:
                                if method != "PATCH":
                                    continue
                                source.request(method, api_path, body)
                                api_changed = True
                            remaining_operations = keys.source_retirement_operations(source, retirement_shared,
                                latest, retirement_hactar, retirement_context)
                            keys.require(all(method == "DELETE" for method, _, _ in remaining_operations),
                                         "Verify every source policy alias before deleting guest ownership records.")
                            for method, api_path, body in remaining_operations:
                                source.request(method, api_path, body)
                                api_changed = True
                            keys.require(not keys.source_retirement_operations(source, retirement_shared,
                                latest, retirement_hactar, retirement_context),
                                "Verify completed source inventory retirement before returning success.")
                        else:
                            for host in source.rows("hosts/?name=" + args["instance_name"]):
                                variables = yaml.safe_load(host.get("variables", "{}")) or {}
                                keys.require(keys.origin("https://" + variables.get("ansible_fqdn", "")) ==
                                             keys.origin(args["record"].get("target")),
                                             "The source inventory entry does not identify the retired instance.")
                                source.request("DELETE", "hosts/%s/" % host["id"])
                                api_changed = True
                        native_name = args["instance_name"] + " MCP and API token"
                        for credential in source.rows("credentials/?name=" + native_name.replace(" ", "%20")):
                            keys.require(keys.origin(credential.get("inputs", {}).get("host", "")) ==
                                         keys.origin(args["record"].get("target")),
                                         "The source manual API credential does not identify the retired instance.")
                            consumers = source.rows("job_templates/?credentials=%s" % credential["id"])
                            consumers += source.rows("workflow_job_template_nodes/?credentials=%s" % credential["id"])
                            keys.require(not consumers, "Detach the retired native API credential before removing it.")
                            source.request("DELETE", "credentials/%s/" % credential["id"])
                            api_changed = True
                    git("fetch", "--quiet", "--depth=1", "origin", "main")
                    observed = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                        git("show", "FETCH_HEAD:" + relative).stdout.encode()))
                    inventory_stable = True
                    if registration:
                        observed_inventory = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:cac/host_inventory.yml").stdout.encode()))
                        observed_allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml").stdout.encode()))
                        observed_hactar = git("show", "FETCH_HEAD:cac/hactar_recovery.yml", optional=True)
                        observed_hactar = (vault_yaml.load_repository_yaml(self._loader._vault.decrypt(observed_hactar.stdout.encode()))
                                           if observed_hactar.returncode == 0 else None)
                        inventory_stable = (observed == latest and observed_inventory == inventory
                            and observed_allocation == latest_allocation and observed_hactar == management_hactar)
                    if retirement_context is not None:
                        observed_inventory = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:cac/host_inventory.yml").stdout.encode()))
                        observed_hactar = git("show", "FETCH_HEAD:cac/hactar_recovery.yml", optional=True)
                        observed_hactar = (vault_yaml.load_repository_yaml(self._loader._vault.decrypt(observed_hactar.stdout.encode()))
                                           if observed_hactar.returncode == 0 else None)
                        observed_allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml").stdout.encode()))
                        observed_records = [row for row in observed_allocation["aap_vm_allocation"]["reservations"].values()
                                            if row.get("vm_name") == args["instance_name"]]
                        inventory_stable = (observed == latest and observed_inventory == retirement_shared
                                            and observed_hactar == retirement_hactar and observed_records == latest_records)
                    if observed.get("aap_instance_api_credentials") == records and inventory_stable:
                        if retiring:
                            # Keep ownership until API cleanup succeeds; see docs/decommission.md.
                            allocation_relative = "state/aap_vm_allocations_vault.yml"
                            allocation_raw = git("show", "FETCH_HEAD:" + allocation_relative).stdout.encode()
                            plain, allocation_label, allocation_secret = self._loader._vault.decrypt_and_get_vault_id(
                                allocation_raw)
                            final_allocation = vault_yaml.load_repository_yaml(plain)
                            state = final_allocation["aap_vm_allocation"]
                            matches = [(key, row) for key, row in state["reservations"].items()
                                       if row.get("vm_name") == args["instance_name"]]
                            keys.require(len(matches) == 1 and matches[0][1] == retirement_record,
                                "The selected retired reservation changed before final removal.")
                            keys.require((isinstance(state.get("next_number"), int) and not isinstance(state.get("next_number"), bool))
                                and retirement_counter <= state["next_number"] < 2**31
                                and all((isinstance(row.get("number"), int) and not isinstance(row.get("number"), bool)) and 0 < row["number"] < state["next_number"]
                                        for row in state["reservations"].values()),
                                "Refuse a regressed allocation counter before final reservation removal.")
                            desired_allocation = deepcopy(final_allocation)
                            del desired_allocation["aap_vm_allocation"]["reservations"][matches[0][0]]
                            sealed = self._loader._vault.encrypt(
                                yaml.dump(desired_allocation, Dumper=vault_yaml.VaultDumper, sort_keys=False, width=110),
                                secret=allocation_secret, vault_id=allocation_label)
                            restored = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(sealed))
                            keys.require(restored == desired_allocation
                                and vault_yaml.literal_paths(restored) == vault_yaml.literal_paths(desired_allocation),
                                "Final reservation removal must preserve other allocations and literal data.")
                            git("checkout", "--quiet", "--detach", "FETCH_HEAD")
                            (checkout / allocation_relative).write_bytes(sealed)
                            git("add", "--", allocation_relative)
                            git("-c", "user.name=AAP AutoDeploy", "-c", "user.email=automation@example.invalid",
                                "commit", "--quiet", "-m", "Remove completed instance reservation")
                            if git("push", "origin", "HEAD:refs/heads/main", optional=True).returncode:
                                continue
                            published = True
                            git("fetch", "--quiet", "--depth=1", "origin", "main")
                            keys.require(git("rev-parse", "HEAD").stdout == git("rev-parse", "FETCH_HEAD").stdout,
                                "Concurrent changes followed final reservation removal; review current CaC.")
                            verified_allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                                git("show", "FETCH_HEAD:" + allocation_relative).stdout.encode()))
                            keys.require(verified_allocation == desired_allocation,
                                "Verify selected reservation absence and unchanged counter after publication.")
                        result.update(changed=published or api_changed, published=True,
                            source_credential_id=synchronized["credential_id"])
                        return result
                raise keys.StoreError("Concurrent instance updates prevented source synchronization; retry using the saved target token.")
        except keys.StoreError as error:
            raise AnsibleActionFail(str(error)) from None
        except Exception:
            raise AnsibleActionFail("Protected instance-token publication failed; the target token remains saved for review.") from None


    def release_guest(self, result, variables):
        """Plan and publish one verified guest change using existing Git/API access."""
        durable = False
        supplemental = False
        try:
            args = self._task.args
            installation = args.get("operation") == "installation_access"
            retirement = args.get("operation") == "retire_guest"
            supplemental = args.get('operation') == 'aap_supplemental_interface'
            aap_release = (args.get("operation") == "release_guest" and isinstance(args.get("guest"), dict)
                           and args["guest"].get("kind") == "aap")
            required = ({"operation", "route", "primary"} if installation else
                        {"operation", "guest_name", "hypervisor"} if retirement else
                        {"operation", "guest", "hypervisor"})
            keys.require(set(args) >= required
                and set(args) <= required | {"phase", "transition"} | ({"guest_kind"} if retirement else set())
                and args.get("phase", "publish") in ("plan", "publish"),
                "Use only the fixed verified guest release request.")
            phase = "plan" if self._task.check_mode else args.get("phase", "publish")
            keys.require(phase == "plan" or isinstance(args.get("transition"), dict),
                "Publish only after protected source preflight and live guest verification.")
            keys.require(bool(os.environ.get("CAC_GIT_TOKEN")),
                "Attach the existing VM allocation git Pseudo CMDB writer for durable release.")
            source = SourceClient()
            keys.verify_source_job(source, None, variables)
            repository = contract.autodeploy_repository(self._loader, self._project_root())
            names = {"autodeploy": "vaults/cac/aap_autodeploy_configascode-cac-vault.yml",
                     "shared": "cac/host_inventory.yml", "hactar": "cac/hactar_recovery.yml"}
            if supplemental:
                names['allocation'] = 'state/aap_vm_allocations_vault.yml'
            with tempfile.TemporaryDirectory(prefix="aap-guest-release-") as temporary:
                workspace = Path(temporary)
                helper = workspace / "askpass"
                helper.write_text('#!/bin/sh\ncase "$1" in\n*Username*) printf "%s\\n" x-access-token ;;\n*Password*) printf "%s\\n" "$CAC_GIT_TOKEN" ;;\n*) exit 1 ;;\nesac\n')
                helper.chmod(0o700)
                environment = dict(os.environ, GIT_ASKPASS=str(helper), GIT_TERMINAL_PROMPT="0",
                    GIT_CONFIG_COUNT="3", GIT_CONFIG_KEY_0="credential.helper", GIT_CONFIG_VALUE_0="",
                    GIT_CONFIG_KEY_1="http.followRedirects", GIT_CONFIG_VALUE_1="false",
                    GIT_CONFIG_KEY_2="http.sslVerify", GIT_CONFIG_VALUE_2="true", LC_ALL="C")
                synchronized = False
                for attempt in range(8):
                    checkout = workspace / str(attempt)
                    checkout.mkdir(mode=0o700)
                    def git(*arguments, optional=False):
                        response = subprocess.run(["git", "-C", str(checkout), *arguments], env=environment,
                            text=True, capture_output=True, timeout=60)
                        if response.returncode and not optional:
                            raise keys.StoreError("Protected guest release Git operation failed; no force push was attempted.")
                        return response
                    git("init", "--quiet")
                    git("remote", "add", "origin", repository)
                    git("fetch", "--quiet", "--depth=1", "origin", "main")
                    git("checkout", "--quiet", "--detach", "FETCH_HEAD")
                    documents, seals = {}, {}
                    for kind, relative in names.items():
                        path = checkout / relative
                        if kind == "hactar" and not path.exists():
                            documents[kind] = None
                            continue
                        keys.require(path.is_file() and not path.is_symlink(), "Use the existing fixed encrypted policy captures.")
                        raw, label, secret = self._loader._vault.decrypt_and_get_vault_id(path.read_bytes())
                        documents[kind] = vault_yaml.load_repository_yaml(raw)
                        seals[kind] = (label, secret)
                    if supplemental:
                        context = keys.supplemental_interface_context(documents['autodeploy'], documents['shared'],
                            documents['allocation'], args['guest'], args['hypervisor'],
                            args.get('transition') if phase == 'publish' else None)
                        capture = keys.supplemental_interface_capture
                        source_operations = keys.source_supplemental_interface_operations
                    elif installation or aap_release:
                        allocation_path = checkout / "state/aap_vm_allocations_vault.yml"
                        keys.require(allocation_path.is_file() and not allocation_path.is_symlink(),
                                     "Read existing consumed AAP ownership before installation access.")
                        allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(allocation_path.read_bytes()))
                        if aap_release:
                            context = keys.aap_release_context(documents["autodeploy"], documents["shared"], allocation,
                                args["guest"], args["hypervisor"], args.get("transition") if phase == "publish" else None)
                            capture = keys.retire_inventory_capture
                            source_operations = keys.source_aap_release_operations
                        else:
                            context = keys.installation_access_context(documents["autodeploy"], documents["shared"], allocation,
                                args["route"], args["primary"], args.get("transition") if phase == "publish" else None)
                            capture = keys.installation_inventory_capture
                            source_operations = keys.source_installation_operations
                    elif retirement:
                        context = keys.generic_retirement_context(documents["autodeploy"], documents["shared"], source,
                            args["guest_name"], args["hypervisor"], args.get("transition") if phase == "publish" else None,
                            args.get("guest_kind"))
                        capture = keys.generic_retirement_capture
                        source_operations = keys.source_generic_retirement_operations
                    else:
                        context = keys.guest_release_context(documents["autodeploy"], documents["shared"],
                            args["guest"], args["hypervisor"], args.get("transition") if phase == "publish" else None,
                            {"guest_bootstrap_https": "bootstrap_https", "guest_bootstrap_http": "bootstrap_http"}.get(args["operation"], "release"))
                        capture = keys.guest_release_inventory_capture
                        source_operations = keys.source_guest_release_operations
                    desired = {kind: capture(value, context, kind) if value is not None else None
                               for kind, value in documents.items()}
                    operations = source_operations(source, desired["shared"], desired["autodeploy"],
                        desired["hactar"], context)
                    transition = {key: context[key] for key in ("previous_policy", "desired_policy")}
                    if supplemental:
                        transition.update({key: context[key] for key in ('previous_resource', 'desired_resource')})
                    if retirement:
                        transition["guest"] = context["guest"]
                    if phase == "plan":
                        result.update(changed=False, published=False, transition=transition,
                                      durable_policy_published=False)
                        if supplemental:
                            present = context['primary'].get('supplemental_interfaces') == [args['guest']['supplemental_interface']]
                            result.update(canonical_resource_present=present, canonical_resource_absent=not present,
                                          durable_ownership_published=context['primary'] == context['desired_resource'])
                        if retirement:
                            result.update(guest=context["guest"], records_absent=context["records_absent"])
                        return result
                    # Recheck the running source job before any durable or API mutation.
                    keys.verify_source_job(source, None, variables)
                    if aap_release or supplemental:
                        git("fetch", "--quiet", "--depth=1", "origin", "main")
                        latest_allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml").stdout.encode()))
                        selected_records = [row for row in latest_allocation["aap_vm_allocation"]["reservations"].values()
                                            if row.get("vm_name") == context["route"]["vm_name"]]
                        keys.require(selected_records == [context["reservation"]],
                                     "Consumed AAP ownership changed before final release publication.")
                    changed = []
                    for kind, value in desired.items():
                        if value is None or value == documents[kind]:
                            continue
                        label, secret = seals[kind]
                        sealed = self._loader._vault.encrypt(yaml.dump(value, Dumper=vault_yaml.VaultDumper,
                            sort_keys=False, width=110), secret=secret, vault_id=label)
                        restored = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(sealed))
                        keys.require(restored == value and vault_yaml.literal_paths(restored) == vault_yaml.literal_paths(value),
                            "Guest release must preserve literals, keys and unrelated configuration.")
                        (checkout / names[kind]).write_bytes(sealed)
                        changed.append(names[kind])
                    if changed:
                        git("add", "--", *changed)
                        git("-c", "user.name=AAP AutoDeploy", "-c", "user.email=automation@example.invalid",
                            "commit", "--quiet", "-m", ("Publish verified generic guest retirement" if retirement else
                            "Publish verified guest rebuild isolation release"))
                        if git("push", "origin", "HEAD:refs/heads/main", optional=True).returncode:
                            continue
                        durable = True
                    else:
                        durable = True
                    if installation or aap_release or supplemental:
                        git("fetch", "--quiet", "--depth=1", "origin", "main")
                        latest_allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml").stdout.encode()))
                        observed_records = [row for row in latest_allocation["aap_vm_allocation"]["reservations"].values()
                                            if row.get("vm_name") == context["route"]["vm_name"]]
                        expected_reservation = (next(row for row in desired['allocation']['aap_vm_allocation']['reservations'].values()
                            if row.get('vm_name') == context['route']['vm_name']) if supplemental else context['reservation'])
                        keys.require(observed_records == [expected_reservation],
                                     "Selected AAP reservation changed before installation source synchronization.")
                    # Exact preflight already validated every API destination. A failed API write leaves
                    # the published policy intact; an idempotent retry completes the source aliases.
                    for method, path, body in operations:
                        if method == "ASSOCIATE":
                            rows = source.rows("hosts/?inventory=%s&name=%s" % (body["inventory"], keys.quote(body["name"])))
                            keys.require(len(rows) == 1, "Associate only the just-verified source guest identity.")
                            source.request("POST", path, {"id": rows[0]["id"]})
                        else:
                            source.request(method, path, body)
                    remaining = source_operations(source, desired["shared"], desired["autodeploy"],
                        desired["hactar"], context)
                    keys.require(not remaining, "Verify source guest placement and policy aliases after publication.")
                    git("fetch", "--quiet", "--depth=1", "origin", "main")
                    observed = {}
                    for kind, relative in names.items():
                        raw = git("show", "FETCH_HEAD:" + relative, optional=kind == "hactar")
                        observed[kind] = (vault_yaml.load_repository_yaml(self._loader._vault.decrypt(raw.stdout.encode()))
                                          if raw.returncode == 0 else None)
                    if observed != desired:
                        # Restart from fresh state; exact transition checks reject unrelated changes.
                        continue
                    if installation or aap_release or supplemental:
                        latest_allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml").stdout.encode()))
                        observed_records = [row for row in latest_allocation["aap_vm_allocation"]["reservations"].values()
                                            if row.get("vm_name") == context["route"]["vm_name"]]
                        keys.require(observed_records == [expected_reservation],
                                     "Selected AAP ownership changed during installation access publication.")
                    synchronized = True
                    result.update(changed=bool(changed or operations), published=True,
                                  transition=transition, durable_policy_published=True)
                    if supplemental:
                        result.update(durable_ownership_published=True,
                                      canonical_resource_present=bool(context['desired_resource'].get('supplemental_interfaces')),
                                      canonical_resource_absent=not context['desired_resource'].get('supplemental_interfaces'))
                    return result
                keys.require(synchronized, "Concurrent policy updates prevented exact guest release synchronization; retry safely.")
        except keys.StoreError as error:
            result.update(failed=True, msg=str(error), durable_policy_published=durable)
            if supplemental:
                result['durable_ownership_published'] = durable
            return result
        except Exception:
            result.update(failed=True, msg="Protected guest release publication failed; inspect protected source state before retry.",
                          durable_policy_published=durable)
            if supplemental:
                result['durable_ownership_published'] = durable
            return result
