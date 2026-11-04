"""Publish one saved token to encrypted CaC and the source AAP token store."""

from importlib.util import module_from_spec, spec_from_file_location
from copy import deepcopy
import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, HTTPSHandler

import yaml
from ansible.errors import AnsibleActionFail
from ansible.parsing.yaml.loader import AnsibleLoader
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


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SourceClient:
    def __init__(self):
        self.origin = keys.origin(os.environ.get("AAP_CAC_SOURCE_URL", ""))
        self.token = os.environ.get("AAP_CAC_SOURCE_TOKEN", "")
        keys.require(bool(self.token), "Attach the existing source AAP API access credential.")
        context = ssl.create_default_context()
        authority = os.environ.get("AAP_CAC_SOURCE_CA_FILE")
        if authority:
            context.load_verify_locations(cafile=authority)
        self.opener = build_opener(NoRedirect(), HTTPSHandler(context=context))

    def request(self, method, path, body=None):
        relative = path if path.startswith("/") else "/api/controller/v2/" + path
        url = urljoin(self.origin + "/", relative)
        keys.require(urlsplit(url).netloc == urlsplit(self.origin).netloc,
                     "Source API pagination must remain on the authenticated source.")
        request = Request(url, data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"}, method=method)
        try:
            with self.opener.open(request, timeout=45) as response:
                raw = response.read()
            return json.loads(raw) if raw else {}
        except Exception:
            raise keys.StoreError("Source token-store API synchronization failed; the saved target token is preserved.") from None

    def rows(self, path):
        result = []
        while path:
            page = self.request("GET", path)
            result.extend(page["results"])
            path = page.get("next")
        return result


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        try:
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
                    declared.get("guest_host_clients", [])) == declared,
                    "Publish the current declared recovery isolation policy without changing its scope.")
            token = os.environ.get("CAC_GIT_TOKEN", "")
            keys.require(bool(token), "Attach VM allocation git Pseudo CMDB writer for token publication.")
            repository = contract.autodeploy_repository(self._loader, ROOT)
            source = SourceClient()
            keys.require(source.origin != keys.origin(args["record"].get("target")),
                         "Source API access must identify the AAP running this fresh deployment.")
            variables = task_vars or {}
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
                    if isolation_retirement is not None:
                        allocation_path = checkout / "state/aap_vm_allocations_vault.yml"
                        keys.require(allocation_path.is_file() and not allocation_path.is_symlink(),
                                     "Read the selected encrypted reservation before planning source retirement.")
                        allocation = AnsibleLoader(self._loader._vault.decrypt(allocation_path.read_bytes())).get_single_data()
                        selected_records = [row for row in allocation["aap_vm_allocation"]["reservations"].values()
                                            if row.get("vm_name") == args["instance_name"]]
                        keys.require(len(selected_records) == 1, "Resolve exactly one consumed selected reservation.")
                        retirement_context = keys.isolation_retirement_context(selected_records[0], args["instance_name"],
                            args["record"].get("target"), isolation_retirement)
                    path = checkout / relative
                    keys.require(path.is_file() and not path.is_symlink(), "Require the existing encrypted AutoDeploy CaC file.")
                    plain, label, secret = self._loader._vault.decrypt_and_get_vault_id(path.read_bytes(), filename=str(path))
                    before = AnsibleLoader(plain).get_single_data()
                    after = (keys.retire_record(before, args["instance_name"], args["record"].get("target"))
                             if retiring else keys.merge_record(before, args["instance_name"], args["record"]))
                    if retirement_context is not None:
                        after = keys.retire_inventory_capture(after, retirement_context, "autodeploy")
                    changes = [(relative, path, before, after, label, secret)]
                    retirement_shared = retirement_hactar = None
                    if registration:
                        extra = "cac/host_inventory.yml"
                        extra_path = checkout / extra
                        keys.require(extra_path.is_file() and not extra_path.is_symlink(),
                                     "Require the maintained encrypted shared inventory capture.")
                        raw, extra_label, extra_secret = self._loader._vault.decrypt_and_get_vault_id(
                            extra_path.read_bytes(), filename=str(extra_path))
                        old = AnsibleLoader(raw).get_single_data()
                        updated = keys.merge_inventory(old, args["instance_name"], registered_route, declared)
                        changes.append((extra, extra_path, old, updated, extra_label, extra_secret))
                    if retiring:
                        for extra in ("state/aap_vm_allocations_vault.yml", "cac/host_inventory.yml"):
                            extra_path = checkout / extra
                            keys.require(extra_path.is_file() and not extra_path.is_symlink(),
                                         "Require maintained encrypted allocation and inventory definitions for retirement.")
                            raw, extra_label, extra_secret = self._loader._vault.decrypt_and_get_vault_id(
                                extra_path.read_bytes(), filename=str(extra_path))
                            old = AnsibleLoader(raw).get_single_data()
                            updated = deepcopy(old)
                            if extra.startswith("state/"):
                                matches = [row for row in updated["aap_vm_allocation"]["reservations"].values()
                                           if row.get("vm_name") == args["instance_name"]]
                                keys.require(len(matches) == 1 and
                                    keys.origin(matches[0]["instance_route"]["aap_hostname"]) ==
                                    keys.origin(args["record"].get("target")),
                                    "Retirement must match exactly one consumed allocation and public URL.")
                                matches[0]["decommissioned"] = True
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
                                         "Use only the maintained encrypted Hactar recovery capture.")
                            raw, extra_label, extra_secret = self._loader._vault.decrypt_and_get_vault_id(
                                extra_path.read_bytes(), filename=str(extra_path))
                            old = AnsibleLoader(raw).get_single_data()
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
                        restored = AnsibleLoader(self._loader._vault.decrypt(sealed)).get_single_data()
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
                    latest = AnsibleLoader(self._loader._vault.decrypt(
                        git("show", "FETCH_HEAD:" + relative).stdout.encode())).get_single_data()
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
                        inventory = AnsibleLoader(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:cac/host_inventory.yml").stdout.encode())).get_single_data()
                        api_changed = keys.ensure_source_inventory(source, inventory,
                            args["instance_name"], registered_route) or api_changed
                    if retiring:
                        if retirement_context is not None:
                            latest_allocation = AnsibleLoader(self._loader._vault.decrypt(
                                git("show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml").stdout.encode())).get_single_data()
                            latest_records = [row for row in latest_allocation["aap_vm_allocation"]["reservations"].values()
                                              if row.get("vm_name") == args["instance_name"]]
                            keys.require(len(latest_records) == 1 and latest_records[0].get("decommissioned") is True
                                and keys.isolation_retirement_context(latest_records[0], args["instance_name"],
                                    args["record"].get("target"), isolation_retirement) == retirement_context,
                                "Selected retirement ownership changed during source synchronization.")
                            keys.require(keys.retire_inventory_capture(latest, retirement_context, "autodeploy") == latest,
                                         "Canonical recovery inventory changed after retirement publication.")
                            retirement_shared = AnsibleLoader(self._loader._vault.decrypt(
                                git("show", "FETCH_HEAD:cac/host_inventory.yml").stdout.encode())).get_single_data()
                            keys.require(keys.retire_inventory_capture(retirement_shared, retirement_context, "shared") == retirement_shared,
                                         "Canonical shared inventory changed after retirement publication.")
                            retirement_hactar = None
                            hactar_file = git("show", "FETCH_HEAD:cac/hactar_recovery.yml", optional=True)
                            if hactar_file.returncode == 0:
                                retirement_hactar = AnsibleLoader(self._loader._vault.decrypt(hactar_file.stdout.encode())).get_single_data()
                                keys.require(keys.retire_inventory_capture(retirement_hactar, retirement_context, "hactar") == retirement_hactar,
                                             "Canonical Hactar capture changed after retirement publication.")
                            for method, api_path, body in keys.source_retirement_operations(source, retirement_shared,
                                    latest, retirement_hactar, retirement_context):
                                source.request(method, api_path, body)
                                api_changed = True
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
                    observed = AnsibleLoader(self._loader._vault.decrypt(
                        git("show", "FETCH_HEAD:" + relative).stdout.encode())).get_single_data()
                    inventory_stable = True
                    if retirement_context is not None:
                        observed_inventory = AnsibleLoader(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:cac/host_inventory.yml").stdout.encode())).get_single_data()
                        observed_hactar = git("show", "FETCH_HEAD:cac/hactar_recovery.yml", optional=True)
                        observed_hactar = (AnsibleLoader(self._loader._vault.decrypt(observed_hactar.stdout.encode())).get_single_data()
                                           if observed_hactar.returncode == 0 else None)
                        observed_allocation = AnsibleLoader(self._loader._vault.decrypt(
                            git("show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml").stdout.encode())).get_single_data()
                        observed_records = [row for row in observed_allocation["aap_vm_allocation"]["reservations"].values()
                                            if row.get("vm_name") == args["instance_name"]]
                        inventory_stable = (observed == latest and observed_inventory == retirement_shared
                                            and observed_hactar == retirement_hactar and observed_records == latest_records)
                    if observed.get("aap_instance_api_credentials") == records and inventory_stable:
                        result.update(changed=published or api_changed, published=True,
                            source_credential_id=synchronized["credential_id"])
                        return result
                raise keys.StoreError("Concurrent instance updates prevented source synchronization; retry using the saved target token.")
        except keys.StoreError as error:
            raise AnsibleActionFail(str(error)) from None
        except Exception:
            raise AnsibleActionFail("Protected instance-token publication failed; the target token remains saved for review.") from None
