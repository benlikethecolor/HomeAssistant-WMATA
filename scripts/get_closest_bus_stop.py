"""List the bus stops around a point, closest first.

python scripts/get_closest_bus_stop.py 38.8983 -77.0281
python scripts/get_closest_bus_stop.py 38.8983 -77.0281 --radius 800
"""

import argparse
import math
import sys

from _api import get, show


def meters_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Flat-earth distance, which is plenty over a few hundred metres."""
    north = (lat2 - lat1) * 111_320
    east = (lon2 - lon1) * 111_320 * math.cos(math.radians(lat1))
    return math.hypot(north, east)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("latitude", type=float)
    parser.add_argument("longitude", type=float)
    parser.add_argument(
        "--radius", type=int, default=500, help="search radius in metres (default 500)"
    )
    parser.add_argument("--raw", action="store_true", help="print the raw response")
    args = parser.parse_args()
    data = get(
        "Bus.svc/json/jStops",
        Lat=str(args.latitude),
        Lon=str(args.longitude),
        Radius=str(args.radius),
    )
    if args.raw:
        show(data)
        return
    stops = [
        stop
        for stop in data.get("Stops") or []
        if isinstance(stop.get("Lat"), (int, float))
        and isinstance(stop.get("Lon"), (int, float))
    ]
    if not stops:
        sys.exit(f"No stops within {args.radius} m. Try a larger --radius.")
    stops.sort(
        key=lambda stop: meters_between(
            args.latitude, args.longitude, stop["Lat"], stop["Lon"]
        )
    )
    for stop in stops:
        away = meters_between(args.latitude, args.longitude, stop["Lat"], stop["Lon"])
        routes = ", ".join(stop.get("Routes") or [])
        print(f"{stop.get('StopID')}  {away:4.0f} m  {stop.get('Name')}  [{routes}]")


if __name__ == "__main__":
    main()
