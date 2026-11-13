"""Authenticated on-demand predictions for train maps and saved journeys."""

import asyncio

import voluptuous as vol
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.helpers import entity_registry as er

from .api import APIAuthError, APIConnectionError
from .const import CONF_JOURNEYS, DOMAIN, STATION_CODE_MAP
from .journeys import trip_matches
from .station_predictions import async_station_predictions


def async_register(hass):
    websocket_api.async_register_command(hass, station_arrivals)
    websocket_api.async_register_command(hass, journey_arrivals)


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
    try:
        connection.send_result(
            msg["id"],
            await async_station_predictions(hass, coordinator.api, msg["station_code"]),
        )
    except (APIAuthError, APIConnectionError):
        connection.send_error(
            msg["id"],
            "cannot_connect",
            "Station arrivals are unavailable. Try again shortly.",
        )


@websocket_api.websocket_command(
    {vol.Required("type"): "wmata/journey_arrivals", vol.Required("entity_id"): str}
)
@websocket_api.async_response
async def journey_arrivals(hass, connection, msg):
    """Only query the legs of the saved journey the caller can read."""
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
        or entry.data.get("service_type") != "train"
        or not coordinator
        or entity.platform != DOMAIN
        or entity.domain != "sensor"
        or getattr(getattr(entry, "state", None), "value", "loaded") != "loaded"
    ):
        connection.send_error(
            msg["id"],
            "invalid_entity",
            "Select an available station-to-station journey",
        )
        return
    prefix = f"wmata_train_{entry.data['id'].lower()}_journey_"
    journey = next(
        (
            j
            for j in entry.options.get(CONF_JOURNEYS, [])
            if j.get("kind") == "station_to_station"
            and entity.unique_id == prefix + j["id"]
        ),
        None,
    )
    route = journey.get("route") if journey else None
    if (
        not route
        or not route.get("legs")
        or STATION_CODE_MAP.get(route.get("origin"))
        != STATION_CODE_MAP.get(entry.data["id"])
    ):
        connection.send_error(
            msg["id"], "invalid_entity", "Select a saved station-to-station journey"
        )
        return

    async def predictions(index, leg):
        result = {
            "index": index,
            "from_name": leg["from_name"],
            "to_name": leg["to_name"],
            "lines": leg["lines"],
            "available": False,
            "arrivals": [],
            "updated_at": None,
        }
        try:
            if index == 0:
                if not coordinator.last_update_success or coordinator.data is None:
                    return result
                data = {
                    "arrivals": coordinator.data.arrivals,
                    "updated_at": coordinator.data.updated_at,
                }
            else:
                data = await async_station_predictions(
                    hass, coordinator.api, leg["from"]
                )
            plan = {
                "origin": leg["from"],
                "origin_name": leg["from_name"],
                "legs": [leg],
            }
            result.update(
                available=True,
                updated_at=data["updated_at"],
                arrivals=[a for a in data["arrivals"] if trip_matches(a, plan)],
            )
        except (APIAuthError, APIConnectionError):
            # One failed transfer should not hide the other stations' predictions.
            pass
        return result

    legs = await asyncio.gather(
        *(predictions(index, leg) for index, leg in enumerate(route["legs"]))
    )
    connection.send_result(msg["id"], {"legs": legs})
