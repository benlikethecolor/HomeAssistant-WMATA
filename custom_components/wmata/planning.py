"""Timetable-only future trips and conservative elevator outage warnings."""

from datetime import UTC, datetime, timedelta

from .const import STATION_CODE_MAP
from .journeys import describe_route


def route_stations(route):
    """Stations where a passenger enters, changes trains, or exits."""
    return {leg["from_name"] for leg in route["legs"]} | {route["legs"][-1]["to_name"]}


def accessibility(routes, outages):
    """Match physical stations, including their alternate platform codes."""
    stations = set().union(*(route_stations(route) for route in routes))
    return [
        {**unit, "station_name": STATION_CODE_MAP[unit["station_code"]]}
        for unit in outages
        if unit.get("type") == "elevator"
        and STATION_CODE_MAP.get(unit.get("station_code")) in stations
    ]


def filter_accessible(routes, warnings, avoid):
    blocked = {unit["station_name"] for unit in warnings}
    return [
        route
        for route in routes
        if not avoid or not route_stations(route).intersection(blocked)
    ]


def scheduled_journeys(schedule, routes, requested, mode, buffer_minutes, now=None):
    """Earliest arrival after departure, or latest departure before a deadline.

    Searches a six-hour window. Explicit scheduled plans never use current live
    predictions or imply that a future connection has been confirmed in real time.
    """
    now = now or datetime.now(UTC)
    begin = (
        requested if mode == "depart_at" else max(now, requested - timedelta(hours=6))
    )
    result = []
    for route in routes:
        boards = [schedule.departures(leg, begin, limit=None) for leg in route["legs"]]
        chosen = []
        boundary = requested.timestamp()
        pairs = list(zip(route["legs"], boards, strict=True))
        if mode == "arrive_by":
            pairs.reverse()
        for leg, board in pairs:
            candidates = []
            for train in board:
                depart = datetime.fromisoformat(train["departure_at"]).timestamp()
                arrive = datetime.fromisoformat(train["arrival_at"]).timestamp()
                if depart < now.timestamp() or arrive <= depart:
                    continue
                if (mode == "depart_at" and depart >= boundary) or (
                    mode == "arrive_by" and arrive <= boundary
                ):
                    candidates.append((depart, arrive, train))
            if not candidates:
                break
            depart, arrive, train = (
                min(candidates, key=lambda item: (item[1], item[0]))
                if mode == "depart_at"
                else max(candidates, key=lambda item: (item[0], -item[1]))
            )
            chosen.append(
                {
                    "from_name": leg["from_name"],
                    "to_name": leg["to_name"],
                    "line": train["line"],
                    "line_name": train["line_name"],
                    "departure_at": train["departure_at"],
                    "arrival_at": train["arrival_at"],
                    "ride_minutes": (arrive - depart) / 60,
                }
            )
            boundary = (
                arrive + buffer_minutes * 60
                if mode == "depart_at"
                else depart - buffer_minutes * 60
            )
        if len(chosen) != len(pairs):
            continue
        if mode == "arrive_by":
            chosen.reverse()
        departure = datetime.fromisoformat(chosen[0]["departure_at"]).timestamp()
        arrival = datetime.fromisoformat(chosen[-1]["arrival_at"]).timestamp()
        for index, leg in enumerate(chosen):
            prior = (
                datetime.fromisoformat(chosen[index - 1]["arrival_at"]).timestamp()
                if index
                else departure
            )
            leg["wait_minutes"] = (
                datetime.fromisoformat(leg["departure_at"]).timestamp() - prior
            ) / 60
        result.append(
            {
                "route_description": describe_route(route),
                "legs": chosen,
                "departure_at": chosen[0]["departure_at"],
                "arrival_at": chosen[-1]["arrival_at"],
                "trip_minutes": (arrival - departure) / 60,
                "transfers": len(chosen) - 1,
                "schedule_estimate": True,
            }
        )
    result.sort(
        key=lambda trip: (
            trip["arrival_at"]
            if mode == "depart_at"
            else -datetime.fromisoformat(trip["departure_at"]).timestamp(),
            trip["transfers"],
            trip["trip_minutes"],
        )
    )
    return result
