import importlib.util
from pathlib import Path
import unittest
from jinja2 import Environment, StrictUndefined, UndefinedError

SPEC = importlib.util.spec_from_file_location(
    "cac_source_credential",
    Path(__file__).resolve().parents[1] / "src/cac_source_credential.py",
)
schema = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(schema)


class SourceCredentialTests(unittest.TestCase):
    def test_used_reader_schema_remains_independent_from_ca_attachment(self):
        reader = schema.definition()
        ca = schema.ca_definition()
        self.assertEqual(
            [f["id"] for f in reader["inputs"]["fields"]], ["source_url", "api_token"]
        )
        self.assertNotIn("file", reader["injectors"])
        self.assertNotIn("AAP_CAC_SOURCE_CA_FILE", reader["injectors"]["env"])
        self.assertEqual(ca["inputs"]["required"], ["source_ca_pem"])
        self.assertTrue(
            set(reader["injectors"]["env"]).isdisjoint(ca["injectors"]["env"])
        )
        injectors = ca["injectors"]
        self.assertIsInstance(injectors["file"]["template"], str)
        environment = Environment(undefined=StrictUndefined)
        filename = "/runner/private-source-ca"
        values = {
            "source_ca_pem": "fixture-existing-ca",
            "tower": {"filename": filename},
        }
        self.assertEqual(
            environment.from_string(injectors["env"]["AAP_CAC_SOURCE_CA_FILE"]).render(
                **values
            ),
            filename,
        )
        self.assertEqual(
            environment.from_string(injectors["file"]["template"]).render(**values),
            "fixture-existing-ca",
        )
        with self.assertRaises(UndefinedError):
            environment.from_string(injectors["file"]["template"]).render(
                tower={"filename": filename}
            )


if __name__ == "__main__":
    unittest.main()
