"""Every setup screen needs text; a missing key shows users a raw identifier."""

import json
import re
import unittest
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "wmata"
SOURCE = (COMPONENT / "config_flow.py").read_text()
STRINGS = json.loads((COMPONENT / "strings.json").read_text())


class StringsTest(unittest.TestCase):
    def test_english_translation_matches_strings(self):
        self.assertEqual(
            STRINGS, json.loads((COMPONENT / "translations" / "en.json").read_text())
        )

    def test_every_step_error_and_abort_reason_has_text(self):
        setup, options = SOURCE.split("class WmataOptionsFlow")
        for section, code in (("config", setup), ("options", options)):
            text = STRINGS[section]
            # Reauthentication starts in a step that only forwards to its form.
            steps = set(re.findall(r"async def async_step_(\w+)", code)) - {"reauth"}
            self.assertEqual(steps, set(text["step"]), section)
            for step in steps:
                self.assertTrue(text["step"][step].get("title"), step)
            errors = set(re.findall(r'errors\[[^\]]+\] = "(\w+)"', code))
            self.assertEqual(errors, set(text["error"]), section)
            aborts = set(re.findall(r'reason="(\w+)"', code)) | set(
                re.findall(r'"(\w+_successful)"', code)
            )
            self.assertEqual(aborts, set(text["abort"]), section)
        # Each menu choice opens an options step and is listed in the menu itself.
        for choice in STRINGS["options"]["step"]["init"]["menu_options"]:
            self.assertIn(f"async def async_step_{choice}", options)
            self.assertIn(f'"{choice}"', options.split("menu_options=")[1])

    def test_description_placeholders_are_supplied_by_the_flow(self):
        for section in ("config", "options"):
            for name, step in STRINGS[section]["step"].items():
                for placeholder in re.findall(r"{(\w+)}", step.get("description", "")):
                    with self.subTest(step=name, placeholder=placeholder):
                        self.assertIn(f'"{placeholder}":', SOURCE)
