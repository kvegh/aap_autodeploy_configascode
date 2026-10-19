"""Exercise the Windows import's actual preflight guards without AAP access."""

import copy
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import yaml
except ImportError:
    yaml = None


PLAYBOOK = Path(__file__).resolve().parents[1] / "deploy-windows-demo.yml"


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class WindowsConfigurationTests(unittest.TestCase):
    def test_incomplete_or_executable_configuration_is_rejected(self):
        source = yaml.safe_load(PLAYBOOK.read_text())[0]
        guards = [task for task in source["pre_tasks"][-1]["block"]
                  if task["name"] in {
                      "Require a reviewed and complete Windows configuration",
                      "Require the secret inputs listed by the Windows configuration",
                      "Require configuration without job launches or schedules",
                  }]
        self.assertEqual(len(guards), 3)
        complete = {
            "windows_disconnected_configuration_ready": True,
            "windows_disconnected_required_secret_variables": ["synthetic_windows_password"],
            "synthetic_windows_password": "synthetic-test-password",
            "controller_schedules_windows_disconnected": [],
        }
        cases = [
            ("complete", {}, (), True),
            ("not reviewed", {"windows_disconnected_configuration_ready": False}, (), False),
            ("missing password", {}, ("synthetic_windows_password",), False),
            ("placeholder password", {"synthetic_windows_password": "CHANGEME"}, (), False),
            ("job launch", {"controller_launch_jobs_windows_disconnected": [{"name": "Synthetic job"}]}, (), False),
            ("workflow launch", {"controller_workflow_launch_jobs": [{"name": "Synthetic workflow"}]}, (), False),
            ("schedule", {"controller_schedules_windows_disconnected": [{"name": "Synthetic schedule"}]}, (), False),
        ]
        with tempfile.TemporaryDirectory(prefix="windows-cac-test-") as directory:
            root = Path(directory)
            config = root / "ansible.cfg"
            config.write_text("[defaults]\nstdout_callback = default\nretry_files_enabled = False\n")
            environment = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                               ANSIBLE_LOCAL_TEMP=str(root / "local"),
                               ANSIBLE_REMOTE_TEMP=str(root / "remote"))
            for name, overrides, missing, succeeds in cases:
                with self.subTest(name=name):
                    variables = copy.deepcopy(complete)
                    variables.update(overrides)
                    for variable in missing:
                        variables.pop(variable)
                    fixture = root / "play.yml"
                    fixture.write_text(yaml.safe_dump([{
                        "hosts": "localhost", "connection": "local", "gather_facts": False,
                        "vars": variables, "tasks": guards,
                    }], sort_keys=False))
                    result = subprocess.run(
                        [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                        cwd=root, env=environment, capture_output=True, text=True, timeout=30,
                    )
                    self.assertEqual(result.returncode == 0, succeeds, result.stdout + result.stderr)
                    self.assertNotIn("synthetic-test-password", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
