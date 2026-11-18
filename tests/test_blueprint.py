"""The blueprint file must be importable and internally consistent.

tools/verify_installation.py runs it for real on Home Assistant; this is the
quick check that every input is declared and used.
"""

import unittest
from pathlib import Path

import yaml

PATH = "blueprints/automation/wmata/time_to_leave.yaml"
FILE = Path(__file__).resolve().parents[1] / PATH


class Loader(yaml.SafeLoader):
    """Collect the names referenced through !input."""

    used: set[str]


def _input(loader, node):
    loader.used.add(node.value)
    return f"!input {node.value}"


Loader.add_constructor("!input", _input)


class BlueprintTest(unittest.TestCase):
    def test_inputs_are_declared_used_and_documented(self):
        Loader.used = set()
        data = yaml.load(FILE.read_text(), Loader=Loader)  # noqa: S506
        blueprint = data["blueprint"]
        self.assertEqual(blueprint["domain"], "automation")
        self.assertTrue(blueprint["source_url"].endswith(PATH))
        inputs = blueprint["input"]
        self.assertEqual(Loader.used, set(inputs))
        for name, definition in inputs.items():
            with self.subTest(name):
                self.assertTrue(definition.get("name"))
                self.assertIn("selector", definition)
        # Only the sensor to watch is required; everything else has a default.
        self.assertEqual(
            [
                name
                for name, definition in inputs.items()
                if "default" not in definition
            ],
            ["next_train"],
        )
        self.assertEqual(data["mode"], "single")
        self.assertEqual(data["max_exceeded"], "silent")
        self.assertEqual({"triggers", "conditions", "actions"} - set(data), set())
