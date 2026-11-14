"""Download support information without credentials or selected locations."""

from collections import Counter
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant

from .const import CARD_VERSION, CONF_JOURNEYS, LINE_NAME_MAP


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return an allowlisted snapshot, never raw config or API payloads."""
    coordinator = getattr(entry, "runtime_data", None)
    service = entry.data.get("service_type")
    result = {
        "home_assistant_version": HA_VERSION,
        "integration_version": CARD_VERSION,
        "service": service
        if service in ("train", "bus", "map", "commute")
        else "unknown",
        "config_entry_version": entry.version,
        "config_entry_state": entry.state.value,
        "journey_count": len(entry.options.get(CONF_JOURNEYS, [])),
        "coordinator_loaded": coordinator is not None,
    }
    if coordinator is None:
        return result
    interval = coordinator.update_interval
    result["poll_interval_seconds"] = interval.total_seconds() if interval else None
    result["last_update_success"] = coordinator.last_update_success
    error = coordinator.last_exception
    result["last_error_type"] = type(error).__name__ if error else None
    data = coordinator.data
    if data is None:
        return result
    if service == "map":
        trains = data.get("trains", [])
        result["updated_at"] = data.get("updated_at")
        result["network"] = {
            "reported_trains": len(trains),
            "geographic_markers": sum(t.get("geo_point") is not None for t in trains),
            "diagram_markers": sum(t.get("point") is not None for t in trains),
            "positions": dict(
                Counter(
                    t.get("position_type")
                    if t.get("position_type") in ("route", "nearby")
                    else "unknown"
                    for t in trains
                )
            ),
            "lines": dict(
                Counter(
                    t.get("line") if t.get("line") in LINE_NAME_MAP else "unknown"
                    for t in trains
                )
            ),
            "geometry_loaded": coordinator.geometry is not None,
        }
    elif service == "commute":
        result["updated_at"] = data.get("updated_at")
        result["commute"] = {
            direction: {
                "has_route": trip is not None,
                "has_arrival_estimate": bool(trip and trip["arrival"] is not None),
                "transfers": trip["transfers"] if trip else None,
                "schedule_estimate": trip["schedule_estimate"] if trip else None,
            }
            for direction, trip in data.get("trips", {}).items()
        }
    else:
        arrivals = data.arrivals
        result["updated_at"] = data.updated_at
        result["arrivals"] = {
            "count": len(arrivals),
            "with_numeric_estimate": sum(
                a.get("minutes") is not None for a in arrivals
            ),
            "statuses": dict(
                Counter(
                    a.get("status")
                    if a.get("status")
                    in ("predicted", "arriving", "boarding", "delayed")
                    else "unknown"
                    for a in arrivals
                )
            ),
        }
    return result
