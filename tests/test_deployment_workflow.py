"""Check deployment ordering, artifact boundaries, and exact-version batching."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import yaml
    from jinja2 import Environment, StrictUndefined
except ImportError:
    yaml = None


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(yaml, "requires installed PyYAML and Jinja")
class DeploymentWorkflowTests(unittest.TestCase):
    def graph(self):
        environment = Environment(undefined=StrictUndefined)
        environment.filters["to_json"] = json.dumps
        template = environment.from_string((ROOT / "templates/deployment-workflow-nodes.yml.j2").read_text())
        mapping = {key: "https://example.invalid/config/" + key + ".git" for key in (
            "base", "aiops", "windows_disconnected", "orchestrator", "assistant_team")}
        return yaml.safe_load(template.render(cac_workflow={"organization": "Synthetic organization",
                                                           "repositories": mapping})), mapping

    def test_all_five_imports_fork_only_after_successful_base_and_prerequisites(self):
        nodes, mapping = self.graph()
        by_id = {node["identifier"]: node for node in nodes}
        self.assertEqual(len(nodes), len(by_id))
        self.assertEqual(len(nodes), 10)
        parents = {identifier: [] for identifier in by_id}
        for node in nodes:
            self.assertEqual(node["related"]["always_nodes"], [])
            self.assertEqual(node["related"]["failure_nodes"], [])
            self.assertNotRegex(node["unified_job_template"]["name"].lower(), "destroy|teardown|cleanup")
            for child in node["related"]["success_nodes"]:
                self.assertIn(child["identifier"], by_id)
                parents[child["identifier"]].append(node["identifier"])
        expected_chain = ["create_vm", "configure_infrastructure", "install_aap", "configure_base", "prepare_use_cases"]
        self.assertEqual(parents[expected_chain[0]], [])
        for parent, child in zip(expected_chain, expected_chain[1:]):
            self.assertEqual(parents[child], [parent])
        branches = {"configure_aiops", "configure_windows", "configure_orchestrator",
                    "configure_assistant_team", "configure_autodeploy"}
        self.assertEqual({item["identifier"] for item in by_id["prepare_use_cases"]["related"]["success_nodes"]}, branches)
        for branch in branches:
            self.assertEqual(parents[branch], ["prepare_use_cases"])
            self.assertEqual(by_id[branch]["related"]["success_nodes"], [])
        self.assertEqual(by_id["configure_autodeploy"]["extra_data"]["aap_config_repo_url"], mapping["base"])

    def test_nodes_do_not_pin_an_old_target_or_pass_secrets_as_artifacts(self):
        nodes, _ = self.graph()
        for node in nodes:
            self.assertLessEqual(set(node.get("extra_data", {})), {"aap_config_repo_url"})
            self.assertNotIn("credentials", node["related"])
        provision = yaml.safe_load((ROOT / "01-linux-vm-setup.yml").read_text())[0]
        artifact = next(task["ansible.builtin.set_stats"] for task in provision["tasks"]
                        if "ansible.builtin.set_stats" in task)
        self.assertEqual(set(artifact["data"]), {"vm_name", "vm_ip", "aap_hostname"})
        self.assertEqual(artifact["data"]["aap_hostname"], "https://{{ new_vm_ip }}")
        self.assertFalse(artifact["per_host"])
        self.assertFalse(artifact["aggregate"])
        installer = yaml.safe_load((ROOT / "03-aap-install.yml").read_text())[-1]
        self.assertNotIn("aap_hostname", installer["vars"])
        self.assertEqual(installer["vars"]["aap_installer_hostname"], "{{ vm_name }}.{{ vault_domain }}")

    @unittest.skipUnless(importlib.util.find_spec("ansible"), "requires installed Ansible")
    def test_duplicate_collection_pins_are_synced_in_nonoverlapping_exact_batches(self):
        tasks = yaml.safe_load((ROOT / "tasks/use-case-pah-repository.yml").read_text())
        select = next(task for task in tasks if task.get("name") == "Separate additional exact versions of the same collection")
        entries = [{"name": "example.roles", "version": "1.2.3"},
                   {"name": "example.roles", "version": "2.4.0"},
                   {"name": "example.windows", "version": "3.1.0"}]
        with tempfile.TemporaryDirectory(prefix="workflow-batches-") as directory:
            root = Path(directory)
            (root / "ansible.cfg").write_text("[defaults]\nretry_files_enabled=False\n")
            tasks = [select, {"ansible.builtin.copy": {
                "dest": str(root / "batches.json"), "content": "{{ cac_required_sync_batches | to_json }}", "mode": "0600"}}]
            fixture = root / "play.yml"
            fixture.write_text(yaml.safe_dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                                               "vars": {"cac_required_repository": {"collections": entries}},
                                               "tasks": tasks}], sort_keys=False))
            environment = dict(os.environ, ANSIBLE_CONFIG=str(root / "ansible.cfg"),
                               ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"))
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                                    cwd=root, env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            batches = json.loads((root / "batches.json").read_text())
        self.assertEqual(len(batches), 2)
        self.assertCountEqual([item for batch in batches for item in batch], entries)
        for batch in batches:
            self.assertEqual(len({entry["name"] for entry in batch}), len(batch))


if __name__ == "__main__":
    unittest.main()
