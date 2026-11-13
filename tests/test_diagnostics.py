"""Diagnostics must be useful without leaking keys or location preferences."""

import json
import unittest
from datetime import timedelta
from types import SimpleNamespace

from custom_components.wmata.coordinator import APIData
from custom_components.wmata.diagnostics import async_get_config_entry_diagnostics

SECRET = "PRIVATE-KEY-OR-LOCATION"


def entry(service, coordinator=None):
    return SimpleNamespace(
        data={"service_type": service, "api_key": SECRET, "id": SECRET},
        options={"journeys": [{"name": SECRET, "destinations": [SECRET]}]},
        title=SECRET,
        unique_id=SECRET,
        version=2,
        state=SimpleNamespace(value="loaded"),
        runtime_data=coordinator,
    )


def coordinator(data, **kwargs):
    return SimpleNamespace(
        data=data,
        update_interval=timedelta(seconds=60),
        last_update_success=False,
        last_exception=ValueError(SECRET),
        **kwargs,
    )


class DiagnosticsTest(unittest.IsolatedAsyncioTestCase):
    async def test_unloaded_and_failed_startup(self):
        for runtime in (None, coordinator(None)):
            result = await async_get_config_entry_diagnostics(
                None, entry("train", runtime)
            )
            self.assertNotIn(SECRET, json.dumps(result))
            self.assertEqual(result["journey_count"], 1)
            self.assertEqual(result["coordinator_loaded"], runtime is not None)
            if runtime:
                self.assertEqual(result["last_error_type"], "ValueError")
                self.assertFalse(result["last_update_success"])

    async def test_rail_and_bus_summaries_hide_preferences_and_raw_payloads(self):
        datasets = [
            (
                "train",
                APIData(
                    [],
                    [
                        {
                            "Min": "BRD",
                            "Line": "OR",
                            "LocationCode": SECRET,
                            "DestinationName": SECRET,
                            "extra": SECRET,
                        },
                        {"Min": "DLY"},
                    ],
                ),
            ),
            (
                "bus",
                APIData(
                    [{"Minutes": 4, "DirectionText": SECRET, "VehicleID": SECRET}], []
                ),
            ),
        ]
        for service, data in datasets:
            with self.subTest(service=service):
                result = await async_get_config_entry_diagnostics(
                    None, entry(service, coordinator(data))
                )
                self.assertNotIn(SECRET, json.dumps(result))
                self.assertEqual(
                    result["arrivals"]["count"], 2 if service == "train" else 1
                )
                self.assertEqual(result["arrivals"]["with_numeric_estimate"], 1)
                self.assertEqual(result["poll_interval_seconds"], 60)
                self.assertEqual(result["updated_at"], data.updated_at)

    async def test_map_coverage_does_not_expose_trains_circuits_or_coordinates(self):
        data = {
            "updated_at": "2026-11-12T12:00:00+00:00",
            "paths": [{"private": SECRET}],
            "trains": [
                {
                    "id": SECRET,
                    "line": "SV",
                    "point": [10, 20],
                    "geo_point": [-77, 39],
                    "position_type": "route",
                    "circuit": SECRET,
                },
                {"line": "BL", "point": [20, 30], "position_type": "nearby"},
                {"line": SECRET, "position_type": SECRET},
            ],
        }
        result = await async_get_config_entry_diagnostics(
            None, entry("map", coordinator(data, geometry=object()))
        )
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual(
            result["network"],
            {
                "reported_trains": 3,
                "geographic_markers": 1,
                "diagram_markers": 2,
                "positions": {"route": 1, "nearby": 1, "unknown": 1},
                "lines": {"SV": 1, "BL": 1, "unknown": 1},
                "geometry_loaded": True,
            },
        )
