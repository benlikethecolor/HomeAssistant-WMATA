"""Regenerate the station lists from WMATA's current station catalog.

    python scripts/generate_station_codes.py            # print STATION_CODE_MAP
    python scripts/generate_station_codes.py --markdown  # rewrite the docs table

Run this when WMATA renames or adds a station, then paste the printed map into
custom_components/wmata/const.py.
"""

import argparse
from pathlib import Path

from _api import get

DOC = Path(__file__).resolve().parents[1] / "docs" / "METRO_STATION_CODES.md"
LINES = {
    "BL": "Blue",
    "GR": "Green",
    "OR": "Orange",
    "RD": "Red",
    "SV": "Silver",
    "YL": "Yellow",
}


def station_map(stations: list[dict]) -> str:
    """Python source for STATION_CODE_MAP, ordered by code."""
    rows = "".join(
        f"    {station['Code']!r}: {station['Name']!r},\n"
        for station in sorted(stations, key=lambda station: station["Code"])
    )
    return "STATION_CODE_MAP = {\n" + rows + "}"


def markdown_table(stations: list[dict]) -> str:
    """The table in docs/METRO_STATION_CODES.md, ordered by name."""
    table = "| Name | Line | Code\n|:-----|:----:|:-----|\n"
    for station in sorted(stations, key=lambda station: station["Name"]):
        codes = (station.get(f"LineCode{number}") for number in range(1, 5))
        lines = sorted(LINES.get(code, code) for code in codes if code)
        table += f"| {station['Name']} | {', '.join(lines)} | {station['Code']} |\n"
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--markdown",
        action="store_true",
        help=f"rewrite {DOC.relative_to(DOC.parents[1])} instead of printing the map",
    )
    args = parser.parse_args()
    stations = get("Rail.svc/json/jStations")["Stations"]
    if args.markdown:
        DOC.write_text(markdown_table(stations))
        print(f"Wrote {len(stations)} stations to {DOC}")
    else:
        print(station_map(stations))


if __name__ == "__main__":
    main()
