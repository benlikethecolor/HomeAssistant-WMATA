# Upgrading to version 4

Version 4 replaces numbered train/bus sensors and per-line duplicates with one Arrivals board per location. Saved journeys provide optional filtered sensors.

## Before installing

1. Back up Home Assistant.
2. Record old sensor references in dashboards and automations.
3. Confirm HA is at least 2026.11.1.

## Install and migrate

1. Update through HACS or replace custom_components/wmata.
2. Restart HA, then refresh the browser.
3. Open Settings → Devices & services → WMATA.
4. Find each station/stop's new Arrivals entity.
5. Replace old cards with WMATA Station Board cards.
6. Add journeys and update arrival-based automations to their sensors.

API keys, locations and polling intervals are preserved. Global line/route filters are removed so each board contains the complete location. Numbered entities are removed from the registry automatically. Update references to those entities.

Version-1 config entries migrate to version 2 during setup. Existing version-4 boards retain their identities.

Legacy entries for separate platform codes at the same transfer station remain separate and each covers both platforms. Consolidate manually after updating dashboards if desired.

The systemwide map is an additional WMATA entry. Add it by selecting Systemwide train map, then add its card.

## Roll back

Restore the previous integration files and your pre-upgrade HA backup together. This restores config-entry and registry state. Downgrading only the Python files does not restore removed numbered entities.
