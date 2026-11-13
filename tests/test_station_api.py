"""Station clicks must respect entity permissions and share transfer-station caches."""

import asyncio
import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.wmata.websocket import station_arrivals


class StationApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_transfer_alias_requests_share_cache_and_expand_names(self):
        api = SimpleNamespace(
            trains=AsyncMock(
                return_value=[
                    {"Line": "OR", "DestinationName": "NewCrlton", "Min": "4"},
                    {"Line": "RD", "DestinationName": "Glenmont", "Min": "BRD"},
                ]
            )
        )
        entry = SimpleNamespace(
            entry_id="map",
            domain="wmata",
            data={"service_type": "map"},
            runtime_data=SimpleNamespace(api=api),
        )
        hass = SimpleNamespace(
            data={}, config_entries=SimpleNamespace(async_get_entry=lambda _: entry)
        )
        registry = MagicMock()
        registry.async_get.return_value = SimpleNamespace(config_entry_id="map")
        connection = MagicMock()
        connection.user.permissions.check_entity.return_value = True
        handler = inspect.unwrap(station_arrivals)
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            await asyncio.gather(
                *(
                    handler(
                        hass,
                        connection,
                        {"id": i, "entity_id": "sensor.map", "station_code": code},
                    )
                    for i, code in enumerate(["A01", "C01"])
                )
            )
        api.trains.assert_awaited_once()
        results = [call.args[1] for call in connection.send_result.call_args_list]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["arrivals"][0]["status"], "boarding")
        self.assertEqual(results[0]["arrivals"][1]["destination"], "New Carrollton")

    async def test_denied_entity_does_not_fetch_data(self):
        connection = MagicMock()
        connection.user.permissions.check_entity.return_value = False
        await inspect.unwrap(station_arrivals)(
            SimpleNamespace(),
            connection,
            {"id": 1, "entity_id": "sensor.private", "station_code": "K01"},
        )
        connection.send_error.assert_called_once_with(
            1, "unauthorized", "Entity access denied"
        )
        connection.send_result.assert_not_called()
