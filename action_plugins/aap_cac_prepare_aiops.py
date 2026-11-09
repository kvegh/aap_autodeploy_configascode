"""Prepare encrypted AIOps data in the importer's existing private checkout."""

from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path
import subprocess
import tempfile

import yaml
from ansible.errors import AnsibleActionFail
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase


ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = spec_from_file_location(name, ROOT / relative)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


settings = load("prepare_aiops_settings", "src/aap_aiops_settings.py")
vault_yaml = load("prepare_aiops_vault_yaml", "src/cac_yaml.py")
capture_schema = load("prepare_aiops_capture_schema", "filter_plugins/cac_import.py")
CAPTURE = "vaults/cac/aiops-selfhealing-demo-cac-vault.yml"
RUNTIME = "vaults/runtime/aiops-selfhealing-demo-runtime-vault.yml"


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        try:
            variables = task_vars or {}
            self._templar.available_variables = variables
            require = settings.require
            require({"operation", "authentication"} <= set(self._task.args)
                    <= {"operation", "authentication", "mcp_connection", "subscription", "source_git_token"}
                    and self._task.args["operation"] in ("pre", "post"),
                    "Choose pre-import preparation or post-import native resource readback.")
            require(not self._task.check_mode, "Encrypted AIOps preparation needs a normal import, not check mode.")
            operation = self._task.args["operation"]
            require((operation == "pre" and {"subscription", "source_git_token"} <= set(self._task.args)
                     and self._task.no_log is True)
                    or (operation == "post" and not ({"subscription", "source_git_token"} & set(self._task.args))),
                    "Pass protected subscription and source-reader inputs only during no-log pre-import preparation.")
            contract = self._templar.template(variables["cac_project_contract"])
            require(contract["project_id"] == "aiops-selfhealing-demo"
                    and contract["configuration_file"] == CAPTURE,
                    "Prepare data only for the fixed existing AIOps project capture.")
            workspace = Path(self._templar.template(variables["cac_workspace"]["path"]))
            require(workspace.name.startswith("aap-project-cac-") and workspace.is_dir()
                    and not workspace.is_symlink() and workspace.stat().st_uid == os.geteuid()
                    and workspace.stat().st_mode & 0o077 == 0,
                    "Use the importer's private job-local checkout workspace.")
            checkout = workspace / "repository"
            require(checkout.is_dir() and not checkout.is_symlink(), "Use the existing private project checkout.")
            helper = workspace / "git-askpass"
            require(helper.is_file() and not helper.is_symlink() and helper.stat().st_uid == os.geteuid()
                    and helper.stat().st_mode & 0o077 == 0 and os.environ.get("CAC_GIT_TOKEN"),
                    "Reuse the existing protected AIOps repository credential and askpass helper.")
            environment = dict(os.environ, GIT_ASKPASS=str(helper), GIT_TERMINAL_PROMPT="0", LC_ALL="C",
                GIT_CONFIG_COUNT="3", GIT_CONFIG_KEY_0="credential.helper", GIT_CONFIG_VALUE_0="",
                GIT_CONFIG_KEY_1="http.followRedirects", GIT_CONFIG_VALUE_1="false",
                GIT_CONFIG_KEY_2="http.sslVerify", GIT_CONFIG_VALUE_2="true")

            def git(*arguments, optional=False):
                response = subprocess.run(["git", "-C", str(checkout), *arguments], env=environment,
                    text=True, capture_output=True, timeout=90)
                if response.returncode and not optional:
                    raise settings.lifecycle.LifecycleError("Protected AIOps Git publication failed; no force push was attempted.")
                return response

            require(git("config", "--get", "remote.origin.url").stdout.strip() == contract["repository"]
                    and not git("status", "--porcelain").stdout,
                    "The existing AIOps checkout must have its fixed origin and no unrelated working edits.")
            auth = self._task.args["authentication"]
            client = settings.lifecycle.Client(auth["hostname"], auth["token"], auth["username"], auth["password"])
            selected_alias = self._templar.template(variables["aap_instance_key"])
            hostvars = variables["hostvars"]

            def record(name, fields):
                require(name in hostvars, "The selected native inventory host is missing.")
                source = hostvars[name]
                return {field: self._templar.template(source[field]) for field in fields if field in source}

            selected = record(selected_alias, ("aap_instance_number", "ansible_fqdn", "ansible_host", "vm_uuid",
                                               "hypervisor_host", "vm_resource"))
            hypervisor = record(selected["hypervisor_host"], ("ansible_host", "public_ipv4", "ansible_user", "ansible_port",
                                                             "machine_id", "host_keys", "isolation_policy"))
            resources = self._templar.template(variables.get("cac_import_resources", {})) if operation == "post" else None

            def document(relative):
                path = checkout / relative
                require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(checkout.resolve()),
                        "Use only the maintained whole-file AIOps Vault files.")
                ciphertext = path.read_bytes()
                require(ciphertext.startswith(b"$ANSIBLE_VAULT;"), "AIOps files must remain whole-file Vault ciphertext.")
                plain, label, secret = self._loader._vault.decrypt_and_get_vault_id(ciphertext, filename=str(path))
                return AnsibleLoader(plain).get_single_data(), label, secret, ciphertext.splitlines()[0]

            changed = False
            for attempt in range(5):
                # Reread both files from one accepted remote commit. A competing
                # writer is merged by recomputing data, never by force/rebase.
                git("fetch", "--quiet", "--depth=1", "origin", "main")
                git("checkout", "--quiet", "--detach", "FETCH_HEAD")
                before, label, secret, header = document(CAPTURE)
                metadata = capture_schema.import_metadata(before.get("cac_import_metadata"), "aiops-selfhealing-demo")
                capture_schema.validate_capture_roots(before)
                require(before.get("aiops_configuration_ready") is True,
                        "AIOps configuration is on hold; complete its capture review before preparing settings.")
                capture_schema.validate_checks(metadata, before)
                require(variables.get("aiops_configuration_ready") is True,
                        "This import's AIOps configuration review is on hold; do not prepare or publish settings.")
                capture_schema.validate_checks(metadata, variables)
                old_runtime, runtime_label, runtime_secret, runtime_header = document(RUNTIME)
                context = settings.selected_context(selected, hypervisor, client.hostname,
                    before["aiops_website_dns_zone"], before["aiops_instances"], selected_alias)
                credential_name = settings.base_machine_credential(client, before["aiops_guest_machine_credential_name"])
                if operation == "pre":
                    sources = {}
                    for role in ("testserver1", "tra", "zabbix"):
                        name = role + "-" + context["version"]
                        if name in hostvars:
                            sources[name] = record(name, ("aap_instance_number", "hypervisor_host", "vm_resource",
                                "ansible_host", "vm_uuid", "machine_id", "host_keys", "ansible_user", "ansible_port"))
                    desired, runtime = settings.prepare_documents(before, old_runtime, context, credential_name, sources,
                        mcp_access=self._task.args.get("mcp_connection"), authentication=auth,
                        subscription=self._task.args["subscription"], source_git_token=self._task.args["source_git_token"])
                else:
                    require(before["aiops_instances"][context["instance_name"]]["guest_machine_credential_name"] == credential_name,
                            "Keep the pre-import base Machine credential binding.")
                    native = settings.target_readbacks(client, context, resources)
                    desired, runtime = settings.complete_documents(before, old_runtime, context, native)
                updates = []

                def seal(value, old, relative, vault_label, vault_secret, original_header):
                    if value == old:
                        return (checkout / relative).read_bytes()
                    plain = yaml.dump(value, Dumper=vault_yaml.VaultDumper, sort_keys=False, width=110).encode()
                    require(AnsibleLoader(plain).get_single_data() == value, "Protected AIOps YAML must roundtrip unchanged.")
                    header_fields = original_header.decode().split(";")
                    original_id = header_fields[3] if len(header_fields) == 4 else None
                    encoded = self._loader._vault.encrypt(plain, secret=vault_secret, vault_id=original_id)
                    restored = AnsibleLoader(self._loader._vault.decrypt(encoded)).get_single_data()
                    require(encoded.splitlines()[0] == original_header and restored == value
                            and vault_yaml.literal_paths(restored) == vault_yaml.literal_paths(value),
                            "AIOps encryption must preserve the original Vault key, identity and literal strings.")
                    updates.append((relative, encoded))
                    return encoded

                runtime_ciphertext = seal(runtime, old_runtime, RUNTIME, runtime_label, runtime_secret, runtime_header)
                desired["aiops_runtime_settings_vault"] = runtime_ciphertext.decode()
                seal(desired, before, CAPTURE, label, secret, header)
                if not updates:
                    result.update(changed=changed, prepared=True)
                    return result
                require(attempt < 4,
                        "Competing updates prevented verified AIOps settings publication; no credential rotation was attempted.")
                for relative, encoded in updates:
                    destination = checkout / relative
                    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".aiops-settings-", delete=False) as output:
                        temporary = Path(output.name)
                        try:
                            output.write(encoded)
                            output.flush()
                            os.fsync(output.fileno())
                            os.replace(temporary, destination)
                        finally:
                            if temporary.exists():
                                temporary.unlink()
                git("add", "--", *(relative for relative, _ in updates))
                git("-c", "user.name=AAP AutoDeploy", "-c", "user.email=automation@example.invalid", "commit", "--quiet",
                    "-m", "Prepare encrypted AIOps instance settings")
                pushed = git("push", "origin", "HEAD:refs/heads/main", optional=True)
                changed = True
                # Even a lost acknowledgement is handled by a fresh remote read
                # on the next pass. No role may use a merely local password.
                if pushed.returncode and any(text in pushed.stderr.lower() for text in
                        ("403", "authentication failed", "permission denied", "write access")):
                    raise settings.lifecycle.LifecycleError("The existing AIOps repository credential lacks authorized write access.")
            raise settings.lifecycle.LifecycleError("Competing updates prevented verified AIOps settings publication; no credential rotation was attempted.")
        except settings.lifecycle.LifecycleError as error:
            raise AnsibleActionFail(str(error)) from None
        except Exception:
            # Native HTTP/YAML/Git diagnostics can contain protected material.
            raise AnsibleActionFail("AIOps settings preparation failed; inspect protected source and target state before retrying.") from None
