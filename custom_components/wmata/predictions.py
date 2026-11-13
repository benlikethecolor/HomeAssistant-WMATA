"""Stable arrival schema shared by boards and saved journeys."""

from .const import LINE_NAME_MAP, STATION_CODE_MAP, station_codes
from .directions import rail_direction


def prediction_minutes(value) -> int | None:
    """Keep missing/invalid estimates unknown, including negative values."""
    if value in ("ARR", "BRD"):
        return 0
    try:
        minutes = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return minutes if minutes >= 0 else None


def destination_name(code, label):
    """Prefer station IDs and expand WMATA's terminal abbreviations."""
    aliases = {
        "newcrlton": "New Carrollton",
        "newcarrollton": "New Carrollton",
        "fransprng": "Franconia-Springfield",
        "franconia": "Franconia-Springfield",
        "vienna": "Vienna/Fairfax-GMU",
        "shadygrv": "Shady Grove",
        "shadygrove": "Shady Grove",
        "branchav": "Branch Ave",
        "brnchave": "Branch Ave",
        "mtvernon": "Mt Vernon Sq 7th St-Convention Center",
        "mtvernsq": "Mt Vernon Sq 7th St-Convention Center",
        "mtvernonsq": "Mt Vernon Sq 7th St-Convention Center",
        "huntingtn": "Huntington",
        "largo": "Downtown Largo",
        "largotowncenter": "Downtown Largo",
        "wiehle": "Wiehle-Reston East",
    }
    if code in STATION_CODE_MAP:
        return STATION_CODE_MAP[code]
    key = "".join(c for c in (label or "").casefold() if c.isalnum())
    full = {
        "".join(c for c in name.casefold() if c.isalnum()): name
        for name in STATION_CODE_MAP.values()
    }
    return full.get(key) or aliases.get(key) or label


def normalize_prediction(raw: dict, service: str) -> dict:
    """Expose predictable names without conflating tracks with directions."""
    rail = service == "train"
    value = raw.get("Min" if rail else "Minutes")
    minutes = prediction_minutes(value)
    status = {"ARR": "arriving", "BRD": "boarding", "DLY": "delayed"}.get(
        str(value), "predicted" if minutes is not None else "unknown"
    )
    destination = raw.get("DestinationName") or raw.get("Destination")
    last_train = rail and any(
        str(raw.get(k, "")).lower().replace(" ", "") == "lasttrain"
        for k in ("DestinationName", "Destination")
    )
    if last_train:
        destination = STATION_CODE_MAP.get(raw.get("DestinationCode")) or next(
            (
                raw[k]
                for k in ("DestinationName", "Destination")
                if raw.get(k) and raw[k].lower().replace(" ", "") != "lasttrain"
            ),
            None,
        )
    if rail:
        destination = destination_name(raw.get("DestinationCode"), destination)
    direction, next_station = (
        rail_direction(
            raw.get("LocationCode"),
            raw.get("Line"),
            raw.get("DestinationCode"),
            destination,
        )
        if rail
        else (raw.get("DirectionText"), None)
    )
    return {
        "minutes": minutes,
        "status": status,
        "raw_status": value,
        "line": raw.get("Line") if rail else None,
        "line_name": LINE_NAME_MAP.get(raw.get("Line")) if rail else None,
        "route": raw.get("RouteID") if not rail else None,
        "last_train": last_train,
        "destination": destination if rail else raw.get("DirectionText"),
        "destination_code": raw.get("DestinationCode") if rail else None,
        "station_code": raw.get("LocationCode") if rail else None,
        "group": str(raw["Group"]) if raw.get("Group") is not None else None,
        "cars": raw.get("Car") if rail else None,
        "direction": direction,
        "next_station_code": next_station,
        "next_station": STATION_CODE_MAP.get(next_station),
        "direction_id": str(raw["DirectionNum"])
        if raw.get("DirectionNum") is not None
        else None,
        "vehicle_id": raw.get("VehicleID") if not rail else None,
        "trip_id": raw.get("TripID") if not rail else None,
    }


def filter_arrivals(arrivals: list[dict], journey: dict) -> list[dict]:
    """All populated filters are ANDed; values within a filter are ORed."""
    destinations = {
        alias
        for code in journey.get("destinations", [])
        for alias in station_codes(code)
    }
    return [
        a
        for a in arrivals
        if (
            (not journey.get("lines") or a["line"] in journey["lines"])
            and (not journey.get("routes") or a["route"] in journey["routes"])
            and (not destinations or a["destination_code"] in destinations)
            and (journey.get("group", "any") == "any" or a["group"] == journey["group"])
            and (
                journey.get("rail_direction", "any") == "any"
                or a.get("direction") == journey["rail_direction"]
            )
            and (
                journey.get("direction_id", "any") == "any"
                or a["direction_id"] == journey["direction_id"]
            )
        )
    ]
