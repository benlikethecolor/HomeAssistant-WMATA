# 4.6.3 — station-specific travel directions

Station boards and map station-arrival popups now show Eastbound, Westbound, Northbound or Southbound instead of platform group numbers. Directions follow the station, line and destination along the route. The same destination can have different labels along a curved line.

New rail journeys can filter by travel direction. Normalized arrivals expose direction, next_station and next_station_code. Existing raw group attributes and saved group filters remain supported; editing a legacy journey replaces its group filter with the selected direction filter.

Unknown or terminating travel directions are shown as unavailable instead of guessing from a track number. Mount Vernon Square destination abbreviations are also expanded.

See [the station coverage reference](RAIL_DIRECTIONS.md) for the direction conventions and all station/line pairings.

Validation: 36 Python tests, 13 card tests, Ruff and whitespace checks passed. A live all-station snapshot resolved all 559 passenger-service predictions; the five remaining predictions were marked No Passenger and were left without a direction. Official hassfest validation passed. Authenticated HACS validation remains assigned to GitHub Actions on push.
