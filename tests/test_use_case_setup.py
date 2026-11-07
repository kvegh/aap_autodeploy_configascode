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
spec = importlib.util.spec_from_file_location(
    "use_case_setup", ROOT / "filter_plugins/use_case_setup.py"
)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class UseCaseSetupTests(unittest.TestCase):
    def setUp(self):
        self.catalog = yaml.safe_load((ROOT / "vars/use-case-catalog.yml").read_text())[
            "aap_use_case_catalog"
        ]
        self.protected = {
            "seed_hostname": "https://seed.example.invalid",
            "organization": "Fixture organization",
            "umbrella_modules": {
                key: "https://git.example.invalid/team/" + key + ".git"
                for key in self.catalog
            },
            "configuration_repositories": {
                key: "https://git.example.invalid/config/" + key + ".git"
                for key in ("base", "aiops", "windows_disconnected", "orchestrator", "assistant_team", "rhel_sniperpatching", "command_center_ng")
            },
        }

    def plan(self, selected):
        return setup.setup_plan(
            selected,
            self.catalog,
            self.protected,
            "https://seed.example.invalid",
            "https://fresh.example.invalid",
        )

    def test_only_explicit_supported_importers_are_selected(self):
        result = self.plan(["AIOps_selfhealing_demo", "disconnected-windows-patching"])
        self.assertEqual(
            [x["key"] for x in result["importers"]],
            ["AIOps_selfhealing_demo", "disconnected-windows-patching"],
        )
        self.assertEqual(result["preparation"]["playbook"], "05-prepare-use-cases.yml")
        self.assertNotIn("credentials", result["importers"][0])
        self.assertEqual([x["playbook"] for x in result["importers"]],
                         ["deploy-cac-project.yml"] * 2)
        self.assertEqual([x["project_id"] for x in result["importers"]],
                         ["aiops-selfhealing-demo", "disconnected-windows-patching"])

    def test_project_ids_determine_names_with_acronyms_and_original_word_order(self):
        expected = {
            "aiops-selfhealing-demo": "Deploy AIOps Selfhealing Demo CaC",
            "disconnected-windows-patching": "Deploy Disconnected Windows Patching CaC",
            "automation-orchestrator": "Deploy Automation Orchestrator CaC",
            "assistant-team": "Deploy Assistant Team CaC",
            "aap_autodeploy_configascode": "Deploy AAP Autodeploy Configascode CaC",
            "RHEL-sniperpatching": "Deploy RHEL Sniperpatching CaC",
            "command-center-ng": "Deploy Command Center NG CaC",
        }
        for project_id, name in expected.items():
            with self.subTest(project_id=project_id):
                self.assertEqual(setup.project_display_name(project_id), name)
        selected = [key for key, entry in self.catalog.items() if "project_id" in entry]
        result = self.plan(selected)
        self.assertEqual([entry["name"] for entry in result["importers"]],
                         [expected[self.catalog[key]["project_id"]] for key in selected])
        for project_id in (None, "", "AiOps", "bad--id", "../other", "id with spaces", "Rhel-sniperpatching", "RHEL-sniperpatching-other"):
            with self.subTest(project_id=project_id), self.assertRaises(AnsibleFilterError):
                setup.project_display_name(project_id)

    def test_rhel_selection_uses_the_common_driver_and_its_own_repository(self):
        result = self.plan(["RHEL-sniperpatching"])
        self.assertEqual(result["importers"], [{
            "key": "RHEL-sniperpatching",
            "name": "Deploy RHEL Sniperpatching CaC",
            "playbook": "deploy-cac-project.yml",
            "project_id": "RHEL-sniperpatching",
            "repository": self.protected["configuration_repositories"]["rhel_sniperpatching"],
        }])

    def test_existing_five_selections_need_no_rhel_configuration_repository(self):
        del self.protected["configuration_repositories"]["rhel_sniperpatching"]
        del self.protected["configuration_repositories"]["command_center_ng"]
        selected = [key for key, entry in self.catalog.items()
                    if "project_id" in entry and key not in ("RHEL-sniperpatching", "command-center-ng")]
        result = self.plan(selected)
        self.assertEqual(len(result["importers"]), 5)
        self.assertNotIn("RHEL-sniperpatching", [item["key"] for item in result["importers"]])

    def test_command_center_selection_uses_the_same_importer_and_own_repository(self):
        result = self.plan(["command-center-ng"])
        self.assertEqual(result["importers"], [{
            "key": "command-center-ng",
            "name": "Deploy Command Center NG CaC",
            "playbook": "deploy-cac-project.yml",
            "project_id": "command-center-ng",
            "repository": self.protected["configuration_repositories"]["command_center_ng"],
        }])

    def test_generic_children_get_only_saved_repository_credentials_and_selected_destination(self):
        original = [
            {"id": 10, "name": "Case Git", "kind": "cloud",
             "summary_fields": {"organization": {"name": "Fixture organization"}}},
            {"id": 11, "name": "Case Vault", "kind": "vault", "inputs": {"vault_id": "cac"},
             "summary_fields": {"organization": {"name": "Fixture organization"}}},
        ]
        api = {"id": 12, "name": "AAP API/MCP Auth Token Store", "credential_type": 46,
               "inputs": {"host": "https://fresh.example.invalid"},
               "summary_fields": {"credential_type": {"name": "Pseudo Instance Key Store"},
                                  "organization": {"name": "Fixture organization"}}}
        original.append(api)
        names = [entry["name"] for entry in original]

        def resolve(source, destination):
            return setup.api_launch_credentials(source, names, destination,
                                                "Fixture organization", "https://fresh.example.invalid")

        self.assertEqual(resolve(original, [api]), [10, 11, 12])
        self.assertEqual(setup.instance_store_credentials(original), [api])
        for credentials in ([], [api, copy.deepcopy(api)], original[:-1]):
            with self.subTest(credentials=credentials), self.assertRaises(AnsibleFilterError):
                setup.instance_store_credentials(credentials)
        for source, destination in (
            (original[:-1], [api]),
            (original + [{"id": 90, "kind": "ssh", "name": "Registry Machine"}], [api]),
            (original, [dict(api, id=99)]),
            (original, original + [api]),
        ):
            with self.subTest(source=source, destination=destination), self.assertRaises(AnsibleFilterError):
                resolve(source, destination)

    def test_real_launch_argument_rendering_separates_preparation_routes_from_generic_imports(self):
        tasks = yaml.safe_load((ROOT / "tasks/selected-use-case-import.yml").read_text())
        launch = next(task["ansible.controller.job_launch"] for task in tasks
                      if "ansible.controller.job_launch" in task)
        organization = "Fixture organization"

        def credential(identity, name, kind="cloud", vault_id=None, type_name=None):
            return {"id": identity, "name": name, "kind": kind,
                    "inputs": {} if vault_id is None else {"vault_id": vault_id},
                    "summary_fields": {"organization": {"name": organization},
                                       "credential_type": {"name": type_name or name}}}

        original = [credential(1, "aap_autodeploy_configascode-secrets CaC repo read token", type_name="Cac_git_token_type"), credential(2, "Case Vault", "vault", "cac"),
                    credential(3, "Environment Vault", "vault", "")]
        route = [credential(6, "Registered Machine", "ssh")]
        native = credential(7, "AAP API/MCP Auth Token Store", type_name="Pseudo Instance Key Store")
        native.update(credential_type=46, inputs={})
        original.append(native)
        for native_mode in ("false", "true"):
            for preparation in (False, True):
                with self.subTest(native=native_mode, preparation=preparation), tempfile.TemporaryDirectory(
                    prefix="aap-selector-forwarding-"
                ) as temporary:
                    directory = Path(temporary)
                    variables = {
                        "aap_selected_importer": {"json": {"results": [{"id": 88}]}, "item": {
                            "name": "Fixture importer", "repository": "https://git.example.invalid/config/base.git",
                            "playbook": "05-prepare-use-cases.yml" if preparation else "deploy-cac-project.yml"}},
                        "aap_selected_saved_credentials": original,
                        "cac_use_case_selector": {"importer_credentials": {"Fixture importer": [x["name"] for x in original]}},
                        "aap_selected_route_credentials": {"results": [{"json": {"results": [entry]}} for entry in route]},
                        "aap_selected_api_credentials": [native],
                        "aap_selected_target_auth": {"hostname": "https://fresh.example.invalid"},
                        "aap_selected_setup_plan": {"organization": organization},
                        "aap_instance_route": {"hypervisor": {"machine_credential_name": "Registered Machine"}},
                        "aap_instance_key": "fixture-target", "aap_selected_importer_extra": {},
                    }
                    expected = [1, 2, 3, 7, 6] if preparation else [1, 2, 3, 7]
                    fixture = [{"hosts": "localhost", "connection": "local", "gather_facts": False,
                                "vars": variables, "tasks": tasks[:3] + [
                                    {"ansible.builtin.set_fact": {"rendered_extra": launch["extra_vars"],
                                                                "rendered_credentials": launch["credentials"]}},
                                    {"ansible.builtin.assert": {"that": [
                                        "aap_selected_launch_credential_ids == " + repr(expected),
                                        "rendered_credentials | map('int') | list == " + repr(expected),
                                        "rendered_extra.aap_instance_key == 'fixture-target'",
                                        "'aap_cac_project_id' not in rendered_extra",
                                        "('aap_config_repo_url' in rendered_extra) == " + ("true" if preparation else "false"),
                                    ]}},
                                ]}]
                    path = directory / "fixture.yml"
                    path.write_text(yaml.safe_dump(fixture))
                    env = dict(os.environ, ANSIBLE_JINJA2_NATIVE=native_mode,
                               ANSIBLE_FILTER_PLUGINS=str(ROOT / "filter_plugins"),
                               ANSIBLE_LOCAL_TEMP=str(directory / "local"), ANSIBLE_REMOTE_TEMP=str(directory / "remote"))
                    process = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(path)],
                                             env=env, text=True, capture_output=True, timeout=30)
                    self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def test_empty_duplicate_unknown_and_unsupported_choices_fail(self):
        for selected in (
            [],
            "AIOps_selfhealing_demo",
            ["unknown"],
            ["AIOps_selfhealing_demo"] * 2,
            ["ServiceNow-ITSM-Integration"],
        ):
            with self.subTest(selected=selected), self.assertRaises(AnsibleFilterError):
                self.plan(selected)

    def test_catalog_drift_fails_before_an_importer_can_launch(self):
        self.protected["umbrella_modules"].pop("Automation_Dashboard")
        with self.assertRaises(AnsibleFilterError):
            self.plan(["AIOps_selfhealing_demo"])

    def test_repository_credentials_and_redirect_parameters_are_refused(self):
        for value in (
            "http://git.example.invalid/config",
            "https://user:fixture@git.example.invalid/config",
            "https://git.example.invalid/config?redirect=elsewhere",
            "https://[invalid/config",
        ):
            with self.subTest(value=value):
                self.protected["configuration_repositories"]["aiops"] = value
                with self.assertRaises(AnsibleFilterError):
                    self.plan(["AIOps_selfhealing_demo"])

    def test_self_target_plan_is_allowed_and_invalid_api_origins_are_refused(self):
        result = setup.setup_plan(["AIOps_selfhealing_demo"], self.catalog, self.protected,
                                  "https://same.example.invalid", "https://SAME.example.invalid:443/")
        self.assertEqual(len(result["importers"]), 1)
        for seed, target in (("https://seed.example.invalid/path", "https://fresh.example.invalid"),
                             ("https://seed.example.invalid", "http://fresh.example.invalid")):
            with self.subTest(seed=seed), self.assertRaises(AnsibleFilterError):
                setup.setup_plan(
                    ["AIOps_selfhealing_demo"],
                    self.catalog,
                    self.protected,
                    seed,
                    target,
                )
        for seed, target in (
            ([], []),
            ([{"uuid": "same"}], [{"uuid": "same"}]),
            ([{}], [{"uuid": "different"}]),
        ):
            with self.subTest(seed=seed), self.assertRaises(AnsibleFilterError):
                setup.distinct_controllers(seed, target)
        self.assertTrue(
            setup.distinct_controllers([{"uuid": "seed"}], [{"uuid": "fresh"}])
        )

    def test_verified_controller_identity_matches_local_or_remote_selection(self):
        local = [{"uuid": "controller-a"}]
        remote = [{"uuid": "controller-b"}]
        source = "https://source.example.invalid"
        self.assertTrue(setup.verified_controllers(local, local, source, "https://SOURCE.example.invalid:443/"))
        self.assertTrue(setup.verified_controllers(local, remote, source, "https://remote.example.invalid"))
        for first, second, destination in (
            (local, remote, source),
            (local, local, "https://remote.example.invalid"),
            ([], local, source),
            ([{}], local, source),
            (local * 2, local, source),
        ):
            with self.subTest(destination=destination), self.assertRaises(AnsibleFilterError):
                setup.verified_controllers(first, second, source, destination)

    def test_each_repository_uses_only_its_pinned_source_vault(self):
        repositories = [
            "aap_autodeploy_configascode-secrets",
            "assistant-team-secrets",
            "disconnected-windows-patching-secrets",
            "automation-orchestrator-secrets",
            "aiops-selfhealing-demo-secrets",
            "RHEL-sniperpatching-secrets",
        ]
        organization = "Fixture organization"

        def cred(identity, name, kind, owner, type_id, type_name, vault_id=None):
            return {
                "id": identity,
                "name": name,
                "kind": kind,
                "organization": owner,
                "credential_type": type_id,
                "inputs": {} if vault_id is None else {"vault_id": vault_id},
                "summary_fields": {
                    "organization": None if owner is None else {"name": organization},
                    "credential_type": {"name": type_name},
                },
            }

        native = cred(90, "AAP API/MCP Auth Token Store", "cloud", 1, 46,
                      "Pseudo Instance Key Store")
        native['inputs'] = {'host': 'https://fresh.example.invalid'}
        pins = {
            repo
            + " CaC vault cred": {
                "id": 200 + index,
                "credential_type": 8,
                "credential_type_name": "Vault",
            }
            for index, repo in enumerate(repositories)
        }
        base_git = repositories[0] + " CaC repo read token"
        pins[base_git] = {
            "id": 100,
            "credential_type": 33,
            "credential_type_name": "Cac_git_token_type",
        }
        for index, repo in enumerate(repositories):
            with self.subTest(repository=repo):
                git = cred(
                    100 + index,
                    repo + " CaC repo read token",
                    "cloud",
                    None if index == 0 else 1,
                    33,
                    "Cac_git_token_type",
                )
                vault = cred(
                    200 + index,
                    repo + " CaC vault cred",
                    "vault",
                    None,
                    8,
                    "Vault",
                    "cac",
                )
                environment = cred(93, "Environment Vault", "vault", 1, 8, "Vault", "")
                original = [git, vault, environment, native]
                expected = [x["name"] for x in original]
                selected = setup.api_launch_credentials(
                    original, expected, [native], organization, "https://fresh.example.invalid", pins
                )
                self.assertEqual(
                    set(selected), {100 + index, 200 + index, 93, 90}
                )
                bad = copy.deepcopy(pins)
                bad[vault["name"]]["id"] += 50
                with self.assertRaises(AnsibleFilterError):
                    setup.api_launch_credentials(
                        original,
                        expected,
                        [native],
                        organization,
                        "https://fresh.example.invalid",
                        bad,
                    )
                other_index = (index + 1) % len(repositories)
                other = cred(
                    200 + other_index,
                    repositories[other_index] + " CaC vault cred",
                    "vault",
                    None,
                    8,
                    "Vault",
                    "cac",
                )
                with self.assertRaises(AnsibleFilterError):
                    setup.api_launch_credentials(
                        original + [other],
                        expected + [other["name"]],
                        [native],
                        organization,
                        "https://fresh.example.invalid",
                        pins,
                    )

    def test_scoped_credentials_are_preserved_and_machine_is_bound_to_registry(self):
        def credential(identity, name, kind=None, vault_id=None):
            return {
                "id": identity,
                "name": name,
                "kind": kind,
                "inputs": {} if vault_id is None else {"vault_id": vault_id},
                "summary_fields": {
                    "organization": {"name": "Fixture organization"},
                    "credential_type": {"name": name},
                },
            }

        original = [
            credential(1, "aap_autodeploy_configascode-secrets CaC repo read token"),
            credential(2, "Case Vault", "vault", "cac"),
            credential(3, "Environment Vault", "vault"),
        ]
        original[0]["summary_fields"]["credential_type"]["name"] = "Cac_git_token_type"
        route = [credential(6, "Registered Machine", "ssh")]
        expected = [entry["name"] for entry in original]

        def resolve(source, dependencies, pins=None):
            return setup.scoped_launch_credentials(
                source,
                expected,
                dependencies,
                "Fixture organization",
                "Registered Machine",
                pins,
            )

        self.assertEqual(resolve(original, route), [1, 2, 3, 6])
        shared = copy.deepcopy(original)
        shared[0].update(organization=None, credential_type=17)
        shared[0]["summary_fields"]["organization"] = None
        pins = {
            "aap_autodeploy_configascode-secrets CaC repo read token": {
                "id": 1,
                "credential_type": 17,
                "credential_type_name": "Cac_git_token_type",
            }
        }
        with self.assertRaises(AnsibleFilterError):
            resolve(shared, route)
        self.assertEqual(resolve(shared, route, pins), [1, 2, 3, 6])
        for changed_id in (True, "1"):
            changed_pins = copy.deepcopy(pins)
            changed_pins["aap_autodeploy_configascode-secrets CaC repo read token"]["id"] = changed_id
            with self.assertRaises(AnsibleFilterError):
                resolve(shared, route, changed_pins)
        for change in ({"id": 99}, {"credential_type": 99}):
            changed = copy.deepcopy(shared)
            changed[0].update(change)
            with self.assertRaises(AnsibleFilterError):
                resolve(changed, route, pins)
        changed = copy.deepcopy(shared)
        changed[0]["summary_fields"]["organization"] = {"name": "Other organization"}
        with self.assertRaises(AnsibleFilterError):
            resolve(changed, route, pins)
        # A source-only pin cannot authorize an unowned route credential.
        changed_route = copy.deepcopy(route)
        changed_route[0].update(organization=None, credential_type=18)
        changed_route[0]["summary_fields"]["organization"] = None
        machine_pin = {
            route[0]["name"]: {
                "id": 6,
                "credential_type": 18,
                "credential_type_name": route[0]["name"],
            }
        }
        with self.assertRaises(AnsibleFilterError):
            resolve(original, changed_route, machine_pin)
        # A previous Machine is replaced only with the exact registry-bound one.
        self.assertEqual(
            resolve(original + [credential(7, "Previous Machine", "ssh")], route),
            [1, 2, 3, 6],
        )
        for changed in (original[:-1], original + [credential(8, "Unreviewed Git")]):
            with self.assertRaises(AnsibleFilterError):
                resolve(changed, route)
        for index, change in (
            (0, {"kind": "vault"}),
            (0, {"name": "Unregistered Machine"}),
            (0, {"summary_fields": {"organization": {"name": "Other"}}}),
        ):
            changed = copy.deepcopy(route)
            changed[index].update(change)
            with self.assertRaises(AnsibleFilterError):
                resolve(original, changed)

    def test_prerequisites_retain_multiple_versions_and_exclude_unselected_cases(self):
        def record(*versions):
            return {
                "reviewed": True,
                "repositories": [
                    {
                        "name": "community",
                        "collections": [
                            {"name": "example.tools", "version": version}
                            for version in versions
                        ],
                    }
                ],
            }

        definitions = {
            "one": record("1.0.0"),
            "two": record("1.0.0", "2.0.0"),
            "unselected": record("9.0.0"),
        }
        result = setup.selected_prerequisites(definitions, ["one", "two"])
        self.assertEqual(
            [x["version"] for x in result["repositories"][0]["collections"]],
            ["1.0.0", "2.0.0"],
        )
        definitions["one"]["reviewed"] = False
        with self.assertRaises(AnsibleFilterError):
            setup.selected_prerequisites(definitions, ["one"])

    def test_real_label_preflight_accepts_complete_capture_and_refuses_omissions(self):
        complete = {
            "cac_required_template_label": "fixture-use-case",
            "cac_label_definitions": [
                {"name": "fixture-use-case", "organization": "Fixture organization"}
            ],
            "cac_label_templates": [
                {
                    "name": "Fixture job",
                    "organization": "Fixture organization",
                    "labels": ["fixture-use-case"],
                }
            ],
        }
        cases = [("complete", complete, True)]
        for include_target, expected in ((False, False), (True, True)):
            value = copy.deepcopy(complete)
            value["cac_registered_setup_playbooks"] = ["fixture-import.yml"]
            template = value["cac_label_templates"][0]
            template.update(
                playbook="fixture-import.yml",
                survey_enabled=True,
                survey_spec={
                    "spec": [
                        {"type": "text", "variable": "debug_logging", "required": True}
                    ]
                },
            )
            if include_target:
                template["survey_spec"]["spec"].extend(
                    [
                        {
                            "type": "text",
                            "variable": "aap_instance_key",
                            "required": True,
                        },
                        {
                            "type": "text",
                            "variable": "aap_config_repo_url",
                            "required": True,
                        },
                    ]
                )
            cases.append(
                ("registered target prompts " + str(include_target), value, expected)
            )
            if include_target:
                permissive = copy.deepcopy(value)
                permissive["cac_label_templates"][0]["ask_variables_on_launch"] = True
                cases.append(("arbitrary importer variables", permissive, False))
        for default, expected in (([], False), ("", True)):
            value = copy.deepcopy(complete)
            value["cac_label_templates"][0]["survey_spec"] = {
                "spec": [
                    {
                        "type": "multiselect",
                        "variable": "fixture_selection",
                        "default": default,
                    }
                ]
            }
            cases.append(("multiselect default " + repr(default), value, expected))
        for label, change in (
            ("missing assignment", {"labels": []}),
            ("undefined label", {"labels": ["fixture-use-case", "unknown"]}),
            ("wrong organization", {"organization": "Other organization"}),
        ):
            value = copy.deepcopy(complete)
            value["cac_label_templates"][0].update(change)
            cases.append((label, value, False))
        for label, variables, expected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory(
                prefix="aap-label-preflight-"
            ) as temporary:
                fixture = Path(temporary) / "fixture.yml"
                fixture.write_text(
                    yaml.safe_dump(
                        [
                            {
                                "hosts": "localhost",
                                "connection": "local",
                                "gather_facts": False,
                                "vars": variables,
                                "tasks": [
                                    {
                                        "ansible.builtin.include_tasks": str(
                                            ROOT / "tasks/cac-template-labels.yml"
                                        )
                                    }
                                ],
                            }
                        ]
                    )
                )
                env = dict(
                    os.environ,
                    ANSIBLE_LOCAL_TEMP=str(Path(temporary) / "local"),
                    ANSIBLE_REMOTE_TEMP=str(Path(temporary) / "remote"),
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
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(
                    result.returncode == 0, expected, result.stdout + result.stderr
                )



if __name__ == "__main__":
    unittest.main()
