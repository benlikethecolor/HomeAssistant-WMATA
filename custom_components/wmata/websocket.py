"""Authenticated, on-demand station arrivals for the train map."""

import asyncio
import time

import voluptuous as vol
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.helpers import entity_registry as er

from .api import APIAuthError, APIConnectionError
from .const import DOMAIN, STATION_CODE_MAP, station_codes
from .predictions import normalize_prediction


def async_register(hass):
    websocket_api.async_register_command(hass, station_arrivals)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "wmata/station_arrivals",
        vol.Required("entity_id"): str,
        vol.Required("station_code"): vol.In(STATION_CODE_MAP),
    }
)
@websocket_api.async_response
async def station_arrivals(hass, connection, msg):
    """Use the selected map entry's client and cache for a requested station."""
    entity_id = msg["entity_id"]
    if not connection.user.permissions.check_entity(entity_id, POLICY_READ):
        connection.send_error(msg["id"], "unauthorized", "Entity access denied")
        return
    entity = er.async_get(hass).async_get(entity_id)
    entry = (
        hass.config_entries.async_get_entry(entity.config_entry_id) if entity else None
    )
    coordinator = getattr(entry, "runtime_data", None)
    if (
        not entry
        or entry.domain != DOMAIN
        or entry.data.get("service_type") != "map"
        or not coordinator
    ):
        connection.send_error(
            msg["id"], "invalid_entity", "Select an available WMATA train map"
        )
        return
    code = min(station_codes(msg["station_code"]))
    cache = hass.data.setdefault("wmata_station_popup_cache", {})
    key = (entry.entry_id, code)
    slot = cache.setdefault(key, {"lock": asyncio.Lock(), "expires": 0})
    try:
        async with slot["lock"]:
            if slot["expires"] <= time.monotonic():
                raw = await coordinator.api.trains(station_codes(code))
                arrivals = [normalize_prediction(row, "train") for row in raw]
                arrivals.sort(
                    key=lambda row: (row["minutes"] is None, row["minutes"] or 0)
                )
                slot["result"] = {
                    "station_name": STATION_CODE_MAP[code],
                    "arrivals": arrivals,
                }
                slot["expires"] = time.monotonic() + 30
            connection.send_result(msg["id"], slot["result"])
    except (APIAuthError, APIConnectionError):
        connection.send_error(
            msg["id"],
            "cannot_connect",
            "Station arrivals are unavailable. Try again shortly.",
        )
