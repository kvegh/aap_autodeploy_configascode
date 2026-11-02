"""Behavioral fixtures for reviewed additions, edits, removals and secret limits."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "cac_compare", ROOT / "src/cac_compare.py"
)
cac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cac)


class CaptureComparisonTests(unittest.TestCase):
    def test_dangling_template_and_inventory_membership_dependencies_are_refused(self):
        model = {
            "job_templates": {
                "job": {"name": "Fixture", "project": "Missing project", "labels": []}
            }
        }
        with self.assertRaises(cac.CaptureError):
            cac.validate_dependencies(model)
        cac.validate_dependencies(model, {"projects": ["Missing project"]})
        model = {
            "inventories": {"inv": {"name": "Fixture inventory"}},
            "hosts": {},
            "groups": {
                "group": {
                    "name": "Fixture group",
                    "inventory": "Fixture inventory",
                    "hosts": ["Missing host"],
                }
            },
        }
        with self.assertRaises(cac.CaptureError):
            cac.validate_dependencies(model)

    def state(self):
        return {
            "job_templates": {
                "fixture": {
                    "name": "Fixture job",
                    "timeout": 60,
                    "labels": ["fixture"],
                    "credentials": ["Scoped Git"],
                    "survey_spec": {"spec": [{"variable": "choice", "type": "text"}]},
                }
            },
            "labels": {"fixture": {"name": "fixture"}},
        }

    def compare(self, live=None, current=None, source=None, desired=None):
        baseline = self.state()
        return cac.compare(
            source or baseline,
            desired or baseline,
            baseline if current is None else current,
            baseline if live is None else live,
            True,
        )

    def test_unchanged_state_has_no_proposed_update(self):
        result = self.compare()
        self.assertEqual(result["source_changes"], [])
        self.assertEqual(result["desired_changes"], [])
        self.assertFalse(result["conflicts"])

    def test_new_job_and_label_are_discovered_and_added(self):
        live = self.state()
        live["job_templates"]["new"] = {"name": "New job", "labels": ["new-label"]}
        live["labels"]["new-label"] = {"name": "new-label"}
        result = self.compare(live=live)
        self.assertEqual(result["merged"], live)
        self.assertEqual(len(result["desired_changes"]), 2)
        self.assertEqual(
            {x["operation"] for x in result["desired_changes"]}, {"addition"}
        )

    def test_pending_repo_edit_and_repo_only_deletion_are_preserved(self):
        current = self.state()
        current["job_templates"]["fixture"]["timeout"] = 180
        current["labels"].pop("fixture")
        self.assertEqual(self.compare(current=current)["merged"], current)

    def test_disjoint_source_and_repo_edits_merge(self):
        current, live = self.state(), self.state()
        current["job_templates"]["fixture"]["timeout"] = 180
        live["job_templates"]["fixture"]["labels"].append("new-label")
        result = self.compare(current=current, live=live)
        self.assertFalse(result["conflicts"])
        self.assertEqual(result["merged"]["job_templates"]["fixture"]["timeout"], 180)
        self.assertIn(
            "new-label", result["merged"]["job_templates"]["fixture"]["labels"]
        )

    def test_same_field_edits_conflict_and_update_refuses(self):
        current, live = self.state(), self.state()
        current["job_templates"]["fixture"]["timeout"] = 180
        live["job_templates"]["fixture"]["timeout"] = 300
        result = self.compare(current=current, live=live)
        self.assertTrue(result["conflicts"])
        with self.assertRaises(cac.CaptureError):
            cac.approved_update(result, result["review_digest"])

    def test_confirmed_deleted_resource_is_removed_from_capture(self):
        live = self.state()
        live["job_templates"].pop("fixture")
        result = self.compare(live=live)
        self.assertEqual(result["merged"], live)
        self.assertIn("removal", {x["operation"] for x in result["desired_changes"]})

    def test_deleted_source_vs_modified_repo_conflicts(self):
        live, current = self.state(), self.state()
        live["job_templates"].pop("fixture")
        current["job_templates"]["fixture"]["timeout"] = 180
        result = self.compare(live=live, current=current)
        self.assertTrue(result["conflicts"])
        self.assertEqual(result["merged"], current)

    def test_removed_credentials_labels_survey_fields_and_workflow_edges(self):
        before = self.state()
        before["workflows"] = {
            "workflow": {
                "workflow_nodes": [
                    {"identifier": "one", "success_nodes": ["two", "three"]}
                ]
            }
        }
        live = deepcopy(before)
        live["job_templates"]["fixture"]["credentials"] = []
        live["job_templates"]["fixture"]["labels"] = []
        live["job_templates"]["fixture"]["survey_spec"]["spec"] = []
        live["workflows"]["workflow"]["workflow_nodes"][0]["success_nodes"] = ["two"]
        result = self.compare(source=before, desired=before, current=before, live=live)
        self.assertEqual(result["merged"], live)
        self.assertEqual(len(result["source_changes"]), 4)
        self.assertEqual(
            {item["operation"] for item in result["source_changes"]}, {"removal"}
        )

    def test_incomplete_visibility_never_implies_removal(self):
        with self.assertRaises(cac.CaptureError):
            cac.compare(self.state(), self.state(), self.state(), {}, False)

    def test_intentionally_excluded_discovered_object_is_not_readded(self):
        source, desired = self.state(), self.state()
        desired["job_templates"].pop("fixture")
        live = deepcopy(source)
        live["job_templates"]["fixture"]["timeout"] = 300
        result = self.compare(
            source=source, desired=desired, current=desired, live=live
        )
        self.assertEqual(result["merged"], desired)
        self.assertTrue(result["preserved_exclusions"])

    def test_secret_placeholders_preserve_existing_inputs_and_refuse_new_credentials(
        self,
    ):
        source = {
            "credentials": {
                "existing": {
                    "name": "Existing",
                    "description": "old",
                    "inputs": {"password": cac.MASK},
                }
            }
        }
        desired = deepcopy(source)
        desired["credentials"]["existing"]["inputs"][
            "password"
        ] = "fixture-secret-canary"
        live = deepcopy(source)
        live["credentials"]["existing"]["description"] = "new"
        result = cac.compare(source, desired, desired, live, True)
        self.assertEqual(
            result["merged"]["credentials"]["existing"]["inputs"]["password"],
            "fixture-secret-canary",
        )
        self.assertEqual(
            result["merged"]["credentials"]["existing"]["description"], "new"
        )
        live["credentials"]["new"] = {"name": "New", "inputs": {"password": cac.MASK}}
        with self.assertRaises(cac.CaptureError):
            cac.compare(source, desired, desired, live, True)
        supplied = deepcopy(desired)
        supplied["credentials"]["new"] = {
            "name": "New",
            "inputs": {"password": "fixture-new-secret"},
            "state": "present",
        }
        recovered = cac.compare(source, desired, supplied, live, True)
        self.assertFalse(recovered["conflicts"])
        self.assertEqual(
            recovered["merged"]["credentials"]["new"]["inputs"]["password"],
            "fixture-new-secret",
        )

    def test_update_requires_exact_fresh_review_digest(self):
        live = self.state()
        live["job_templates"]["fixture"]["timeout"] = 300
        result = self.compare(live=live)
        self.assertEqual(cac.approved_update(result, result["review_digest"]), live)
        with self.assertRaises(cac.CaptureError):
            cac.approved_update(result, "stale-review")

    def test_survey_secret_follows_variable_identity_after_reordering_and_new_fields(
        self,
    ):
        desired = [
            {"variable": "password", "default": "fixture-secret-canary"},
            {"variable": "normal", "default": "ordinary"},
        ]
        source = [
            {"variable": "added", "default": "new"},
            {"variable": "normal", "default": "ordinary"},
            {"variable": "password", "default": cac.MASK},
        ]
        merged = cac.preserve_masks(source, desired)
        self.assertEqual(merged[2]["default"], "fixture-secret-canary")
        source.append({"variable": "new_password", "default": cac.MASK})
        with self.assertRaises(cac.CaptureError):
            cac.preserve_masks(source, desired)


if __name__ == "__main__":
    unittest.main()
