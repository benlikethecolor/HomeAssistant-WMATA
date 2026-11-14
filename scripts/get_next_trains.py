"""Print WMATA's raw train predictions for one or more station codes.

python scripts/get_next_trains.py A01
python scripts/get_next_trains.py A01 C01
"""

import argparse

from _api import get, show


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "station",
        nargs="+",
        help="station code, such as A01 (see docs/METRO_STATION_CODES.md)",
    )
    codes = ",".join(code.strip().upper() for code in parser.parse_args().station)
    show(get(f"StationPrediction.svc/json/GetPrediction/{codes}"))


if __name__ == "__main__":
    main()
