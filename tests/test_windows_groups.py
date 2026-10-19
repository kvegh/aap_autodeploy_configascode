"""Exercise real group-module resolution against an initially empty inventory."""

import copy
import importlib
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

try:
    import yaml
except ImportError:
    yaml = None


PLAYBOOK = Path(__file__).resolve().parents[1] / "deploy-windows-demo.yml"


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class WindowsGroupTests(unittest.TestCase):
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
        source = yaml.safe_load(PLAYBOOK.read_text())[0]
        self.assertIn("controller_host_groups", source["vars"]["aap_configuration_dispatcher_exclude_roles"])
        tasks = source["pre_tasks"][-1]["block"]
        skeleton = next(task for task in tasks if task["name"] ==
                        "Create all Windows inventory groups before adding memberships")
        membership = next(task for task in tasks if task["name"] ==
                          "Apply the declared Windows inventory group memberships")
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
