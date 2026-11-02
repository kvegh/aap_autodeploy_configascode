import importlib.util
from pathlib import Path
import unittest
from jinja2 import Environment, StrictUndefined

SPEC = importlib.util.spec_from_file_location(
    "cac_source_credential",
    Path(__file__).resolve().parents[1] / "src/cac_source_credential.py",
)
schema = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(schema)


class SourceCredentialTests(unittest.TestCase):
    def test_controller_single_file_schema_and_optional_rendering(self):
        definition = schema.definition()
        injectors = definition["injectors"]
        self.assertIsInstance(injectors["file"]["template"], str)
        self.assertNotIn("source_ca_pem", definition["inputs"]["required"])
        environment = Environment(undefined=StrictUndefined)
        template = environment.from_string(injectors["env"]["AAP_CAC_SOURCE_CA_FILE"])
        values = {
            "source_url": "https://source.example.invalid",
            "api_token": "fixture-canary",
            "tower": {"filename": "/runner/private-source-ca"},
        }
        self.assertEqual(template.render(**values), "")
        self.assertEqual(template.render(**values, source_ca_pem=""), "")
        self.assertEqual(
            template.render(**values, source_ca_pem="fixture-ca"),
            "/runner/private-source-ca",
        )
        file_template = environment.from_string(injectors["file"]["template"])
        self.assertEqual(file_template.render(**values), "")
        self.assertEqual(
            file_template.render(**values, source_ca_pem="fixture-ca"), "fixture-ca"
        )


if __name__ == "__main__":
    unittest.main()
