# Development

## Tests and packaging

Run the backend tests in an HA container:

~~~sh
docker run --rm -v "$PWD:/work" -w /work --entrypoint python \
  ghcr.io/home-assistant/home-assistant:2026.11.1 \
  -m unittest discover -s tests -v
~~~

The installation tests extract a release ZIP into a temporary HA config and exercise setup, migration, and reload with fixture API responses. Use Docker's default bridge; HA's DNS resolver needs a network interface even with mocked responses. No production config or API key is needed.

For the card tests and a manual-install ZIP:

~~~sh
python3 -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
npm ci
npm run format:check
npm test
python3 tools/build_release.py --output /tmp/wmata.zip
~~~

CI runs the tests on HA 2026.11.1 and stable, plus hassfest and HACS validation. Before releasing, also try setup and the cards against a live WMATA subscription.

## Releases and dependency updates

After merging to main, update `manifest.json` and `CARD_VERSION` together, then push a matching tag such as `v4.6.3`. **Prepare release** runs the tests and validators, builds a ZIP, and creates a draft release with upgrade notes. Review the draft before publishing it. Tags must point to a commit on main.

For a build without a release, run the workflow manually with **create_draft** unchecked. To create a draft manually, run it on the existing version tag with **create_draft** checked. The tag, manifest, and card versions must match.

Dependabot checks Actions, npm tools, and the Python linter weekly after this configuration reaches the default branch. Bundled Leaflet is updated manually; keep its license and run the card tests when replacing it.

## Rail directions

`directions.py` resolves the station and destination on the train's route. It uses east/west for Orange and Silver, north/south for Green and Yellow, and changes direction along the Blue and Red corridors:

- Blue uses north/south on its Virginia branch and east/west through downtown. At Rosslyn, trains toward Franconia-Springfield are southbound and trains toward downtown are eastbound.
- Red uses north/south on the outer legs and east/west through Metro Center, Gallery Place, and Judiciary Square.

These are derived travel labels, not official platform numbers. Prediction `Group` values don't determine direction. Unknown destinations and trains terminating at the current station have no direction label. The tests cover every station/line pairing, transfers, short turns, and either eastern branch for Orange/Blue/Silver service.

Raw `group` attributes and existing group-filtered journeys still work. Editing one of those journeys replaces the track filter with the selected direction filter.

## Rebuilding map geometry

[Source URLs](../custom_components/wmata/GEO_SOURCES.md) are kept with the integration. The generators' `--help` output lists their arguments.

- `tools/build_geographic_geometry.py` takes the station catalog array, rail and extension GIS FeatureSets (`outSR=4326`), schematic shapes, and station anchors. It writes `geo_shapes.json` and `www/geo_routes.json` using standard-library Python.
- `tools/build_schematic_geometry.py` takes the official PDF, station anchors, and a JSON array of `[line_code, ordered_station_codes]` pairs. It needs PyMuPDF, NumPy, Pillow, SciPy, and scikit-image. The PDF hash is pinned because artwork changes can invalidate the drawing IDs.

Generate into a temporary directory, compare with the bundled JSON, and inspect the map before replacing assets. Keep data and vendor attribution with the integration.
