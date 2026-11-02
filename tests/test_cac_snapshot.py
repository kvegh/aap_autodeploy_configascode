"""Prove scope discovery, stable references and complete GET visibility."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for name in ("cac_compare", "cac_snapshot"):
    spec = importlib.util.spec_from_file_location(name, ROOT / "src" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
core, snapshot = sys.modules["cac_compare"], sys.modules["cac_snapshot"]


class ReadTransportTests(unittest.TestCase):
    def reader(self):
        return snapshot.ControllerReader(
            "https://source.example.invalid", "fixture-token-canary"
        )

    def test_related_pages_cannot_escape_origin_controller_prefix_or_redirect(self):
        reader = self.reader()
        for path in (
            "https://elsewhere.example.invalid/api/controller/v2/jobs/",
            "http://source.example.invalid/api/controller/v2/jobs/",
            "/api/gateway/v1/tokens/",
            "https://source.example.invalid:444/api/controller/v2/jobs/",
            "/api/controller/v2/../gateway/users/",
            "/api/controller/v2/%2e%2e/gateway/users/",
        ):
            with self.subTest(path=path), mock.patch.object(
                reader.opener, "open"
            ) as opened:
                with self.assertRaises(core.CaptureError):
                    reader.get(path)
                opened.assert_not_called()
        with self.assertRaises(core.CaptureError):
            snapshot.NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://elsewhere.example.invalid"
            )

    def test_pagination_requires_consistent_count_unique_ids_and_all_pages(self):
        reader = self.reader()
        valid = [
            {"count": 2, "results": [{"id": 1}], "next": "second"},
            {"count": 2, "results": [{"id": 2}], "next": None},
        ]
        with mock.patch.object(reader, "get", side_effect=valid):
            self.assertEqual(reader.all("first"), [{"id": 1}, {"id": 2}])
        for pages in (
            [{"count": 2, "results": [{"id": 1}], "next": None}],
            [valid[0], {"count": 2, "results": [{"id": 1}], "next": None}],
            [valid[0], {"count": 3, "results": [{"id": 2}], "next": None}],
            [{"results": [], "next": None}],
        ):
            with self.subTest(pages=pages), mock.patch.object(
                reader, "get", side_effect=pages
            ):
                with self.assertRaises(core.CaptureError):
                    reader.all("first")


class FakeAPI:
    def __init__(self, offset=0):
        self.offset = offset
        self.admin = True
        self.incomplete_relationship = False
        self.jobs = [
            self.job("Original job", 71 + offset),
            self.job("New discovered job", 72 + offset),
        ]

    def job(self, name, identity):
        return {
            "id": identity,
            "name": name,
            "organization": 1 + self.offset,
            "project": 11 + self.offset,
            "inventory": None,
            "execution_environment": None,
            "playbook": "fixture.yml",
            "description": "",
            "extra_vars": '{"choice":true}',
            "survey_enabled": True,
            "timeout": 300,
            "modified": "variable-runtime-time",
            "related": {
                key: "/api/controller/v2/job_templates/%s/%s/" % (identity, key)
                for key in ["credentials", "labels", "survey_spec"]
            },
        }

    def all(self, path):
        parsed = urlsplit(path)
        endpoint = parsed.path.removeprefix("/api/controller/v2/").strip("/")
        query = parse_qs(parsed.query)
        if endpoint == "me":
            return [{"id": 3 + self.offset, "is_superuser": self.admin}]
        if endpoint == "organizations":
            return [{"id": 1 + self.offset, "name": "Fixture organization"}]
        if endpoint == "projects":
            return [
                {
                    "id": 11 + self.offset,
                    "name": "Source project",
                    "scm_url": "https://git.example.invalid/source.git",
                }
            ]
        if endpoint == "job_templates":
            return deepcopy(self.jobs)
        if endpoint == "labels":
            return [{"id": 9 + self.offset, "name": query["name"][0]}]
        if endpoint.startswith("job_templates/") and endpoint.endswith("/labels"):
            return [{"id": 9 + self.offset, "name": "owned-label"}]
        if endpoint.startswith("job_templates/") and endpoint.endswith("/credentials"):
            if self.incomplete_relationship:
                raise core.CaptureError("Relationship access denied.")
            return []
        raise AssertionError("Unexpected fixture endpoint: " + endpoint)

    def get(self, path):
        if path.startswith("projects/"):
            return self.all("projects/")[0]
        if path.endswith("/survey_spec/"):
            return {
                "name": "",
                "description": "",
                "spec": [{"variable": "choice", "type": "text", "default": ""}],
            }
        raise AssertionError("Unexpected fixture GET: " + path)


class SnapshotTests(unittest.TestCase):
    def test_removed_association_does_not_imply_deleted_owned_credential(self):
        import json

        class CredentialAPI(FakeAPI):
            associated = True
            exists = True

            def credential(self):
                return {
                    "id": 41,
                    "name": "Owned credential",
                    "organization": 1,
                    "credential_type": 2,
                    "inputs": {"password": "$encrypted$"},
                }

            def all(self, path):
                endpoint = (
                    urlsplit(path).path.removeprefix("/api/controller/v2/").strip("/")
                )
                if endpoint == "credentials":
                    return [self.credential()] if self.exists else []
                if endpoint.startswith("job_templates/") and endpoint.endswith(
                    "/credentials"
                ):
                    return [self.credential()] if self.associated else []
                return super().all(path)

            def get(self, path):
                if path.startswith("credentials/"):
                    return self.credential()
                if path.startswith("credential_types/"):
                    return {
                        "name": "Vault",
                        "managed": True,
                        "inputs": {"fields": [{"id": "password", "secret": True}]},
                    }
                return super().get(path)

        api = CredentialAPI()
        scope = self.scope()
        scope["dependency_names"] = {"credentials": ["Owned credential"]}
        before = snapshot.Snapshot(api, scope, json.loads).collect()
        api.associated = False
        after = snapshot.Snapshot(api, scope, json.loads).collect()
        self.assertEqual(before["credentials"], after["credentials"])
        self.assertTrue(
            core.semantic_diff(before["job_templates"], after["job_templates"])
        )
        api.exists = False
        self.assertEqual(
            snapshot.Snapshot(api, scope, json.loads).collect()["credentials"], {}
        )
        api.exists = True
        api.associated = True
        scope["aliases"]["credentials"] = {"Owned credential": "Portable credential"}
        scope["external_dependencies"] = {"credentials": ["Portable credential"]}
        projected = snapshot.Snapshot(api, scope, json.loads).collect()
        self.assertEqual(projected["credentials"], {})
        self.assertEqual(
            next(iter(projected["job_templates"].values()))["credentials"],
            ["Portable credential"],
        )

    def scope(self):
        return {
            "organization": "Fixture organization",
            "project_names": ["Source project"],
            "owned_labels": ["owned-label"],
            "max_job_templates": 10,
            "aliases": {"projects": {"Source project": "Desired project"}},
            "sections": {
                "job_templates": [],
                "projects": [],
                "labels": [],
                "credentials": [],
                "inventories": [],
                "execution_environments": [],
            },
        }

    def capture(self, api):
        import json

        return snapshot.Snapshot(api, self.scope(), json.loads).collect()

    def test_new_job_is_discovered_and_runtime_ids_timestamps_are_irrelevant(self):
        first = self.capture(FakeAPI())
        second = self.capture(FakeAPI(100))
        self.assertEqual(first, second)
        self.assertEqual(len(first["job_templates"]), 2)
        self.assertEqual(
            {item["project"] for item in first["job_templates"].values()},
            {"Desired project"},
        )
        self.assertNotIn("modified", next(iter(first["job_templates"].values())))

    def test_no_admin_or_incomplete_relationship_never_implies_deletion(self):
        api = FakeAPI()
        api.admin = False
        with self.assertRaises(core.CaptureError):
            self.capture(api)
        api.admin = True
        api.incomplete_relationship = True
        with self.assertRaises(core.CaptureError):
            self.capture(api)

    def test_confirmed_complete_project_job_absence_produces_empty_scope(self):
        api = FakeAPI()
        api.jobs = []
        self.assertEqual(self.capture(api)["job_templates"], {})

    def test_workflow_subtype_gets_and_named_edges_detect_real_relationship_removal(
        self,
    ):
        import json

        class WorkflowAPI(FakeAPI):
            edge_present = True

            def all(self, path):
                endpoint = (
                    urlsplit(path).path.removeprefix("/api/controller/v2/").strip("/")
                )
                if endpoint == "workflow_job_templates":
                    return [
                        {
                            "id": 88,
                            "name": "Fixture graph",
                            "description": "",
                            "survey_enabled": False,
                            "extra_vars": "{}",
                            "inventory": None,
                            "related": {
                                "labels": "workflow_job_templates/88/labels/",
                                "workflow_nodes": "workflow_job_templates/88/workflow_nodes/",
                            },
                        }
                    ]
                if endpoint == "workflow_job_templates/88/labels":
                    return [{"id": 9, "name": "owned-label"}]
                if endpoint == "workflow_job_templates/88/workflow_nodes":
                    return [
                        {
                            "id": identity,
                            "identifier": name,
                            "unified_job_template": job,
                            "summary_fields": {
                                "unified_job_template": {"unified_job_type": "job"}
                            },
                            "extra_data": {"choice": True},
                            "all_parents_must_converge": False,
                            "inventory": None,
                            "related": {
                                key: f"workflow_job_template_nodes/{identity}/{key}/"
                                for key in [
                                    "success_nodes",
                                    "failure_nodes",
                                    "always_nodes",
                                    "credentials",
                                    "labels",
                                    "instance_groups",
                                ]
                            },
                        }
                        for identity, name, job in [(900, "one", 71), (901, "two", 72)]
                    ]
                if endpoint.startswith("workflow_job_template_nodes/"):
                    return (
                        [{"id": 901}]
                        if self.edge_present and endpoint.endswith("900/success_nodes")
                        else []
                    )
                return super().all(path)

            def get(self, path):
                if path.startswith("job_templates/"):
                    return {
                        "type": "job_template",
                        "name": (
                            "Original job" if "/71/" in path else "New discovered job"
                        ),
                    }
                return super().get(path)

        api = WorkflowAPI()
        scope = self.scope()
        scope["sections"]["workflows"] = []
        before = snapshot.Snapshot(api, scope, json.loads).collect()
        api.edge_present = False
        after = snapshot.Snapshot(api, scope, json.loads).collect()
        changes = core.semantic_diff(before, after)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["operation"], "removal")
        self.assertEqual(
            next(iter(after["workflows"].values()))["workflow_nodes"][0]["extra_data"],
            {"choice": True},
        )


if __name__ == "__main__":
    unittest.main()
