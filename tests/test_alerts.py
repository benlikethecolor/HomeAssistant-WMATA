"""Service alerts, elevator outages and last trains."""

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.wmata.alerts import (
    alerts_for,
    bus_alert,
    rail_alert,
    unit_outage,
)
from custom_components.wmata.api import APIAuthError, APIConnectionError, WmataApi
from custom_components.wmata.binary_sensor import (
    WmataAlertSensor,
    WmataCommuteAlertSensor,
    WmataElevatorSensor,
    WmataLastTrainSensor,
)
from custom_components.wmata.binary_sensor import async_setup_entry as setup_binary
from custom_components.wmata.coordinator import APIData
from custom_components.wmata.sensor import WmataBoardSensor, WmataJourneySensor
from tests import test_wmata
from tests.test_wmata import entry

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "wmata_api.json").read_text()
)
RAIL = FIXTURE["Incidents.svc/json/Incidents"]["Incidents"]
BUS = FIXTURE["Incidents.svc/json/BusIncidents"]["BusIncidents"]
UNITS = FIXTURE["Incidents.svc/json/ElevatorIncidents"]["ElevatorIncidents"]


class ParsingTest(unittest.TestCase):
    def test_rail_alerts_list_their_lines_and_use_eastern_time(self):
        red, green = map(rail_alert, RAIL)
        self.assertEqual(red["lines"], ["RD"])
        self.assertEqual(red["type"], "delay")
        self.assertEqual(red["updated_at"], "2026-11-13T08:15:00-05:00")
        self.assertEqual(green["lines"], ["GR", "YL"])
        self.assertEqual(green["type"], "alert")

    def test_rows_without_a_line_or_description_are_dropped(self):
        for raw in (
            {},
            {"Description": "No lines named", "LinesAffected": ""},
            {"Description": " ", "LinesAffected": "RD;"},
            {"Description": "Unknown line", "LinesAffected": "ZZ;"},
            {"Description": "Bad type", "LinesAffected": None},
        ):
            self.assertIsNone(rail_alert(raw), raw)
        self.assertIsNone(bus_alert({"Description": "x", "RoutesAffected": "D34"}))
        self.assertIsNone(unit_outage({"StationCode": "ZZ9", "UnitType": "ELEVATOR"}))
        self.assertIsNone(unit_outage({"StationCode": "A01", "UnitType": "STAIRS"}))

    def test_bus_alerts_match_route_variants(self):
        alert = bus_alert(BUS[0])
        self.assertEqual(alert["routes"], ["D34", "D36"])
        self.assertEqual(alerts_for([alert], routes=["D34v1"]), [alert])
        self.assertEqual(alerts_for([alert], routes=["d36*2"]), [alert])
        self.assertEqual(alerts_for([alert], routes=["C10"]), [])
        self.assertEqual(alerts_for([alert], lines=["RD"]), [])
        self.assertEqual(alerts_for(None, lines=["RD"]), [])

    def test_unit_outages_keep_what_a_rider_needs(self):
        elevator, escalator = map(unit_outage, UNITS)
        self.assertEqual(elevator["type"], "elevator")
        self.assertEqual(elevator["station_code"], "A01")
        self.assertEqual(elevator["location"], "Elevator between street and mezzanine")
        self.assertEqual(elevator["estimated_return"], "2026-11-15T23:59:59-05:00")
        self.assertEqual(escalator["type"], "escalator")
        self.assertIsNone(escalator["estimated_return"])


class AlertApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_alerts_are_shared_by_key_and_fetched_once_a_minute(self):
        hass = SimpleNamespace(data={})
        one = WmataApi(MagicMock(), "same", hass=hass)
        two = WmataApi(MagicMock(), "same", hass=hass)
        one.get = AsyncMock(return_value={"Incidents": RAIL})
        two.get = AsyncMock()
        self.assertEqual(len(await one.rail_alerts()), 2)
        self.assertEqual(len(await two.rail_alerts()), 2)
        one.get.assert_awaited_once_with("Incidents.svc/json/Incidents")
        two.get.assert_not_awaited()
        one._state.alerts["rail"] = (0, one._state.alerts["rail"][1])
        # After a minute the next caller, whichever entry it is, refreshes.
        two.get.return_value = {"Incidents": RAIL[:1]}
        self.assertEqual(len(await two.rail_alerts()), 1)

    async def test_an_outage_keeps_the_last_alerts_and_never_raises(self):
        api = WmataApi(MagicMock(), "key")
        api.get = AsyncMock(return_value={"Incidents": RAIL})
        known = await api.rail_alerts()
        api._state.alerts["rail"] = (0, known)
        api.get.side_effect = APIConnectionError("Offline")
        self.assertEqual(await api.rail_alerts(), known)
        # Backed off, so the next poll doesn't ask again straight away.
        await api.rail_alerts()
        self.assertEqual(api.get.await_count, 2)

    async def test_a_key_without_incident_access_still_works(self):
        api = WmataApi(MagicMock(), "key")
        api.get = AsyncMock(side_effect=APIAuthError())
        self.assertEqual(await api.rail_alerts(), [])
        self.assertEqual(await api.bus_alerts(), [])
        self.assertEqual(await api.unit_outages(), [])
        self.assertEqual(api.get.await_count, 3)
        await api.unit_outages()
        self.assertEqual(api.get.await_count, 3)

    async def test_malformed_feeds_are_treated_as_no_alerts(self):
        api = WmataApi(MagicMock(), "key")
        api.get = AsyncMock(return_value={"Incidents": None})
        self.assertEqual(await api.rail_alerts(), [])
        api.get.return_value = {"ElevatorIncidents": [UNITS[0], {"junk": 1}]}
        self.assertEqual(len(await api.unit_outages()), 1)


class AlertEntityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = test_wmata.IntegrationTest()
        self.hass = self.fixture.hass = HomeAssistant("/tmp/wmata-alerts")
        self.patch = patch(
            "custom_components.wmata.coordinator.async_get_clientsession",
            return_value=MagicMock(),
        )
        self.patch.start()

    async def asyncTearDown(self):
        self.patch.stop()
        await self.hass.async_stop(force=True)

    async def test_station_shows_alerts_for_its_lines_and_its_own_elevators(self):
        c = self.fixture.coordinator()
        c.api.rail_alerts.return_value = [rail_alert(row) for row in RAIL]
        c.api.unit_outages.return_value = [unit_outage(row) for row in UNITS]
        c.data = await c._async_update_data()
        # Metro Center has Red, Blue, Orange and Silver, but not Green or Yellow.
        board = WmataBoardSensor(c)
        attributes = board.extra_state_attributes
        self.assertEqual([a["id"] for a in attributes["alerts"]], ["RD-1"])
        self.assertEqual([u["unit"] for u in attributes["outages"]], ["A01E01"])
        self.assertTrue({"alerts", "outages"} <= board._unrecorded_attributes)
        alert = WmataAlertSensor(c)
        self.assertTrue(alert.is_on)
        self.assertTrue(alert.entity_registry_enabled_default)
        self.assertIn("signal problem", alert.extra_state_attributes["summary"])
        self.assertEqual(alert.unique_id, "wmata_train_a01_board_alert")
        elevator = WmataElevatorSensor(c)
        self.assertTrue(elevator.is_on)
        self.assertFalse(elevator.entity_registry_enabled_default)
        self.assertEqual(elevator.extra_state_attributes["escalators"], [])
        # A journey follows its own lines, including one it transfers to.
        blue = WmataJourneySensor(c, {"id": "b", "name": "Blue", "lines": ["BL"]})
        self.assertEqual(blue.extra_state_attributes["alerts"], [])
        trip = {
            "id": "t",
            "name": "To Greenbelt",
            "kind": "station_to_station",
            "route": {
                "origin": "A01",
                "origin_name": "Metro Center",
                "legs": [
                    {"lines": ["RD"], "to_name": "Fort Totten"},
                    {"lines": ["GR"], "to_name": "Greenbelt"},
                ],
            },
        }
        self.assertEqual(
            [a["id"] for a in WmataJourneySensor(c, trip).alerts], ["RD-1", "GR-1"]
        )
        c.api.rail_alerts.return_value = []
        c.api.unit_outages.return_value = [unit_outage(UNITS[1])]
        c.data = await c._async_update_data()
        self.assertFalse(alert.is_on)
        self.assertIsNone(alert.extra_state_attributes["summary"])
        self.assertFalse(elevator.is_on)

    async def test_bus_stop_matches_alerts_to_routes_seen_there(self):
        c = self.fixture.coordinator(entry("bus", "1001195"))
        c.api.bus_alerts.return_value = [bus_alert(BUS[0])]
        c.api.buses.return_value = [{"Minutes": 4, "RouteID": "D34v1"}]
        c.data = await c._async_update_data()
        alert = WmataAlertSensor(c)
        self.assertTrue(alert.is_on)
        # The route is remembered through a gap with no buses predicted.
        c.api.buses.return_value = []
        c.data = await c._async_update_data()
        self.assertTrue(alert.is_on)
        other = self.fixture.coordinator(entry("bus", "1001051"))
        other.api.bus_alerts.return_value = [bus_alert(BUS[0])]
        other.api.buses.return_value = [{"Minutes": 4, "RouteID": "C10"}]
        other.data = await other._async_update_data()
        self.assertFalse(WmataAlertSensor(other).is_on)

    async def test_last_train_sensor_names_the_trains(self):
        c = self.fixture.coordinator()
        c.data = APIData(
            [],
            [
                {"Line": "RD", "Min": "6", "DestinationName": "Glenmont"},
                {
                    "Line": "RD",
                    "Min": "14",
                    "LocationCode": "A01",
                    "DestinationCode": "A15",
                    "DestinationName": "Last Train",
                },
            ],
        )
        sensor = WmataLastTrainSensor(c)
        self.assertTrue(sensor.is_on)
        self.assertFalse(sensor.entity_registry_enabled_default)
        self.assertEqual(
            sensor.extra_state_attributes["trains"],
            [
                {
                    "line": "RD",
                    "line_name": "Red",
                    "destination": "Shady Grove",
                    "direction": "Westbound",
                    "minutes": 14,
                }
            ],
        )
        c.data = APIData([], [{"Line": "RD", "Min": "6"}])
        self.assertFalse(sensor.is_on)
        c.data = None
        self.assertFalse(sensor.is_on)

    async def test_each_service_gets_the_binary_sensors_that_apply(self):
        add = MagicMock()
        for service, location, expected in (
            ("train", "A01", ["due_soon", "alert", "last_train", "elevator_outage"]),
            ("bus", "1001195", ["due_soon", "alert"]),
        ):
            e = entry(service, location)
            e.runtime_data = self.fixture.coordinator(e)
            await setup_binary(self.hass, e, add)
            self.assertEqual(
                [s.unique_id.rsplit("_board_", 1)[1] for s in add.call_args.args[0]],
                expected,
            )
        add.reset_mock()
        e = entry("map", "network")
        e.runtime_data = None
        await setup_binary(self.hass, e, add)
        add.assert_not_called()

    async def test_commute_alert_covers_both_directions_without_repeats(self):
        red = rail_alert(RAIL[0])
        green = rail_alert(RAIL[1])
        coordinator = SimpleNamespace(
            home="C04",
            work="B35",
            commute_name="Commute",
            data={
                "trips": {
                    "outbound": {"alerts": [red]},
                    "return": {"alerts": [red, green]},
                }
            },
            last_update_success=True,
            async_add_listener=MagicMock(),
        )
        sensor = WmataCommuteAlertSensor(coordinator)
        self.assertTrue(sensor.is_on)
        self.assertEqual(
            [a["id"] for a in sensor.extra_state_attributes["alerts"]],
            ["RD-1", "GR-1"],
        )
        coordinator.data = {"trips": {"outbound": None, "return": {"alerts": []}}}
        self.assertFalse(sensor.is_on)
        coordinator.data = None
        self.assertFalse(sensor.is_on)
