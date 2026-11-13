"""Shared on-demand station predictions for map popups and journey cards."""

import asyncio
import time
from datetime import UTC, datetime

from .const import DOMAIN, STATION_CODE_MAP, station_codes
from .predictions import normalize_prediction


def _request_state(api):
    return getattr(api, "_state", api)


def _configured_predictions(hass, api, code):
    """Reuse a configured station's recent poll when it uses the same key."""
    entries = getattr(hass.config_entries, "async_entries", None)
    if entries is None:
        return None
    for entry in entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if (
            entry.data.get("service_type") != "train"
            or not coordinator
            or code not in station_codes(entry.data.get("id", ""))
            or _request_state(coordinator.api) is not _request_state(api)
            or not coordinator.last_update_success
            or coordinator.data is None
        ):
            continue
        data = coordinator.data
        age = (
            datetime.now(UTC).timestamp()
            - datetime.fromisoformat(data.updated_at).timestamp()
        )
        if 0 <= age <= 30:
            return {
                "station_name": STATION_CODE_MAP[code],
                "arrivals": data.arrivals,
                "updated_at": data.updated_at,
            }
    return None


async def async_station_predictions(hass, api, station_code):
    """Coalesce requests across entries/cards using the same subscription."""
    code = min(station_codes(station_code))
    cache = hass.data.setdefault("wmata_station_popup_cache", {})
    key = (id(_request_state(api)), code)
    slot = cache.setdefault(key, {"lock": asyncio.Lock(), "expires": 0})
    async with slot["lock"]:
        if slot["expires"] <= time.monotonic():
            result = _configured_predictions(hass, api, code)
            if result is None:
                raw = await api.trains(station_codes(code))
                arrivals = [normalize_prediction(row, "train") for row in raw]
                arrivals.sort(
                    key=lambda row: (row["minutes"] is None, row["minutes"] or 0)
                )
                result = {
                    "station_name": STATION_CODE_MAP[code],
                    "arrivals": arrivals,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            slot["result"] = result
            # A reused poll keeps its original age; it cannot extend the TTL.
            age = max(
                0,
                datetime.now(UTC).timestamp()
                - datetime.fromisoformat(result["updated_at"]).timestamp(),
            )
            slot["expires"] = time.monotonic() + max(0, 30 - age)
        return slot["result"]
