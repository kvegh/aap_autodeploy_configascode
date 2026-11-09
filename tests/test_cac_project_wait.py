"""Resolve the actual pinned CoP project/collector wait without API calls or sleeps."""

import json
from pathlib import Path
import unittest

from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar
from ansible.utils.collection_loader._collection_finder import _get_collection_role_path
import yaml


ROOT = Path(__file__).resolve().parents[1]


class ProjectWaitRoutingTests(unittest.TestCase):
    def test_only_project_wait_override_reaches_the_actual_pinned_role_and_collector(self):
        init_plugin_loader()
        selected = _get_collection_role_path("infra.aap_configuration.controller_projects")
        self.assertIsNotNone(selected, "The pinned CoP collection must already be installed")
        role = Path(selected[1])
        manifest = json.loads((role.parents[1] / "MANIFEST.json").read_text())
        declared = yaml.safe_load((ROOT / "collections/requirements.yml").read_text())["collections"]
        expected_version = next(row["version"] for row in declared if row["name"] == "infra.aap_configuration")
        self.assertEqual(manifest["collection_info"]["version"], expected_version)
        defaults = yaml.safe_load((role / "defaults/main.yml").read_text())
        project_tasks = yaml.safe_load((role / "tasks/main.yml").read_text())[0]["block"]
        call = next(task for task in project_tasks if task.get("ansible.builtin.include_role", {}).get("name")
                    == "infra.aap_configuration.collect_async_status")
        collect = yaml.safe_load((role.parent / "collect_async_status/tasks/main.yml").read_text())[0]["block"][0]
        importer = yaml.safe_load((ROOT / "tasks/cac-resource-definitions.yml").read_text())[0]
        self.assertTrue(importer["no_log"])
        self.assertTrue(importer["ansible.builtin.include_role"]["apply"]["no_log"])
        self.assertNotIn("aap_configuration_async_retries", importer["vars"])
        self.assertNotIn("aap_configuration_async_delay", importer["vars"])
        variables = dict(defaults, **importer["vars"], aap_configuration_secure_logging=True)
        templar = Templar(loader=DataLoader(), variables=variables)
        collector_vars = {key: templar.template(call["vars"][key])
                          for key in ("cas_async_delay", "cas_async_retries", "cas_secure_logging")}
        templar.available_variables = collector_vars
        retries = int(templar.template(collect["retries"]))
        delay = int(templar.template(collect["delay"]))
        self.assertEqual((retries, delay), (180, 1))
        self.assertTrue(collector_vars["cas_secure_logging"])
        self.assertEqual(collect["until"], "__cas_job_async_result.finished")
        async_budget = Templar(loader=DataLoader(), variables={"ansible_check_mode": False}).template(
            next(task["async"] for task in project_tasks if "async" in task))
        self.assertLess(retries * delay, int(async_budget))


if __name__ == "__main__":
    unittest.main()
