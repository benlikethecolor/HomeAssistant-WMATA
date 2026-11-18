"""The Python estimator must agree with the card on the shared scenarios."""

import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from custom_components.wmata.estimates import best_trip, estimate_route

CASES = json.loads((Path(__file__).parent / "fixtures" / "estimates.json").read_text())
NOW = datetime(2026, 11, 13, 13, 0, tzinfo=UTC)


def at(minutes):
    return (NOW + timedelta(minutes=minutes)).isoformat()


def expand(legs):
    """Turn the fixture's minute offsets into the payload both estimators read."""
    return [
        {
            "index": index,
            "available": leg.get("available", True),
            "ride_minutes": leg["ride_minutes"],
            "updated_at": (
                NOW - timedelta(seconds=leg.get("age_seconds", 0))
            ).isoformat(),
            "arrivals": leg["arrivals"],
            "scheduled_departures": [
                {
                    "line": train["line"],
                    "status": "predicted",
                    "prediction_source": "schedule",
                    "departure_at": at(train["departs"]),
                    "arrival_at": at(train["arrives"]),
                }
                for train in leg.get("scheduled", [])
            ],
        }
        for index, leg in enumerate(legs)
    ]


def minutes(value):
    return None if value is None else round((value - NOW.timestamp()) / 60, 3)


class EstimateTest(unittest.TestCase):
    def test_shared_scenarios(self):
        for case in CASES:
            with self.subTest(case["name"]):
                result = estimate_route(
                    expand(case["legs"]), NOW.timestamp(), case["buffer"]
                )
                expect = case["expect"]
                self.assertEqual(minutes(result["arrival"]), expect["arrival"])
                self.assertEqual(minutes(result["departure"]), expect["departure"])
                self.assertEqual(
                    (result["first_train"] or {}).get("line"), expect["first_line"]
                )
                self.assertEqual(
                    result["schedule_estimate"], expect["schedule_estimate"]
                )

    def test_the_first_train_is_the_one_that_finishes_the_leg_soonest(self):
        # A timetable train that leaves later can still get there first.
        legs = expand(
            [
                {
                    "ride_minutes": 20,
                    "arrivals": [{"line": "RD", "minutes": 2, "status": "predicted"}],
                    "scheduled": [{"line": "YL", "departs": 6, "arrives": 15}],
                }
            ]
        )
        result = estimate_route(legs, NOW.timestamp(), 3)
        self.assertEqual(result["first_train"]["line"], "YL")
        self.assertEqual(minutes(result["arrival"]), 15)
        self.assertEqual(result["trip_minutes"], 9)

    def test_routes_rank_by_arrival_then_live_data_then_fewer_changes(self):
        def option(name, legs, stops=5):
            return {
                "id": name,
                "route": {"legs": [{}] * len(legs), "stops": stops},
                "route_description": name,
                "legs": expand(legs),
            }

        def leg(minute, ride, **extra):
            train = {"line": "RD", "minutes": minute, "status": "predicted"}
            return {"ride_minutes": ride, "arrivals": [train], **extra}

        direct = option("direct", [leg(10, 20)])
        quicker = option("one change", [leg(2, 5), leg(11, 8)])
        best = best_trip([direct, quicker], NOW.timestamp(), 3)
        self.assertEqual(best["route_description"], "one change")
        self.assertEqual(best["transfers"], 1)
        self.assertEqual(minutes(best["arrival"]), 19)
        # The same arrival: prefer live trains, then the simpler route.
        timetable = option(
            "timetable",
            [
                {
                    "ride_minutes": 9,
                    "arrivals": [],
                    "scheduled": [{"line": "RD", "departs": 10, "arrives": 19}],
                }
            ],
        )
        self.assertEqual(
            best_trip([timetable, quicker], NOW.timestamp(), 3)["route_description"],
            "one change",
        )
        same = option("direct tie", [leg(10, 9)])
        self.assertEqual(
            best_trip([quicker, same], NOW.timestamp(), 3)["route_description"],
            "direct tie",
        )
        # A route that can't be estimated never beats one that can.
        unknown = option("unknown", [leg(1, None)])
        self.assertEqual(
            best_trip([unknown, direct], NOW.timestamp(), 3)["route_description"],
            "direct",
        )
        self.assertIsNone(best_trip([unknown], NOW.timestamp(), 3)["arrival"])
        self.assertIsNone(best_trip([], NOW.timestamp(), 3))
