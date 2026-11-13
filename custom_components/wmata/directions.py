"""Station-specific travel directions from WMATA route order.

Group is intentionally unused: it describes a prediction track, not travel
direction. Directions describe travel toward the next station, not the bearing
of the final terminus. Source and conventions: docs/RAIL_DIRECTIONS.md.
"""

import itertools
from collections import deque
from functools import lru_cache

from .const import STATION_CODE_MAP, station_codes

ROUTES = {
    "BL": (
        "J03",
        "J02",
        "C13",
        "C12",
        "C11",
        "C10",
        "C09",
        "C08",
        "C07",
        "C06",
        "C05",
        "C04",
        "C03",
        "C02",
        "C01",
        "D01",
        "D02",
        "D03",
        "D04",
        "D05",
        "D06",
        "D07",
        "D08",
        "G01",
        "G02",
        "G03",
        "G04",
        "G05",
    ),
    "GR": (
        "F11",
        "F10",
        "F09",
        "F08",
        "F07",
        "F06",
        "F05",
        "F04",
        "F03",
        "F02",
        "F01",
        "E01",
        "E02",
        "E03",
        "E04",
        "E05",
        "E06",
        "E07",
        "E08",
        "E09",
        "E10",
    ),
    "OR": (
        "K08",
        "K07",
        "K06",
        "K05",
        "K04",
        "K03",
        "K02",
        "K01",
        "C05",
        "C04",
        "C03",
        "C02",
        "C01",
        "D01",
        "D02",
        "D03",
        "D04",
        "D05",
        "D06",
        "D07",
        "D08",
        "D09",
        "D10",
        "D11",
        "D12",
        "D13",
    ),
    "RD": (
        "A15",
        "A14",
        "A13",
        "A12",
        "A11",
        "A10",
        "A09",
        "A08",
        "A07",
        "A06",
        "A05",
        "A04",
        "A03",
        "A02",
        "A01",
        "B01",
        "B02",
        "B03",
        "B35",
        "B04",
        "B05",
        "B06",
        "B07",
        "B08",
        "B09",
        "B10",
        "B11",
    ),
    "SV": (
        "N12",
        "N11",
        "N10",
        "N09",
        "N08",
        "N07",
        "N06",
        "N04",
        "N03",
        "N02",
        "N01",
        "K05",
        "K04",
        "K03",
        "K02",
        "K01",
        "C05",
        "C04",
        "C03",
        "C02",
        "C01",
        "D01",
        "D02",
        "D03",
        "D04",
        "D05",
        "D06",
        "D07",
        "D08",
        "G01",
        "G02",
        "G03",
        "G04",
        "G05",
    ),
    "YL": (
        "C15",
        "C14",
        "C13",
        "C12",
        "C11",
        "C10",
        "C09",
        "C08",
        "C07",
        "F03",
        "F02",
        "F01",
        "E01",
        "E02",
        "E03",
        "E04",
        "E05",
        "E06",
        "E07",
        "E08",
        "E09",
        "E10",
    ),
}


@lru_cache(maxsize=6)
def _graph(line):
    graph = {}
    directions = {}
    route = ROUTES.get(line, ())
    paths = [route]
    # Orange, Silver and Blue can use either eastern branch. This also supports
    # announced Silver-to-New-Carrollton service without guessing from Group.
    if line in ("OR", "SV", "BL"):
        split = route.index("D08")
        for other in ("OR", "BL"):
            branch = ROUTES[other]
            paths.append(route[:split] + branch[branch.index("D08") :])
    for path in paths:
        for i, (a, b) in enumerate(itertools.pairwise(path)):
            forward, backward = "Eastbound", "Westbound"
            if line in ("GR", "YL") or (line == "BL" and i < path.index("C05")):
                forward, backward = "Northbound", "Southbound"
            elif line == "RD":
                forward = (
                    "Southbound"
                    if a.startswith("A") and a != "A01"
                    else ("Eastbound" if a in ("A01", "B01", "B02") else "Northbound")
                )
                backward = (
                    "Northbound"
                    if b.startswith("A") and b != "A01"
                    else ("Westbound" if b in ("A01", "B01", "B02") else "Southbound")
                )
            directions[a, b] = forward
            directions[b, a] = backward
            graph.setdefault(a, set()).add(b)
            graph.setdefault(b, set()).add(a)
    return graph, directions


def rail_direction(station, line, destination_code, destination):
    """Return (corridor departure direction, next station), or (None, None).

    Resolve line-specific transfer codes before walking the route. Unknown or
    contradictory endpoints and terminating trains must never inherit a track
    group's assumed direction.
    """
    if line not in ROUTES or station not in STATION_CODE_MAP:
        return None, None
    graph, directions = _graph(line)
    origins = [code for code in station_codes(station) if code in graph]
    if destination_code in STATION_CODE_MAP:
        targets = set(station_codes(destination_code)) & graph.keys()
    else:
        targets = {
            code
            for code, name in STATION_CODE_MAP.items()
            if name == destination and code in graph
        }
    if len(origins) != 1 or not targets or targets.intersection(origins):
        return None, None
    origin = origins[0]
    queue = deque([(origin, None)])
    visited = {origin}
    while queue:
        current, first = queue.popleft()
        if current in targets:
            return directions[origin, first], first
        for neighbor in sorted(graph[current]):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, first or neighbor))
    return None, None
