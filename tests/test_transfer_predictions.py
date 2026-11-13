"""Transfer predictions are filtered, permission-checked, and shared safely."""

import asyncio
import inspect
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.wmata.api import APIConnectionError
from custom_components.wmata.coordinator import APIData
from custom_components.wmata.journeys import direct_legs, plan_journey
from custom_components.wmata.station_predictions import async_station_predictions
from custom_components.wmata.websocket import journey_arrivals


def fixture(route=None):
    route = route or plan_journey("C04", "B35")
    api = SimpleNamespace(
        _state=object(),
        trains=AsyncMock(
            return_value=[
                {
                    "LocationCode": "A01",
                    "Line": "RD",
                    "DestinationCode": "B11",
                    "Min": "ARR",
                },
                {
                    "LocationCode": "A01",
                    "Line": "RD",
                    "DestinationCode": "B08",
                    "Min": "10",
                },
                {
                    "LocationCode": "A01",
                    "Line": "RD",
                    "DestinationCode": "B03",
                    "Min": "2",
                },
                {
                    "LocationCode": "A01",
                    "Line": "RD",
                    "DestinationCode": "A15",
                    "Min": "3",
                },
                {
                    "LocationCode": "C01",
                    "Line": "OR",
                    "DestinationCode": "D13",
                    "Min": "5",
                },
            ]
        ),
    )
    coordinator = SimpleNamespace(
        api=api,
        last_update_success=True,
        data=APIData(
            [],
            [
                {
                    "LocationCode": "C04",
                    "Line": "OR",
                    "DestinationCode": "D13",
                    "Min": "4",
                },
                {
                    "LocationCode": "C04",
                    "Line": "SV",
                    "DestinationCode": "N12",
                    "Min": "2",
                },
            ],
        ),
    )
    entry = SimpleNamespace(
        entry_id="origin",
        domain="wmata",
        data={"service_type": "train", "id": "C04"},
        options={
            "journeys": [{"id": "saved", "kind": "station_to_station", "route": route}]
        },
        runtime_data=coordinator,
    )
    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_get_entry=lambda _: entry, async_entries=lambda _: []
        ),
    )
    entity = SimpleNamespace(
        config_entry_id="origin",
        unique_id="wmata_train_c04_journey_saved",
        platform="wmata",
        domain="sensor",
    )
    registry = SimpleNamespace(async_get=lambda _: entity)
    connection = MagicMock()
    connection.user.permissions.check_entity.return_value = True
    return hass, entry, entity, registry, connection, api


class TransferPredictionsTest(unittest.IsolatedAsyncioTestCase):
    async def test_each_leg_is_filtered_and_multiple_cards_share_the_request(self):
        hass, entry, entity, registry, connection, api = fixture()
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            await asyncio.gather(
                *(
                    inspect.unwrap(journey_arrivals)(
                        hass, connection, {"id": i, "entity_id": "sensor.trip"}
                    )
                    for i in (1, 2)
                )
            )
        api.trains.assert_awaited_once_with(["A01", "C01"])
        response = connection.send_result.call_args_list[0].args[1]
        self.assertEqual(len(response["legs"]), 2)
        self.assertEqual(response["legs"][0]["arrivals"][0]["minutes"], 4)
        self.assertEqual(
            [a["destination_code"] for a in response["legs"][1]["arrivals"]],
            ["B11", "B08"],
        )
        self.assertEqual(response["legs"][1]["arrivals"][0]["status"], "arriving")
        self.assertTrue(
            all(leg["available"] and leg["updated_at"] for leg in response["legs"])
        )

    async def test_permissions_and_non_journey_entities_cannot_query_stations(self):
        hass, entry, entity, registry, connection, api = fixture()
        connection.user.permissions.check_entity.return_value = False
        await inspect.unwrap(journey_arrivals)(
            hass, connection, {"id": 1, "entity_id": "sensor.trip"}
        )
        connection.send_error.assert_called_once_with(
            1, "unauthorized", "Entity access denied"
        )
        connection.user.permissions.check_entity.return_value = True
        entity.unique_id = "wmata_train_c04_board"
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            await inspect.unwrap(journey_arrivals)(
                hass, connection, {"id": 2, "entity_id": "sensor.trip"}
            )
        self.assertEqual(connection.send_error.call_args.args[1], "invalid_entity")
        entity.unique_id = "wmata_train_c04_journey_saved"
        entry.state = SimpleNamespace(value="not_loaded")
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            await inspect.unwrap(journey_arrivals)(
                hass, connection, {"id": 3, "entity_id": "sensor.trip"}
            )
        self.assertEqual(connection.send_error.call_args.args[1], "invalid_entity")
        api.trains.assert_not_awaited()

    async def test_one_failed_transfer_does_not_hide_other_legs(self):
        route = {
            "origin": "C04",
            "origin_name": "Foggy Bottom-GWU",
            "legs": [
                dict(direct_legs("C04", "A01")[0]),
                dict(direct_legs("A01", "B01")[0]),
                dict(direct_legs("B01", "E10")[0]),
            ],
        }
        hass, entry, entity, registry, connection, api = fixture(route)

        async def response(codes):
            if "A01" in codes:
                raise APIConnectionError("offline")
            return [
                {
                    "LocationCode": "F01",
                    "Line": "GR",
                    "DestinationCode": "E10",
                    "Min": "7",
                }
            ]

        api.trains.side_effect = response
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            await inspect.unwrap(journey_arrivals)(
                hass, connection, {"id": 1, "entity_id": "sensor.trip"}
            )
        legs = connection.send_result.call_args.args[1]["legs"]
        self.assertEqual([leg["available"] for leg in legs], [True, False, True])
        self.assertEqual(legs[1]["arrivals"], [])
        self.assertEqual(legs[2]["arrivals"][0]["minutes"], 7)

    async def test_cache_is_shared_by_subscription_not_entry_or_station_alias(self):
        hass, entry, entity, registry, connection, api = fixture()
        same = SimpleNamespace(_state=api._state, trains=AsyncMock(return_value=[]))
        await asyncio.gather(
            async_station_predictions(hass, api, "A01"),
            async_station_predictions(hass, same, "C01"),
        )
        self.assertEqual(api.trains.await_count + same.trains.await_count, 1)
        different = SimpleNamespace(_state=object(), trains=AsyncMock(return_value=[]))
        await async_station_predictions(hass, different, "A01")
        different.trains.assert_awaited_once()

    async def test_recent_configured_station_poll_is_reused_without_extending_its_age(
        self,
    ):
        hass, entry, entity, registry, connection, api = fixture()
        updated = (datetime.now(UTC) - timedelta(seconds=20)).isoformat()
        data = APIData([], [], updated_at=updated)
        configured = SimpleNamespace(
            data={"service_type": "train", "id": "C01"},
            runtime_data=SimpleNamespace(api=api, last_update_success=True, data=data),
        )
        hass.config_entries.async_entries = lambda _: [configured]
        with patch(
            "custom_components.wmata.station_predictions.time.monotonic",
            return_value=100,
        ):
            result = await async_station_predictions(hass, api, "A01")
        self.assertEqual(result["updated_at"], updated)
        api.trains.assert_not_awaited()
        slot = next(iter(hass.data["wmata_station_popup_cache"].values()))
        self.assertGreater(slot["expires"], 109)
        self.assertLess(slot["expires"], 111)
