"""Exercise the native DNF action with a synthetic package-transaction boundary."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class SkopeoPrerequisite(unittest.TestCase):
    def test_skopeo_is_declared_on_the_receiving_vm_after_subscription_setup(self):
        plays = yaml.safe_load((ROOT / "03-aap-install.yml").read_text())
        prep = next(play for play in plays if play["name"] == "Prepare host for AAP installation")
        self.assertEqual(prep["hosts"], "target_vm")
        packages = next(task for task in prep["tasks"] if "ansible.builtin.dnf" in task)
        self.assertEqual(packages["ansible.builtin.dnf"], {"name": ["ansible-core", "skopeo"], "state": "present"})
        subscription = next(task for task in prep["tasks"] if
                            task.get("ansible.builtin.include_role", {}).get("name") == "redhat.rhel_system_roles.rhc")
        self.assertLess(prep["tasks"].index(subscription), prep["tasks"].index(packages))

    def test_native_dnf_dispatch_installs_only_the_missing_skopeo_and_is_idempotent(self):
        plays = yaml.safe_load((ROOT / "03-aap-install.yml").read_text())
        prep = next(play for play in plays if play["name"] == "Prepare host for AAP installation")
        task = copy.deepcopy(next(task for task in prep["tasks"] if "ansible.builtin.dnf" in task))
        with tempfile.TemporaryDirectory(prefix="skopeo-prerequisite-") as directory:
            root = Path(directory)
            (root / "action_plugins").mkdir()
            (root / "action_plugins/fixture_dnf.py").write_text('''
import json
from pathlib import Path
from ansible.plugins.action.dnf import ActionModule as NativeDnf

class ActionModule(NativeDnf):
    def _execute_module(self, module_name=None, module_args=None, task_vars=None, **kwargs):
        # Retain the actual Core DNF action; intercept every external module call.
        # No native package manager, remote module or system transaction executes.
        if module_name == 'ansible.legacy.setup':
            return {'ansible_facts': {'ansible_pkg_mgr': 'dnf'}}
        assert module_name in ('ansible.legacy.dnf', 'ansible.builtin.dnf'), module_name
        assert module_args == {'name': ['ansible-core', 'skopeo'], 'state': 'present'}, module_args
        path = Path(task_vars['fixture_package_state'])
        state = json.loads(path.read_text())
        added = sorted(set(module_args['name']) - set(state['installed']))
        state['installed'] = sorted(set(state['installed']) | set(module_args['name']))
        state['transactions'].append({'module': module_name, 'added': added})
        path.write_text(json.dumps(state))
        return {'changed': bool(added), 'results': added}
''')
            state = root / "state.json"
            state.write_text(json.dumps({"installed": ["ansible-core"], "transactions": []}))
            task["fixture_dnf"] = task.pop("ansible.builtin.dnf")
            first, second = copy.deepcopy(task), copy.deepcopy(task)
            first["register"], second["register"] = "first", "second"
            play = [{"hosts": "localhost", "connection": "local", "gather_facts": False,
                     "vars": {"ansible_facts": {"pkg_mgr": "dnf"}, "fixture_package_state": str(state)},
                     "tasks": [first, second, {"ansible.builtin.assert": {"that": [
                         "first.changed is sameas true", "second.changed is sameas false"]}}]}]
            path = root / "play.yml"
            path.write_text(yaml.safe_dump(play, sort_keys=False))
            env = dict(os.environ, ANSIBLE_ACTION_PLUGINS=str(root / "action_plugins"),
                       ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"),
                       ANSIBLE_NOCOLOR="1")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(path)],
                                    cwd=root, env=env, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            observed = json.loads(state.read_text())
            self.assertEqual(observed["installed"], ["ansible-core", "skopeo"])
            self.assertEqual([item["added"] for item in observed["transactions"]], [["skopeo"], []])


if __name__ == "__main__":
    unittest.main()
