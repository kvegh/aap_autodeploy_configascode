"""Publish one saved token to encrypted CaC and the source AAP token store."""

from importlib.util import module_from_spec, spec_from_file_location
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

import yaml
from ansible.errors import AnsibleActionFail, AnsibleFilterError
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
        if self._task.args.get('operation') == 'reconcile_inventory_metadata':
            try:
                return self.reconcile_inventory_metadata(result, task_vars or {})
            except (keys.StoreError, AnsibleActionFail, AnsibleFilterError) as error:
                raise AnsibleActionFail(str(error)) from None
            except Exception:
                raise AnsibleActionFail('Selected Source inventory metadata could not be verified; deployment selection remains blocked.') from None
        try:
            if self._task.args.get("operation") in ("release_guest", "guest_bootstrap_https", "guest_bootstrap_http", "installation_access", "retire_guest", "aap_supplemental_interface", "retire_aiops_workload"):
                return self.release_guest(result, task_vars or {})
            if self._task.check_mode and self._task.args.get('operation') != 'post_reset_inspect':
                result.update(changed=False, published=False)
                return result
            args = self._task.args
            keys.require(set(args) >= {"instance_name", "record", "organization"} and
                         set(args) <= {"instance_name", "record", "organization", "operation", "inventory_registration",
                                      "isolation_retirement", "post_reset_verification_job"},
                         "Publish only the selected instance's verified saved token.")
            inspecting_reset = args.get('operation') == 'post_reset_inspect'
            retiring = args.get("operation", "publish") in ("retire", "post_reset_inspect")
            keys.require(args.get("operation", "publish") in ("publish", "retire", "post_reset_inspect"),
                         "Choose instance access publication or retirement.")
            post_reset = 'post_reset_verification_job' in args
            keys.require(not post_reset or (retiring and 'isolation_retirement' not in args),
                         'Post-reset retirement derives its exact transition from protected ownership and native proof.')
            keys.require(not inspecting_reset or post_reset, 'Inspect post-reset retirement with the actual verification job.')
            reset_guard = load('post_reset_retirement_guard', ROOT / 'filter_plugins/aap_post_reset_retirement.py') if post_reset else None
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
                    if post_reset:
                        def protected_file(name):
                            selected_path = checkout / name
                            keys.require(selected_path.is_file() and not selected_path.is_symlink(),
                                         'Retain current encrypted ownership until reset retirement is complete.')
                            return vault_yaml.load_repository_yaml(self._loader._vault.decrypt(selected_path.read_bytes()))
                        reset_configuration = protected_file(relative)
                        settings = reset_guard.protected_settings(reset_configuration, args['instance_name'])
                        reset_proof = reset_guard.verified_job(source, args['post_reset_verification_job'], settings,
                            retirement_job=dict(id=int(job_id), template_id=int(template_id), project_revision=revision),
                            source_inventory_id=preflight_ownership.get('inventory_id') if isinstance(preflight_ownership, dict) else None)
                        reset_shared = protected_file('cac/host_inventory.yml')
                        reset_hactar = protected_file('cac/hactar_recovery.yml')
                        retirement_context, source_ownership_snapshot, reset_resources = reset_guard.combined_context(
                            reset_configuration, reset_shared, reset_hactar, protected_file('state/aap_vm_allocations_vault.yml'),
                            source, args['instance_name'], variables.get('aap_isolation_app_capture', {}).get('ansible_facts'),
                            settings['expectation'])
                        keys.require(isinstance(preflight_ownership, dict)
                            and preflight_ownership.get('source_job_id') == str(job_id)
                            and preflight_ownership.get('source_project_revision') == revision
                            and all(preflight_ownership.get(key) == source_ownership_snapshot[key] for key in (
                                'instance_name', 'inventory_name', 'inventory_id', 'hypervisor_name',
                                'hypervisor_machine_id', 'related_resources')),
                            'Reset metadata retirement requires this running job\'s fresh source ownership read.')
                        if inspecting_reset:
                            # Validate every mixed old/new Source destination
                            # before the playbook removes any selected DNS record.
                            reset_guard.source_operations(source,
                                keys.retire_inventory_capture(reset_shared, retirement_context, 'shared'),
                                keys.retire_inventory_capture(reset_configuration, retirement_context, 'autodeploy'),
                                keys.retire_inventory_capture(reset_hactar, retirement_context, 'hactar'),
                                retirement_context, settings, reset_proof)
                            result.update(changed=False, reset_verified=True, retirement=reset_resources,
                                          expectation_sha256=reset_guard.digest(settings['expectation']))
                            return result
                    if isolation_retirement is not None and not post_reset:
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
                    if retirement_context is not None and not post_reset:
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
                                    if not post_reset:
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
                            retirement_hactar = (deepcopy(old) if post_reset else
                                keys.retire_inventory_capture(old, retirement_context, "hactar"))
                            changes.append((extra, extra_path, old, retirement_hactar, extra_label, extra_secret))
                        # Validate every current API target before any encrypted publication or source write.
                        desired_source_captures = (
                            keys.retire_inventory_capture(retirement_shared, retirement_context, 'shared') if post_reset else retirement_shared,
                            keys.retire_inventory_capture(after, retirement_context, 'autodeploy') if post_reset else after,
                            keys.retire_inventory_capture(retirement_hactar, retirement_context, 'hactar') if post_reset else retirement_hactar)
                        if post_reset:
                            reset_guard.source_operations(source, *desired_source_captures, retirement_context, settings, reset_proof)
                        else:
                            keys.source_retirement_operations(source, *desired_source_captures, retirement_context)
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
                            keys.require(len(latest_records) == 1 and latest_records[0].get("decommissioned") is True,
                                "Selected retirement ownership changed during source synchronization.")
                            if post_reset:
                                keys.require(latest_records[0] == retirement_record,
                                             'The proved retired reservation changed during source synchronization.')
                                keys.require(reset_guard.protected_settings(latest, args['instance_name']) == settings,
                                             'The protected reset verifier binding changed during source synchronization.')
                                reset_proof = reset_guard.verified_job(source, args['post_reset_verification_job'], settings,
                                    retirement_job=dict(id=int(job_id), template_id=int(template_id), project_revision=revision),
                                    source_inventory_id=source_ownership_snapshot['inventory_id'])
                            else:
                                keys.require(keys.isolation_retirement_context(latest_records[0], args["instance_name"],
                                    args["record"].get("target"), isolation_retirement,
                                    source_ownership_snapshot["related_resources"]) == retirement_context,
                                    "Selected retirement ownership changed during source synchronization.")
                            keys.require(post_reset or keys.retire_inventory_capture(latest, retirement_context, "autodeploy") == latest,
                                         "Canonical rebuild inventory changed after retirement publication.")
                            retirement_shared = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                                git("show", "FETCH_HEAD:cac/host_inventory.yml").stdout.encode()))
                            keys.require(post_reset or keys.retire_inventory_capture(retirement_shared, retirement_context, "shared") == retirement_shared,
                                         "Canonical shared inventory changed after retirement publication.")
                            retirement_hactar = None
                            hactar_file = git("show", "FETCH_HEAD:cac/hactar_recovery.yml", optional=True)
                            if hactar_file.returncode == 0:
                                retirement_hactar = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(hactar_file.stdout.encode()))
                                keys.require(post_reset or keys.retire_inventory_capture(retirement_hactar, retirement_context, "hactar") == retirement_hactar,
                                             "Canonical Hactar capture changed after retirement publication.")
                            # A replacement already erased native resources. Keep all
                            # nine canonical owners until API deletion/readback succeeds;
                            # use only the validated desired views for Source changes.
                            source_retirement_shared = (keys.retire_inventory_capture(retirement_shared, retirement_context, 'shared')
                                if post_reset else retirement_shared)
                            source_retirement_main = (keys.retire_inventory_capture(latest, retirement_context, 'autodeploy')
                                if post_reset else latest)
                            source_retirement_hactar = (keys.retire_inventory_capture(retirement_hactar, retirement_context, 'hactar')
                                if post_reset else retirement_hactar)
                            def planned_retirement_operations():
                                if post_reset:
                                    return reset_guard.source_operations(source, source_retirement_shared,
                                        source_retirement_main, source_retirement_hactar, retirement_context, settings, reset_proof)
                                return keys.source_retirement_operations(source, source_retirement_shared,
                                    source_retirement_main, source_retirement_hactar, retirement_context)
                            source_operations = planned_retirement_operations()
                            for method, api_path, body in source_operations:
                                if method != "PATCH":
                                    continue
                                source.request(method, api_path, body)
                                api_changed = True
                            remaining_operations = planned_retirement_operations()
                            keys.require(all(method == "DELETE" for method, _, _ in remaining_operations),
                                         "Verify every source policy alias before deleting guest ownership records.")
                            for method, api_path, body in remaining_operations:
                                source.request(method, api_path, body)
                                api_changed = True
                            keys.require(not planned_retirement_operations(),
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
                            host_installation = matches[0][1].get('host_installation_id')
                            if host_installation is None:
                                del desired_allocation["aap_vm_allocation"]["reservations"][matches[0][0]]
                            else:
                                keys.require(isinstance(host_installation, str)
                                    and re.fullmatch(r'[a-f0-9]{64}', host_installation)
                                    and matches[0][0] == str(uuid.uuid5(uuid.NAMESPACE_URL, 'aap-host-install:' + host_installation))
                                    and matches[0][1].get('decommissioned') is True,
                                    'Retain the complete consumed host generation as retired allocation history.')
                            sealed = self._loader._vault.encrypt(
                                yaml.dump(desired_allocation, Dumper=vault_yaml.VaultDumper, sort_keys=False, width=110),
                                secret=allocation_secret, vault_id=allocation_label)
                            restored = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(sealed))
                            keys.require(restored == desired_allocation
                                and vault_yaml.literal_paths(restored) == vault_yaml.literal_paths(desired_allocation),
                                "Final reservation removal must preserve other allocations and literal data.")
                            git("checkout", "--quiet", "--detach", "FETCH_HEAD")
                            (checkout / allocation_relative).write_bytes(sealed)
                            final_files = [allocation_relative]
                            final_captures = {}
                            if post_reset:
                                # Complete the same recoverable transaction only after
                                # all exact native Source operations were read back.
                                for final_relative, kind, current in (
                                    (relative, 'autodeploy', latest),
                                    ('cac/host_inventory.yml', 'shared', retirement_shared),
                                    ('cac/hactar_recovery.yml', 'hactar', retirement_hactar)):
                                    old_ciphertext = git('show', 'FETCH_HEAD:' + final_relative).stdout.encode()
                                    old_plain, final_label, final_secret = self._loader._vault.decrypt_and_get_vault_id(old_ciphertext)
                                    current_capture = vault_yaml.load_repository_yaml(old_plain)
                                    keys.require(current_capture == current,
                                                 'Canonical ownership changed before final reset retirement publication.')
                                    desired_capture = keys.retire_inventory_capture(current_capture, retirement_context, kind)
                                    final_ciphertext = self._loader._vault.encrypt(yaml.dump(desired_capture,
                                        Dumper=vault_yaml.VaultDumper, sort_keys=False, width=110),
                                        secret=final_secret, vault_id=final_label)
                                    final_restored = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(final_ciphertext))
                                    keys.require(final_restored == desired_capture
                                        and vault_yaml.literal_paths(final_restored) == vault_yaml.literal_paths(desired_capture),
                                        'Final reset retirement must preserve unrelated records and literal data.')
                                    (checkout / final_relative).write_bytes(final_ciphertext)
                                    final_files.append(final_relative)
                                    final_captures[final_relative] = desired_capture
                            git("add", "--", *final_files)
                            git("-c", "user.name=AAP AutoDeploy", "-c", "user.email=automation@example.invalid",
                                "commit", "--quiet", "-m", "Retain retired host generation history" if host_installation is not None
                                else "Remove completed instance reservation")
                            if git("push", "origin", "HEAD:refs/heads/main", optional=True).returncode:
                                continue
                            published = True
                            git("fetch", "--quiet", "--depth=1", "origin", "main")
                            keys.require(git("rev-parse", "HEAD").stdout == git("rev-parse", "FETCH_HEAD").stdout,
                                "Concurrent changes followed final reservation removal; review current CaC.")
                            verified_allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                                git("show", "FETCH_HEAD:" + allocation_relative).stdout.encode()))
                            keys.require(verified_allocation == desired_allocation,
                                "Verify selected retirement history and unchanged counter after publication.")
                            for final_relative, desired_capture in final_captures.items():
                                verified_capture = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(
                                    git('show', 'FETCH_HEAD:' + final_relative).stdout.encode()))
                                keys.require(verified_capture == desired_capture,
                                             'Verify completed reset retirement and unrelated record preservation.')
                        result.update(changed=published or api_changed, published=True,
                            source_credential_id=synchronized["credential_id"])
                        return result
                raise keys.StoreError("Concurrent instance updates prevented source synchronization; retry using the saved target token.")
        except keys.StoreError as error:
            raise AnsibleActionFail(str(error)) from None
        except Exception:
            raise AnsibleActionFail("Protected instance-token publication failed; the target token remains saved for review.") from None


    def reconcile_inventory_metadata(self, result, variables):
        """Repair only missing selected Source metadata, without a Git writer or native work."""
        args = self._task.args
        keys.require(set(args) == {'operation', 'inventory_host'},
                     'Reconcile only the explicitly selected Source inventory host.')
        selected = args['inventory_host']
        hosts = variables.get('hostvars', {})
        keys.require(isinstance(selected, str) and selected in hosts,
                     'Select an existing AAP host from this job inventory.')
        # Copy only identity fields; resolving all magic hostvars may read unrelated data.
        caller = {key: deepcopy(hosts[selected][key]) for key in (
            'vm_resource', 'hypervisor_host', 'aap_instance_number', 'ansible_host',
            'vm_uuid', 'vm_ip', 'host_keys', 'ansible_fqdn', 'machine_id') if key in hosts[selected]}
        physical = keys.inventory_identity().inventory_instance_name(selected, caller)
        reader = load('reconcile_instance_registry_reader',
                      self._project_root() / 'action_plugins/aap_read_instance.py')
        registered = reader.ActionModule.read_instance(self._loader, self._project_root(),
            {'instance_key': physical, 'read_inventory_metadata': True}, variables)
        source = SourceClient()
        job = keys.verify_source_job(source, registered['instance_route']['aap_hostname'], variables)
        keys.require(job.get('id') == int(variables['awx_job_id']),
                     'Metadata repair must identify the actual running Source job.')
        result.update(keys.ensure_source_inventory(source, registered['inventory_configuration'],
            selected, registered['instance_route'], missing_supplemental_only=True,
            resources=registered['instance_resources'], job_inventory_id=job.get('inventory'),
            caller_host=caller, check_mode=self._task.check_mode))
        result['metadata_verified'] = True
        return result

    def release_guest(self, result, variables):
        """Plan and publish one verified guest change using existing Git/API access."""
        durable = False
        supplemental = False
        try:
            args = self._task.args
            installation = args.get("operation") == "installation_access"
            retirement = args.get("operation") == "retire_guest"
            workload = args.get("operation") == "retire_aiops_workload"
            supplemental = args.get('operation') == 'aap_supplemental_interface'
            aap_release = (args.get("operation") == "release_guest" and isinstance(args.get("guest"), dict)
                           and args["guest"].get("kind") == "aap")
            required = ({"operation", "instance_name", "hypervisor"} if workload else
                        {"operation", "route", "primary"} if installation else
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
                        seals[kind] = (label, secret, path.read_bytes().splitlines()[0])
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
                    elif workload:
                        workload_helpers = load('publish_aiops_workload', ROOT / 'src/aap_aiops_teardown.py')
                        allocation_path = checkout / 'state/aap_vm_allocations_vault.yml'
                        keys.require(allocation_path.is_file() and not allocation_path.is_symlink(),
                                     'Keep the active AAP allocation during workload-only retirement.')
                        allocation = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(allocation_path.read_bytes()))
                        context = workload_helpers.publication_context(documents['autodeploy'], documents['shared'],
                            allocation, source, args['instance_name'], args['hypervisor'],
                            variables.get('aap_isolation_app_capture', {}).get('ansible_facts'),
                            args.get('transition') if phase == 'publish' else None)
                        capture = keys.retire_inventory_capture
                        source_operations = keys.source_retirement_operations
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
                    if workload:
                        transition = workload_helpers.publication_transition(context)
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
                        if workload:
                            result.update(workload_resources=context['related_resources'], route=context['route'])
                        return result
                    if workload:
                        keys.require(variables.get('aap_aiops_teardown_native_absence_verified') is True
                            and variables.get('aap_aiops_teardown_apply') is True
                            and variables.get('aap_aiops_teardown_confirmation') == args['instance_name'],
                            'Publish AIOps retirement only after this confirmed job verified native absence.')
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
                        label, secret, original_header = seals[kind]
                        if workload:
                            original_fields = original_header.decode().split(';')
                            label = original_fields[3] if len(original_fields) == 4 else None
                        sealed = self._loader._vault.encrypt(yaml.dump(value, Dumper=vault_yaml.VaultDumper,
                            sort_keys=False, width=110), secret=secret, vault_id=label)
                        restored = vault_yaml.load_repository_yaml(self._loader._vault.decrypt(sealed))
                        keys.require(restored == value and vault_yaml.literal_paths(restored) == vault_yaml.literal_paths(value)
                            and (not workload or sealed.splitlines()[0] == original_header),
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
                    if installation or aap_release or supplemental or workload:
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
                    if installation or aap_release or supplemental or workload:
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
