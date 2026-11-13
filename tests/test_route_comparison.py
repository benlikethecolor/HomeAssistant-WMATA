"""Competing routes are loop-free and share station snapshots."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from test_transfer_predictions import fixture

from custom_components.wmata.api import APIConnectionError
from custom_components.wmata.const import STATION_CODE_MAP
from custom_components.wmata.coordinator import APIData
from custom_components.wmata.journeys import candidate_journeys, line_paths
from custom_components.wmata.station_predictions import (
    async_station_predictions,
    async_station_predictions_many,
)


class CandidatesTest(unittest.TestCase):
    def test_candidates_include_different_transfer_counts_and_interchanges(self):
        routes = candidate_journeys("E10", "N12")
        self.assertTrue(any(route["transfers"] == 1 for route in routes))
        self.assertTrue(any(route["transfers"] == 2 for route in routes))
        self.assertTrue(
            any(route["legs"][0]["to_name"] == "L'Enfant Plaza" for route in routes)
        )
        self.assertTrue(
            any(route["legs"][0]["to_name"] == "Fort Totten" for route in routes)
        )

    def test_routes_do_not_revisit_a_station_or_add_a_same_line_change(self):
        for origin, destination in (
            ("E10", "N12"),
            ("C04", "B35"),
            ("A01", "B03"),
            ("J03", "D13"),
        ):
            for route in candidate_journeys(origin, destination):
                visited = {STATION_CODE_MAP[origin]}
                previous = set()
                self.assertLessEqual(route["transfers"], 3)
                for leg in route["legs"]:
                    self.assertFalse(previous.intersection(leg["lines"]))
                    path = line_paths(
                        leg["lines"][0], leg["from"], leg["to"], scheduled=True
                    )[0]
                    names = [STATION_CODE_MAP[code] for code in path[1:]]
                    self.assertFalse(visited.intersection(names))
                    visited.update(names)
                    previous = set(leg["lines"])
                self.assertEqual(
                    route["legs"][-1]["to_name"], STATION_CODE_MAP[destination]
                )
        self.assertEqual(candidate_journeys("A01", "C01"), ())
        self.assertEqual(candidate_journeys("invalid", "A01"), ())


class BatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_aliases_share_one_bulk_request_and_map_popups_reuse_the_cache(self):
        hass, entry, entity, registry, connection, api = fixture()
        api.trains.return_value = [
            {"LocationCode": "A01", "Line": "RD", "DestinationCode": "B11", "Min": "3"},
            {"LocationCode": "C04", "Line": "OR", "DestinationCode": "D13", "Min": "7"},
        ]
        result = await async_station_predictions_many(hass, api, ["A01", "C01", "C04"])
        api.trains.assert_awaited_once_with(["A01", "C01", "C04"])
        self.assertEqual(result["C04"]["arrivals"][0]["minutes"], 7)
        self.assertIs(await async_station_predictions(hass, api, "C01"), result["A01"])
        self.assertEqual(api.trains.await_count, 1)

    async def test_failed_bulk_fetch_preserves_a_recent_configured_station(self):
        hass, entry, entity, registry, connection, api = fixture()
        data = APIData([], [])
        configured = SimpleNamespace(
            data={"service_type": "train", "id": "C01"},
            runtime_data=SimpleNamespace(api=api, last_update_success=True, data=data),
        )
        hass.config_entries.async_entries = lambda _: [configured]
        api.trains.side_effect = APIConnectionError("offline")
        result = await async_station_predictions_many(hass, api, ["A01", "C04"])
        api.trains.assert_awaited_once_with(["C04"])
        self.assertEqual(result["A01"]["updated_at"], data.updated_at)
        self.assertIsNone(result["C04"])

    async def test_simultaneous_cards_share_the_batch_and_single_station_cache(self):
        hass, entry, entity, registry, connection, api = fixture()

        async def response(codes):
            await asyncio.sleep(0)
            return []

        api.trains = AsyncMock(side_effect=response)
        await asyncio.gather(
            async_station_predictions_many(hass, api, ["A01", "C04"]),
            async_station_predictions_many(hass, api, ["C01", "C04"]),
            async_station_predictions(hass, api, "C04"),
        )
        api.trains.assert_awaited_once()
