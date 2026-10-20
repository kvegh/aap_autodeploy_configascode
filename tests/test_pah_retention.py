"""Behavioral checks for PAH retention semantics and pruning safeguards."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


PATH = Path(__file__).resolve().parents[1] / "library/pah_collection_retention.py"
SPEC = importlib.util.spec_from_file_location("pah_retention", PATH)
retention = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(retention)

POLICY = {"mode": "latest_installed_plus_requirements", "sync_highest_versions": 1,
          "retain_repo_versions": 1, "repositories": ["certified"],
          "require_complete_requirements_audit": True}


def collection(name, version, dependencies=None):
    namespace, short = name.split(".")
    return {"namespace": namespace, "name": short, "version": version,
            "dependencies": dependencies or {}, "pulp_href": "/pulp/content/" + name + "/" + version + "/"}


def repository(items):
    return {"name": "certified", "pulp_href": "/pulp/repositories/certified/",
            "latest_version_href": "/pulp/repositories/certified/versions/1/", "collections": items}


class FakeClient:
    def __init__(self):
        self.remote = {"name": "certified", "pulp_href": "/pulp/remotes/certified/", "sync_highest_versions": 0}
        self.repository = {"name": "certified", "pulp_href": "/pulp/repositories/certified/", "remote": self.remote["pulp_href"], "retain_repo_versions": 0}
        self.calls = []
        self.wait_error = False

    def pages(self, path):
        self.calls.append(("GET", path))
        if "/remotes/" in path:
            return [deepcopy(self.remote)]
        if "/repositories/" in path:
            return [deepcopy(self.repository)]
        return []

    def request(self, method, path, body=None, expected=(200,)):
        self.calls.append((method, path, body))
        item = self.remote if path == self.remote["pulp_href"] else self.repository
        if method == "PATCH":
            item.update(body)
            return {"task": "/pulp/tasks/policy/"}
        return deepcopy(item)

    def wait(self, result):
        if self.wait_error:
            raise retention.PolicyError("The asynchronous PAH task failed.")


class SelectionSettingsTests(unittest.TestCase):
    def test_base_configures_limits_without_syncing_or_removing_releases(self):
        client = FakeClient()
        result = retention.configure(client, POLICY)
        self.assertTrue(result["changed"])
        self.assertFalse(result["content_synced"])
        self.assertEqual(result["collection_releases_removed"], 0)
        self.assertEqual(client.remote["sync_highest_versions"], 1)
        self.assertEqual(client.repository["retain_repo_versions"], 1)
        self.assertEqual({item[0] for item in client.calls}, {"GET", "PATCH"})

    def test_a_rerun_preserves_the_already_configured_limits(self):
        client = FakeClient()
        retention.configure(client, POLICY)
        client.calls.clear()
        self.assertFalse(retention.configure(client, POLICY)["changed"])
        self.assertTrue(all(item[0] == "GET" for item in client.calls))

    def test_check_mode_predicts_changes_without_writing(self):
        client = FakeClient()
        self.assertTrue(retention.configure(client, POLICY, check_mode=True)["changed"])
        self.assertTrue(all(item[0] == "GET" for item in client.calls))

    def test_an_unsupported_remote_setting_blocks_all_changes(self):
        client = FakeClient()
        del client.remote["sync_highest_versions"]
        with self.assertRaises(retention.PolicyError):
            retention.configure(client, POLICY)
        self.assertTrue(all(item[0] == "GET" for item in client.calls))

    def test_a_repository_using_another_remote_is_left_untouched(self):
        client = FakeClient()
        client.repository["remote"] = "/pulp/remotes/other/"
        with self.assertRaises(retention.PolicyError):
            retention.configure(client, POLICY)
        self.assertTrue(all(item[0] == "GET" for item in client.calls))

    def test_an_async_policy_failure_is_reported(self):
        client = FakeClient()
        client.wait_error = True
        with self.assertRaises(retention.PolicyError):
            retention.configure(client, POLICY)


class ReleasePlanningTests(unittest.TestCase):
    def test_keeps_numeric_newest_installed_release(self):
        plan = retention.make_plan([repository([collection("demo.tools", "4.9.0"), collection("demo.tools", "4.10.0")])], [])
        self.assertEqual([item["version"] for item in plan["repositories"][0]["keep"]], ["4.10.0"])
        self.assertEqual(plan["remove_count"], 1)

    def test_a_provenanced_exact_project_pin_preserves_an_older_release(self):
        items = [collection("demo.tools", value) for value in ("1.0.0", "2.0.0", "3.0.0")]
        plan = retention.make_plan([repository(items)], [{"name": "demo.tools", "version": "1.0.0", "reason": "project demo: collections/requirements.yml"}])
        self.assertEqual({item["version"] for item in plan["repositories"][0]["keep"]}, {"1.0.0", "3.0.0"})
        self.assertEqual([item["version"] for item in plan["repositories"][0]["remove"]], ["2.0.0"])

    def test_latest_is_local_to_each_repository_and_does_not_preserve_old_copies_elsewhere(self):
        first = repository([collection("demo.tools", "1.0.0"), collection("demo.tools", "2.0.0")])
        second = repository([collection("demo.tools", "1.0.0")])
        second["name"] = "community"
        second["pulp_href"] = "/pulp/repositories/community/"
        plan = retention.make_plan([first, second], [])
        self.assertEqual([item["version"] for item in plan["repositories"][0]["keep"]], ["2.0.0"])
        self.assertEqual([item["version"] for item in plan["repositories"][1]["keep"]], ["1.0.0"])
        self.assertEqual(plan["remove_count"], 1)
        pinned = retention.make_plan([first, second], [{"name": "demo.tools", "version": "1.0.0", "reason": "project demo: exact playbook pin"}])
        self.assertEqual(pinned["remove_count"], 0)

    def test_a_required_dependency_keeps_its_older_compatible_version(self):
        items = [collection("demo.tools", "1.0.0", {"demo.base": "<2.0.0"}),
                 collection("demo.base", "1.2.0"), collection("demo.base", "2.0.0")]
        plan = retention.make_plan([repository(items)], [])
        self.assertEqual(plan["remove_count"], 0)
        reasons = next(item["reasons"] for item in plan["retained"] if item["name"] == "demo.base" and item["version"] == "1.2.0")
        self.assertIn("demo.tools 1.0.0 requires <2.0.0", reasons)

    def test_a_missing_project_pin_blocks_pruning(self):
        with self.assertRaises(retention.PolicyError):
            retention.make_plan([repository([collection("demo.tools", "2.0.0")])], [{"name": "demo.tools", "version": "1.0.0", "reason": "reviewed project requirement"}])

    def test_a_missing_dependency_blocks_pruning(self):
        with self.assertRaises(retention.PolicyError):
            retention.make_plan([repository([collection("demo.tools", "2.0.0", {"demo.base": "<1.0.0"})])], [])

    def test_a_version_or_constraint_with_unknown_semantics_blocks_pruning(self):
        with self.assertRaises(retention.PolicyError):
            retention.make_plan([repository([collection("demo.tools", "2.0.0-beta.1")])], [])
        with self.assertRaises(retention.PolicyError):
            retention.make_plan([repository([collection("demo.tools", "2.0.0")])], [{"name": "demo.tools", "version": "^2.0.0", "reason": "project"}])

    def test_missing_dependency_metadata_is_not_treated_as_no_dependencies(self):
        item = collection("demo.tools", "2.0.0")
        del item["dependencies"]
        with self.assertRaises(retention.PolicyError):
            retention.make_plan([repository([item])], [])


class RequirementAuditTests(unittest.TestCase):
    def setUp(self):
        self.projects = [{"name": "demo", "scm_revision": "a" * 40}]
        self.audit = {"complete": True, "projects": [{"name": "demo", "scm_revision": "a" * 40, "files": [{"path": "collections/requirements.yml", "sha256": "a" * 64, "kind": "project", "collections": [{"name": "demo.tools", "version": "1.0.0"}]}]}], "execution_environments": []}

    def test_a_reviewed_file_supplies_the_pin_and_its_provenance(self):
        requirements = retention.audit_requirements(self.projects, [], self.audit)
        self.assertEqual(requirements[0]["version"], "1.0.0")
        self.assertIn("collections/requirements.yml", requirements[0]["reason"])

    def test_unknown_projects_or_changed_revisions_block_pruning(self):
        with self.assertRaises(retention.PolicyError):
            retention.audit_requirements(self.projects + [{"name": "unknown", "scm_revision": "abc"}], [], self.audit)
        self.projects[0]["scm_revision"] = "new"
        with self.assertRaises(retention.PolicyError):
            retention.audit_requirements(self.projects, [], self.audit)

    def test_unreviewed_requirements_or_execution_environments_block_pruning(self):
        self.audit["complete"] = False
        with self.assertRaises(retention.PolicyError):
            retention.audit_requirements(self.projects, [], self.audit)
        self.audit["complete"] = True
        with self.assertRaises(retention.PolicyError):
            retention.audit_requirements(self.projects, [{"name": "unknown", "image": "example/image:latest"}], self.audit)

    def test_a_stale_preview_is_rejected_before_any_removal(self):
        client = FakeClient()
        with patch.object(retention, "collect_plan", return_value={"remove_count": 2}):
            with self.assertRaises(retention.PolicyError):
                retention.apply_plan(client, POLICY, self.audit, {"remove_count": 1})
        self.assertEqual(client.calls, [])

    def test_an_image_inventory_must_match_an_immutable_live_image(self):
        digest = "sha256:" + "b" * 64
        image = "example/image@" + digest
        self.audit["execution_environments"] = [{"name": "vendor", "image": image,
            "image_inventory": {"digest": digest, "sha256": "c" * 64,
                                "collections": [{"name": "demo.vendor", "version": "2.0.0"}]}}]
        result = retention.audit_requirements(self.projects, [{"name": "vendor", "image": image}], self.audit)
        self.assertEqual(result[-1]["name"], "demo.vendor")
        self.audit["execution_environments"][0]["image"] = "example/image:latest"
        with self.assertRaises(retention.PolicyError):
            retention.audit_requirements(self.projects, [{"name": "vendor", "image": "example/image:latest"}], self.audit)


if __name__ == "__main__":
    unittest.main()
