"""Build the same integration-only archive used by installation tests."""

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "manifest.json",
    "__init__.py",
    "config_flow.py",
    "sensor.py",
    "directions.py",
    "websocket.py",
    "geo_shapes.json",
    "route_shapes.json",
    "strings.json",
    "translations/en.json",
    "www/wmata-station-card.js",
    "www/system-map.png",
    "www/geo_routes.json",
    "www/vendor/leaflet.js",
    "www/vendor/leaflet.css",
    "www/vendor/LEAFLET-LICENSE",
}


def build(output):
    source = ROOT / "custom_components" / "wmata"
    files = [
        path
        for path in source.rglob("*")
        if path.is_file()
        and not any(
            part.startswith(".") or part == "__pycache__"
            for part in path.relative_to(source).parts
        )
        and path.suffix != ".pyc"
    ]
    missing = REQUIRED - {str(path.relative_to(source)) for path in files}
    if missing:
        raise ValueError(f"Missing release assets: {sorted(missing)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(
                path, Path("custom_components/wmata") / path.relative_to(source)
            )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.output))
