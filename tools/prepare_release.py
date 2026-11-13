"""Check release versions and build an integration ZIP and short release notes."""

import argparse
import json
import re
from pathlib import Path

from build_release import ROOT, build


def prepare(tag: str, output: Path) -> dict[str, str]:
    """Only accept a version tag matching both the backend and bundled card."""
    manifest = json.loads((ROOT / "custom_components/wmata/manifest.json").read_text())
    version = manifest["version"]
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.?\d+)?", tag):
        raise ValueError("Use a version tag such as v4.6.3 or v4.7.0-beta.1")
    if tag != f"v{version}":
        raise ValueError("Release tag must match manifest.json version")
    constants = (ROOT / "custom_components/wmata/const.py").read_text()
    card = re.search(r'^CARD_VERSION = "([^"]+)"$', constants, re.MULTILINE)
    if not card or card[1] != version:
        raise ValueError("CARD_VERSION must match manifest.json version")
    minimum = json.loads((ROOT / "hacs.json").read_text())["homeassistant"]
    archive = build(output / f"wmata-{version}.zip")
    notes = output / "release-notes.md"
    body = f"Requires Home Assistant {minimum} or newer.\n\n"
    if version.startswith("4."):
        body += (
            "Upgrading from 2.x: numbered sensors are replaced by arrival boards. "
            "Update dashboard and automation entity references after upgrading.\n\n"
        )
    body += (
        "[Installation and upgrade instructions]"
        "(https://github.com/benlikethecolor/HomeAssistant-WMATA#upgrading).\n"
    )
    notes.write_text(body)
    return {
        "tag": tag,
        "version": version,
        "archive": str(archive),
        "notes": str(notes),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.tag, args.output_dir)))
