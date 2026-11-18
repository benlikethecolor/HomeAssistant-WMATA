"""Arrival estimates for a planned route.

This follows the same rules as the dashboard card's connection calculator in
www/wmata-station-card.js, so a commute sensor and a card looking at the same
predictions agree. Times are epoch seconds.
"""

import math
from datetime import datetime

FRESH_SECONDS = 90
LIVE_STATUSES = ("predicted", "arriving", "boarding")


def _timestamp(value) -> float | None:
    try:
        return datetime.fromisoformat(value).timestamp()
    except (TypeError, ValueError):
        return None


def _scheduled(arrival) -> bool:
    return arrival.get("prediction_source") == "schedule"


def departure_at(arrival, updated_at) -> float | None:
    """When a train leaves: its timetable time, or the snapshot plus its minutes."""
    if _scheduled(arrival):
        return _timestamp(arrival.get("departure_at"))
    minutes = arrival.get("minutes")
    if (
        type(minutes) not in (int, float)
        or minutes < 0
        or arrival.get("status") not in LIVE_STATUSES
    ):
        return None
    snapshot = _timestamp(updated_at)
    return None if snapshot is None else snapshot + minutes * 60


def fresh(updated_at, now) -> bool:
    """A snapshot older than 90 seconds can't be trusted for a connection."""
    snapshot = _timestamp(updated_at)
    return (
        snapshot is not None
        and now - snapshot <= FRESH_SECONDS
        and snapshot <= now + 30
    )


def leg_departures(leg, now) -> list[tuple[float, dict]]:
    """Usable departures for a leg, soonest first.

    Live predictions win inside each line's prediction window. Timetable
    departures only fill in after the last live train on that line.
    """
    updated_at = leg.get("updated_at")
    live_ok = bool(leg.get("available")) and fresh(updated_at, now)
    departures = []
    windows = {}
    if live_ok:
        for arrival in leg.get("arrivals") or []:
            time = departure_at(arrival, updated_at)
            if time is not None:
                departures.append((time, arrival))
                line = arrival.get("line")
                windows[line] = max(windows.get(line, 0), time)
    for arrival in leg.get("scheduled_departures") or []:
        time = _timestamp(arrival.get("departure_at"))
        if (
            time is not None
            and time >= now
            and time > windows.get(arrival.get("line"), 0) + 60
        ):
            departures.append((time, arrival))
    departures.sort(key=lambda item: item[0])
    return departures


def ride_arrival(train, departure, leg) -> float | None:
    """A timetable train knows its own arrival; live trains use the ride time."""
    if departure is None:
        return None
    if train is not None and _scheduled(train):
        arrival = _timestamp(train.get("arrival_at"))
        if arrival is not None and arrival > departure:
            return arrival
    ride = leg.get("ride_minutes")
    if type(ride) in (int, float) and math.isfinite(ride) and ride > 0:
        return departure + ride * 60
    return None


def _earliest_reach(candidates, leg):
    """Prefer the train that finishes the leg first, not the first to leave."""
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: (
            reach
            if (reach := ride_arrival(item[1], item[0], leg)) is not None
            else math.inf,
            item[0],
        ),
    )


def estimate_route(legs, now, buffer_minutes) -> dict:
    """Follow one route leg by leg and say when it reaches the destination."""
    result = {
        "arrival": None,
        "departure": None,
        "first_train": None,
        "schedule_estimate": False,
        "trip_minutes": None,
    }
    if not legs:
        return result
    # Trains leaving within the last half minute may still be on the platform.
    origins = [
        (max(now, time), train)
        for time, train in leg_departures(legs[0], now)
        if time >= now - 30
    ]
    chosen = _earliest_reach(origins, legs[0])
    if chosen is None:
        return result
    boarded, train = chosen
    result.update(
        departure=boarded, first_train=train, schedule_estimate=_scheduled(train)
    )
    for index, leg in enumerate(legs):
        reach = ride_arrival(train, boarded, leg)
        if reach is None:
            return result
        if index == len(legs) - 1:
            result["arrival"] = reach
            result["trip_minutes"] = (reach - result["departure"]) / 60
            return result
        following = legs[index + 1]
        ready = reach + buffer_minutes * 60
        connection = _earliest_reach(
            [
                (time, candidate)
                for time, candidate in leg_departures(following, now)
                if time >= ready and time >= now
            ],
            following,
        )
        if connection is None:
            return result
        boarded, train = connection
        if _scheduled(train):
            result["schedule_estimate"] = True
    return result


def best_trip(alternatives, now, buffer_minutes) -> dict | None:
    """Earliest arrival first, then live data over timetable, then fewer changes."""
    ranked = []
    for option in alternatives:
        estimate = estimate_route(option["legs"], now, buffer_minutes)
        route = option["route"]
        ranked.append(
            (
                (
                    estimate["arrival"]
                    if estimate["arrival"] is not None
                    else math.inf,
                    estimate["schedule_estimate"],
                    len(route["legs"]),
                    route.get("stops", 0),
                    option["id"],
                ),
                option,
                estimate,
            )
        )
    if not ranked:
        return None
    _, option, estimate = min(ranked, key=lambda item: item[0])
    return {
        **estimate,
        "route": option["route"],
        "route_description": option["route_description"],
        "transfers": len(option["route"]["legs"]) - 1,
        "calculated_at": now,
    }
