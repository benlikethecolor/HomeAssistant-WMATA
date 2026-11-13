"""Timetable departures must respect service dates, stop order and boarding rules."""

import asyncio
import csv
import io
import unittest
import zipfile
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.wmata.api import APIConnectionError, WmataApi
from custom_components.wmata.schedules import (
    ZONE,
    RailSchedule,
    seconds,
    service_anchor,
)

NOW = datetime(2026, 11, 13, 14, 0, tzinfo=UTC)
LEG = {
    "from_name": "Foggy Bottom-GWU",
    "to_name": "Metro Center",
    "lines": ["OR", "SV", "BL"],
}


def feed(
    *,
    departure="09:10:00",
    arrival="09:14:00",
    day="20261113",
    pickup="0",
    dropoff="0",
    reverse=False,
    short=False,
    extra=None,
):
    codes = ["C04", "C03", "C01"] if not reverse else ["C01", "C03", "C04"]
    if short:
        codes = codes[:2]
    tables = {
        "agency.txt": [{"agency_timezone": "America/New_York"}],
        "feed_info.txt": [{"feed_start_date": "20261101", "feed_end_date": "20261120"}],
        "calendar_dates.txt": [
            {"service_id": "weekday", "date": day, "exception_type": "1"}
        ],
        "routes.txt": [
            {"route_id": "orange", "route_long_name": "Orange", "route_type": "1"}
        ],
        "stops.txt": [
            {"stop_id": "PF_" + code + "_C", "parent_station": "STN_" + code}
            for code in codes
        ],
        "trips.txt": [{"trip_id": "t1", "service_id": "weekday", "route_id": "orange"}],
        "stop_times.txt": [
            {
                "trip_id": "t1",
                "stop_id": "PF_" + code + "_C",
                "stop_sequence": str(i + 1),
                "arrival_time": departure if i == 0 else arrival,
                "departure_time": departure if i == 0 else arrival,
                "pickup_type": pickup if i == 0 else "0",
                "drop_off_type": dropoff if i == len(codes) - 1 else "0",
            }
            for i, code in enumerate(codes)
        ],
    }
    tables.update(extra or {})
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w") as archive:
        for name, rows in tables.items():
            text = io.StringIO()
            writer = csv.DictWriter(text, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            archive.writestr(name, text.getvalue())
    return content.getvalue()


class ScheduleTest(unittest.TestCase):
    def test_departure_reaches_goal_using_platform_aliases_and_timetable_ride(self):
        rows = RailSchedule(feed(), NOW).departures(LEG, NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["departure_at"], "2026-11-13T14:10:00+00:00")
        self.assertEqual(rows[0]["arrival_at"], "2026-11-13T14:14:00+00:00")
        self.assertEqual(rows[0]["prediction_source"], "schedule")
        self.assertEqual(rows[0]["ride_minutes"], 4)
        self.assertEqual(rows[0]["direction"], "Eastbound")

    def test_wrong_direction_short_turns_and_no_pickup_or_dropoff_are_excluded(self):
        for options in (
            {"reverse": True},
            {"short": True},
            {"pickup": "1"},
            {"dropoff": "1"},
        ):
            self.assertEqual(
                RailSchedule(feed(**options), NOW).departures(LEG, NOW), []
            )

    def test_calendar_removals_override_regular_service(self):
        calendar = {
            "service_id": "weekday",
            "start_date": "20261101",
            "end_date": "20261120",
            **{
                day: "1"
                for day in (
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                )
            },
        }
        content = feed(
            extra={
                "calendar.txt": [calendar],
                "calendar_dates.txt": [
                    {"service_id": "weekday", "date": "20261113", "exception_type": "2"}
                ],
            }
        )
        schedule = RailSchedule(content, NOW)
        # Tomorrow's service exists but today's removed service must not appear.
        self.assertEqual(schedule.departures(LEG, NOW), [])

    def test_after_midnight_uses_previous_service_day(self):
        now = datetime(2026, 11, 14, 5, 50, tzinfo=UTC)
        rows = RailSchedule(
            feed(departure="25:05:00", arrival="25:09:00"), now
        ).departures(LEG, now)
        self.assertEqual(rows[0]["departure_at"], "2026-11-14T06:05:00+00:00")
        self.assertEqual(rows[0]["arrival_at"], "2026-11-14T06:09:00+00:00")

    def test_expired_feed_and_frequency_templates_do_not_invent_departures(self):
        schedule = RailSchedule(feed(), NOW)
        self.assertEqual(
            schedule.departures(LEG, datetime(2026, 11, 21, 14, tzinfo=UTC)), []
        )
        with self.assertRaises(ValueError):
            RailSchedule(
                feed(
                    extra={
                        "frequencies.txt": [
                            {
                                "trip_id": "t1",
                                "start_time": "09:00:00",
                                "end_time": "10:00:00",
                                "headway_secs": "300",
                            }
                        ]
                    }
                ),
                NOW,
            )

    def test_service_anchor_handles_both_daylight_saving_changes(self):
        for day in (date(2026, 3, 8), date(2026, 11, 1)):
            self.assertEqual(
                service_anchor(day) + 6 * 3600,
                datetime.combine(day, datetime.min.time(), ZONE)
                .replace(hour=6)
                .timestamp(),
            )
        self.assertEqual(seconds("25:05:00"), 90300)
        for value in ("-1:00:00", "12:60:00", "bad", "12:12"):
            with self.assertRaises(ValueError):
                seconds(value)


class ScheduleCacheTest(unittest.IsolatedAsyncioTestCase):
    async def test_shared_key_singleflight_and_failure_backoff(self):
        async def execute(func, *args):
            return func(*args)

        hass = SimpleNamespace(data={}, async_add_executor_job=execute)
        one = WmataApi(MagicMock(), "key", hass=hass)
        two = WmataApi(MagicMock(), "key", hass=hass)
        one._download_rail_schedule = AsyncMock(return_value=b"fixture")
        two._download_rail_schedule = AsyncMock(return_value=b"fixture")
        parsed = object()
        with patch("custom_components.wmata.api.RailSchedule", return_value=parsed):
            a, b = await asyncio.gather(one.rail_schedule(), two.rail_schedule())
        self.assertIs(a, parsed)
        self.assertIs(a, b)
        one._download_rail_schedule.assert_awaited_once()
        two._download_rail_schedule.assert_not_awaited()
        one._state.schedule_expiry = 0
        one._download_rail_schedule.side_effect = APIConnectionError("offline")
        with self.assertRaises(APIConnectionError):
            await one.rail_schedule()
        self.assertIs(await two.rail_schedule(), parsed)
        self.assertEqual(one._download_rail_schedule.await_count, 2)

    async def test_malformed_download_fails_without_retaining_credentials(self):
        api = WmataApi(MagicMock(), "private-key")
        api._download_rail_schedule = AsyncMock(return_value=b"not a zip")
        with self.assertRaises(APIConnectionError) as error:
            await api.rail_schedule()
        self.assertNotIn("private-key", str(error.exception))
        self.assertIsNone(await api.rail_schedule())
