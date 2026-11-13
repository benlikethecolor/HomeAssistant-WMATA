# Development and release verification

The declared minimum is HA 2026.11.1. CI tests it and the stable image. Node 22+ runs the card tests.

## Tests

From the repository root:

    docker run --rm -v "$PWD:/work" -w /work --entrypoint python       ghcr.io/home-assistant/home-assistant:2026.11.1       -m unittest discover -s tests -v

    npm ci
    npm test

Installation tests build a ZIP, extract it into a temporary config directory, and run real HA config/options flows with fixture API responses. Each scenario runs in its own process. Clean setup covers rail, bus, network map and a journey. Upgrade starts with a version-1 entry and numbered entity. Both check registration, frontend assets, unload and reload.

Use Docker's default private bridge. HA's DNS resolver needs an interface even when API responses are mocked. No host ports, production configuration or real API keys are required.

## Packaging and validators

    python3 tools/build_release.py --output /tmp/wmata.zip

The ZIP contains only integration files under custom_components/wmata. Required scripts, translations, geometry, map image, Leaflet and its license are checked. HACS installs from the repository. Manual users can extract the archive into HA's configuration directory.

Local hassfest:

    docker run --rm -v "$PWD:/github/workspace" ghcr.io/home-assistant/hassfest

CI also runs the official HACS validator with GitHub's supplied token. If no token is available locally, that authenticated check runs when pushed. Python/card tests do not substitute for it.

## Rebuilding geometry

Source URLs are in custom_components/wmata/GEO_SOURCES.md. Generator inputs contain public data only.

Geographic generation uses standard-library Python:

    python3 tools/build_geographic_geometry.py       --stations /tmp/stations.json       --rail /tmp/rail.json       --extension /tmp/extension.json       --schematic-shapes custom_components/wmata/route_shapes.json       --anchors custom_components/wmata/schematic.py       --output /tmp/generated-wmata

The station file is the station catalog's array of objects. Rail and extension files are ArcGIS JSON FeatureSets with outSR=4326, all fields and geometries.

Schematic generation requires developer-only PyMuPDF, NumPy, Pillow, SciPy and scikit-image:

    python3 tools/build_schematic_geometry.py       --pdf /tmp/system-map-rail.pdf       --anchors custom_components/wmata/schematic.py       --routes /tmp/route-stations.json       --output /tmp/generated-wmata/route_shapes.json

The route-stations file is an array of pairs containing LineCode and its ordered station codes. The PDF's SHA-256 is verified because drawing IDs change between artwork revisions. For revised artwork, inspect drawing IDs and station anchors before updating the expected hash.

Compare generated JSON with bundled assets, inspect coverage and bends, and copy reviewed outputs into the integration. The current three assets reproduce exactly from their source data.

## Release checklist

- Run Python/card tests, including packaged clean installation and upgrade.
- Run hassfest and authenticated HACS validation.
- Check setup with a live subscription covering the required endpoints.
- Check boards, map, popups, themes and narrow layouts in a browser.
- Review migration notes and version.
- Include media/vendor attribution.
- Attach the validated ZIP if providing a manual-install release archive.

Fixture scenarios make setup tests deterministic. Check a live subscription before publishing because endpoint permissions and service availability can change.
