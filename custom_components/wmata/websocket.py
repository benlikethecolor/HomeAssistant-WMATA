"""Authenticated on-demand predictions for train maps and saved journeys."""

import asyncio
from datetime import UTC, datetime

import voluptuous as vol
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.helpers import entity_registry as er

from .api import APIAuthError, APIConnectionError
from .connections import ride_minutes
from .const import CONF_JOURNEYS, DOMAIN, STATION_CODE_MAP, station_codes
from .directions import ROUTES
from .journeys import candidate_journeys, describe_route, trip_matches
from .station_predictions import (
    async_station_predictions,
    async_station_predictions_many,
)


def async_register(hass):
    websocket_api.async_register_command(hass, station_arrivals)
    websocket_api.async_register_command(hass, journey_arrivals)
    websocket_api.async_register_command(hass, planner_stations)
    websocket_api.async_register_command(hass, plan_trip)


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

    legs = await route_predictions(hass, coordinator.api, route, coordinator)
    connection.send_result(msg["id"], {"legs": legs})


async def route_predictions(
    hass, api, route, coordinator=None, station_data=None, timetable=True
):
    """Share filtering and prediction caches between saved and temporary routes.

    Pass timetable=False to answer from live predictions alone, without waiting
    for the rail timetable to download.
    """

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
            if index == 0 and coordinator is not None:
                if not coordinator.last_update_success or coordinator.data is None:
                    return result
                data = {
                    "arrivals": coordinator.data.arrivals,
                    "updated_at": coordinator.data.updated_at,
                }
            elif station_data is not None:
                data = station_data.get(min(station_codes(leg["from"])))
                if data is None:
                    return result
            else:
                data = await async_station_predictions(hass, api, leg["from"])
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
    try:
        times = await api.rail_times()
    except (APIAuthError, APIConnectionError):
        times = None
    for result, leg in zip(legs, route["legs"], strict=True):
        result["ride_minutes"] = ride_minutes(leg, times)
    try:
        schedule = await api.rail_schedule() if timetable else None
    except (APIAuthError, APIConnectionError):
        schedule = None
    now = datetime.now(UTC)
    if schedule:
        scheduled = await hass.async_add_executor_job(
            lambda: [schedule.departures(leg, now) for leg in route["legs"]]
        )
    else:
        scheduled = [[] for leg in legs]
    for result, departures in zip(legs, scheduled, strict=True):
        result["scheduled_departures"] = departures
        if result["ride_minutes"] is None and departures:
            result["ride_minutes"] = departures[0]["ride_minutes"]
    return legs


def planner_client(hass, connection, msg):
    """A readable, loaded rail entity provides credentials; never accept a key."""
    if not connection.user.permissions.check_entity(msg["entity_id"], POLICY_READ):
        connection.send_error(msg["id"], "unauthorized", "Entity access denied")
        return None
    entity = er.async_get(hass).async_get(msg["entity_id"])
    entry = (
        hass.config_entries.async_get_entry(entity.config_entry_id) if entity else None
    )
    coordinator = getattr(entry, "runtime_data", None)
    if (
        not entry
        or entry.domain != DOMAIN
        or entry.data.get("service_type") not in ("train", "map", "commute")
        or not coordinator
        or entity.platform != DOMAIN
        or entity.domain != "sensor"
        or getattr(getattr(entry, "state", None), "value", "loaded") != "loaded"
    ):
        connection.send_error(
            msg["id"],
            "invalid_entity",
            "Select an available WMATA rail board, commute or train map",
        )
        return None
    return coordinator.api


@websocket_api.websocket_command(
    {vol.Required("type"): "wmata/planner_stations", vol.Required("entity_id"): str}
)
@websocket_api.async_response
async def planner_stations(hass, connection, msg):
    """Return named stations once, combining lines at interchange platforms."""
    if planner_client(hass, connection, msg) is None:
        return
    stations = {}
    for code, name in STATION_CODE_MAP.items():
        station = stations.setdefault(name, {"code": code, "name": name, "lines": []})
        for line, route in ROUTES.items():
            if code in route and line not in station["lines"]:
                station["lines"].append(line)
    connection.send_result(
        msg["id"],
        {"stations": sorted(stations.values(), key=lambda station: station["name"])},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "wmata/plan_trip",
        vol.Required("entity_id"): str,
        vol.Required("origin"): vol.In(STATION_CODE_MAP),
        vol.Required("destination"): vol.In(STATION_CODE_MAP),
    }
)
@websocket_api.async_response
async def plan_trip(hass, connection, msg):
    """Plan a temporary route without creating entities or changing settings."""
    api = planner_client(hass, connection, msg)
    if api is None:
        return
    routes = candidate_journeys(msg["origin"], msg["destination"])
    if not routes:
        connection.send_error(
            msg["id"], "invalid_route", "Choose two different Metro stations"
        )
        return
    alternatives = await trip_alternatives(hass, api, routes)
    # Clients rank these using the same live/timetable connection calculator as
    # their journey card and the user's platform-change allowance.
    connection.send_result(msg["id"], {**alternatives[0], "alternatives": alternatives})


async def trip_alternatives(hass, api, routes, station_data=None, timetable=True):
    """Attach departures and ride times to each candidate route.

    Legs shared by several routes are fetched and filtered once. Pass
    station_data to reuse predictions that were already requested together.
    """

    def key(leg):
        return (leg["from"], leg["to"], tuple(leg["lines"]))

    unique = {key(leg): leg for route in routes for leg in route["legs"]}
    if station_data is None:
        station_data = await async_station_predictions_many(
            hass, api, [leg["from"] for leg in unique.values()]
        )
    shared = await route_predictions(
        hass,
        api,
        {"legs": list(unique.values())},
        station_data=station_data,
        timetable=timetable,
    )
    by_leg = dict(zip(unique, shared, strict=True))
    alternatives = []
    for route in routes:
        legs = [
            {**by_leg[key(leg)], "index": index}
            for index, leg in enumerate(route["legs"])
        ]
        durations = [leg["ride_minutes"] for leg in legs]
        alternatives.append(
            {
                "id": "|".join(
                    f"{leg['from']}>{leg['to']}:{','.join(leg['lines'])}"
                    for leg in route["legs"]
                ),
                "route": route,
                "route_description": describe_route(route),
                "legs": legs,
                "scheduled_ride_minutes": sum(durations)
                if all(value is not None for value in durations)
                else None,
            }
        )
    return alternatives
