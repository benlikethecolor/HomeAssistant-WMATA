"""Separate processes ensure installation uses the ZIP rather than imported source."""

import subprocess
import sys
import unittest
from pathlib import Path


class InstallationTest(unittest.TestCase):
    def test_clean_install_from_archive(self):
        self.verify("clean")

    def test_upgrade_from_version_one(self):
        self.verify("upgrade")

    def verify(self, scenario):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                sys.executable,
                str(root / "tools/verify_installation.py"),
                "--scenario",
                scenario,
            ],
            cwd="/tmp",
            capture_output=True,
            check=False,
            text=True,
            timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"result": "passed"', result.stdout)
