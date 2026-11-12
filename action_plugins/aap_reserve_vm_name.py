"""Git compare-and-swap reservation using the active CaC Vault secret."""

from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid

import yaml
from ansible.errors import AnsibleActionFail
from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase

spec = spec_from_file_location(
    "aap_name_allocation",
    Path(__file__).resolve().parents[1] / "src/aap_name_allocation.py",
)
allocator = module_from_spec(spec)
spec.loader.exec_module(allocator)

contract_spec = spec_from_file_location(
    "allocation_cac_contract",
    Path(__file__).resolve().parents[1] / "filter_plugins/cac_import.py",
)
contract = module_from_spec(contract_spec)
contract_spec.loader.exec_module(contract)


class ActionModule(ActionBase):
    TRANSFERS_FILES = False

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        args = self._task.args
        if "repository" in args:
            raise AnsibleActionFail(
                "The allocation repository is fixed by encrypted AutoDeploy configuration."
            )
        if "instance_resources" in args and (args.get("instance_route") is None
                or not isinstance(args["instance_resources"], dict) or set(args["instance_resources"]) != {"aap"}):
            raise AnsibleActionFail("Primary ownership is published only with its existing consumed instance route.")
        token = os.environ.get("CAC_GIT_TOKEN", "")
        if not token:
            raise AnsibleActionFail(
                "Attach the authorized shared-allocation Git writer credential."
            )
        try:
            repository = contract.autodeploy_repository(
                self._loader, Path(__file__).resolve().parents[1]
            )
        except Exception:
            raise AnsibleActionFail(
                "Load the encrypted AutoDeploy repository configuration with its environment Vault credential."
            ) from None
        request_id = args.get("request_id") or str(uuid.uuid4())
        floor = args.get("observed_floor", 1)
        if isinstance(floor, str) and floor.isdecimal():
            floor = int(floor)
        relative = "state/aap_vm_allocations_vault.yml"
        with tempfile.TemporaryDirectory(prefix="aap-name-reservation-") as temporary:
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

            def git(directory, *arguments, optional=False):
                process = subprocess.run(
                    ["git", "-C", str(directory), *arguments],
                    env=environment,
                    text=True,
                    capture_output=True,
                    timeout=60,
                )
                if process.returncode and not optional:
                    raise AnsibleActionFail(
                        "Allocation Git access failed; inspect the repository/writer binding. No VM was provisioned."
                    )
                return process

            for attempt in range(8):
                checkout = workspace / ("attempt-%s" % attempt)
                checkout.mkdir(mode=0o700)
                git(checkout, "init", "--quiet")
                git(checkout, "remote", "add", "origin", repository)
                git(checkout, "fetch", "--quiet", "--depth=1", "origin", "main")
                git(checkout, "checkout", "--quiet", "--detach", "FETCH_HEAD")
                path = checkout / relative
                ciphertext = path.read_bytes()
                plaintext, vault_id, secret = (
                    self._loader._vault.decrypt_and_get_vault_id(
                        ciphertext
                    )
                )
                configuration = AnsibleLoader(plaintext).get_single_data()
                state = configuration.get("aap_vm_allocation")
                updated, record = allocator.reserve(
                    state, args["prefix"], request_id, args["hypervisor_id"], floor
                )
                if args.get("instance_route") is not None:
                    if request_id not in state["reservations"]:
                        raise AnsibleActionFail(
                            "A verified route requires an existing consumed reservation."
                        )
                    updated, record = allocator.publish_route(
                        state, request_id, args["instance_route"], args.get("instance_resources")
                    )
                if self._task.check_mode:
                    git(checkout, "push", "--dry-run", "origin", "HEAD:refs/heads/main")
                    result.update(
                        changed=False, reserved=False, candidate=record["vm_name"]
                    )
                    return result
                if updated == state:
                    result.update(
                        changed=False, reserved=True, request_id=request_id, **record
                    )
                    return result
                configuration["aap_vm_allocation"] = updated
                encoded = yaml.dump(
                    configuration, Dumper=AnsibleDumper, sort_keys=False, width=110
                ).encode()
                sealed = self._loader._vault.encrypt(
                    encoded, secret=secret, vault_id=vault_id
                )
                if (
                    AnsibleLoader(self._loader._vault.decrypt(sealed)).get_single_data()
                    != configuration
                ):
                    raise AnsibleActionFail(
                        "Allocation Vault roundtrip failed before publication."
                    )
                path.write_bytes(sealed.rstrip(b"\n") + b"\n")
                git(checkout, "add", "--", relative)
                git(
                    checkout,
                    "-c",
                    "user.name=AAP AutoDeploy",
                    "-c",
                    "user.email=automation@example.invalid",
                    "commit",
                    "--quiet",
                    "-m",
                    "Reserve an AAP test VM name",
                )
                pushed = git(
                    checkout, "push", "origin", "HEAD:refs/heads/main", optional=True
                )
                if pushed.returncode == 0:
                    # Verify the accepted reservation from a fresh remote read, including lost-response retries.
                    git(checkout, "fetch", "--quiet", "--depth=1", "origin", "main")
                    published = git(
                        checkout, "show", "FETCH_HEAD:" + relative
                    ).stdout.encode()
                    verified = AnsibleLoader(
                        self._loader._vault.decrypt(published)
                    ).get_single_data()
                    if (
                        verified["aap_vm_allocation"]["reservations"].get(request_id)
                        != record
                    ):
                        raise AnsibleActionFail(
                            "The published reservation could not be verified; never reuse its number."
                        )
                    result.update(
                        changed=True, reserved=True, request_id=request_id, **record
                    )
                    return result
                if re.search(
                    r"403|authentication failed|permission denied|write access",
                    pushed.stderr,
                    re.I,
                ):
                    raise AnsibleActionFail(
                        "The allocation credential lacks repository write access. No VM was provisioned."
                    )
                # A competing writer may have advanced main; reread and reserve against its accepted state.
                time.sleep(min(0.1 * (attempt + 1), 1))
        raise AnsibleActionFail(
            "Allocation contention or network failure prevented reservation. No VM was provisioned."
        )
