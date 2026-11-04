"""Exercise real group-module resolution against an initially empty inventory."""

import copy
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    import yaml
except ImportError:
    yaml = None


PLAYBOOK = Path(__file__).resolve().parents[1] / "deploy-cac-project.yml"


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class WindowsGroupTests(unittest.TestCase):
    def test_native_group_skeleton_handles_empty_variables_before_real_module_validation(self):
        roots = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
        if not any((Path(root) / "ansible_collections/ansible/controller/plugins/modules/group.py").is_file()
                   for root in roots if root):
            self.skipTest("requires installed ansible.controller")
        definitions = [
            {"name": "empty-string", "inventory": "Synthetic inventory", "variables": ""},
            {"name": "omitted", "inventory": "Synthetic inventory"},
            {"name": "empty-mapping", "inventory": "Synthetic inventory", "variables": {}},
            {"name": "nonempty-mapping", "inventory": "Synthetic inventory", "variables": {"setting": "synthetic"}},
            {"name": "serialized-mapping", "inventory": "Synthetic inventory", "variables": '{"setting":"synthetic"}'},
        ]
        source = yaml.safe_load((PLAYBOOK.parent / "tasks/cac-resource-definitions.yml").read_text())
        skeleton = copy.deepcopy(next(task for task in source if task["name"] ==
                                     "Create all group skeletons before establishing group relationships"))
        skeleton["group_argument_proof"] = skeleton.pop("ansible.controller.group")
        previous = copy.deepcopy(skeleton)
        previous.update(name="Reproduce the previous empty-string module rejection", loop=definitions[:1],
                        register="previous_group_argument", ignore_errors=True)
        previous["group_argument_proof"]["variables"] = "{{ item.variables | default(omit) }}"
        plugin = '''import json
from pathlib import Path
from unittest.mock import patch
from ansible.plugins.action import ActionBase
from ansible.module_utils.common.arg_spec import ArgumentSpecValidator
from ansible_collections.ansible.controller.plugins.modules import group

class Captured(Exception):
    pass

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        specification = {}
        def capture(argument_spec):
            specification.update(argument_spec)
            raise Captured()
        with patch.object(group, "ControllerAPIModule", capture):
            try:
                group.main()
            except Captured:
                pass
        arguments = {key: value for key, value in self._task.args.items() if key in specification}
        result = ArgumentSpecValidator(specification).validate(arguments)
        if result.errors.errors:
            return {"failed": True, "msg": "Actual group-module argument validation failed."}
        with Path(task_vars["proof_file"]).open("a") as output:
            output.write(json.dumps({"name": arguments["name"],
                "variables_present": "variables" in arguments,
                "validated_variables": result.validated_parameters.get("variables")}) + "\\n")
        return {"changed": False}
'''
        for native in ("false", "true"):
            with self.subTest(native=native), tempfile.TemporaryDirectory(prefix="group-empty-vars-") as temporary:
                root = Path(temporary)
                plugins = root / "action_plugins"
                plugins.mkdir()
                (plugins / "group_argument_proof.py").write_text(plugin)
                proof = root / "proof.jsonl"
                play = root / "play.yml"
                play.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local",
                    "gather_facts": False, "vars": {"controller_groups": definitions,
                    "proof_file": str(proof), "aap_hostname": "https://aap.example.invalid",
                    "aap_token": "synthetic-token"}, "tasks": [previous,
                    {"ansible.builtin.assert": {"that": ["previous_group_argument is failed"]}},
                    skeleton]}], sort_keys=False))
                config = root / "ansible.cfg"
                config.write_text("[defaults]\n")
                environment = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_JINJA2_NATIVE=native,
                    ANSIBLE_ACTION_PLUGINS=str(plugins), ANSIBLE_LOCAL_TEMP=str(root / "local"),
                    ANSIBLE_REMOTE_TEMP=str(root / "remote"))
                result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play)],
                    capture_output=True, text=True, env=environment, timeout=40)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                rows = [json.loads(line) for line in proof.read_text().splitlines()]
                self.assertEqual([row["variables_present"] for row in rows], [False, False, False, True, True])
                self.assertTrue(all(row["validated_variables"] is None for row in rows[:3]))
                self.assertEqual([row["validated_variables"] for row in rows[3:]], [{"setting": "synthetic"}] * 2)

    def test_parent_groups_can_precede_their_children_on_a_clean_target(self):
        # Load already-installed collections only. No dependency installation.
        roots = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "").split(os.pathsep)
        collection_root = next((Path(root) for root in roots if root and (
            Path(root) / "ansible_collections/ansible/controller/plugins/modules/group.py"
        ).is_file()), None)
        if collection_root is None:
            self.skipTest("requires installed ansible.controller and infra.aap_configuration")
        sys.path.insert(0, str(collection_root))
        group_module = importlib.import_module("ansible_collections.ansible.controller.plugins.modules.group")
        role_file = collection_root / "ansible_collections/infra/aap_configuration/roles/controller_host_groups/tasks/main.yml"
        if not role_file.is_file():
            self.skipTest("requires installed infra.aap_configuration")
        role_module = yaml.safe_load(role_file.read_text())[0]["block"][0]["ansible.controller.group"]
        tasks = yaml.safe_load((PLAYBOOK.parent / 'tasks/cac-resource-definitions.yml').read_text())
        source = tasks[0]
        self.assertIn("controller_host_groups", source["vars"]["aap_configuration_dispatcher_exclude_roles"])
        skeleton = next(task for task in tasks if task["name"] ==
                        "Create all group skeletons before establishing group relationships")
        membership = next(task for task in tasks if task["name"] ==
                          "Link group relationships after every group skeleton exists")
        self.assertLess(tasks.index(skeleton), tasks.index(membership))
        self.assertEqual(membership["ansible.builtin.include_role"]["name"],
                         "infra.aap_configuration.controller_host_groups")

        from ansible.parsing.dataloader import DataLoader
        from ansible.template import Templar

        definitions = [
            {"name": "parent", "inventory": "Synthetic inventory", "children": ["child"], "hosts": []},
            {"name": "child", "inventory": "Synthetic inventory", "children": [], "hosts": ["Synthetic host"]},
        ]
        state = {}

        class Finished(Exception):
            pass

        class InventoryAPI:
            """Mock only the controller boundary used by the real group module."""

            def __init__(self, argument_spec):
                self.params = {key: value.get("default") for key, value in argument_spec.items()}
                self.params.update(copy.deepcopy(module_arguments))

            def resolve_name_to_id(self, endpoint, name):
                if endpoint != "inventories" or name != "Synthetic inventory":
                    raise AssertionError("Unexpected inventory lookup")
                return 1

            def get_one(self, endpoint, name_or_id, **kwargs):
                if endpoint == "groups":
                    return state.get(name_or_id)
                if endpoint == "hosts" and name_or_id == "Synthetic host":
                    return {"id": 101}
                raise AssertionError("Unexpected object lookup")

            @staticmethod
            def get_item_name(item):
                return item["name"]

            @staticmethod
            def fail_json(msg, **kwargs):
                raise RuntimeError(msg)

            def create_or_update_if_needed(self, existing, fields, **kwargs):
                name = fields["name"]
                item = state.setdefault(name, {"id": len(state) + 1, "hosts": [], "children": []})
                item.update(fields)
                item.update(kwargs["associations"])
                raise Finished()

        def run(parameters, definition):
            variables = {
                "item": definition, "__controller_groups_item": definition,
                "aap_hostname": "https://aap.example.invalid", "aap_token": "synthetic-token",
                "aap_validate_certs": True, "controller_configuration_groups_enforce_defaults": False,
                "omit": "__omit__",
            }
            rendered = Templar(loader=DataLoader(), variables=variables).template(parameters)
            nonlocal module_arguments
            module_arguments = {key: value for key, value in rendered.items() if value != "__omit__"}
            with patch.object(group_module, "ControllerAPIModule", InventoryAPI):
                try:
                    group_module.main()
                except Finished:
                    pass

        module_arguments = {}
        # Reproduce the actual module failure before any child group exists.
        with self.assertRaisesRegex(RuntimeError, "Could not find groups with name child"):
            run(role_module, definitions[0])
        self.assertEqual(state, {})

        for definition in definitions:
            run(skeleton["ansible.controller.group"], definition)
        for definition in definitions:
            run(role_module, definition)
        self.assertEqual(state["parent"]["children"], [state["child"]["id"]])
        self.assertEqual(state["parent"]["hosts"], [])
        self.assertEqual(state["child"]["hosts"], [101])
        self.assertEqual(state["child"]["children"], [])


if __name__ == "__main__":
    unittest.main()
