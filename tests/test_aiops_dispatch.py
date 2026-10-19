"""Exercise real CoP dispatch without contacting AAP.

Run with an Ansible/PyYAML Python and ANSIBLE_COLLECTIONS_PATH pointing at the
installed runtime collections. No dependencies are downloaded by this test.
"""

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


PLAYBOOK = Path(__file__).resolve().parents[1] / "deploy-aiops-demo.yml"
EDA_ROLES = ("eda_event_streams", "eda_rulebook_activations")


def tasks_in(tasks):
    for task in tasks:
        yield task
        for section in ("block", "rescue", "always"):
            yield from tasks_in(task.get(section, []))


@unittest.skipUnless(yaml and importlib.util.find_spec("ansible"), "requires Ansible and PyYAML")
class AIOpsDispatchTests(unittest.TestCase):
    def test_initial_dispatch_defers_streams_and_activations(self):
        source = yaml.safe_load(PLAYBOOK.read_text())[0]
        dispatch = next(
            task for task in tasks_in(source["pre_tasks"])
            if task.get("ansible.builtin.include_role", {}).get("name")
            == "infra.aap_configuration.dispatch"
        )
        with tempfile.TemporaryDirectory(prefix="aiops-dispatch-test-") as directory:
            root = Path(directory)
            variables = copy.deepcopy(source["vars"])
            variables.update({
                "aap_hostname": "https://aap.example.invalid",
                "aap_password": "synthetic-test-password",
                "aap_token": "synthetic-test-token",
                "debug_logging": True,
                "ansible_python_interpreter": sys.executable,
                "aap_configuration_async_dir": str(root / "async"),
                "eda_event_streams_aiops_demo": [{
                    "name": "Synthetic stream",
                    "organization_name": "Synthetic organization",
                    "credential_name": "Synthetic credential",
                }],
                "eda_rulebook_activations_aiops_demo": [{
                    "name": "Synthetic activation",
                    "organization": "Synthetic organization",
                    "event_streams": [{"event_stream": "Synthetic stream", "source_index": 0}],
                }],
            })
            play = [{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": variables,
                "tasks": [dispatch, {"ansible.builtin.assert": {"that": [
                    "eda_event_streams == eda_event_streams_aiops_demo",
                    "eda_rulebook_activations == eda_rulebook_activations_aiops_demo",
                ]}}],
            }]
            config = root / "ansible.cfg"
            config.write_text("[defaults]\nstdout_callback = default\nretry_files_enabled = False\n")
            environment = dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                               ANSIBLE_LOCAL_TEMP=str(root / "local"),
                               ANSIBLE_REMOTE_TEMP=str(root / "remote"))

            def run_dispatch():
                fixture = root / "play.yml"
                fixture.write_text(yaml.safe_dump(play, sort_keys=False))
                result = subprocess.run(
                    [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,",
                     "--check", str(fixture)],
                    cwd=root, env=environment, capture_output=True, text=True, timeout=60,
                )
                output = result.stdout + result.stderr
                if ("the role 'infra.aap_configuration.dispatch' was not found" in output
                        or "couldn't resolve module/action 'ansible.eda." in output):
                    self.skipTest("requires installed infra.aap_configuration and ansible.eda collections")
                return result.returncode, output

            status, output = run_dispatch()
            self.assertEqual(status, 0, output)
            for role in EDA_ROLES:
                self.assertNotIn(f"TASK [infra.aap_configuration.{role} :", output, output)

            # Prove both exclusions matter. Check mode rejects CoP's async task
            # before any mutation module runs, even for these reserved .invalid inputs.
            exclusions = variables["aap_configuration_dispatcher_exclude_roles"]
            for role in EDA_ROLES:
                with self.subTest(missing_exclusion=role):
                    variables["aap_configuration_dispatcher_exclude_roles"] = [
                        excluded for excluded in exclusions if excluded != role
                    ]
                    status, output = run_dispatch()
                    self.assertNotEqual(status, 0, output)
                    self.assertIn(f"TASK [infra.aap_configuration.{role} :", output, output)
                    self.assertIn("check mode and async cannot be used on same task", output, output)


if __name__ == "__main__":
    unittest.main()
