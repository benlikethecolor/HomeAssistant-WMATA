"""Scheduled ride durations along the saved journey's actual station sequence."""

from .const import STATION_CODE_MAP
from .journeys import line_paths


def ride_minutes(leg, times):
    """Sum adjacent station times rather than an unrelated shortest-path trip."""
    if not times:
        return None
    by_name = {
        (STATION_CODE_MAP[a], STATION_CODE_MAP[b]): minutes
        for (a, b), minutes in times.items()
        if a in STATION_CODE_MAP and b in STATION_CODE_MAP
    }
    durations = []
    for line in leg["lines"]:
        for path in line_paths(line, leg["from"], leg["to"], scheduled=True):
            segments = [
                by_name.get((STATION_CODE_MAP[a], STATION_CODE_MAP[b]))
                for a, b in zip(path, path[1:], strict=False)
            ]
            if segments and all(value is not None for value in segments):
                durations.append(sum(segments))
    # Shared-track alternatives should agree; prefer the conservative duration.
    return max(durations) if durations else None
