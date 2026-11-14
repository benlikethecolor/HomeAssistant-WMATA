"""Print WMATA's raw bus predictions for a stop.

python scripts/get_next_buses.py 1001195
"""

import argparse

from _api import get, show


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("stop", help="seven-digit stop ID from the sign at the stop")
    show(get("NextBusService.svc/json/jPredictions", StopID=parser.parse_args().stop))


if __name__ == "__main__":
    main()
