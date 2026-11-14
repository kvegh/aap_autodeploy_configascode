"""Qualify the shared VM recipe through the existing native CoP base merge."""

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

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("shared_vm_cac_yaml", ROOT / "src/cac_yaml.py")
cac_yaml = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cac_yaml)
CANARY = "fixture-private-generic-vm-credential-canary"


class SharedVmBaseTests(unittest.TestCase):
    def test_native_merge_keeps_shared_launch_inputs_separate_from_existing_resources(self):
        roots = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
        if not any(
            (Path(path) / "ansible_collections/infra/aap_configuration/roles/dispatch/tasks/include_wildcard_vars.yml").is_file()
            for path in roots if path
        ):
            self.skipTest("requires already installed infra.aap_configuration")
        example = cac_yaml.load_repository_yaml((ROOT / "cac/base_CaC_vault.yml.example").read_text())
        base = yaml.safe_load((ROOT / "04-aap-config.yml").read_text())[0]
        protected = next(task["block"] for task in base["pre_tasks"]
                         if task.get("name") == "Retrieve and load the encrypted shared configuration")
        merge = deepcopy(next(task for task in protected
                              if task.get("name") == "Combine shared configuration without logging credential inputs"))
        self.assertTrue(merge["ansible.builtin.include_role"]["apply"]["no_log"])
        existing_project = {"name": "Existing unrelated project", "scm_branch": "preserved"}
        existing_template = {"name": "Existing unrelated template", "credentials": ["Existing credential"]}
        values = {
            "aap_default_execution_environment": "Fixture common Core 2.20",
            "controller_projects": [existing_project],
            "controller_templates": [existing_template],
            "controller_projects_base": example["controller_projects_base"],
            "controller_templates_base": example["controller_templates_base"],
            "controller_credentials_base": [{"name": "Fixture existing access", "inputs": {"token": CANARY}}],
            "controller_credential_types_base": example["controller_credential_types_base"],
        }
        with tempfile.TemporaryDirectory(prefix="shared-vm-base-test-") as directory:
            private = Path(directory)
            result_file = private / "result.json"
            tasks = [merge, {
                "name": "Retain only the private fixture merge result",
                "ansible.builtin.copy": {
                    "dest": str(result_file), "mode": "0600",
                    "content": cac_yaml.trust_as_template("{{ {'projects': controller_projects, 'templates': controller_templates, 'credentials': controller_credentials, 'types': controller_credential_types} | to_json }}"),
                }, "no_log": True, "diff": False,
            }]
            play = private / "play.yml"
            play.write_text(yaml.dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": values, "tasks": tasks,
            }], Dumper=cac_yaml.VaultDumper, sort_keys=False))
            play.chmod(0o600)
            config = private / "ansible.cfg"
            config.write_text("[defaults]\nretry_files_enabled=False\n")
            environment = dict(
                os.environ, ANSIBLE_CONFIG=str(config),
                ANSIBLE_LOCAL_TEMP=str(private / "local"),
                ANSIBLE_REMOTE_TEMP=str(private / "remote"),
                ANSIBLE_NOCOLOR="1", ANSIBLE_DISPLAY_ARGS_TO_STDOUT="True",
            )
            result = subprocess.run([
                sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play),
            ], cwd=ROOT, env=environment, capture_output=True, text=True, timeout=40)
            output = result.stdout + result.stderr
            self.assertNotIn(CANARY, output)
            self.assertEqual(result.returncode, 0, output)
            merged = json.loads(result_file.read_text())
        self.assertEqual(merged["projects"][0], existing_project)
        self.assertEqual(merged["templates"][0], existing_template)
        self.assertEqual(merged["credentials"], values["controller_credentials_base"])
        kind = merged["types"][0]
        self.assertEqual(kind["name"], "Generic Linux VM encrypted configuration")
        self.assertEqual(kind["inputs"]["required"], ["configuration_vault"])
        self.assertEqual(len(kind["inputs"]["fields"]), 1)
        self.assertTrue(kind["inputs"]["fields"][0]["secret"])
        self.assertEqual(kind["injectors"], {
            "file": {"template": "{{ configuration_vault }}"},
            "extra_vars": {"generic_linux_vm_config_file": "{{ tower.filename }}"},
        })
        project, template = merged["projects"][1], merged["templates"][1]
        self.assertEqual(project["name"], "AAP Shared VM Deployment")
        self.assertEqual(project["scm_url"], "https://github.com/kvegh/AAP-advanced-features.git")
        self.assertEqual(project["scm_branch"], "main")
        self.assertTrue(project["wait"])
        self.assertFalse(project["scm_track_submodules"])
        self.assertEqual(template["project"], project["name"])
        self.assertEqual(template["playbook"], "playbooks/deploy_generic_linux_vm.yml")
        self.assertEqual(template["execution_environment"], values["aap_default_execution_environment"])
        for field in ("ask_inventory_on_launch", "ask_credential_on_launch", "ask_variables_on_launch"):
            self.assertTrue(template[field])
        self.assertFalse(template["ask_tags_on_launch"])
        self.assertFalse(template["ask_skip_tags_on_launch"])
        self.assertEqual(template["job_tags"], "")
        self.assertEqual(template["skip_tags"], "")
        self.assertEqual(template["credentials"], [])
        self.assertEqual(template["extra_vars"], {})
        self.assertNotIn("inventory", template)


if __name__ == "__main__":
    unittest.main()
