"""WMATA GTFS rail timetables, separate from live train predictions."""

import csv
import io
import re
import zipfile
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .const import LINE_NAME_MAP, STATION_CODE_MAP
from .directions import rail_direction

ZONE = ZoneInfo("America/New_York")
WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def seconds(value):
    """GTFS service times can extend beyond midnight (for example 25:10)."""
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError("Invalid service time")
    hour, minute, second = map(int, parts)
    if not 0 <= hour < 48 or not 0 <= minute < 60 or not 0 <= second < 60:
        raise ValueError("Invalid service time")
    return hour * 3600 + minute * 60 + second


def service_anchor(day):
    """GTFS defines service time from local noon minus twelve elapsed hours."""
    return datetime.combine(day, time(12), ZONE).timestamp() - 43200


class RailSchedule:
    """Keep only services near today, indexed by boarding station."""

    def __init__(self, content, now=None):
        self.day = (now or datetime.now(UTC)).astimezone(ZONE).date()
        self.boarding = defaultdict(list)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if (
                any(info.file_size > 80000000 for info in archive.infolist())
                or sum(info.file_size for info in archive.infolist()) > 160000000
            ):
                raise ValueError("Rail timetable exceeds size limit")

            def rows(name):
                if name not in archive.namelist():
                    return iter(())

                def read():
                    with archive.open(name) as raw:
                        yield from csv.DictReader(
                            io.TextIOWrapper(raw, encoding="utf-8-sig")
                        )

                return read()

            agency = next(rows("agency.txt"), {})
            if agency.get("agency_timezone") != "America/New_York":
                raise ValueError("Unexpected rail timetable timezone")
            info = next(rows("feed_info.txt"), {})
            self.start = (
                datetime.strptime(info["feed_start_date"], "%Y%m%d").date()
                if info.get("feed_start_date")
                else date.min
            )
            self.end = (
                datetime.strptime(info["feed_end_date"], "%Y%m%d").date()
                if info.get("feed_end_date")
                else date.max
            )
            self.days = [self.day + timedelta(days=offset) for offset in (-1, 0, 1)]
            active = {day: set() for day in self.days}
            for row in rows("calendar.txt"):
                for day in self.days:
                    key = day.strftime("%Y%m%d")
                    if (
                        row.get(WEEKDAYS[day.weekday()]) == "1"
                        and row["start_date"] <= key <= row["end_date"]
                    ):
                        active[day].add(row["service_id"])
            for row in rows("calendar_dates.txt"):
                day = datetime.strptime(row["date"], "%Y%m%d").date()
                if day in active:
                    if row["exception_type"] == "1":
                        active[day].add(row["service_id"])
                    elif row["exception_type"] == "2":
                        active[day].discard(row["service_id"])
            service_days = defaultdict(list)
            for day, services in active.items():
                if self.start <= day <= self.end:
                    for service in services:
                        service_days[service].append(service_anchor(day))
            line_by_name = {
                name.casefold(): code for code, name in LINE_NAME_MAP.items()
            }
            routes = {
                row["route_id"]: line_by_name.get(
                    row.get("route_long_name", "").casefold()
                )
                for row in rows("routes.txt")
                if row.get("route_type") in ("0", "1")
            }
            stops = {}
            for row in rows("stops.txt"):
                match = re.search(
                    r"(?:^|_)([A-Z][0-9]{2})(?:_|$)", row["stop_id"]
                ) or re.search(
                    r"(?:^|_)([A-Z][0-9]{2})(?:_|$)", row.get("parent_station", "")
                )
                if match and match[1] in STATION_CODE_MAP:
                    stops[row["stop_id"]] = match[1]
            trips = {
                row["trip_id"]: {
                    "line": routes[row["route_id"]],
                    "anchors": service_days[row["service_id"]],
                    "stops": [],
                }
                for row in rows("trips.txt")
                if row.get("route_id") in routes
                and routes[row["route_id"]]
                and row.get("service_id") in service_days
            }
            # Frequency templates must not be mistaken for actual departures.
            frequency_trips = {row["trip_id"] for row in rows("frequencies.txt")}
            for row in rows("stop_times.txt"):
                trip = trips.get(row.get("trip_id"))
                code = stops.get(row.get("stop_id"))
                if not trip or not code or row["trip_id"] in frequency_trips:
                    continue
                try:
                    trip["stops"].append(
                        (
                            int(row["stop_sequence"]),
                            code,
                            seconds(row["arrival_time"]),
                            seconds(row["departure_time"]),
                            row.get("pickup_type", "0") or "0",
                            row.get("drop_off_type", "0") or "0",
                        )
                    )
                except (KeyError, ValueError):
                    # Do not interpolate missing stop times into a false timetable.
                    continue
            for trip in trips.values():
                trip["stops"].sort()
                if len(trip["stops"]) < 2:
                    continue
                trip["positions"] = {
                    STATION_CODE_MAP[stop[1]]: i for i, stop in enumerate(trip["stops"])
                }
                for i, stop in enumerate(trip["stops"][:-1]):
                    if stop[4] == "0":
                        self.boarding[STATION_CODE_MAP[stop[1]]].append((trip, i))
            if not self.boarding:
                raise ValueError("No supported scheduled rail trips")

    def departures(self, leg, now=None):
        """Return only trains that actually reach the leg's goal, within six hours."""
        now = now or datetime.now(UTC)
        timestamp = now.timestamp()
        if not self.start <= now.astimezone(ZONE).date() <= self.end:
            return []
        result = []
        seen = set()
        for trip, index in self.boarding.get(leg["from_name"], []):
            target = trip["positions"].get(leg["to_name"], -1)
            if trip["line"] not in leg["lines"] or target <= index:
                continue
            start, end = trip["stops"][index], trip["stops"][target]
            if end[5] != "0" or end[2] <= start[3]:
                continue
            for anchor in trip["anchors"]:
                departure, arrival = anchor + start[3], anchor + end[2]
                key = (trip["line"], departure, arrival)
                if not timestamp <= departure <= timestamp + 21600 or key in seen:
                    continue
                seen.add(key)
                destination = trip["stops"][-1][1]
                result.append(
                    {
                        "line": trip["line"],
                        "line_name": LINE_NAME_MAP[trip["line"]],
                        "direction": rail_direction(
                            start[1], trip["line"], destination, None
                        )[0],
                        "station_code": start[1],
                        "destination_code": destination,
                        "destination": STATION_CODE_MAP[destination],
                        "minutes": max(0, int((departure - timestamp) / 60)),
                        "status": "predicted",
                        "prediction_source": "schedule",
                        "departure_at": datetime.fromtimestamp(
                            departure, UTC
                        ).isoformat(),
                        "station_arrival_at": datetime.fromtimestamp(
                            anchor + start[2], UTC
                        ).isoformat(),
                        "arrival_at": datetime.fromtimestamp(arrival, UTC).isoformat(),
                        "ride_minutes": (arrival - departure) / 60,
                    }
                )
        result.sort(key=lambda row: row["departure_at"])
        return result[:120]
