"""Release preparation must reject wrong versions before building an archive."""

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTest(unittest.TestCase):
    def prepare(self, tag, directory):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/prepare_release.py"),
                "--tag",
                tag,
                "--output-dir",
                directory,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_matching_version_builds_complete_archive_and_upgrade_notes(self):
        version = json.loads(
            (ROOT / "custom_components/wmata/manifest.json").read_text()
        )["version"]
        with tempfile.TemporaryDirectory() as folder:
            result = self.prepare(f"v{version}", folder)
            self.assertEqual(result.returncode, 0, result.stderr)
            metadata = json.loads(result.stdout)
            with zipfile.ZipFile(metadata["archive"]) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn(
                    "custom_components/wmata/diagnostics.py", archive.namelist()
                )
                self.assertTrue(
                    all(
                        p.startswith("custom_components/wmata/")
                        for p in archive.namelist()
                    )
                )
            self.assertIn("numbered sensors", Path(metadata["notes"]).read_text())

    def test_bad_or_mismatched_tags_create_no_artifacts(self):
        for tag in ("v0.0.0", "main", "v3.0.0;echo bad", "../v3.0.0"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as folder:
                self.assertNotEqual(self.prepare(tag, folder).returncode, 0)
                self.assertEqual(list(Path(folder).iterdir()), [])
