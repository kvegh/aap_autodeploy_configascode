"""Read one completed instance route from the shared encrypted registry."""

from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path
import subprocess
import tempfile

from ansible.errors import AnsibleActionFail
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase

spec = spec_from_file_location(
    "aap_instance_route",
    Path(__file__).resolve().parents[1] / "filter_plugins/aap_instance_route.py",
)
routing = module_from_spec(spec)
spec.loader.exec_module(routing)

contract_spec = spec_from_file_location(
    "registry_cac_contract",
    Path(__file__).resolve().parents[1] / "filter_plugins/cac_import.py",
)
contract = module_from_spec(contract_spec)
contract_spec.loader.exec_module(contract)


def source_keys():
    """Load the existing API helper only for the optional decommission read."""
    key_spec = spec_from_file_location("read_related_instance_keys",
        Path(__file__).resolve().parents[1] / "src/aap_instance_keys.py")
    keys = module_from_spec(key_spec)
    key_spec.loader.exec_module(keys)
    return keys


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        token = os.environ.get("CAC_GIT_TOKEN", "")
        if not token:
            raise AnsibleActionFail(
                "Attach the AutoDeploy secrets repository CaC read-token credential."
            )
        if set(self._task.args) - {"instance_key", "expected_route", "allow_retired", "read_related_resources"}:
            raise AnsibleActionFail("The registry repository is fixed by encrypted AutoDeploy configuration.")
        if type(self._task.args.get("read_related_resources", False)) is not bool:
            raise AnsibleActionFail("Select source-related ownership explicitly with a boolean option.")
        try:
            repository = contract.autodeploy_repository(
                self._loader, Path(__file__).resolve().parents[1]
            )
        except Exception:
            raise AnsibleActionFail("Load the encrypted AutoDeploy repository configuration with its environment Vault credential.") from None
        with tempfile.TemporaryDirectory(prefix="aap-instance-registry-") as temporary:
            workspace = Path(temporary)
            helper = workspace / "git-askpass"
            helper.write_text(
                '#!/bin/sh\ncase "$1" in\n*Username*) printf "%s\\n" x-access-token ;;\n'
                '*Password*) printf "%s\\n" "$CAC_GIT_TOKEN" ;;\n*) exit 1 ;;\nesac\n'
            )
            helper.chmod(0o700)
            environment = dict(
                os.environ,
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

            def git(*arguments):
                process = subprocess.run(
                    ["git", "-C", str(workspace), *arguments],
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=60,
                )
                if process.returncode:
                    raise AnsibleActionFail(
                        "Instance registry read failed; no target connection was attempted."
                    )
                return process.stdout

            git("init", "--quiet")
            git("remote", "add", "origin", repository)
            git("fetch", "--quiet", "--depth=1", "origin", "main")
            ciphertext = git(
                "show", "FETCH_HEAD:state/aap_vm_allocations_vault.yml"
            ).encode()
            configuration = AnsibleLoader(
                self._loader._vault.decrypt(ciphertext)
            ).get_single_data()
            route = routing.registered_instance(
                configuration.get("aap_vm_allocation"),
                self._task.args.get("instance_key"),
                self._task.args.get("allow_retired", False),
            )
            expected = self._task.args.get("expected_route")
            if expected is not None and expected != route:
                raise AnsibleActionFail(
                    "The supplied workflow handoff differs from the registered instance."
                )
            ownership = next(record.get("instance_resources", {}) for record in
                configuration["aap_vm_allocation"]["reservations"].values()
                if record.get("vm_name") == route["vm_name"])
            proof = None
            if self._task.args.get("read_related_resources", False):
                # Normal registry reads never load this source API helper or require its credential.
                try:
                    keys = source_keys()
                    source = keys.SourceClient()
                    keys.verify_source_job(source, route["aap_hostname"], task_vars or {})
                    shared = AnsibleLoader(self._loader._vault.decrypt(
                        git("show", "FETCH_HEAD:cac/host_inventory.yml").encode())).get_single_data()
                    proof = keys.source_related_resources(source, shared, configuration["aap_vm_allocation"], route["vm_name"])
                    proof.update(source_job_id=str((task_vars or {}).get("awx_job_id")),
                                 source_project_revision=(task_vars or {}).get("awx_project_revision"))
                    ownership = dict(ownership, **proof["related_resources"])
                except Exception:
                    raise AnsibleActionFail("Source related-VM ownership could not be verified; no target connection was attempted.") from None
            result.update(changed=False, instance_route=route, registry_repository=repository,
                          instance_resources=ownership)
            if proof is not None:
                result["related_resource_proof"] = proof
            return result
