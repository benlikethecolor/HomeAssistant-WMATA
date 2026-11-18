"""Planning, metadata changes, historical upgrades and prolonged failure recovery."""

import asyncio
import importlib.util
import inspect
import io
import json
import unittest
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.wmata import async_migrate_entry
from custom_components.wmata.api import APIConnectionError, WmataApi
from custom_components.wmata.health import health_snapshot
from custom_components.wmata.journeys import plan_journey
from custom_components.wmata.planning import (
    accessibility,
    filter_accessible,
    scheduled_journeys,
)
from custom_components.wmata.schedules import RailSchedule
from custom_components.wmata.sensor import (
    WmataHealthSensor,
    async_setup_entry,
)
from custom_components.wmata.websocket import plan_trip
from tests import test_wmata as wmata_tests
from tests.test_schedules import LEG, NOW, feed
from tests.test_transfer_predictions import fixture
from tests.test_wmata import entry

_spec = importlib.util.spec_from_file_location(
    "wmata_monitor", Path(__file__).resolve().parents[1] / "tools/monitor_soak.py"
)
_monitor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_monitor)
sample = _monitor.sample


class FuturePlanningTest(unittest.TestCase):
    def test_future_service_days_are_loaded_and_feed_expiry_is_respected(self):
        schedule = RailSchedule(feed(day="20261119"), now=NOW)
        requested = NOW + timedelta(days=6)
        route = plan_journey("C04", "A01")
        trips = scheduled_journeys(schedule, [route], requested, "depart_at", 3, NOW)
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0]["trip_minutes"], 4)
        self.assertTrue(trips[0]["schedule_estimate"])
        self.assertEqual(schedule.departures(LEG, NOW + timedelta(days=8)), [])

    def test_transfer_buffer_and_arrive_by_deadline_select_catchable_connections(self):
        route = plan_journey("C04", "B35")
        base = NOW

        def train(depart, arrive, line):
            return {
                "departure_at": (base + timedelta(minutes=depart)).isoformat(),
                "arrival_at": (base + timedelta(minutes=arrive)).isoformat(),
                "line": line,
                "line_name": "Orange" if line == "OR" else "Red",
            }

        board = {
            "Foggy Bottom-GWU": [train(2, 6, "OR"), train(10, 14, "OR")],
            "Metro Center": [
                train(7, 11, "RD"),
                train(10, 14, "RD"),
                train(20, 24, "RD"),
            ],
        }
        schedule = SimpleNamespace(
            departures=lambda leg, begin, limit=None: board[leg["from_name"]]
        )
        first = scheduled_journeys(schedule, [route], base, "depart_at", 3, base)[0]
        self.assertEqual(first["arrival_at"], train(10, 14, "RD")["arrival_at"])
        self.assertEqual(first["legs"][1]["wait_minutes"], 4)
        later = scheduled_journeys(
            schedule, [route], base + timedelta(minutes=25), "arrive_by", 3, base
        )[0]
        self.assertEqual(later["departure_at"], train(10, 14, "OR")["departure_at"])
        self.assertEqual(
            scheduled_journeys(
                schedule, [route], base + timedelta(minutes=10), "arrive_by", 3, base
            ),
            [],
        )

    def test_elevator_warnings_include_transfer_aliases_and_exclude_pass_through_stations(
        self,
    ):
        route = plan_journey("C04", "B35")
        units = [
            {"type": "elevator", "station_code": "C01"},
            {"type": "elevator", "station_code": "C03"},
            {"type": "escalator", "station_code": "A01"},
        ]
        warnings = accessibility([route], units)
        self.assertEqual([u["station_name"] for u in warnings], ["Metro Center"])
        self.assertEqual(filter_accessible([route], warnings, True), [])
        self.assertEqual(filter_accessible([route], warnings, False), [route])


class PlanningApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_scheduled_plan_does_not_request_live_predictions(self):
        hass, ent, entity, registry, conn, api = fixture(plan_journey("C04", "A01"))

        async def execute(func, *args):
            return func(*args)

        hass.async_add_executor_job = execute
        requested = datetime.now(UTC) + timedelta(hours=1)
        api.rail_schedule_nowait.return_value = SimpleNamespace(
            departures=lambda leg, begin, limit=None: [
                {
                    "departure_at": requested.isoformat(),
                    "arrival_at": (requested + timedelta(minutes=4)).isoformat(),
                    "line": "OR",
                    "line_name": "Orange",
                }
            ]
        )
        with patch(
            "custom_components.wmata.websocket.er.async_get", return_value=registry
        ):
            await inspect.unwrap(plan_trip)(
                hass,
                conn,
                {
                    "id": 1,
                    "entity_id": "sensor.trip",
                    "origin": "C04",
                    "destination": "A01",
                    "mode": "depart_at",
                    "when": requested.isoformat(),
                },
            )
        self.assertEqual(
            len(conn.send_result.call_args.args[1]["planning"]["journeys"]), 1
        )
        api.trains.assert_not_awaited()

    async def test_outage_filter_requires_a_current_feed_and_invalid_dates_are_rejected(
        self,
    ):
        for extra, code in [
            ({"accessibility": "avoid"}, "accessibility_unavailable"),
            ({"mode": "depart_at", "when": "2020-01-01"}, "invalid_time"),
        ]:
            hass, ent, entity, registry, conn, api = fixture()
            with patch(
                "custom_components.wmata.websocket.er.async_get", return_value=registry
            ):
                await inspect.unwrap(plan_trip)(
                    hass,
                    conn,
                    {
                        "id": 1,
                        "entity_id": "sensor.trip",
                        "origin": "C04",
                        "destination": "A01",
                        **extra,
                    },
                )
            self.assertEqual(conn.send_error.call_args.args[1], code)
            api.trains.assert_not_awaited()


class ReliabilityTest(unittest.IsolatedAsyncioTestCase):
    async def test_metadata_refresh_replaces_routes_and_recovers_from_a_failed_refresh(
        self,
    ):
        self.hass = HomeAssistant("/tmp/wmata-next-test")
        test = wmata_tests.IntegrationTest()
        test.hass = self.hass
        try:
            with patch(
                "custom_components.wmata.coordinator.async_get_clientsession",
                return_value=MagicMock(),
            ):
                c = test.coordinator(entry("bus", "1001195"))
            c.api.stop_info.return_value = {"Name": "First", "Routes": ["D34v1"]}
            c.data = await c._async_update_data()
            self.assertEqual(c.routes, {"D34"})
            c._metadata_refresh_at = 0
            c.api.stop_info.side_effect = APIConnectionError("offline")
            c.data = await c._async_update_data()
            self.assertEqual(c.location_name, "First")
            self.assertTrue(c.metadata_status["stale"])
            self.assertEqual(health_snapshot(c)["status"], "degraded")
            self.assertEqual(c.routes, {"D34"})
            self.assertGreater(
                c._metadata_refresh_at, asyncio.get_running_loop().time()
            )
            c._metadata_refresh_at = 0
            c.api.stop_info.side_effect = None
            c.api.stop_info.return_value = {"Name": "Updated", "Routes": ["D36"]}
            c.data = await c._async_update_data()
            self.assertEqual(c.routes, {"D36"})
            self.assertEqual(c.location_name, "Updated")
            self.assertFalse(c.metadata_status["stale"])
        finally:
            await self.hass.async_stop(force=True)

    async def test_new_lines_register_optional_entities_without_reloading(self):
        hass = HomeAssistant("/tmp/wmata-next-lines")
        test = wmata_tests.IntegrationTest()
        test.hass = hass
        try:
            with patch(
                "custom_components.wmata.coordinator.async_get_clientsession",
                return_value=MagicMock(),
            ):
                c = test.coordinator()
            e = entry()
            e.runtime_data = c
            c.served_lines = ["RD"]
            c.async_add_listener = MagicMock()
            add = MagicMock()
            with (
                patch("custom_components.wmata.sensor.er.async_get"),
                patch(
                    "custom_components.wmata.sensor.er.async_entries_for_config_entry",
                    return_value=[],
                ),
            ):
                await async_setup_entry(hass, e, add)
            callback = c.async_add_listener.call_args.args[0]
            c.served_lines = ["RD", "OR"]
            callback()
            self.assertTrue(
                all(s.journey["lines"] == ["OR"] for s in add.call_args.args[0])
            )
            add.reset_mock()
            callback()
            add.assert_not_called()
        finally:
            await hass.async_stop(force=True)

    async def test_withdrawn_line_entity_identity_survives_an_entry_reload(self):
        hass = HomeAssistant("/tmp/wmata-withdrawn-line")
        test = wmata_tests.IntegrationTest()
        test.hass = hass
        try:
            with patch(
                "custom_components.wmata.coordinator.async_get_clientsession",
                return_value=MagicMock(),
            ):
                c = test.coordinator()
            c.served_lines = ["RD"]
            e = entry()
            e.runtime_data = c
            retired = SimpleNamespace(
                platform="wmata",
                domain="sensor",
                unique_id="wmata_train_a01_journey_line_OR_eastbound",
                entity_id="sensor.my_orange_arrival",
            )
            add = MagicMock()
            registry = MagicMock()
            with (
                patch(
                    "custom_components.wmata.sensor.er.async_get", return_value=registry
                ),
                patch(
                    "custom_components.wmata.sensor.er.async_entries_for_config_entry",
                    return_value=[retired],
                ),
            ):
                await async_setup_entry(hass, e, add)
            sensor = next(
                s for s in add.call_args.args[0] if s.unique_id == retired.unique_id
            )
            self.assertFalse(sensor.available)
            registry.async_remove.assert_not_called()
        finally:
            await hass.async_stop(force=True)

    async def test_72_hours_of_incident_outages_preserve_last_success_then_recover(
        self,
    ):
        api = WmataApi(MagicMock(), "fixture")
        api.get = AsyncMock(return_value={"Incidents": []})
        clock = [0]
        fake_asyncio = SimpleNamespace(
            get_running_loop=lambda: SimpleNamespace(time=lambda: clock[0])
        )
        with (
            patch("custom_components.wmata.api.asyncio", fake_asyncio),
            patch("custom_components.wmata.api.datetime") as wall,
        ):
            wall.now.side_effect = lambda zone: NOW + timedelta(seconds=clock[0])
            await api.rail_alerts()
            checked = api.alert_status("rail")["updated_at"]
            api.get.side_effect = APIConnectionError("offline")
            for hour in range(1, 73):
                clock[0] = hour * 3600
                await api.rail_alerts()
                self.assertEqual(
                    api.alert_status("rail"), {"updated_at": checked, "stale": True}
                )
                # Repeated callers during the retry interval share the cached result.
                await api.rail_alerts()
                self.assertEqual(api.get.await_count, hour + 1)
            clock[0] += 3600
            api.get.side_effect = None
            await api.rail_alerts()
            self.assertFalse(api.alert_status("rail")["stale"])
            self.assertEqual(
                api.alert_status("rail")["updated_at"],
                (NOW + timedelta(hours=73)).isoformat(),
            )

    async def test_historical_entry_data_preserves_keys_locations_and_saved_journeys(
        self,
    ):
        fixtures = json.loads(
            (Path(__file__).parent / "fixtures/historical_entries.json").read_text()
        )
        for row in fixtures:
            e = SimpleNamespace(**{k: row[k] for k in ("version", "data", "options")})
            update = MagicMock()
            hass = SimpleNamespace(
                config_entries=SimpleNamespace(async_update_entry=update)
            )
            self.assertTrue(await async_migrate_entry(hass, e))
            result = (
                update.call_args.kwargs
                if update.called
                else {"data": e.data, "options": e.options}
            )
            self.assertEqual(result["data"]["api_key"], "fixture")
            self.assertEqual(result["data"]["id"], row["data"]["id"])
            self.assertEqual(
                result["options"].get("journeys", []),
                row["options"].get("journeys", []),
            )

    async def test_health_survives_poll_failure_and_excludes_credentials(self):
        api = WmataApi(MagicMock(), "secret-key")
        api._state.last_success = NOW.isoformat()
        api._state.blocked_until = asyncio.get_running_loop().time() + 60
        c = SimpleNamespace(api=api, last_update_success=False)
        status = health_snapshot(c)
        self.assertEqual(status["status"], "rate_limited")
        self.assertNotIn("secret-key", json.dumps(status))
        reference = SimpleNamespace(unique_id="board", device_info=None)
        sensor = WmataHealthSensor(c, reference)
        self.assertTrue(sensor.available)
        self.assertFalse(sensor.entity_registry_enabled_default)


class MonitorTest(unittest.TestCase):
    def test_monitor_redacts_payloads_and_refuses_non_health_entities(self):
        payload = {
            "state": "healthy",
            "attributes": {
                "polling_available": True,
                "timetable": "ready",
                "api_key": "secret",
                "arrivals": [{"destination": "private"}],
            },
        }
        response = MagicMock()
        response.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
        with patch("urllib.request.urlopen", return_value=response):
            result = sample("http://localhost:8123", "token-secret", "sensor.health")
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("private", json.dumps(result))
        response.__enter__.return_value = io.BytesIO(
            json.dumps({"state": "secret", "attributes": {}}).encode()
        )
        with patch("urllib.request.urlopen", return_value=response):
            self.assertEqual(
                sample("http://localhost:8123", "token", "sensor.other")["error"],
                "not_health_entity",
            )
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("private response"),
        ):
            self.assertNotIn(
                "private",
                json.dumps(sample("http://localhost:8123", "token", "sensor.health")),
            )


class HealthCounterTest(unittest.IsolatedAsyncioTestCase):
    async def test_health_records_success_and_failure_without_response_bodies(self):
        api = WmataApi(MagicMock(), "secret-key")
        api._request = AsyncMock(return_value={})
        await api.get("fixture")
        self.assertIsNotNone(api.health()["last_successful_request"])
        api._state.next_request = 0
        api._request.side_effect = APIConnectionError("private response")
        with self.assertRaises(APIConnectionError):
            await api.get("fixture")
        status = api.health()
        self.assertEqual(status["requests"], 2)
        self.assertEqual(status["failures"], 1)
        self.assertEqual(status["last_error_type"], "APIConnectionError")
        self.assertNotIn("private", json.dumps(status))
        self.assertNotIn("secret", json.dumps(status))
