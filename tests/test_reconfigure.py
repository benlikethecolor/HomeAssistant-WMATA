"""Reconfigure can replace the key or move an entry to a different place."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.wmata.api import InvalidLocation
from custom_components.wmata.config_flow import WmataConfigFlow
from custom_components.wmata.journeys import plan_journey
from tests.test_wmata import entry


def validated(data):
    """Stand in for the API checks, filling in what a station lookup adds."""
    data = dict(data)
    if data["service_type"] == "train":
        from custom_components.wmata.const import STATION_CODE_MAP, station_codes

        data["station_codes"] = sorted(station_codes(data["id"]))
        data["location_name"] = STATION_CODE_MAP[data["id"]]
    elif data["service_type"] == "bus":
        data["location_name"] = f"Stop {data['id']}"
    return data


class ReconfigureTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = HomeAssistant("/tmp/wmata-reconfigure")
        self.entities = MagicMock()
        self.devices = MagicMock()
        patches = [
            patch(
                "custom_components.wmata.config_flow.validate_location",
                AsyncMock(side_effect=lambda hass, data: validated(data)),
            ),
            patch("custom_components.wmata.config_flow.er.async_get"),
            patch(
                "custom_components.wmata.config_flow.er.async_entries_for_config_entry",
                return_value=[
                    MagicMock(entity_id="sensor.old_board"),
                    MagicMock(entity_id="binary_sensor.old_alert"),
                ],
            ),
            patch("custom_components.wmata.config_flow.dr.async_get"),
            patch(
                "custom_components.wmata.config_flow.dr.async_entries_for_config_entry",
                return_value=[MagicMock(id="device-1")],
            ),
        ]
        started = [p.start() for p in patches]
        self.validate = started[0]
        self.entities = started[1].return_value
        self.devices = started[3].return_value
        for p in patches:
            self.addCleanup(p.stop)

    async def asyncTearDown(self):
        await self.hass.async_stop(force=True)

    def flow(self, target, others=()):
        flow = WmataConfigFlow()
        flow.hass = self.hass
        flow._async_current_entries = MagicMock(return_value=[target, *others])
        flow._get_reconfigure_entry = MagicMock(return_value=target)
        flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
        return flow

    async def test_form_shows_the_current_place_and_never_the_key(self):
        flow = self.flow(entry(location="C01"))
        form = await flow.async_step_reconfigure()
        self.assertEqual(form["step_id"], "reconfigure")
        self.assertNotIn("test-key", str(form))
        fields = {str(key): key for key in form["data_schema"].schema}
        self.assertEqual(set(fields), {"api_key", "station"})
        # Metro Center is listed under its first platform code.
        self.assertEqual(fields["station"].default(), "A01")
        bus = await self.flow(entry("bus", "1001195")).async_step_reconfigure()
        self.assertEqual(
            {str(key) for key in bus["data_schema"].schema}, {"api_key", "stop"}
        )
        network = await self.flow(entry("map", "network")).async_step_reconfigure()
        self.assertEqual(
            {str(key) for key in network["data_schema"].schema}, {"api_key"}
        )

    async def test_moving_a_station_replaces_its_entities_and_replans_journeys(self):
        filtered = {"id": "f", "name": "Red only", "lines": ["RD"]}
        kept = {
            "id": "k",
            "name": "To Huntington",
            "kind": "station_to_station",
            "target_station": "C15",
            "route": plan_journey("A01", "C15"),
        }
        dropped = {**kept, "id": "d", "name": "To Union", "target_station": "B03"}
        target = entry(
            location="A01",
            options={"journeys": [filtered, kept, dropped], "scan_interval": 60},
        )
        flow = self.flow(target)
        await flow.async_step_reconfigure({"station": "Union Station"})
        self.assertEqual(self.entities.async_remove.call_count, 2)
        self.devices.async_remove_device.assert_called_once_with("device-1")
        update = flow.async_update_reload_and_abort.call_args
        self.assertIs(update.args[0], target)
        self.assertEqual(update.kwargs["reason"], "reconfigure_successful")
        self.assertEqual(update.kwargs["unique_id"], "train:B03")
        self.assertEqual(update.kwargs["title"], "Union Station")
        self.assertEqual(update.kwargs["data"]["id"], "B03")
        self.assertEqual(update.kwargs["data"]["api_key"], "test-key")
        options = update.kwargs["options"]
        self.assertEqual(options["scan_interval"], 60)
        self.assertEqual([j["id"] for j in options["journeys"]], ["f", "k"])
        self.assertEqual(
            options["journeys"][1]["route"]["origin_name"], "Union Station"
        )

    async def test_the_same_station_or_only_a_new_key_leaves_entities_alone(self):
        target = entry(location="C01")
        flow = self.flow(target)
        # Metro Center again, though the list returns its other platform code.
        await flow.async_step_reconfigure({"station": "A01", "api_key": " fresh "})
        self.entities.async_remove.assert_not_called()
        self.devices.async_remove_device.assert_not_called()
        update = flow.async_update_reload_and_abort.call_args.kwargs
        self.assertEqual(update["data"]["id"], "C01")
        self.assertEqual(update["data"]["api_key"], "fresh")
        self.assertNotIn("unique_id", update)
        self.assertNotIn("options", update)
        # An empty key keeps the saved one.
        await flow.async_step_reconfigure({"station": "A01", "api_key": ""})
        self.assertEqual(
            flow.async_update_reload_and_abort.call_args.kwargs["data"]["api_key"],
            "test-key",
        )

    async def test_a_place_that_already_has_an_entry_is_refused(self):
        target = entry(location="A01")
        flow = self.flow(target, others=[entry(location="F03"), entry("bus", "B03")])
        # L'Enfant Plaza is configured under its other platform code.
        form = await flow.async_step_reconfigure({"station": "D03"})
        self.assertEqual(form["errors"], {"base": "already_added"})
        flow.async_update_reload_and_abort.assert_not_called()
        self.validate.assert_not_awaited()
        self.assertEqual(
            (await flow.async_step_reconfigure({"station": "Atlantis"}))["errors"],
            {"station": "unknown_station"},
        )
        # What was typed is still in the form.
        fields = {str(key): key for key in form["data_schema"].schema}
        self.assertEqual(fields["station"].default(), "D03")

    async def test_a_bus_stop_can_be_swapped_and_bad_ids_are_reported(self):
        target = entry("bus", "1001195")
        flow = self.flow(target)
        await flow.async_step_reconfigure({"stop": " 1001051 "})
        update = flow.async_update_reload_and_abort.call_args.kwargs
        self.assertEqual(update["unique_id"], "bus:1001051")
        self.assertEqual(update["title"], "Stop 1001051")
        self.validate.side_effect = InvalidLocation()
        form = await flow.async_step_reconfigure({"stop": "nope"})
        self.assertEqual(form["errors"], {"base": "invalid_location"})

    async def test_a_commute_can_change_either_station(self):
        target = entry(
            "commute", "C04-A01", home="C04", work="A01", location_name="Work"
        )
        flow = self.flow(target)
        same = await flow.async_step_reconfigure({"home": "C04", "work": "C04"})
        self.assertEqual(same["errors"], {"work": "same_station"})
        await flow.async_step_reconfigure({"home": "C04", "work": "NoMa-Gallaudet U"})
        update = flow.async_update_reload_and_abort.call_args.kwargs
        self.assertEqual(update["unique_id"], "commute:C04:B35")
        self.assertEqual(update["title"], "Foggy Bottom-GWU ↔ NoMa-Gallaudet U")
        self.assertEqual(update["data"]["work"], "B35")
        self.assertEqual(update["data"]["id"], "C04-B35")
        self.assertEqual(update["data"]["location_name"], "Work")
        self.entities.async_remove.assert_called()
        # Renaming alone doesn't move it.
        self.entities.reset_mock()
        await flow.async_step_reconfigure(
            {"home": "C04", "work": "A01", "name": "Office"}
        )
        update = flow.async_update_reload_and_abort.call_args.kwargs
        self.assertEqual(update["data"]["location_name"], "Office")
        self.assertNotIn("unique_id", update)
        self.entities.async_remove.assert_not_called()
