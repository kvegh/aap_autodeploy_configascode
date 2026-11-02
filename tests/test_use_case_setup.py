"""Verify bounded use-case setup and label checks without contacting AAP."""
import copy
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml
from ansible.errors import AnsibleFilterError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("use_case_setup", ROOT / "filter_plugins/use_case_setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

class UseCaseSetupTests(unittest.TestCase):
    def setUp(self):
        self.catalog = yaml.safe_load((ROOT / "vars/use-case-catalog.yml").read_text())["aap_use_case_catalog"]
        self.protected = {"organization": "Fixture organization",
            "umbrella_modules": {key: "https://git.example.invalid/team/" + key + ".git" for key in self.catalog},
            "configuration_repositories": {key: "https://git.example.invalid/config/" + key + ".git"
                for key in ("base", "aiops", "windows_disconnected", "orchestrator")}}

    def plan(self, selected):
        return setup.setup_plan(selected, self.catalog, self.protected,
                                "https://seed.example.invalid", "https://fresh.example.invalid")

    def test_only_explicit_supported_importers_are_selected(self):
        result = self.plan(["AIOps_selfhealing_demo", "disconnected-windows-patching"])
        self.assertEqual([x["key"] for x in result["importers"]],
                         ["AIOps_selfhealing_demo", "disconnected-windows-patching"])
        self.assertEqual(result["preparation"]["playbook"], "05-prepare-use-cases.yml")
        self.assertNotIn("credentials", result["importers"][0])

    def test_empty_duplicate_unknown_and_unsupported_choices_fail(self):
        for selected in ([], "AIOps_selfhealing_demo", ["unknown"],
                         ["AIOps_selfhealing_demo"] * 2, ["ServiceNow-ITSM-Integration"]):
            with self.subTest(selected=selected), self.assertRaises(AnsibleFilterError):
                self.plan(selected)

    def test_catalog_drift_fails_before_an_importer_can_launch(self):
        self.protected["umbrella_modules"].pop("Automation_Dashboard")
        with self.assertRaises(AnsibleFilterError):
            self.plan(["AIOps_selfhealing_demo"])

    def test_repository_credentials_and_redirect_parameters_are_refused(self):
        for value in ("http://git.example.invalid/config", "https://user:fixture@git.example.invalid/config",
                      "https://git.example.invalid/config?redirect=elsewhere", "https://[invalid/config"):
            with self.subTest(value=value):
                self.protected["configuration_repositories"]["aiops"] = value
                with self.assertRaises(AnsibleFilterError):
                    self.plan(["AIOps_selfhealing_demo"])

    def test_seed_url_aliases_and_shared_controller_instances_are_refused(self):
        for seed, target in (("https://same.example.invalid", "https://SAME.example.invalid:443/"),
                             ("https://seed.example.invalid/path", "https://fresh.example.invalid")):
            with self.subTest(seed=seed), self.assertRaises(AnsibleFilterError):
                setup.setup_plan(["AIOps_selfhealing_demo"], self.catalog, self.protected, seed, target)
        for seed, target in (([], []), ([{"uuid": "same"}], [{"uuid": "same"}]),
                             ([{}], [{"uuid": "different"}])):
            with self.subTest(seed=seed), self.assertRaises(AnsibleFilterError):
                setup.distinct_controllers(seed, target)
        self.assertTrue(setup.distinct_controllers([{"uuid": "seed"}], [{"uuid": "fresh"}]))

    def test_prerequisites_retain_multiple_versions_and_exclude_unselected_cases(self):
        def record(*versions):
            return {"reviewed": True, "repositories": [{"name": "community", "collections": [
                {"name": "example.tools", "version": version} for version in versions]}]}
        definitions = {"one": record("1.0.0"), "two": record("1.0.0", "2.0.0"),
                       "unselected": record("9.0.0")}
        result = setup.selected_prerequisites(definitions, ["one", "two"])
        self.assertEqual([x["version"] for x in result["repositories"][0]["collections"]], ["1.0.0", "2.0.0"])
        definitions["one"]["reviewed"] = False
        with self.assertRaises(AnsibleFilterError):
            setup.selected_prerequisites(definitions, ["one"])

    def test_real_label_preflight_accepts_complete_capture_and_refuses_omissions(self):
        complete = {"cac_required_template_label": "fixture-use-case",
            "cac_label_definitions": [{"name": "fixture-use-case", "organization": "Fixture organization"}],
            "cac_label_templates": [{"name": "Fixture job", "organization": "Fixture organization",
                                      "labels": ["fixture-use-case"]}]}
        cases = [("complete", complete, True)]
        for label, change in (("missing assignment", {"labels": []}),
                              ("undefined label", {"labels": ["fixture-use-case", "unknown"]}),
                              ("wrong organization", {"organization": "Other organization"})):
            value = copy.deepcopy(complete)
            value["cac_label_templates"][0].update(change)
            cases.append((label, value, False))
        for label, variables, expected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory(prefix="aap-label-preflight-") as temporary:
                fixture = Path(temporary) / "fixture.yml"
                fixture.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                    "vars": variables, "tasks": [{"ansible.builtin.include_tasks": str(ROOT / "tasks/cac-template-labels.yml")}]}]))
                env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(Path(temporary) / "local"),
                           ANSIBLE_REMOTE_TEMP=str(Path(temporary) / "remote"))
                result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                                        env=env, text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode == 0, expected, result.stdout + result.stderr)

    def test_imported_aiops_activations_cannot_start_from_saved_enabled_state(self):
        source = yaml.safe_load((ROOT / "deploy-aiops-demo.yml").read_text())[0]
        block = next(t["block"] for t in source["pre_tasks"] if "block" in t)
        task = next(t for t in block if t.get("name") == "Keep imported AIOps rulebooks disabled for separate explicit activation")
        with tempfile.TemporaryDirectory(prefix="aap-inert-activations-") as temporary:
            directory = Path(temporary)
            fixture = directory / "fixture.yml"
            fixture.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": {"eda_rulebook_activations_aiops_demo": [{"name": "Fixture activation", "enabled": True, "state": "enabled"}]},
                "tasks": [task, {"ansible.builtin.assert": {"that": [
                    "not eda_rulebook_activations[0].enabled", "eda_rulebook_activations[0].state == 'present'"]}}]}]))
            env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(directory / "local"), ANSIBLE_REMOTE_TEMP=str(directory / "remote"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                                    env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
