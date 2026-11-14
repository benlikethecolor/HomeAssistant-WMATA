"""Name-based setup, credential reuse and optional automation entities."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.wmata.api import APIAuthError
from custom_components.wmata.binary_sensor import WmataDueSoonSensor
from custom_components.wmata.config_flow import WmataConfigFlow
from custom_components.wmata.coordinator import APIData
from custom_components.wmata.sensor import WmataDetailSensor, WmataDirectionSensor
from tests import test_wmata
from tests.test_wmata import entry


class UsabilityTest(unittest.IsolatedAsyncioTestCase):
    async def test_saved_key_is_reused_without_returning_it_in_the_form(self):
        hass = HomeAssistant("/tmp/wmata-key-reuse")
        existing = entry(location="A01", location_name="Metro Center")
        flow = WmataConfigFlow()
        flow.hass = hass
        flow._async_current_entries = MagicMock(return_value=[existing])
        form = await flow.async_step_user()
        self.assertNotIn("test-key", str(form))
        fields = {str(k) for k in form["data_schema"].schema}
        self.assertIn("credential_source", fields)
        self.assertNotIn("api_key", fields)
        with (
            patch("custom_components.wmata.config_flow.async_get_clientsession"),
            patch("custom_components.wmata.config_flow.WmataApi") as api,
        ):
            api.return_value.validate_service = AsyncMock()
            result = await flow.async_step_user(
                {"credential_source": existing.entry_id, "service_type": "train"}
            )
        self.assertEqual(result["step_id"], "location")
        self.assertEqual(flow._setup_data["api_key"], "test-key")
        options = next(iter(result["data_schema"].schema.values())).config["options"]
        self.assertTrue(any(o["label"] == "Metro Center" for o in options))
        self.assertFalse(any("(A01" in o["label"] for o in options))
        other = await flow.async_step_user(
            {"credential_source": "new", "service_type": "bus"}
        )
        self.assertEqual(other["step_id"], "api_key")
        await hass.async_stop(force=True)

    async def test_key_change_updates_matching_entries_only(self):
        hass = HomeAssistant("/tmp/wmata-shared-key")
        one, two, separate = (
            entry(),
            entry(location="G01"),
            entry(location="B03", api_key="different"),
        )
        flow = WmataConfigFlow()
        flow.hass = hass
        flow._async_current_entries = MagicMock(return_value=[one, two, separate])
        flow._get_reconfigure_entry = MagicMock(return_value=one)
        flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})
        manager = SimpleNamespace(
            async_update_entry=MagicMock(), async_reload=AsyncMock()
        )
        data = {**one.data, "api_key": "replacement"}
        with (
            patch(
                "custom_components.wmata.config_flow.validate_location",
                return_value=data,
            ),
            patch.object(hass, "config_entries", manager),
        ):
            await flow.async_step_reconfigure({"api_key": "replacement"})
            await hass.async_block_till_done()
        manager.async_update_entry.assert_called_once_with(
            two, data={**two.data, "api_key": "replacement"}
        )
        self.assertEqual(separate.data["api_key"], "different")
        self.assertIn(
            two.entry_id, [call.args[0] for call in manager.async_reload.call_args_list]
        )
        await hass.async_stop(force=True)

    async def test_rejected_shared_service_leaves_every_key_unchanged(self):
        hass = HomeAssistant("/tmp/wmata-shared-permissions")
        one, two = entry(), entry(service="bus", location="1001051")
        flow = WmataConfigFlow()
        flow.hass = hass
        flow._async_current_entries = MagicMock(return_value=[one, two])
        flow._get_reconfigure_entry = MagicMock(return_value=one)
        manager = SimpleNamespace(
            async_update_entry=MagicMock(), async_reload=AsyncMock()
        )
        with (
            patch.object(hass, "config_entries", manager),
            patch(
                "custom_components.wmata.config_flow.validate_location",
                side_effect=[{**one.data, "api_key": "replacement"}, APIAuthError()],
            ),
        ):
            result = await flow.async_step_reconfigure({"api_key": "replacement"})
        self.assertEqual(result["errors"]["base"], "invalid_auth")
        manager.async_update_entry.assert_not_called()
        manager.async_reload.assert_not_awaited()
        self.assertEqual(one.data["api_key"], "test-key")
        self.assertEqual(two.data["api_key"], "test-key")
        await hass.async_stop(force=True)

    async def test_optional_line_direction_sensor_filters_the_shared_board(self):
        # Use a real coordinator; these sensors must never create another API client.
        fixture = test_wmata.IntegrationTest()
        fixture.hass = HomeAssistant("/tmp/wmata-optional")
        with patch(
            "custom_components.wmata.coordinator.async_get_clientsession",
            return_value=MagicMock(),
        ):
            coordinator = fixture.coordinator()
        coordinator.data = APIData(
            [],
            [
                {
                    "LocationCode": "C01",
                    "Line": "OR",
                    "DestinationCode": "D13",
                    "Min": "4",
                },
                {
                    "LocationCode": "C01",
                    "Line": "OR",
                    "DestinationCode": "K08",
                    "Min": "2",
                },
                {
                    "LocationCode": "A01",
                    "Line": "RD",
                    "DestinationCode": "B11",
                    "Min": "BRD",
                },
            ],
        )
        sensor = WmataDirectionSensor(coordinator, "OR", "Eastbound")
        self.assertEqual(sensor.native_value, 4)
        self.assertFalse(sensor.entity_registry_enabled_default)
        self.assertEqual(WmataDetailSensor(coordinator, "count").native_value, 3)
        self.assertEqual(WmataDetailSensor(coordinator, "line").native_value, "Orange")
        self.assertEqual(
            WmataDetailSensor(coordinator, "destination").native_value, "New Carrollton"
        )
        due = WmataDueSoonSensor(coordinator, entry(options={"due_soon_minutes": 3}))
        self.assertTrue(due.is_on)
        self.assertFalse(due.entity_registry_enabled_default)
        coordinator.data = APIData([], [{"Min": "DLY"}])
        self.assertFalse(due.is_on)
        coordinator.data = APIData([], [])
        self.assertFalse(due.is_on)
        self.assertIsNone(sensor.native_value)
        coordinator.last_update_success = False
        self.assertFalse(due.available)
        await fixture.hass.async_stop(force=True)
