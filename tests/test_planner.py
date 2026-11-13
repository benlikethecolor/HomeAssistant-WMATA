"""Temporary trips use authorized credentials and never save configuration."""

import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test_transfer_predictions import fixture

from custom_components.wmata.api import APIConnectionError
from custom_components.wmata.websocket import plan_trip, planner_stations


class PlannerTest(unittest.IsolatedAsyncioTestCase):
    async def call(self, handler, parts=None):
        hass, entry, entity, registry, connection, api = fixture()
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            await inspect.unwrap(handler)(
                hass, connection, {"id": 1, "entity_id": "sensor.rail", **(parts or {})}
            )
        return hass, entry, entity, connection, api

    async def test_catalog_combines_transfer_platforms_without_api_requests(self):
        hass, entry, entity, connection, api = await self.call(planner_stations)
        stations = connection.send_result.call_args.args[1]["stations"]
        center = [s for s in stations if s["name"] == "Metro Center"]
        self.assertEqual(len(center), 1)
        self.assertEqual(set(center[0]["lines"]), {"RD", "BL", "OR", "SV"})
        self.assertEqual(len(stations), len({s["name"] for s in stations}))
        api.trains.assert_not_awaited()
        api.rail_times.assert_not_awaited()

    async def test_temporary_route_queries_unconfigured_origin_and_does_not_save(self):
        hass, entry, entity, registry, connection, api = fixture()
        entry.data["service_type"] = "map"
        options_before = dict(entry.options)
        api.trains.return_value = [
            {"LocationCode": "C04", "Line": "OR", "DestinationCode": "D13", "Min": "7"}
        ]
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            await inspect.unwrap(plan_trip)(
                hass,
                connection,
                {
                    "id": 1,
                    "entity_id": "sensor.map",
                    "origin": "C04",
                    "destination": "A01",
                },
            )
        result = connection.send_result.call_args.args[1]
        self.assertEqual(result["route"]["destination_name"], "Metro Center")
        self.assertEqual(result["scheduled_ride_minutes"], 4)
        self.assertEqual(result["legs"][0]["arrivals"][0]["minutes"], 7)
        api.trains.assert_awaited_once_with(["C04"])
        self.assertEqual(entry.options, options_before)
        self.assertNotIn("api_key", str(result))

    async def test_access_checks_apply_to_both_commands_before_requests(self):
        for handler in (planner_stations, plan_trip):
            for invalid in ("permission", "bus", "domain", "platform", "unloaded"):
                hass, entry, entity, registry, connection, api = fixture()
                if invalid == "permission":
                    connection.user.permissions.check_entity.return_value = False
                if invalid == "bus":
                    entry.data["service_type"] = "bus"
                if invalid == "domain":
                    entry.domain = "other"
                if invalid == "platform":
                    entity.platform = "other"
                if invalid == "unloaded":
                    entry.state = SimpleNamespace(value="not_loaded")
                with patch(
                    "custom_components.wmata.websocket.er.async_get",
                    return_value=registry,
                ):
                    await inspect.unwrap(handler)(
                        hass,
                        connection,
                        {
                            "id": 1,
                            "entity_id": "sensor.rail",
                            "origin": "C04",
                            "destination": "A01",
                        },
                    )
                connection.send_error.assert_called_once()
                api.trains.assert_not_awaited()
                api.rail_times.assert_not_awaited()

    async def test_same_station_platform_aliases_are_rejected(self):
        hass, entry, entity, connection, api = await self.call(
            plan_trip, {"origin": "A01", "destination": "C01"}
        )
        self.assertEqual(connection.send_error.call_args.args[1], "invalid_route")
        api.trains.assert_not_awaited()

    async def test_live_outage_keeps_scheduled_duration_and_route(self):
        hass, entry, entity, registry, connection, api = fixture()
        api.trains.side_effect = APIConnectionError("offline")
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            await inspect.unwrap(plan_trip)(
                hass,
                connection,
                {
                    "id": 1,
                    "entity_id": "sensor.rail",
                    "origin": "C04",
                    "destination": "A01",
                },
            )
        result = connection.send_result.call_args.args[1]
        self.assertFalse(result["legs"][0]["available"])
        self.assertEqual(result["scheduled_ride_minutes"], 4)
