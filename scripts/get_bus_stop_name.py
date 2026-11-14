"""Print the name WMATA has on file for a bus stop.

python scripts/get_bus_stop_name.py 1001195
python scripts/get_bus_stop_name.py 1001195 --raw
"""

import argparse
import sys

from _api import get, show


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("stop", help="seven-digit stop ID from the sign at the stop")
    parser.add_argument(
        "--raw", action="store_true", help="print the whole schedule response"
    )
    args = parser.parse_args()
    data = get("Bus.svc/json/jStopSchedule", StopID=args.stop)
    if args.raw:
        show(data)
        return
    name = (data.get("Stop") or {}).get("Name")
    if not name:
        sys.exit(f"WMATA doesn't have a stop with the ID {args.stop}.")
    print(name)


if __name__ == "__main__":
    main()
