"""Station-to-station routes and matching boarding predictions."""

from collections import defaultdict
from functools import lru_cache
from heapq import heappop, heappush
from itertools import count

from .const import LINE_NAME_MAP, STATION_CODE_MAP, station_codes
from .directions import ROUTES

STATIONS_BY_NAME = {name: code for code, name in reversed(STATION_CODE_MAP.items())}


@lru_cache(maxsize=6)
def variants(line):
    """Include either eastern branch when a prediction reports that service."""
    paths = [ROUTES[line]]
    if line in ("BL", "OR", "SV"):
        prefix = ROUTES[line][: ROUTES[line].index("D08")]
        for branch in (ROUTES["OR"], ROUTES["BL"]):
            paths.append(prefix + branch[branch.index("D08") :])
    return tuple(dict.fromkeys(paths))


@lru_cache(maxsize=4096)
def line_paths(line, origin, destination, scheduled=False):
    """Return contiguous routes without changing lines or reversing at a fork."""
    if line not in ROUTES:
        return ()
    origins, targets = set(station_codes(origin)), set(station_codes(destination))
    result = set()
    for route in (ROUTES[line],) if scheduled else variants(line):
        starts = [i for i, code in enumerate(route) if code in origins]
        ends = [i for i, code in enumerate(route) if code in targets]
        for a in starts:
            for b in ends:
                if a != b:
                    path = (
                        route[a : b + 1] if a < b else tuple(reversed(route[b : a + 1]))
                    )
                    result.add(path)
    return tuple(sorted(result, key=lambda path: (len(path), path)))


@lru_cache(maxsize=2048)
def direct_legs(origin, destination):
    grouped = {}
    for line in ROUTES:
        for path in line_paths(line, origin, destination, scheduled=True):
            key = tuple(STATION_CODE_MAP[code] for code in path)
            if key not in grouped:
                grouped[key] = {
                    "from": STATIONS_BY_NAME[key[0]],
                    "to": STATIONS_BY_NAME[key[-1]],
                    "from_name": key[0],
                    "to_name": key[-1],
                    "lines": [],
                    "stops": len(path) - 1,
                }
            grouped[key]["lines"].append(line)
    return tuple(grouped.values())


@lru_cache(maxsize=1)
def transfer_stations():
    """Only route junctions need consideration; shared-track stops add no route."""
    edges = defaultdict(lambda: defaultdict(set))
    served = defaultdict(set)
    for line in ROUTES:
        for path in (ROUTES[line],):
            for a, b in zip(path, path[1:], strict=False):
                a, b = STATION_CODE_MAP[a], STATION_CODE_MAP[b]
                edges[a][b].add(line)
                edges[b][a].add(line)
                served[a].add(line)
                served[b].add(line)
    return {
        name
        for name, lines in served.items()
        if len(lines) > 1 and any(edge != lines for edge in edges[name].values())
    }


@lru_cache(maxsize=256)
def plan_journey(origin, destination):
    """Prefer fewer changes, then fewer stops. No travel-time estimate is made."""
    if origin not in STATION_CODE_MAP or destination not in STATION_CODE_MAP:
        return None
    start, target = STATION_CODE_MAP[origin], STATION_CODE_MAP[destination]
    if start == target:
        return None
    transfers = transfer_stations()
    candidates = sorted(transfers | {target})
    serial = count()
    queue = [(0, 0, next(serial), start, (), [])]
    best = {}
    while queue:
        changes, stops, _, current, previous, legs = heappop(queue)
        state = (current, previous)
        if state in best and best[state] <= (changes, stops):
            continue
        best[state] = (changes, stops)
        if current == target:
            return {
                "origin": STATIONS_BY_NAME[start],
                "origin_name": start,
                "destination": STATIONS_BY_NAME[target],
                "destination_name": target,
                "legs": legs,
                "transfers": max(0, len(legs) - 1),
                "stops": stops,
            }
        for name in candidates:
            if name == current:
                continue
            for leg in direct_legs(STATIONS_BY_NAME[current], STATIONS_BY_NAME[name]):
                if set(previous).intersection(leg["lines"]):
                    continue
                # Adding a same-line leg would be an unnecessary change or reversal.
                following = [*legs, leg]
                heappush(
                    queue,
                    (
                        len(following) - 1,
                        stops + leg["stops"],
                        next(serial),
                        name,
                        tuple(leg["lines"]),
                        following,
                    ),
                )
    return None


def describe_route(plan):
    parts = []
    for i, leg in enumerate(plan["legs"]):
        lines = " / ".join(LINE_NAME_MAP[line] for line in leg["lines"])
        parts.append(
            f"{'Board' if i == 0 else 'Change to'} {lines} to {leg['to_name']}"
        )
    return ". ".join(parts) + "."


def trip_matches(arrival, plan):
    """Only show trains whose reported terminus reaches the first leg's goal."""
    leg = plan["legs"][0]
    origin = arrival.get("station_code") or plan["origin"]
    if STATION_CODE_MAP.get(origin) != plan["origin_name"]:
        return False
    destination = arrival.get("destination_code")
    if destination not in STATION_CODE_MAP:
        destination = STATIONS_BY_NAME.get(arrival.get("destination"))
    if destination is None:
        return False
    return any(
        leg["to_name"] in [STATION_CODE_MAP[c] for c in path[1:]]
        for path in line_paths(arrival["line"], origin, destination)
    )


@lru_cache(maxsize=256)
def candidate_journeys(origin, destination):
    """Enumerate loop-free rail routes with up to three platform changes."""
    baseline = plan_journey(origin, destination)
    if not baseline:
        return ()
    start, target = baseline["origin_name"], baseline["destination_name"]
    junctions = sorted(transfer_stations() | {target})
    found = {}

    def visit(current, previous, visited, legs):
        if len(legs) >= 4:
            return
        for name in junctions:
            if name in visited:
                continue
            for leg in direct_legs(STATIONS_BY_NAME[current], STATIONS_BY_NAME[name]):
                if set(previous).intersection(leg["lines"]):
                    continue
                path = line_paths(
                    leg["lines"][0], leg["from"], leg["to"], scheduled=True
                )[0]
                following = [STATION_CODE_MAP[code] for code in path[1:]]
                if visited.intersection(following) or (
                    target in following and name != target
                ):
                    continue
                trip = [*legs, leg]
                if name == target:
                    key = tuple(
                        (value["from"], value["to"], tuple(value["lines"]))
                        for value in trip
                    )
                    found[key] = {
                        **baseline,
                        "legs": trip,
                        "transfers": len(trip) - 1,
                        "stops": sum(value["stops"] for value in trip),
                    }
                else:
                    visit(name, leg["lines"], visited | set(following), trip)

    visit(start, (), {start}, [])
    # Stable ordering is only for presentation fallback, never an arrival ranking.
    return tuple(
        sorted(
            found.values(),
            key=lambda trip: (
                trip["transfers"],
                trip["stops"],
                tuple(leg["to"] for leg in trip["legs"]),
            ),
        )
    )
