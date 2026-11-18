"""Route planning and matching trains that actually reach the boarding goal."""

import unittest
from unittest.mock import PropertyMock, patch

from custom_components.wmata.config_flow import WmataOptionsFlow
from custom_components.wmata.journeys import describe_route, plan_journey, trip_matches
from custom_components.wmata.predictions import normalize_prediction
from tests.test_wmata import entry


def arrival(line, terminus, origin="C01", label=None):
    return normalize_prediction(
        {
            "Line": line,
            "LocationCode": origin,
            "DestinationCode": terminus,
            "DestinationName": label,
            "Min": "4",
        },
        "train",
    )


class JourneyTest(unittest.TestCase):
    def test_direct_shared_lines_and_transfer_aliases(self):
        plan = plan_journey("A01", "C05")
        self.assertEqual(plan["transfers"], 0)
        self.assertEqual(set(plan["legs"][0]["lines"]), {"BL", "OR", "SV"})
        for line, terminus in (("BL", "J03"), ("OR", "K08"), ("SV", "N12")):
            self.assertTrue(trip_matches(arrival(line, terminus), plan))
        self.assertFalse(trip_matches(arrival("RD", "B11", "A01"), plan))
        self.assertIsNone(plan_journey("A01", "C01"))
        self.assertIsNone(plan_journey("invalid", "C01"))

    def test_short_turn_wrong_direction_and_eastern_branch(self):
        plan = plan_journey("A01", "D13")
        self.assertTrue(trip_matches(arrival("OR", "D13"), plan))
        # A real diverted Silver prediction is useful even with a standard Orange route.
        self.assertTrue(trip_matches(arrival("SV", None, label="NewCrlton"), plan))
        self.assertFalse(trip_matches(arrival("OR", "D08"), plan))
        self.assertFalse(trip_matches(arrival("OR", "K08"), plan))
        self.assertFalse(trip_matches(arrival("SV", "G05"), plan))
        self.assertFalse(trip_matches(arrival("OR", None), plan))
        self.assertFalse(trip_matches(arrival("OR", "D13", "G01"), plan))

    def test_transfer_route_and_standard_service_do_not_invent_direct_trains(self):
        plan = plan_journey("B03", "C15")
        self.assertEqual(plan["transfers"], 1)
        self.assertEqual(plan["legs"][0]["to_name"], "Gallery Pl-Chinatown")
        self.assertTrue(trip_matches(arrival("RD", "A15", "B03"), plan))
        self.assertFalse(trip_matches(arrival("RD", "B11", "B03"), plan))
        self.assertIn("Change to", describe_route(plan))
        self.assertGreaterEqual(plan_journey("K08", "G05")["transfers"], 1)

    def test_every_station_is_reachable_from_a_transfer_station(self):
        from custom_components.wmata.journeys import STATIONS_BY_NAME

        for name, code in STATIONS_BY_NAME.items():
            if name != "Metro Center":
                with self.subTest(destination=name):
                    self.assertIsNotNone(plan_journey("A01", code))


class JourneyFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_ui_preview_save_edit_and_remove_keep_identity(self):
        e = entry(location="B03", location_name="Union Station")
        flow = WmataOptionsFlow()
        with patch.object(
            WmataOptionsFlow, "config_entry", new_callable=PropertyMock, return_value=e
        ):
            menu = await flow.async_step_init()
            self.assertIn("add_trip", menu["menu_options"])
            form = await flow.async_step_add_trip()
            self.assertEqual(
                form["description_placeholders"]["origin"], "Union Station"
            )
            confirm = await flow.async_step_add_trip(
                {"target_station": "C15", "name": ""}
            )
            self.assertEqual(confirm["step_id"], "trip_confirm")
            self.assertEqual(confirm["description_placeholders"]["transfers"], "1")
            saved = (await flow.async_step_trip_confirm({}))["data"]["journeys"][0]
        self.assertEqual(saved["name"], "To Huntington")
        e = entry(location="B03", options={"journeys": [saved]})
        with patch.object(
            WmataOptionsFlow, "config_entry", new_callable=PropertyMock, return_value=e
        ):
            form = await flow.async_step_edit_journey({"journey_id": saved["id"]})
            self.assertEqual(form["step_id"], "edit_trip")
            await flow.async_step_edit_trip(
                {"target_station": "A03", "name": "To Dupont"}
            )
            updated = (await flow.async_step_trip_confirm({}))["data"]["journeys"][0]
            self.assertEqual(updated["id"], saved["id"])
            self.assertEqual(updated["route"]["destination_name"], "Dupont Circle")
            self.assertEqual(
                (await flow.async_step_remove_journey({"journey_id": saved["id"]}))[
                    "data"
                ]["journeys"],
                [],
            )
