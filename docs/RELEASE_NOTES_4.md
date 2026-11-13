# WMATA 4 — arrival boards, saved journeys and live train maps

Version 4 introduces one complete arrival board per station/stop, optional journey sensors and a bundled systemwide map.

**Requires HA 2026.11.1 or newer. This is a breaking update for numbered sensors.**

Old numbered and per-line duplicate entities are replaced automatically. Keys, locations and polling intervals are preserved. Update dashboards to WMATA Station Board cards and use journey sensors for filtered automations. Read [the upgrade guide](UPGRADING.md) first.

## Included

- Multiple stations/stops, including both platforms at transfer stations.
- Boards and journeys reporting minutes until the next matching arrival.
- Automatic card loading, visual editors, expanded destinations and arrival-status labels.
- OpenStreetMap with the official diagram as an optional view.
- Train and station-arrival popups, automatic dark mode, sizing controls and refresh timestamps.
- Endpoint-access validation, pacing, rate-limit recovery and reauthentication.

Add Systemwide train map as an additional WMATA entry. Its station popups work without creating every station entry. Arrival automations use station or journey sensors.

Positions remain estimates from circuit occupancy and bundled geometry. See [the setup guide](../README.md) for installation, YAML, automations and troubleshooting.
