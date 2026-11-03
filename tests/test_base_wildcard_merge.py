"""Use the installed CoP merge task without APIs or unprotected credential logs."""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.utils.unsafe_proxy import AnsibleUnsafeText
from ansible.utils.unsafe_proxy import wrap_var

ROOT = Path(__file__).resolve().parents[1]
CANARY = "fixture-private-wildcard-credential-canary"
SPEC = importlib.util.spec_from_file_location("cac_yaml", ROOT / "src/cac_yaml.py")
vault_yaml = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vault_yaml)


class BaseWildcardMergeTests(unittest.TestCase):
    def test_yaml_roundtrip_preserves_literal_tags_without_freezing_ordinary_inputs(
        self,
    ):
        values = {
            "literal": wrap_var("{{ api_token }}"),
            "input": "{{ fixture_upstream_token }}",
        }
        rendered = yaml.dump(values, Dumper=vault_yaml.VaultDumper)
        loaded = AnsibleLoader(rendered).get_single_data()
        self.assertEqual(loaded, values)
        self.assertIsInstance(loaded["literal"], AnsibleUnsafeText)
        self.assertNotIsInstance(loaded["input"], AnsibleUnsafeText)
        self.assertEqual(vault_yaml.literal_paths(loaded), {("literal",)})

    def test_exact_vendor_merge_preserves_literal_injectors_and_resolves_ordinary_inputs(
        self,
    ):
        roots = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
        if not any(
            (
                Path(path)
                / "ansible_collections/infra/aap_configuration/roles/dispatch/tasks/include_wildcard_vars.yml"
            ).is_file()
            for path in roots
            if path
        ):
            self.skipTest("requires already installed infra.aap_configuration")
        source = yaml.safe_load((ROOT / "04-aap-config.yml").read_text())[0]
        protected = next(
            task
            for task in source["pre_tasks"]
            if task["name"] == "Retrieve and load the encrypted shared configuration"
        )["block"]
        merge = next(
            task
            for task in protected
            if task["name"]
            == "Combine shared configuration without logging credential inputs"
        )
        self.assertTrue(merge["ansible.builtin.include_role"]["apply"]["no_log"])
        for native in ("False", "True"):
            for literal in (False, True):
                with self.subTest(
                    native=native, literal=literal
                ), tempfile.TemporaryDirectory(
                    prefix="base-wildcard-test-"
                ) as directory:
                    private = Path(directory)
                    output = private / "merged.json"
                    injectors = {
                        "CAC_GIT_TOKEN": "{{ token }}",
                    }
                    if literal:
                        injectors = {
                            key: wrap_var(value) for key, value in injectors.items()
                        }
                    variables = {
                        "fixture_current_admin": "Fixture operator",
                        "fixture_upstream_token": CANARY,
                        "aap_user_accounts_base": [
                            {"username": "{{ fixture_current_admin }}"}
                        ],
                        "hub_collection_remotes_base": [
                            {
                                "name": "Fixture remote",
                                "token": "{{ fixture_upstream_token }}",
                            }
                        ],
                        "controller_credential_types_base": [
                            {
                                "name": "Cac_git_token_type",
                                "kind": "cloud",
                                "injectors": {"env": injectors},
                            }
                        ],
                        "controller_credentials_base": [
                            {"name": "Fixture writer", "inputs": {"token": CANARY}}
                        ],
                    }
                    tasks = [
                        deepcopy(merge),
                        {
                            "name": "Retain private merge assertions",
                            "ansible.builtin.copy": {
                                "dest": str(output),
                                "mode": "0600",
                                "content": "{{ {'types': controller_credential_types, 'credentials': controller_credentials, 'users': aap_user_accounts, 'remotes': hub_collection_remotes} | to_json }}",
                            },
                            "no_log": True,
                            "diff": False,
                        },
                    ]
                    play = [
                        {
                            "hosts": "localhost",
                            "connection": "local",
                            "gather_facts": False,
                            "vars": variables,
                            "tasks": tasks,
                        }
                    ]
                    fixture = private / "play.yml"
                    fixture.write_text(
                        yaml.dump(play, Dumper=vault_yaml.VaultDumper, sort_keys=False)
                    )
                    fixture.chmod(0o600)
                    config = private / "ansible.cfg"
                    config.write_text("[defaults]\nretry_files_enabled=False\n")
                    environment = dict(
                        os.environ,
                        ANSIBLE_CONFIG=str(config),
                        ANSIBLE_JINJA2_NATIVE=native,
                        ANSIBLE_LOCAL_TEMP=str(private / "local"),
                        ANSIBLE_REMOTE_TEMP=str(private / "remote"),
                        ANSIBLE_NOCOLOR="1",
                        ANSIBLE_DISPLAY_ARGS_TO_STDOUT="True",
                    )
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "ansible.cli.playbook",
                            "-i",
                            "localhost,",
                            str(fixture),
                        ],
                        cwd=ROOT,
                        env=environment,
                        capture_output=True,
                        text=True,
                        timeout=40,
                    )
                    self.assertNotIn(CANARY, result.stdout + result.stderr)
                    if not literal:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertFalse(output.exists())
                        continue
                    self.assertEqual(
                        result.returncode, 0, result.stdout + result.stderr
                    )
                    merged = json.loads(output.read_text())
                    self.assertEqual(merged["types"][0]["injectors"]["env"], injectors)
                    self.assertEqual(
                        merged["credentials"][0]["inputs"]["token"], CANARY
                    )
                    self.assertEqual(merged["users"][0]["username"], "Fixture operator")
                    self.assertEqual(merged["remotes"][0]["token"], CANARY)


if __name__ == "__main__":
    unittest.main()
