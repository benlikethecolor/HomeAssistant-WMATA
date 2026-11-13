"""Regressions for map setup access, circuit mapping, and stale-data behavior."""

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.wmata.api import APIAuthError, APIConnectionError, WmataApi
from custom_components.wmata.config_flow import WmataConfigFlow
from custom_components.wmata.train_map import (
    MapCoordinator,
    build_geometry,
    mapped_train,
)
from tests.test_wmata import entry

ROUTES = [
    {
        "LineCode": "RD",
        "TrackNum": 1,
        "TrackCircuits": [
            {"CircuitId": 1, "StationCode": "A01"},
            {"CircuitId": 2},
            {"CircuitId": 3, "StationCode": "A02"},
        ],
    }
]
CIRCUITS = [{"CircuitId": 2, "Neighbors": [{"CircuitIds": [1, 3, 4]}]}]
SHAPES = {"RD/A01/A02": [[10, 20], [20, 30], [30, 40]]}
GEOGRAPHIC = {"RD/A01/A02": [[-77.1, 38.9], [-77.2, 38.95], [-77.3, 39.0]]}


class GeometryTest(unittest.TestCase):
    def test_reverse_track_shared_lines_and_side_tracks(self):
        reverse = {
            "LineCode": "RD",
            "TrackNum": 2,
            "TrackCircuits": [
                {"CircuitId": 10, "StationCode": "A02"},
                {"CircuitId": 11},
                {"CircuitId": 12, "StationCode": "A01"},
            ],
        }
        geometry = build_geometry(SHAPES, GEOGRAPHIC, [*ROUTES, reverse], CIRCUITS)
        self.assertEqual(geometry.geographic[10]["RD"], [-77.3, 39.0])
        self.assertEqual(geometry.geographic[12]["RD"], [-77.1, 38.9])
        side = mapped_train({"CircuitId": 4, "LineCode": "RD"}, geometry)
        self.assertEqual(side["position_type"], "nearby")
        self.assertEqual(side["geo_point"], [-77.2, 38.95])
        unknown = mapped_train({"CircuitId": 999, "LineCode": None}, geometry)
        self.assertIsNone(unknown["geo_point"])
        self.assertEqual(unknown["position_type"], "unknown")

    def test_each_shared_line_keeps_its_schematic_stripe(self):
        shared = [{**ROUTES[0], "LineCode": "BL"}, *ROUTES]
        geometry = build_geometry(
            {**SHAPES, "BL/A01/A02": [[0, 0], [1, 1], [2, 2]]},
            GEOGRAPHIC,
            shared,
            CIRCUITS,
        )
        self.assertEqual(
            mapped_train({"CircuitId": 2, "LineCode": "BL"}, geometry)["point"], [1, 1]
        )
        self.assertEqual(
            mapped_train({"CircuitId": 2, "LineCode": "RD"}, geometry)["point"],
            [20, 30],
        )


class NetworkTest(unittest.IsolatedAsyncioTestCase):
    async def test_map_flow_checks_every_required_endpoint_and_preserves_form_on_failure(
        self,
    ):
        flow = WmataConfigFlow()
        flow.hass = SimpleNamespace(data={})
        with (
            patch(
                "custom_components.wmata.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                WmataApi,
                "_request",
                side_effect=[
                    {"StandardRoutes": [{}]},
                    {"TrackCircuits": [{}]},
                    APIAuthError("Denied"),
                ],
            ) as request,
        ):
            result = await flow.async_step_user(
                {"api_key": "fixture-key", "service_type": "map"}
            )
        self.assertEqual(result["errors"]["base"], "invalid_auth")
        self.assertEqual(result["step_id"], "user")
        self.assertEqual(request.await_count, 3)

    async def test_bus_validation_uses_bus_api(self):
        api = WmataApi(MagicMock(), "fixture-key")
        with patch.object(api, "get", return_value={"Routes": []}) as request:
            await api.validate_service("bus")
        request.assert_awaited_once_with("Bus.svc/json/jRoutes")

    async def test_failed_refresh_preserves_successful_timestamp(self):
        hass = HomeAssistant("/tmp/wmata-network-unit")
        try:
            with patch(
                "custom_components.wmata.train_map.async_get_clientsession",
                return_value=MagicMock(),
            ):
                coordinator = MapCoordinator(
                    hass, entry("map", "network", options={"scan_interval": 60})
                )
            coordinator.api = SimpleNamespace(
                standard_routes=AsyncMock(return_value=ROUTES),
                track_circuits=AsyncMock(return_value=CIRCUITS),
                train_positions=AsyncMock(
                    return_value=[{"CircuitId": 2, "LineCode": "RD"}]
                ),
            )
            with patch(
                "custom_components.wmata.train_map.read_shapes",
                return_value=(SHAPES, GEOGRAPHIC),
            ):
                await coordinator.async_refresh()
                successful = coordinator.data["updated_at"]
                datetime.fromisoformat(successful)
                coordinator.api.train_positions.side_effect = APIConnectionError(
                    "Offline"
                )
                await coordinator.async_refresh()
            self.assertEqual(coordinator.data["updated_at"], successful)
            self.assertFalse(coordinator.last_update_success)
            coordinator.api.standard_routes.assert_awaited_once()
            self.assertEqual(coordinator.update_interval.total_seconds(), 60)
        finally:
            await hass.async_stop(force=True)
