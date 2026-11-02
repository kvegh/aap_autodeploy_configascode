"""Exercise encrypted review, initialization and update against real local Git."""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import yaml
from ansible.errors import AnsibleActionFail
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase
from ansible.utils.unsafe_proxy import wrap_var

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "capture_action", ROOT / "action_plugins/aap_cac_capture.py"
)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class CaptureActionTests(unittest.TestCase):
    def test_desired_yaml_and_json_variable_formatting_has_identical_meaning(self):
        first = {
            "name": "Fixture",
            "extra_vars": 'value: 1\nchoice: "{{ bound_value }}"\n',
        }
        second = {
            "name": "Fixture",
            "extra_vars": {"value": 1, "choice": "{{ bound_value }}"},
        }
        self.assertEqual(
            capture.normalized_resource(first), capture.normalized_resource(second)
        )
        first["extra_vars"] = wrap_var(first["extra_vars"])
        self.assertEqual(
            capture.normalized_resource(first), capture.normalized_resource(second)
        )

    def test_real_vault_git_preview_initialization_update_and_removal(self):
        secret = VaultSecret(b"fixture-vault-secret")
        vault = VaultLib([("cac", secret)])
        real_run = subprocess.run
        with tempfile.TemporaryDirectory(prefix="aap-capture-action-") as temporary:
            directory = Path(temporary)
            remote, seed = directory / "remote.git", directory / "seed"
            seed.mkdir()

            def git(path, *args):
                return real_run(
                    ["git", "-C", str(path), *args],
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout

            real_run(
                ["git", "init", "--bare", "--initial-branch=main", str(remote)],
                check=True,
                capture_output=True,
            )
            git(seed, "init", "--initial-branch=main")
            (seed / "cac").mkdir()
            owner = "Fixture organization"
            job = {
                "name": "Fixture job",
                "organization": owner,
                "playbook": "capture-aap-cac.yml",
                "timeout": 60,
                "labels": ["fixture-label"],
            }
            credential = {
                "name": "Fixture credential",
                "organization": owner,
                "inputs": {"password": "fixture-secret-canary"},
            }
            configuration = {
                "owned": {
                    "job_templates": [job],
                    "labels": [{"name": "fixture-label", "organization": owner}],
                    "credentials": [credential],
                },
                "unrelated": "preserve-exactly",
            }
            scope = {
                "source_controller": "https://source.example.invalid",
                "organization": owner,
                "code_repository": "https://git.example.invalid/code.git",
                "owned_labels": ["fixture-label"],
                "sections": {
                    kind: ["owned", kind]
                    for kind in ["job_templates", "labels", "credentials"]
                },
            }
            for file, data in [
                ("config.yml", configuration),
                (
                    "capture_scopes_vault.yml",
                    {"schema_version": 1, "scopes": {"fixture": scope}},
                ),
            ]:
                (seed / "cac" / file).write_bytes(
                    vault.encrypt(yaml.safe_dump(data).encode(), vault_id="cac")
                )
            scope["configuration_file"] = "cac/config.yml"
            (seed / "cac/capture_scopes_vault.yml").write_bytes(
                vault.encrypt(
                    yaml.safe_dump(
                        {"schema_version": 1, "scopes": {"fixture": scope}}
                    ).encode(),
                    vault_id="cac",
                )
            )
            git(seed, "add", ".")
            git(
                seed,
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-m",
                "Initialize fixture",
            )
            git(seed, "remote", "add", "origin", str(remote))
            git(seed, "push", "origin", "main")
            live = {
                kind: capture.core.indexed(values, owner)
                for kind, values in configuration["owned"].items()
            }
            next(iter(live["credentials"].values()))["inputs"][
                "password"
            ] = capture.core.MASK

            class FakeSnapshot:
                def __init__(self, *args):
                    self.objects = {
                        "job_templates": list(live["job_templates"].values())
                    }
                    self.raw_by_kind = {
                        "projects": [{"scm_url": scope["code_repository"]}]
                    }

                def collect(self):
                    self.objects["job_templates"] = list(live["job_templates"].values())
                    return deepcopy(live)

            missing_code_metadata = [False]

            def redirected(command, *args, **kwargs):
                if (
                    missing_code_metadata[0]
                    and str(ROOT) in command
                    and "rev-parse" in command
                ):
                    return subprocess.CompletedProcess(
                        command, 128, "", "Fixture checkout has no Git metadata."
                    )
                command = [
                    (
                        str(remote)
                        if value == "https://git.example.invalid/capture.git"
                        else value
                    )
                    for value in command
                ]
                return real_run(command, *args, **kwargs)

            def run(
                mode="preview",
                digest="",
                commit=False,
                push=False,
                project_revision=None,
            ):
                plugin = capture.ActionModule.__new__(capture.ActionModule)
                plugin._task = SimpleNamespace(
                    args={
                        "scope": "fixture",
                        "mode": mode,
                        "review_digest": digest,
                        "commit": commit,
                        "push": push,
                    },
                    check_mode=False,
                )
                # An unrelated default secret cannot replace the correct named capture Vault.
                plugin._loader = SimpleNamespace(
                    _vault=VaultLib(
                        [
                            ("default", VaultSecret(b"wrong-fixture-secret")),
                            ("cac", secret),
                        ]
                    )
                )
                return plugin.run(
                    task_vars=(
                        {"awx_project_revision": project_revision}
                        if project_revision
                        else {}
                    )
                )

            with mock.patch.object(
                ActionBase, "run", side_effect=lambda *args, **kwargs: {}
            ), mock.patch.object(
                capture.subprocess, "run", side_effect=redirected
            ), mock.patch.object(
                capture.extraction, "Snapshot", FakeSnapshot
            ), mock.patch.dict(
                os.environ,
                {
                    "AAP_CAC_CAPTURE_REPOSITORY": "https://git.example.invalid/capture.git",
                    "AAP_CAC_CAPTURE_GIT_TOKEN": "fixture-git-token-canary",
                    "AAP_CAC_SOURCE_URL": scope["source_controller"],
                    "AAP_CAC_SOURCE_TOKEN": "fixture-api-token-canary",
                },
            ):
                preview = run()
                missing_code_metadata[0] = True
                fallback = run(project_revision="a" * 40)
                fallback_report = AnsibleLoader(
                    vault.decrypt(fallback["encrypted_review"])
                ).get_single_data()
                self.assertEqual(fallback_report["source_code_revision"], "a" * 40)
                with self.assertRaises(AnsibleActionFail):
                    run()
                missing_code_metadata[0] = False
                self.assertFalse(preview["changed"])
                self.assertTrue(preview["initialization_required"])
                self.assertEqual(
                    git(remote, "rev-list", "--count", "main").strip(), "1"
                )
                review = AnsibleLoader(
                    vault.decrypt(preview["encrypted_review"])
                ).get_single_data()
                self.assertTrue(
                    review["visibility_evidence"]["controller_superuser_verified"]
                )
                for canary in [
                    "fixture-secret-canary",
                    "fixture-git-token-canary",
                    "fixture-api-token-canary",
                ]:
                    self.assertNotIn(canary, json.dumps(preview))
                with self.assertRaises(AnsibleActionFail):
                    run("initialize", "stale-digest", True, True)
                accepted = run("initialize", preview["review_digest"], True, True)
                self.assertTrue(accepted["pushed"])
                self.assertEqual(
                    git(remote, "rev-list", "--count", "main").strip(), "2"
                )
                first = next(iter(live["job_templates"].values()))
                first["timeout"] = 300
                new = dict(job, name="New discovered job")
                live["job_templates"][capture.core.identity(new, owner)] = new
                changed = run()
                self.assertGreater(changed["desired_change_count"], 0)
                with self.assertRaises(AnsibleActionFail):
                    run("update", preview["review_digest"], True, True)
                updated = run("update", changed["review_digest"], True, True)
                self.assertTrue(updated["pushed"])
                stored = AnsibleLoader(
                    vault.decrypt(git(remote, "show", "main:cac/config.yml").encode())
                ).get_single_data()
                self.assertEqual(len(stored["owned"]["job_templates"]), 2)
                self.assertEqual(
                    stored["owned"]["credentials"][0]["inputs"]["password"],
                    "fixture-secret-canary",
                )
                self.assertEqual(stored["unrelated"], "preserve-exactly")
                unchanged = run()
                self.assertFalse(
                    run("update", unchanged["review_digest"], True, True)["changed"]
                )
                live["job_templates"].pop(capture.core.identity(job, owner))
                removed = run()
                self.assertGreater(removed["source_change_counts"].get("removal", 0), 0)
                run("update", removed["review_digest"], True, True)
                stored = AnsibleLoader(
                    vault.decrypt(git(remote, "show", "main:cac/config.yml").encode())
                ).get_single_data()
                self.assertEqual(
                    [entry["name"] for entry in stored["owned"]["job_templates"]],
                    ["New discovered job"],
                )


if __name__ == "__main__":
    unittest.main()
