"""Travel-time caching and route-specific ride estimates."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from custom_components.wmata.api import APIConnectionError, WmataApi
from custom_components.wmata.connections import ride_minutes


class RideTimesTest(unittest.TestCase):
    def test_adjacent_times_follow_saved_path_and_platform_aliases(self):
        leg = {"from": "C04", "to": "A01", "lines": ["OR", "SV"]}
        times = {
            ("C04", "C03"): 2,
            ("C03", "C02"): 1,
            ("C02", "C01"): 1,
            ("C04", "A01"): 99,
        }
        self.assertEqual(ride_minutes(leg, times), 4)
        self.assertIsNone(ride_minutes(leg, {("C04", "A01"): 4}))
        self.assertIsNone(ride_minutes(leg, None))

    def test_directional_times_are_not_reversed(self):
        leg = {"from": "C03", "to": "C04", "lines": ["BL"]}
        self.assertIsNone(ride_minutes(leg, {("C04", "C03"): 2}))
        self.assertEqual(ride_minutes(leg, {("C03", "C04"): 3}), 3)


class TravelTimeCacheTest(unittest.IsolatedAsyncioTestCase):
    async def test_clients_share_one_daily_request_and_reject_invalid_values(self):
        hass = SimpleNamespace(data={})
        one = WmataApi(MagicMock(), "same", hass=hass)
        two = WmataApi(MagicMock(), "same", hass=hass)
        row = {"SourceStation": "C04", "DestinationStation": "C03", "RailTime": 2}
        one.get = AsyncMock(
            return_value={
                "StationToStationInfos": [
                    row,
                    *[
                        {**row, "DestinationStation": f"bad{i}", "RailTime": value}
                        for i, value in enumerate(
                            [None, True, 0, -1, "3", float("nan"), float("inf")]
                        )
                    ],
                ]
            }
        )
        two.get = AsyncMock()
        first, second = await asyncio.gather(one.rail_times(), two.rail_times())
        self.assertEqual(first, {("C04", "C03"): 2})
        self.assertIs(first, second)
        one.get.assert_awaited_once_with("Rail.svc/json/jSrcStationToDstStationInfo")
        two.get.assert_not_awaited()
        one._state.rail_times_expiry = 0
        await one.rail_times()
        self.assertEqual(one.get.await_count, 2)

    async def test_failed_requests_back_off_without_blocking_predictions(self):
        api = WmataApi(MagicMock(), "key")
        api.get = AsyncMock(side_effect=APIConnectionError("offline"))
        with self.assertRaises(APIConnectionError):
            await api.rail_times()
        self.assertIsNone(await api.rail_times())
        api.get.assert_awaited_once()
