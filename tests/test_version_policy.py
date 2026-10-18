"""Exercise version maintenance through its public command-line interface."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HELPER = Path(__file__).resolve().parents[1] / "src" / "bump-version.py"


class VersionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "src").mkdir()
        self.helper = self.root / "src" / "bump-version.py"
        shutil.copyfile(HELPER, self.helper)
        self.version = self.root / "VERSION"

    def run_helper(self, *arguments):
        return subprocess.run(
            [sys.executable, str(self.helper), *arguments],
            cwd=self.root / "src",
            capture_output=True,
            text=True,
            check=False,
        )

    def test_patch_increment_uses_project_file_from_another_directory(self):
        self.version.write_text("0.0.1\n")
        unrelated_version = self.root / "src" / "VERSION"
        unrelated_version.write_text("9.9.9\n")

        result = self.run_helper()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.version.read_text(), "0.0.2\n")
        self.assertEqual(unrelated_version.read_text(), "9.9.9\n")
        self.assertEqual(result.stdout, "0.0.2\n")

    def test_feature_increment_resets_patch(self):
        self.version.write_text("0.2.7\n")

        result = self.run_helper("--feature")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.version.read_text(), "0.3.0\n")

    def test_invalid_version_is_rejected_without_rewriting_it(self):
        for value in ("0.1\n", "0.-1.2\n", "0.1.2-extra\n"):
            with self.subTest(value=value):
                self.version.write_text(value)

                result = self.run_helper()

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.version.read_text(), value)
                self.assertIn("major.minor.patch", result.stderr)

    def test_missing_version_is_rejected_without_creating_one(self):
        result = self.run_helper()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.version.exists())


if __name__ == "__main__":
    unittest.main()
