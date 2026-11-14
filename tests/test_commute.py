"""Commute entries: setup, one shared request per poll, and travel-time sensors."""

import asyncio
import json
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.wmata.api import APIAuthError, APIConnectionError
from custom_components.wmata.commute import CommuteCoordinator
from custom_components.wmata.config_flow import WmataConfigFlow, WmataOptionsFlow
from custom_components.wmata.diagnostics import async_get_config_entry_diagnostics
from custom_components.wmata.sensor import WmataCommuteSensor
from custom_components.wmata.sensor import async_setup_entry as setup_sensors
from custom_components.wmata.websocket import planner_client
from tests.test_wmata import entry

# Foggy Bottom to Metro Center is a direct ride on Blue, Orange or Silver.
RIDE_TIMES = {
    ("C04", "C03"): 2,
    ("C03", "C02"): 1,
    ("C02", "C01"): 1,
    ("C01", "C02"): 1,
    ("C02", "C03"): 2,
    ("C03", "C04"): 3,
}
TRAINS = [
    {"LocationCode": "C04", "Line": "OR", "DestinationCode": "D13", "Min": "4"},
    {"LocationCode": "C04", "Line": "OR", "DestinationCode": "K08", "Min": "1"},
    {"LocationCode": "C01", "Line": "SV", "DestinationCode": "N12", "Min": "BRD"},
    {"LocationCode": "A01", "Line": "RD", "DestinationCode": "B11", "Min": "2"},
]


def commute_entry(**options):
    return entry(
        "commute",
        "C04-A01",
        options=options,
        home="C04",
        work="A01",
        location_name="Commute",
    )


class CommuteTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = HomeAssistant("/tmp/wmata-commute")
        self.hass.config_entries = SimpleNamespace(async_entries=lambda domain: [])
        with patch(
            "custom_components.wmata.commute.async_get_clientsession",
            return_value=MagicMock(),
        ):
            self.coordinator = CommuteCoordinator(self.hass, commute_entry())
        self.api = self.coordinator.api = SimpleNamespace(
            stations=AsyncMock(return_value=[]),
            trains=AsyncMock(return_value=TRAINS),
            rail_times=AsyncMock(return_value=RIDE_TIMES),
            rail_schedule=AsyncMock(side_effect=APIConnectionError("No timetable")),
            rail_schedule_ready=lambda: True,
        )

    async def asyncTearDown(self):
        await self.hass.async_stop(force=True)

    def sensor(self, direction, kind):
        return WmataCommuteSensor(self.coordinator, direction, kind)

    async def test_both_directions_come_from_one_prediction_request(self):
        self.coordinator.data = await self.coordinator._async_update_data()
        self.api.trains.assert_awaited_once()
        self.assertTrue(
            {"C04", "A01", "C01"} <= set(self.api.trains.await_args.args[0])
        )
        # To work: the eastbound Orange in 4 minutes, then a 4 minute ride.
        there = self.sensor("outbound", "travel_time")
        self.assertEqual(there.name, "To Metro Center travel time")
        self.assertEqual(there.native_value, 8)
        self.assertEqual(self.sensor("outbound", "next_train").native_value, 4)
        arrival = self.sensor("outbound", "arrival").native_value
        self.assertAlmostEqual(
            (arrival - datetime.now(UTC)).total_seconds(), 480, delta=5
        )
        attributes = there.extra_state_attributes
        self.assertEqual(attributes["board_type"], "commute")
        self.assertEqual(attributes["origin_name"], "Foggy Bottom-GWU")
        self.assertEqual(attributes["destination_name"], "Metro Center")
        self.assertEqual(attributes["transfers"], 0)
        self.assertEqual(attributes["first_train"]["line"], "OR")
        self.assertFalse(attributes["schedule_estimate"])
        self.assertIsNone(self.sensor("outbound", "arrival").extra_state_attributes)
        # Home again: the boarding Silver train, then a 6 minute ride back.
        back = self.sensor("return", "travel_time")
        self.assertEqual(back.name, "To Foggy Bottom-GWU travel time")
        self.assertEqual(back.native_value, 6)
        self.assertEqual(self.sensor("return", "next_train").native_value, 0)
        self.assertNotEqual(there.unique_id, back.unique_id)

    async def test_missing_trains_leave_the_sensors_unknown(self):
        self.api.trains.return_value = TRAINS[2:]
        self.coordinator.data = await self.coordinator._async_update_data()
        self.assertIsNone(self.sensor("outbound", "travel_time").native_value)
        self.assertIsNone(self.sensor("outbound", "next_train").native_value)
        self.assertIsNone(self.sensor("outbound", "arrival").native_value)
        self.assertEqual(self.sensor("return", "travel_time").native_value, 6)
        self.coordinator.data = None
        self.assertIsNone(self.sensor("return", "travel_time").native_value)

    async def test_setup_does_not_wait_for_the_timetable_download(self):
        loaded = asyncio.Event()
        ready = False

        async def download():
            nonlocal ready
            await loaded.wait()
            ready = True

        self.api.rail_schedule = AsyncMock(side_effect=download)
        self.api.rail_schedule_ready = lambda: ready
        self.coordinator.async_request_refresh = AsyncMock()
        # The first estimate comes back from live trains while it downloads.
        self.coordinator.data = await self.coordinator._async_update_data()
        self.assertEqual(self.sensor("outbound", "travel_time").native_value, 8)
        task = self.coordinator._timetable_task
        self.assertFalse(task.done())
        await self.coordinator._async_update_data()
        self.assertIs(self.coordinator._timetable_task, task)
        loaded.set()
        await task
        # Once it has loaded, one refresh brings the timetable into the estimate.
        self.coordinator.async_request_refresh.assert_awaited_once()
        self.api.rail_schedule.reset_mock(side_effect=True)
        self.api.rail_schedule.return_value = None
        await self.coordinator._async_update_data()
        self.api.rail_schedule.assert_awaited()

    async def test_a_failed_timetable_download_does_not_cause_a_refresh_loop(self):
        self.api.rail_schedule_ready = lambda: False
        self.coordinator.async_request_refresh = AsyncMock()
        await self.coordinator._async_update_data()
        await self.coordinator._timetable_task
        self.coordinator.async_request_refresh.assert_not_awaited()

    async def test_platform_allowance_comes_from_the_entry_options(self):
        with patch(
            "custom_components.wmata.commute.async_get_clientsession",
            return_value=MagicMock(),
        ):
            coordinator = CommuteCoordinator(
                self.hass, commute_entry(transfer_buffer=7, scan_interval=60)
            )
        self.assertEqual(coordinator.buffer, 7)
        self.assertEqual(coordinator.update_interval.total_seconds(), 60)
        self.assertEqual(self.coordinator.buffer, 3)

    async def test_rejected_key_asks_for_reauth_and_outages_fail_the_update(self):
        self.api.trains.side_effect = APIConnectionError("Offline")
        with self.assertRaises(UpdateFailed):
            await self.coordinator._async_update_data()
        self.api.stations.side_effect = APIAuthError()
        with self.assertRaises(ConfigEntryAuthFailed):
            await self.coordinator._async_update_data()

    async def test_setup_creates_six_sensors_and_no_board_entities(self):
        e = commute_entry()
        e.runtime_data = self.coordinator
        add = MagicMock()
        await setup_sensors(self.hass, e, add)
        sensors = list(add.call_args.args[0])
        self.assertEqual(len(sensors), 6)
        self.assertEqual(len({s.unique_id for s in sensors}), 6)
        self.assertTrue(all(isinstance(s, WmataCommuteSensor) for s in sensors))


class CommuteFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_two_stations_become_one_entry_named_for_both(self):
        flow = WmataConfigFlow()
        flow.hass = SimpleNamespace(data={})
        flow.context = {"source": "user"}
        flow._setup_data = {"api_key": "test", "service_type": "commute"}
        form = await flow.async_step_commute()
        self.assertEqual(form["step_id"], "commute")
        # Both platforms of a transfer station are the same place.
        same = await flow.async_step_commute({"home": "A01", "work": "C01"})
        self.assertEqual(same["errors"], {"work": "same_station"})
        typo = await flow.async_step_commute({"home": "C04", "work": "Metro Centre"})
        self.assertEqual(typo["errors"], {"work": "unknown_station"})
        with (
            patch.object(flow, "async_set_unique_id", AsyncMock()) as unique,
            patch.object(flow, "_abort_if_unique_id_configured"),
        ):
            # A name typed into the search box works as well as a picked row.
            result = await flow.async_step_commute(
                {"home": "foggy bottom-gwu", "work": "C01", "name": " "}
            )
        unique.assert_awaited_once_with("commute:C04:A01")
        self.assertEqual(result["title"], "Foggy Bottom-GWU ↔ Metro Center")
        self.assertEqual(
            result["data"],
            {
                "api_key": "test",
                "service_type": "commute",
                "id": "C04-A01",
                "home": "C04",
                "work": "A01",
                "location_name": "Commute",
            },
        )

    async def test_options_offer_polling_and_platform_time_only(self):
        flow = WmataOptionsFlow()
        with patch.object(
            WmataOptionsFlow,
            "config_entry",
            new_callable=PropertyMock,
            return_value=commute_entry(),
        ):
            form = await flow.async_step_init()
            self.assertEqual(form["step_id"], "settings")
            fields = {str(key) for key in form["data_schema"].schema}
            self.assertEqual(fields, {"scan_interval", "transfer_buffer"})
            saved = await flow.async_step_settings(
                {"scan_interval": 60, "transfer_buffer": 5}
            )
        self.assertEqual(saved["data"], {"scan_interval": 60, "transfer_buffer": 5})

    async def test_a_commute_sensor_can_lend_its_key_to_the_planner_card(self):
        api = object()
        e = SimpleNamespace(
            entry_id="commute",
            domain="wmata",
            data={"service_type": "commute"},
            runtime_data=SimpleNamespace(api=api),
        )
        registry = MagicMock()
        registry.async_get.return_value = SimpleNamespace(
            config_entry_id=e.entry_id, platform="wmata", domain="sensor"
        )
        hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_get_entry=lambda _: e)
        )
        connection = MagicMock()
        connection.user.permissions.check_entity.return_value = True
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            self.assertIs(
                planner_client(hass, connection, {"id": 1, "entity_id": "sensor.c"}),
                api,
            )
            connection.user.permissions.check_entity.return_value = False
            self.assertIsNone(
                planner_client(hass, connection, {"id": 2, "entity_id": "sensor.c"})
            )

    async def test_diagnostics_describe_the_estimate_without_naming_stations(self):
        secret = "PRIVATE-STATION"
        trip = {
            "arrival": 1.0,
            "transfers": 1,
            "schedule_estimate": True,
            "route": {"origin_name": secret},
            "route_description": secret,
        }
        coordinator = SimpleNamespace(
            data={"trips": {"outbound": trip, "return": None}, "updated_at": "now"},
            update_interval=None,
            last_update_success=True,
            last_exception=None,
        )
        e = SimpleNamespace(
            data={"service_type": "commute", "api_key": secret, "home": secret},
            options={},
            version=2,
            state=SimpleNamespace(value="loaded"),
            runtime_data=coordinator,
        )
        result = await async_get_config_entry_diagnostics(None, e)
        self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(result["service"], "commute")
        self.assertEqual(
            result["commute"]["outbound"],
            {
                "has_route": True,
                "has_arrival_estimate": True,
                "transfers": 1,
                "schedule_estimate": True,
            },
        )
        self.assertFalse(result["commute"]["return"]["has_route"])
