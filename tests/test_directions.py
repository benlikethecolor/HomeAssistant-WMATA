"""Travel directions must follow station topology, never prediction groups."""

import unittest

from custom_components.wmata.const import STATION_CODE_MAP
from custom_components.wmata.directions import ROUTES, rail_direction
from custom_components.wmata.predictions import filter_arrivals, normalize_prediction


class DirectionsTest(unittest.TestCase):
    def test_court_house_and_group_independence(self):
        mt_vernon = normalize_prediction(
            {"LocationCode": "C11", "Line": "YL", "DestinationName": "MtVern Sq"},
            "train",
        )
        self.assertEqual(mt_vernon["direction"], "Northbound")
        self.assertEqual(
            mt_vernon["destination"], "Mt Vernon Sq 7th St-Convention Center"
        )
        for group in ("1", "2", None):
            for line, code, expected in (
                ("OR", "D13", "Eastbound"),
                ("OR", "K08", "Westbound"),
                ("SV", "N12", "Westbound"),
                ("SV", "G05", "Eastbound"),
                ("SV", "D13", "Eastbound"),
            ):
                row = normalize_prediction(
                    {
                        "LocationCode": "K01",
                        "Line": line,
                        "DestinationCode": code,
                        "Group": group,
                        "Min": "5",
                    },
                    "train",
                )
                self.assertEqual(row["direction"], expected)
                self.assertEqual(
                    row["next_station_code"],
                    "C05" if expected == "Eastbound" else "K02",
                )
        # WMATA sometimes omits the destination code but retains an abbreviation.
        row = normalize_prediction(
            {"LocationCode": "K01", "Line": "SV", "DestinationName": "NewCrlton"},
            "train",
        )
        self.assertEqual(row["direction"], "Eastbound")

    def test_curves_short_turns_transfer_platforms_and_terminals(self):
        cases = [
            ("A03", "RD", "B11", "Southbound", "A02"),
            ("B03", "RD", "B11", "Northbound", "B35"),
            ("B03", "RD", "A15", "Southbound", "B02"),
            ("A03", "RD", "A01", "Southbound", "A02"),
            ("A01", "OR", "D13", "Eastbound", "D01"),
            ("C01", "RD", "B11", "Eastbound", "B01"),
            ("C05", "BL", "J03", "Southbound", "C06"),
            ("C05", "OR", "K08", "Westbound", "K01"),
            ("C12", "YL", "E10", "Northbound", "C11"),
            ("B06", "YL", "C15", "Southbound", "E05"),
            ("F01", "GR", "F11", "Southbound", "F02"),
            # Both prediction groups can be departures from a terminal.
            ("K08", "OR", "D13", "Eastbound", "K07"),
            ("D13", "OR", "K08", "Westbound", "D12"),
        ]
        for station, line, destination, direction, next_stop in cases:
            with self.subTest(station=station, line=line, destination=destination):
                self.assertEqual(
                    rail_direction(station, line, destination, None),
                    (direction, next_stop),
                )
        for station, line, destination in (
            ("K01", "OR", "K01"),
            ("D13", "OR", "D13"),
            ("A03", "RD", "N12"),
            ("K01", "XX", "D13"),
            (None, "OR", "D13"),
            ("K01", "OR", None),
        ):
            self.assertEqual(
                rail_direction(station, line, destination, None), (None, None)
            )

    def test_every_published_station_and_line_has_bidirectional_coverage(self):
        covered = set()
        for line, route in ROUTES.items():
            self.assertEqual(len(route), len(set(route)))
            for i, station in enumerate(route):
                covered.add(station)
                self.assertIn(station, STATION_CODE_MAP)
                for j in (i - 1, i + 1):
                    if 0 <= j < len(route):
                        direction, next_stop = rail_direction(
                            station, line, route[j], None
                        )
                        self.assertIn(
                            direction,
                            ("Northbound", "Southbound", "Eastbound", "Westbound"),
                        )
                        self.assertEqual(next_stop, route[j])
        self.assertEqual(covered, set(STATION_CODE_MAP))

    def test_direction_filter_and_bus_text(self):
        rows = [
            normalize_prediction(
                {
                    "LocationCode": "K01",
                    "Line": "OR",
                    "DestinationCode": dest,
                    "Group": "1",
                },
                "train",
            )
            for dest in ("D13", "K08", None)
        ]
        self.assertEqual(
            filter_arrivals(rows, {"rail_direction": "Westbound"}), [rows[1]]
        )
        self.assertEqual(filter_arrivals(rows, {"rail_direction": "any"}), rows)
        self.assertEqual(filter_arrivals(rows, {"group": "1"}), rows)
        self.assertEqual(
            normalize_prediction(
                {"DirectionText": "Downtown", "DirectionNum": 0}, "bus"
            )["direction"],
            "Downtown",
        )
