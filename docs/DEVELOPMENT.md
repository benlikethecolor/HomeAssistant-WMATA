# Development

Notes for working on the integration itself. If you only want to use it, the [README](../README.md) has everything you need.

## What's where

- `custom_components/wmata/` is the integration. The dashboard cards live in `www/wmata-station-card.js` as a single file with no build step, next to a vendored copy of Leaflet.
- `tests/` has the Python tests (plain `unittest`) and `test_card.mjs` for the cards.
- `tools/` has the release packaging, the install check that the tests run, and the map geometry generators.
- `scripts/` is a handful of standalone scripts for poking at the WMATA API by hand: raw predictions for a station or stop, stops near a point, and a generator for the station lists. They aren't part of the integration and only need the standard library. Set `WMATA_API_KEY` in your environment and run any of them with `--help`.

## Running the tests

The Python tests import Home Assistant, so the easiest way to run them is inside the HA container:

```sh
docker run --rm -v "$PWD:/work" -w /work --entrypoint python \
  ghcr.io/home-assistant/home-assistant:2024.12.5 \
  -m unittest discover -s tests -v
```

Leave Docker on its default bridge network. HA's DNS resolver wants a network interface even though the tests never talk to WMATA.

If you'd rather not use Docker, a virtualenv with `homeassistant` installed works as well. Pin a release that supports your Python version. The suite passes that way on Python 3.13 with `homeassistant==2025.6.3`, though that combination also needs `pycares<5`.

The two installation tests are the slow ones and the most useful. They build the release ZIP, unpack it into a temporary config directory, and boot a real Home Assistant against the canned responses in `tests/fixtures/`. One sets everything up from scratch through the config flow. The other starts from a 2.x entry and checks the migration. No API key or real config is involved.

Linting, the card tests, and a local ZIP:

```sh
python3 -m pip install -r requirements-dev.txt
ruff check .
ruff format --check .
npm ci
npm run format:check
npm test
python3 tools/build_release.py --output /tmp/wmata.zip
```

CI runs the Python tests against HA 2024.12.5, 2025.6.3, 2026.1.3, and the current stable image, plus hassfest and the HACS validator. None of that touches the real API, so before a release it's worth installing the build on a real instance and clicking through setup and all three cards with your own key.

## Releasing

1. Merge to `main`.
2. Set the same version in `manifest.json` and `CARD_VERSION` in `const.py`. The card version is the cache-busting query string on the JavaScript, so if it doesn't change, browsers keep the old cards.
3. Push a matching tag, such as `v3.0.0`. The tag has to point at a commit on `main`.

The **Prepare release** workflow then runs the tests and validators, builds the ZIP, and creates a draft release with an upgrade note. Read the draft over and publish it yourself. HACS only sees published releases.

The workflow can also be started by hand. With **create_draft** unchecked it builds and validates without creating a release. With it checked, it creates the draft for a tag that already exists. Either way the tag, manifest version, and card version have to agree or it stops.

Dependabot opens weekly PRs for the GitHub Actions, the npm dev tools, and ruff. Leaflet is vendored and updated by hand. When you replace it, keep its license file and run the card tests.

## How journeys work

### Choosing a route

`journeys.py` plans over the standard service patterns in `directions.py`. It looks for the fewest transfers first and the fewest stops second. Only junctions where lines actually diverge are considered as transfer points, since changing trains at a station where both lines continue along the same track gets you nothing.

A saved journey filters its origin station's board down to trains whose reported destination is at or beyond the end of the first leg. A diverted or short-turning train counts if it really does reach that stop. The planner never suggests a route that depends on a diversion, though.

The journey's sensor is always the wait for the next train at the origin. Everything about transfers and arrival times is worked out by the card.

### Estimating arrival

The card puts an itinerary together from three things:

- Live departures at the origin and at each transfer, each with the time its snapshot was taken, so an older snapshot isn't treated as fresh.
- Scheduled ride times from WMATA's station-to-station endpoint. These are summed stop by stop along the saved route, because the endpoint's own figure for two distant stations may assume a different path.
- The platform-change allowance, three minutes unless the user changes it.

Each leg after the first starts from the first train you could actually catch, which is your arrival at the transfer plus the allowance. The destination time is the last leg's departure plus its ride. Transfer waits and platform time are already contained in that departure, so they aren't added again. A direct journey is simply the origin departure plus the ride.

The summary shows the trip two ways: from boarding to destination, and from now, which adds the wait for the first train.

When someone picks a specific origin train with **Use this train**, the card has to find that train again after each refresh. WMATA's predictions have no train IDs, so it matches on line, destination, track group, car count, and a predicted departure within 90 seconds of the expected one. If nothing matches, or more than one train does, the user is asked to choose again.

### Falling back to the timetable

Live predictions only cover the next few trains on each line. Within that window they always win. Past it, connections come from WMATA's rail GTFS feed and are labeled as schedule estimates in the card.

`schedules.py` reads the feed with service days in America/New_York. It handles calendar additions and removals, the stop IDs for each platform of a transfer station, pickup and drop-off restrictions, and service times after midnight (a 25:10 departure belongs to the previous service day). Trips defined only by a frequency are skipped, because they aren't real departure times. Nothing is estimated outside the feed's validity dates. If service has ended for the day or the feed has expired, the time stays unknown.

The feed is downloaded at most once every six hours per API key, and again when the service day rolls over. It's parsed in the executor, size-limited, and backed off for five minutes after a failure.

### The trip planner card

The planner uses two WebSocket commands, `wmata/planner_stations` and `wmata/plan_trip`. The caller passes an entity ID for a rail station or the train map. The server checks that the user can read that entity and uses its entry's API key, so the browser never handles a key. Nothing is saved and no entities are created.

On the server, `candidate_journeys` lists every loop-free route with up to three transfers. Predictions for all the stations involved are fetched in one request, minus anything already cached, and each distinct leg is filtered once even when several routes share it.

Ranking happens in the browser with the same connection calculator the journey card uses. All routes are compared at the same moment and with the user's platform allowance. On each leg it takes the catchable train that reaches the next stop earliest, which isn't always the first one to leave. Routes are ordered by arrival time. Ties go to the route with more live data, then to the one with fewer changes.

A route or departure the user picks by hand stays selected until they reset it. The comparison list keeps showing each route's automatic best so the numbers stay comparable.

### Commute sensors

A commute entry (`commute.py`) plans both directions on every poll. It collects the boarding stations of every candidate route in both directions, fetches their predictions in one request, and hands the result to the same route assembly the trip planner uses (`trip_alternatives` in `websocket.py`).

The arrival estimate itself is `estimates.py`, a Python port of the card's connection calculator. Two implementations of the same rules will drift unless something holds them together, so `tests/fixtures/estimates.json` lists scenarios as minute offsets and both `tests/test_estimates.py` and `tests/test_card.mjs` run every one of them. When you change how connections are worked out, change both and add a scenario.

The sensors always follow the route with the earliest estimated arrival. There is no per-train selection as there is on the card.

### Requests and caching

- Journey sensors read from the origin station's coordinator. They add no requests.
- A commute entry makes one prediction request per poll for all of its stations, and reuses the 30-second cache and any recently polled station entry like everything else.
- Transfer boards come from `wmata/journey_arrivals`, which is only called while a card is open. The server looks the route up from the entity the user is allowed to read, so a client can't ask for arbitrary stations through it. The results never become entity state, which keeps them out of the recorder.
- Station predictions requested on demand are cached for 30 seconds per API key and shared between journey cards, the planner, and the map's station popups. If a configured station was polled within the last 30 seconds, that poll is reused.
- Ride times are cached for a day per API key, with a five-minute backoff after a failure.
- The destination summary and the transfer boards can be switched off separately. The request keeps running as long as either is on.

## Rail directions

`directions.py` works out a direction from where the train is and where it's heading along its route. Orange and Silver are east/west, and Green and Yellow are north/south. Blue and Red change partway:

- Blue is north/south on its Virginia branch and east/west through downtown. At Rosslyn, a train toward Franconia-Springfield is southbound and one toward downtown is eastbound.
- Red is north/south on both outer legs and east/west between Metro Center, Gallery Place, and Judiciary Square.

These labels describe travel. They aren't official platform or track numbers, and the `Group` field in WMATA's predictions isn't used to derive them. A train with an unrecognized destination, or one terminating at the current station, gets no label.

The tests check every station and line pairing, the transfer stations, short turns, and both eastern branches for Orange, Blue, and Silver.

Older saved filters that match on `group` still work. Editing one in the UI swaps the track filter for a direction filter.

## Rebuilding the map geometry

The source URLs are in [GEO_SOURCES.md](../custom_components/wmata/GEO_SOURCES.md), which ships with the integration. Both generators list their arguments with `--help`.

- `tools/build_geographic_geometry.py` needs only the standard library. It takes the station list from the API, the rail and Silver Line extension GIS layers (requested with `outSR=4326`), the schematic shapes, and the station anchor points, and writes `geo_shapes.json` and `www/geo_routes.json`.
- `tools/build_schematic_geometry.py` traces the official map PDF. It needs PyMuPDF, NumPy, Pillow, SciPy, and scikit-image, along with the station anchors and a JSON list of `[line_code, ordered_station_codes]` pairs. The PDF's hash is pinned in the script, because new artwork changes the drawing IDs it relies on.

Write the output to a temporary directory first, diff it against the bundled JSON, and look at both map views before replacing anything. Keep the data and Leaflet attribution files with the integration.
