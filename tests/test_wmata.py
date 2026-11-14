"""Run with python -m unittest discover -s tests -v inside an HA environment."""

import asyncio
import unittest
from inspect import signature
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.wmata import (
    _async_update_listener,
    async_migrate_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.wmata.api import (
    APIAuthError,
    APIConnectionError,
    InvalidLocation,
    WmataApi,
)
from custom_components.wmata.config_flow import (
    WmataConfigFlow,
    WmataOptionsFlow,
    search_start,
    stop_label,
    validate_location,
)
from custom_components.wmata.const import CARD_VERSION, station_codes
from custom_components.wmata.coordinator import (
    APIData,
    WmataCoordinator,
    prediction_minutes,
    sorted_predictions,
)
from custom_components.wmata.frontend import async_setup_card
from custom_components.wmata.predictions import filter_arrivals, normalize_prediction
from custom_components.wmata.sensor import WmataBoardSensor, WmataJourneySensor
from custom_components.wmata.sensor import async_setup_entry as setup_sensors


def entry(service="train", location="A01", options=None, version=2, **data):
    return ConfigEntry(
        domain="wmata",
        title="Test",
        data={"api_key": "test-key", "id": location, "service_type": service, **data},
        options=options or {},
        version=version,
        minor_version=1,
        source="user",
        unique_id=location,
        discovery_keys={},
        **(
            {"subentries_data": []}
            if "subentries_data" in signature(ConfigEntry).parameters
            else {}
        ),
    )


STATIONS = [
    {
        "Code": "A01",
        "Name": "Metro Center",
        "StationTogether1": "C01",
        "LineCode1": "RD",
    },
    {
        "Code": "C01",
        "Name": "Metro Center",
        "StationTogether1": "A01",
        "LineCode1": "BL",
        "LineCode2": "OR",
        "LineCode3": "SV",
    },
    {"Code": "G01", "Name": "Benning Road", "LineCode1": "BL", "LineCode2": "SV"},
]


class PredictionsTest(unittest.TestCase):
    def test_statuses_and_unknowns(self):
        for value, expected in [
            ("ARR", 0),
            ("BRD", 0),
            ("3", 3),
            (7, 7),
            (None, None),
            ("", None),
            ("---", None),
            ("DLY", None),
            (-1, None),
        ]:
            with self.subTest(value=value):
                self.assertEqual(prediction_minutes(value), expected)

    def test_transfer_station_codes(self):
        self.assertEqual(set(station_codes("A01")), {"A01", "C01"})
        self.assertEqual(set(station_codes("F03")), {"D03", "F03"})
        self.assertEqual(station_codes("G01"), ["G01"])

    def test_sort_unknown_last_and_boarding_first(self):
        items = [{"Min": "10"}, {"Min": None}, {"Min": "BRD"}, {"Min": "2"}]
        self.assertEqual(
            [p["Min"] for p in sorted_predictions(items, "Min")],
            ["BRD", "2", "10", None],
        )


class IntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = HomeAssistant("/tmp/wmata-unit-hass")
        self.session_patch = patch(
            "custom_components.wmata.coordinator.async_get_clientsession",
            return_value=MagicMock(),
        )
        self.session_patch.start()

    async def asyncTearDown(self):
        self.session_patch.stop()
        await self.hass.async_stop(force=True)

    def coordinator(self, e=None):
        c = WmataCoordinator(self.hass, e or entry())
        c.api = SimpleNamespace(
            stations=AsyncMock(return_value=STATIONS),
            trains=AsyncMock(return_value=[]),
            buses=AsyncMock(return_value=[]),
            stop_name=AsyncMock(return_value="Test stop"),
        )
        return c

    async def test_train_board_keeps_every_line_and_loads_metadata_once(self):
        c = self.coordinator()
        c.api.trains.return_value = [
            {"Min": "3", "Line": "BL"},
            {"Min": "7", "Line": "RD"},
        ]
        data = await c._async_update_data()
        self.assertEqual(len(data.next_trains), 2)
        self.assertEqual(data.arrivals[0]["line"], "BL")
        self.assertEqual(set(c.codes), {"A01", "C01"})
        self.assertEqual(set(c.served_lines), {"RD", "BL", "OR", "SV"})
        await c._async_update_data()
        c.api.stations.assert_awaited_once()
        c.api.trains.assert_awaited_with(c.codes)

    async def test_bus_board_keeps_every_route_and_uses_the_stop_name(self):
        c = self.coordinator(entry("bus", "1001195"))
        c.api.buses.return_value = [
            {"Minutes": 5, "RouteID": "D10"},
            {"Minutes": 1, "RouteID": "C10"},
        ]
        data = await c._async_update_data()
        self.assertEqual(len(data.next_buses), 2)
        self.assertEqual(data.arrivals[0]["route"], "C10")
        self.assertEqual(c.location_name, "Test stop")

    async def test_auth_and_outages(self):
        c = self.coordinator()
        c.api.stations.side_effect = APIAuthError()
        with self.assertRaises(ConfigEntryAuthFailed):
            await c._async_update_data()
        c.api.stations.side_effect = APIConnectionError("Offline")
        with self.assertRaises(UpdateFailed):
            await c._async_update_data()

    async def test_board_and_journey_empty_statuses_and_failed_refresh(self):
        c = self.coordinator()
        c.data = APIData(
            [],
            [
                {
                    "Min": "BRD",
                    "Line": "RD",
                    "DestinationName": "Glenmont",
                    "DestinationCode": "B11",
                    "Group": "1",
                },
                {
                    "Min": "7",
                    "Line": "BL",
                    "DestinationName": "Downtown Largo",
                    "DestinationCode": "G05",
                    "Group": "2",
                },
            ],
        )
        board = WmataBoardSensor(c)
        self.assertEqual(board.unique_id, "wmata_train_a01_board")
        self.assertEqual(board.native_value, 0)
        self.assertEqual(board.extra_state_attributes["arrival_count"], 2)
        self.assertEqual(board.arrivals[0]["status"], "boarding")
        journey = WmataJourneySensor(
            c,
            {
                "id": "saved",
                "name": "Blue to Largo",
                "lines": ["BL"],
                "destinations": ["G05"],
            },
        )
        self.assertEqual(journey.native_value, 7)
        self.assertEqual(journey.extra_state_attributes["arrival_count"], 1)
        self.assertEqual(journey.extra_state_attributes["board_type"], "journey")
        renamed = WmataJourneySensor(
            c, {"id": "saved", "name": "Renamed", "lines": ["BL"]}
        )
        self.assertEqual(journey.unique_id, renamed.unique_id)
        c.data = APIData([], [])
        self.assertIsNone(board.native_value)
        self.assertEqual(board.arrivals, [])
        c.last_update_success = False
        self.assertFalse(board.available)
        c.last_update_success = True
        self.assertTrue(board.available)

    async def test_only_board_by_default_and_registry_reconciliation(self):
        c = self.coordinator()
        c.data = APIData([], [])
        e = entry()
        e.runtime_data = c
        add = MagicMock()
        registry = MagicMock()
        old = SimpleNamespace(
            entity_id="sensor.old",
            platform="wmata",
            domain="sensor",
            unique_id="wmata_a01_train_1",
        )
        deleted = SimpleNamespace(
            entity_id="sensor.removed_journey",
            platform="wmata",
            domain="sensor",
            unique_id="removed",
        )
        other = SimpleNamespace(
            entity_id="sensor.other",
            platform="different",
            domain="sensor",
            unique_id="other",
        )
        with (
            patch("custom_components.wmata.sensor.er.async_get", return_value=registry),
            patch(
                "custom_components.wmata.sensor.er.async_entries_for_config_entry",
                return_value=[old, deleted, other],
            ),
        ):
            await setup_sensors(self.hass, e, add)
        self.assertEqual(
            sum(s.entity_registry_enabled_default for s in add.call_args.args[0]), 1
        )
        self.assertEqual(registry.async_remove.call_count, 2)
        other_board = WmataBoardSensor(self.coordinator(entry(location="G01")))
        self.assertNotEqual(add.call_args.args[0][0].unique_id, other_board.unique_id)

    async def test_optional_journeys_have_stable_distinct_identities(self):
        e = entry(
            options={
                "journeys": [
                    {"id": "one", "name": "Work"},
                    {"id": "two", "name": "Home"},
                ]
            }
        )
        e.runtime_data = self.coordinator(e)
        add = MagicMock()
        with (
            patch("custom_components.wmata.sensor.er.async_get"),
            patch(
                "custom_components.wmata.sensor.er.async_entries_for_config_entry",
                return_value=[],
            ),
        ):
            await setup_sensors(self.hass, e, add)
        sensors = add.call_args.args[0]
        self.assertEqual(sum(s.entity_registry_enabled_default for s in sensors), 3)
        self.assertEqual(len({s.unique_id for s in sensors}), len(sensors))
        self.assertIn("arrivals", sensors[0]._unrecorded_attributes)

    async def test_v1_migration_preserves_credentials_and_polling(self):
        e = entry(
            version=1,
            lines=["RD"],
            options={"lines": ["RD"], "prediction_count": 6, "scan_interval": 60},
        )
        hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_update_entry=MagicMock())
        )
        self.assertTrue(await async_migrate_entry(hass, e))
        update = hass.config_entries.async_update_entry.call_args.kwargs
        self.assertEqual(update["version"], 2)
        self.assertEqual(update["data"]["api_key"], "test-key")
        self.assertNotIn("lines", update["data"])
        self.assertEqual(update["options"], {"scan_interval": 60, "journeys": []})

    async def test_newer_entry_versions_are_not_downgraded(self):
        hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_update_entry=MagicMock())
        )
        self.assertFalse(await async_migrate_entry(hass, entry(version=3)))
        self.assertTrue(await async_migrate_entry(hass, entry(version=2)))
        hass.config_entries.async_update_entry.assert_not_called()

    async def test_bundled_card_served_and_registered(self):
        hass = SimpleNamespace(
            http=SimpleNamespace(async_register_static_paths=AsyncMock())
        )
        with patch("custom_components.wmata.frontend.add_extra_js_url") as register:
            await async_setup_card(hass)
        config = hass.http.async_register_static_paths.call_args.args[0][0]
        self.assertEqual(config.url_path, "/wmata/wmata-station-card.js")
        register.assert_called_once_with(
            hass, f"/wmata/wmata-station-card.js?v={CARD_VERSION}"
        )

    async def test_setup_and_unload_listener(self):
        e = MagicMock()
        c = MagicMock()
        c.async_config_entry_first_refresh = AsyncMock()
        hass = SimpleNamespace(
            config_entries=SimpleNamespace(
                async_forward_entry_setups=AsyncMock(),
                async_unload_platforms=AsyncMock(return_value=True),
                async_reload=AsyncMock(),
            )
        )
        with patch("custom_components.wmata.WmataCoordinator", return_value=c):
            self.assertTrue(await async_setup_entry(hass, e))
        c.async_config_entry_first_refresh.assert_awaited_once()
        self.assertIs(e.runtime_data, c)
        e.async_on_unload.assert_called_once()
        self.assertTrue(await async_unload_entry(hass, e))
        await _async_update_listener(hass, e)
        hass.config_entries.async_reload.assert_awaited_once()

    async def test_location_validation(self):
        api = SimpleNamespace(
            stations=AsyncMock(return_value=STATIONS),
            trains=AsyncMock(return_value=[]),
            stop_name=AsyncMock(return_value="Bus stop"),
            buses=AsyncMock(return_value=[]),
        )
        with (
            patch("custom_components.wmata.config_flow.WmataApi", return_value=api),
            patch("custom_components.wmata.config_flow.async_get_clientsession"),
        ):
            data = await validate_location(self.hass, dict(entry().data, id=" a01 "))
            self.assertEqual(data["id"], "A01")
            self.assertEqual(data["station_codes"], ["A01", "C01"])
            with self.assertRaises(InvalidLocation):
                await validate_location(self.hass, dict(entry().data, id="ZZZ"))
            with self.assertRaises(InvalidLocation):
                await validate_location(self.hass, dict(entry("bus", "invalid").data))

    async def test_flow_forms_and_error_codes(self):
        flow = WmataConfigFlow()
        flow.hass = self.hass
        flow._async_current_entries = MagicMock(return_value=[])
        form = await flow.async_step_user()
        self.assertEqual(form["step_id"], "user")
        with (
            patch(
                "custom_components.wmata.config_flow.WmataApi.stations",
                return_value=STATIONS,
            ),
            patch("custom_components.wmata.config_flow.async_get_clientsession"),
        ):
            form = await flow.async_step_user(
                {"api_key": "test", "service_type": "train"}
            )
        self.assertEqual(form["step_id"], "location")
        for exception, field, code in [
            (APIAuthError(), "base", "invalid_auth"),
            (APIConnectionError(), "base", "cannot_connect"),
            (InvalidLocation(), "id", "invalid_location"),
        ]:
            with patch(
                "custom_components.wmata.config_flow.validate_location",
                side_effect=exception,
            ):
                form = await flow.async_step_location({"id": "A01"})
            self.assertEqual(form["errors"][field], code)

    async def test_initial_auth_error_keeps_key_editable(self):
        flow = WmataConfigFlow()
        flow.hass = self.hass
        flow._async_current_entries = MagicMock(return_value=[])
        with (
            patch(
                "custom_components.wmata.config_flow.WmataApi.stations",
                side_effect=APIAuthError(),
            ),
            patch("custom_components.wmata.config_flow.async_get_clientsession"),
        ):
            form = await flow.async_step_user(
                {"api_key": "invalid", "service_type": "train"}
            )
        self.assertEqual(form["step_id"], "user")
        self.assertEqual(form["errors"]["base"], "invalid_auth")

    async def test_transfer_alias_duplicate(self):
        flow = WmataConfigFlow()
        flow.hass = self.hass
        flow._async_current_entries = MagicMock(return_value=[])
        flow._setup_data = {"api_key": "test", "service_type": "train"}
        data = dict(
            entry(location="C01").data,
            station_codes=["A01", "C01"],
            location_name="Metro Center",
        )
        with (
            patch(
                "custom_components.wmata.config_flow.validate_location",
                return_value=data,
            ),
            patch.object(flow, "_async_current_entries", return_value=[entry()]),
        ):
            result = await flow.async_step_location({"id": "C01"})
        self.assertEqual(result["reason"], "already_configured")

    async def test_bus_stop_is_named_after_the_stop_and_only_added_once(self):
        flow = WmataConfigFlow()
        flow.hass = self.hass
        flow.context = {"source": "user"}
        flow._async_current_entries = MagicMock(return_value=[])
        flow._setup_data = {"api_key": "test", "service_type": "bus"}
        form = await flow.async_step_bus_stop()
        self.assertEqual(form["step_id"], "bus_stop")
        self.assertIn("buseta", form["description_placeholders"]["bus_stop_url"])
        api = SimpleNamespace(
            stop_name=AsyncMock(return_value="16th St NW + U St NW"),
            buses=AsyncMock(return_value=[]),
        )
        with (
            patch("custom_components.wmata.config_flow.WmataApi", return_value=api),
            patch("custom_components.wmata.config_flow.async_get_clientsession"),
            patch.object(flow, "async_set_unique_id", AsyncMock()) as unique,
            patch.object(flow, "_abort_if_unique_id_configured"),
        ):
            result = await flow.async_step_bus_stop({"id": " 1001195 "})
            unique.assert_awaited_once_with("bus:1001195")
            self.assertEqual(result["title"], "16th St NW + U St NW")
            self.assertEqual(result["data"]["id"], "1001195")
            api.buses.assert_awaited_once_with("1001195")
            # A rail station with the same digits would be a different service.
            flow._async_current_entries.return_value = [
                entry("train", "1001195"),
                entry("bus", "1001195"),
            ]
            again = await flow.async_step_bus_stop({"id": "1001195"})
        self.assertEqual(again["reason"], "already_configured")

    async def test_bus_stop_search_lists_the_closest_new_stops_first(self):
        flow = WmataConfigFlow()
        flow.hass = self.hass
        flow.context = {"source": "user"}
        flow._async_current_entries = MagicMock(
            return_value=[entry("bus", "1000003"), entry("train", "A01")]
        )
        flow._setup_data = {"api_key": "test", "service_type": "bus"}
        pin = {"latitude": 38.9000, "longitude": -77.0300}

        def stop(stop_id, name, latitude, routes=()):
            return {
                "StopID": stop_id,
                "Name": name,
                "Lat": latitude,
                "Lon": -77.03,
                "Routes": list(routes),
            }

        api = SimpleNamespace(
            nearby_stops=AsyncMock(
                return_value=[
                    stop("1000002", "Farther", 38.9040, ["D34", "D34v1", "C10*2"]),
                    stop("1000001", "Nearest", 38.9005),
                    stop("1000003", "Already added", 38.9001),
                    *[
                        stop(f"20000{i:02}", f"Stop {i}", 38.905 + i / 10000)
                        for i in range(20)
                    ],
                ]
            ),
            stop_name=AsyncMock(return_value="Nearest"),
            buses=AsyncMock(return_value=[]),
        )
        with (
            patch("custom_components.wmata.config_flow.WmataApi", return_value=api),
            patch("custom_components.wmata.config_flow.async_get_clientsession"),
            patch.object(flow, "async_set_unique_id", AsyncMock()),
            patch.object(flow, "_abort_if_unique_id_configured"),
        ):
            form = await flow.async_step_bus_stop({"near": pin})
            self.assertEqual(form["step_id"], "nearby_stop")
            api.nearby_stops.assert_awaited_once_with(38.9, -77.03, 800)
            options = form["data_schema"].schema["id"].config["options"]
            self.assertEqual([o["value"] for o in options[:2]], ["1000001", "1000002"])
            self.assertEqual(len(options), 16)
            self.assertEqual(options[-1]["value"], "search_again")
            self.assertEqual(form["description_placeholders"]["count"], "15")
            self.assertNotIn("1000003", [o["value"] for o in options])
            self.assertEqual(options[0]["label"], "Nearest · 60 m · #1000001")
            self.assertEqual(
                options[1]["label"], "Farther · D34, C10 · 440 m · #1000002"
            )
            again = await flow.async_step_nearby_stop({"id": "search_again"})
            self.assertEqual(again["step_id"], "bus_stop")
            result = await flow.async_step_nearby_stop({"id": "1000001"})
            self.assertEqual(result["title"], "Nearest")
            self.assertEqual(result["data"]["id"], "1000001")

    async def test_bus_stop_search_reports_empty_areas_and_outages(self):
        flow = WmataConfigFlow()
        flow.hass = self.hass
        flow._async_current_entries = MagicMock(return_value=[])
        flow._setup_data = {"api_key": "test", "service_type": "bus"}
        pin = {"latitude": 39.5, "longitude": -76.5}
        api = SimpleNamespace(nearby_stops=AsyncMock(return_value=[]))
        with (
            patch("custom_components.wmata.config_flow.WmataApi", return_value=api),
            patch("custom_components.wmata.config_flow.async_get_clientsession"),
        ):
            form = await flow.async_step_bus_stop({"near": pin})
            self.assertEqual(form["step_id"], "bus_stop")
            self.assertEqual(form["errors"], {"near": "no_stops_nearby"})
            # The pin stays where the user put it.
            near = next(k for k in form["data_schema"].schema if str(k) == "near")
            self.assertEqual(near.default(), pin)
            for error, code in (
                (APIConnectionError("Offline"), "cannot_connect"),
                (APIAuthError(), "invalid_auth"),
            ):
                api.nearby_stops.side_effect = error
                form = await flow.async_step_bus_stop({"near": pin})
                self.assertEqual(form["errors"], {"base": code})

    async def test_search_starts_at_home_only_inside_the_service_area(self):
        self.hass.config.latitude, self.hass.config.longitude = 38.93, -77.07
        self.assertEqual(
            search_start(self.hass), {"latitude": 38.93, "longitude": -77.07}
        )
        self.hass.config.latitude, self.hass.config.longitude = 52.37, 4.89
        self.assertEqual(
            search_start(self.hass), {"latitude": 38.8983, "longitude": -77.0281}
        )
        self.hass.config.units = US_CUSTOMARY_SYSTEM
        stop = {"StopID": "1000001", "Name": "Stop", "Routes": None}
        self.assertEqual(stop_label(self.hass, stop, 100), "Stop · 350 ft · #1000001")
        self.assertEqual(stop_label(self.hass, stop, 700), "Stop · 0.4 mi · #1000001")

    async def test_reauth_asks_for_a_key_and_keeps_the_form_when_it_is_rejected(self):
        flow = WmataConfigFlow()
        flow.hass = self.hass
        flow._async_current_entries = MagicMock(return_value=[])
        e = entry()
        with (
            patch.object(flow, "_get_reauth_entry", return_value=e),
            patch.object(
                flow, "async_update_reload_and_abort", return_value={"type": "abort"}
            ) as update,
        ):
            form = await flow.async_step_reauth(e.data)
            self.assertEqual(form["step_id"], "reauth_confirm")
            self.assertNotIn("test-key", str(form))
            with patch(
                "custom_components.wmata.config_flow.validate_location",
                side_effect=APIAuthError(),
            ):
                form = await flow.async_step_reauth_confirm({"api_key": "wrong"})
            self.assertEqual(form["errors"]["base"], "invalid_auth")
            update.assert_not_called()
            with patch(
                "custom_components.wmata.config_flow.validate_location",
                return_value=dict(e.data, api_key="new"),
            ):
                await flow.async_step_reauth_confirm({"api_key": "new"})
        self.assertEqual(update.call_args.kwargs["reason"], "reauth_successful")
        self.assertEqual(update.call_args.kwargs["data_updates"]["api_key"], "new")

    async def test_reconfigure_preserves_entry_and_reloads_once(self):
        flow = WmataConfigFlow()
        flow.hass = self.hass
        flow._async_current_entries = MagicMock(return_value=[])
        e = entry()
        with (
            patch.object(flow, "_get_reconfigure_entry", return_value=e),
            patch(
                "custom_components.wmata.config_flow.validate_location",
                return_value=dict(e.data, api_key="new"),
            ),
            patch.object(
                flow, "async_update_reload_and_abort", return_value={"type": "abort"}
            ) as update,
        ):
            await flow.async_step_reconfigure({"api_key": "new"})
        self.assertIs(update.call_args.args[0], e)
        self.assertEqual(update.call_args.kwargs["data_updates"]["api_key"], "new")

    async def test_options_settings_and_journey_crud(self):
        flow = WmataOptionsFlow()
        e = entry()
        with patch.object(
            WmataOptionsFlow,
            "config_entry",
            new_callable=unittest.mock.PropertyMock,
            return_value=e,
        ):
            menu = await flow.async_step_init()
            self.assertIn("add_journey", menu["menu_options"])
            journey_form = await flow.async_step_add_journey()
            schema = journey_form["data_schema"]
            self.assertIn("rail_direction", [str(key) for key in schema.schema])
            self.assertNotIn("group", [str(key) for key in schema.schema])
            self.assertEqual(
                schema({"name": "West", "rail_direction": "Westbound"})[
                    "rail_direction"
                ],
                "Westbound",
            )
            form = await flow.async_step_settings()
            for interval in (14, 301):
                with self.assertRaises(vol.Invalid):
                    form["data_schema"]({"scan_interval": interval})
            result = await flow.async_step_add_journey(
                {
                    "name": "To work",
                    "lines": ["SV"],
                    "destinations": ["N12"],
                    "rail_direction": "any",
                }
            )
            saved = result["data"]["journeys"][0]
            self.assertTrue(saved["id"])
        e = entry(options={"journeys": [saved], "scan_interval": 60})
        with patch.object(
            WmataOptionsFlow,
            "config_entry",
            new_callable=unittest.mock.PropertyMock,
            return_value=e,
        ):
            bad = await flow.async_step_add_journey({"name": " to WORK "})
            self.assertEqual(bad["errors"]["name"], "duplicate_name")
            await flow.async_step_edit_journey({"journey_id": saved["id"]})
            result = await flow.async_step_journey(
                {
                    "name": "Ashburn",
                    "lines": ["SV"],
                    "destinations": ["N12"],
                    "rail_direction": "any",
                }
            )
            self.assertEqual(result["data"]["journeys"][0]["id"], saved["id"])
            self.assertEqual(result["data"]["scan_interval"], 60)
            result = await flow.async_step_remove_journey({"journey_id": saved["id"]})
            self.assertEqual(result["data"]["journeys"], [])

    async def test_bus_journey_routes_and_direction_zero(self):
        flow = WmataOptionsFlow()
        e = entry("bus", "1001051")
        with patch.object(
            WmataOptionsFlow,
            "config_entry",
            new_callable=unittest.mock.PropertyMock,
            return_value=e,
        ):
            result = await flow.async_step_add_journey(
                {"name": "Bus home", "routes": "d34, D34, C10", "direction_id": "0"}
            )
        journey = result["data"]["journeys"][0]
        self.assertEqual(journey["routes"], ["D34", "C10"])
        raw = [
            {"Minutes": 4, "RouteID": "D34", "DirectionNum": 0},
            {"Minutes": 1, "RouteID": "D34", "DirectionNum": 1},
        ]
        arrivals = [normalize_prediction(r, "bus") for r in raw]
        self.assertEqual(len(filter_arrivals(arrivals, journey)), 1)
        self.assertEqual(filter_arrivals(arrivals, journey)[0]["minutes"], 4)

    async def test_journey_terminal_alias_and_combined_filters(self):
        arrivals = [
            normalize_prediction(
                {"Min": "2", "Line": "RD", "DestinationCode": "A01", "Group": "1"},
                "train",
            ),
            normalize_prediction(
                {"Min": "3", "Line": "BL", "DestinationCode": "C01", "Group": "2"},
                "train",
            ),
        ]
        self.assertEqual(len(filter_arrivals(arrivals, {"destinations": ["C01"]})), 2)
        self.assertEqual(
            len(
                filter_arrivals(
                    arrivals, {"destinations": ["C01"], "lines": ["BL"], "group": "2"}
                )
            ),
            1,
        )
        self.assertEqual(filter_arrivals(arrivals, {"lines": ["SV"]}), [])


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def request(self, status=200, data=None, error=None):
        response = MagicMock()
        response.status = status
        response.json = AsyncMock(
            return_value={} if data is None else data, side_effect=error
        )
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=response)
        context.__aexit__ = AsyncMock(return_value=False)
        session = MagicMock()
        session.get.return_value = context
        api = WmataApi(session, "private-key")
        result = await api.get("test")
        self.assertEqual(session.get.call_args.args[0], "https://api.wmata.com/test")
        return result

    async def test_http_auth_rate_limit_errors_and_json(self):
        for code in (401, 403):
            with self.assertRaises(APIAuthError):
                await self.request(code)
        for code in (429, 500, 404):
            with self.assertRaises(APIConnectionError):
                await self.request(code)
        with self.assertRaises(APIConnectionError):
            await self.request(error=ValueError())
        with self.assertRaises(APIConnectionError):
            await self.request(data=[])
        self.assertEqual(await self.request(data={"Trains": []}), {"Trains": []})

    async def test_request_state_shared_by_key_and_station_cache(self):
        hass = SimpleNamespace(data={})
        one = WmataApi(MagicMock(), "same-key", hass=hass)
        two = WmataApi(MagicMock(), "same-key", hass=hass)
        other = WmataApi(MagicMock(), "different-key", hass=hass)
        self.assertIs(one._state, two._state)
        self.assertIsNot(one._state, other._state)
        with patch.object(one, "get", return_value={"Stations": STATIONS}) as request:
            self.assertEqual(await one.stations(), STATIONS)
            self.assertEqual(await two.stations(), STATIONS)
            request.assert_awaited_once()
        one._state.blocked_until = asyncio.get_running_loop().time() + 60
        with self.assertRaises(APIConnectionError):
            await two.get("test")
        two.session.get.assert_not_called()

    async def test_rate_limit_pauses_every_request_for_a_bounded_retry_after(self):
        loop = asyncio.get_running_loop()
        for header, expected in (
            ("120", 120),
            ("9999", 300),
            ("0", 1),
            ("soon", 60),
            (None, 60),
        ):
            with self.subTest(header=header):
                response = MagicMock()
                response.status = 429
                response.headers = {} if header is None else {"Retry-After": header}
                context = MagicMock()
                context.__aenter__ = AsyncMock(return_value=response)
                context.__aexit__ = AsyncMock(return_value=False)
                session = MagicMock()
                session.get.return_value = context
                api = WmataApi(session, "private-key")
                started = loop.time()
                with self.assertRaises(APIConnectionError):
                    await api.get("test")
                self.assertAlmostEqual(
                    api._state.blocked_until - started, expected, delta=2
                )
                # The cooldown is honoured locally instead of asking WMATA again.
                with self.assertRaises(APIConnectionError):
                    await api.get("test")
                self.assertEqual(session.get.call_count, 1)

    async def test_unknown_bus_stop_is_an_invalid_location(self):
        api = WmataApi(MagicMock(), "private-key")
        for payload in ({}, {"Stop": None}, {"Stop": {"Name": ""}}):
            with (
                self.subTest(payload=payload),
                patch.object(api, "get", return_value=payload),
            ):
                with self.assertRaises(InvalidLocation):
                    await api.stop_name("0000000")
        with patch.object(api, "get", return_value={"Stop": {"Name": "K St + 16th"}}):
            self.assertEqual(await api.stop_name("1001195"), "K St + 16th")

    async def test_nearby_stops_rounds_the_pin_and_drops_unusable_rows(self):
        api = WmataApi(MagicMock(), "private-key")
        good = {"StopID": "1001195", "Name": "K St", "Lat": 38.9, "Lon": -77.03}
        rows = [
            good,
            {**good, "StopID": "0"},
            {**good, "StopID": None},
            {**good, "Name": None},
            {**good, "Lat": "38.9"},
            {**good, "Lon": float("nan")},
        ]
        with patch.object(api, "get", return_value={"Stops": rows}) as request:
            self.assertEqual(await api.nearby_stops(38.123456, -77.654321, 800), [good])
        request.assert_awaited_once_with(
            "Bus.svc/json/jStops", Lat="38.1235", Lon="-77.6543", Radius="800"
        )

    async def test_malformed_lists(self):
        for data in ({}, {"Trains": None}, {"Trains": [None]}):
            with self.assertRaises(APIConnectionError):
                WmataApi._items(data, "Trains")
        self.assertEqual(WmataApi._items({"Trains": []}, "Trains"), [])
