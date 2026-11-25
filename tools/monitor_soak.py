"""Read-only Health entity monitor for an isolated Home Assistant instance."""

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

FIELDS = {
    "last_successful_request",
    "last_error_type",
    "requests",
    "failures",
    "rate_limit_seconds",
    "timetable",
    "polling_available",
}


def sample(url, token, entity):
    request = urllib.request.Request(
        url.rstrip("/") + "/api/states/" + urllib.parse.quote(entity, safe=""),
        headers={"Authorization": "Bearer " + token},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            state = json.load(response)
        attrs = state.get("attributes", {})
        if "polling_available" not in attrs or "timetable" not in attrs:
            return {"entity": entity, "error": "not_health_entity"}
        if state.get("state") not in (
            "healthy",
            "degraded",
            "rate_limited",
            "unavailable",
            "unknown",
        ):
            return {"entity": entity, "error": "unexpected_health_state"}
        return {
            "entity": entity,
            "state": state.get("state"),
            "health": {key: value for key, value in attrs.items() if key in FIELDS},
            "feeds": {
                kind: {key: status.get(key) for key in ("stale", "updated_at")}
                for kind, status in attrs.get("feeds", {}).items()
                if kind in ("rail", "bus", "units")
            },
        }
    except (
        urllib.error.URLError,
        ValueError,
        TimeoutError,
        AttributeError,
        TypeError,
    ) as error:
        return {"entity": entity, "error": type(error).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--entities", nargs="+", required=True)
    parser.add_argument("--hours", type=float, default=48)
    parser.add_argument("--interval", type=float, default=60)
    args = parser.parse_args()
    url = urllib.parse.urlparse(args.url)
    if (
        url.scheme not in ("http", "https")
        or not url.netloc
        or url.username
        or url.password
    ):
        parser.error("Use an HTTP(S) HA base URL without embedded credentials")
    if not 0 < args.hours <= 168 or not 10 <= args.interval <= 3600:
        parser.error(
            "Hours must be between 0 and 168; interval must be between 10 and 3600 seconds"
        )
    token = args.token_file.read_text().strip()
    if not token:
        parser.error("The token file is empty")
    end = time.monotonic() + args.hours * 3600
    while time.monotonic() < end:
        print(
            json.dumps(
                {
                    "checked_at": datetime.now(UTC).isoformat(),
                    "entities": [
                        sample(args.url, token, entity) for entity in args.entities
                    ],
                }
            ),
            flush=True,
        )
        time.sleep(min(args.interval, max(0, end - time.monotonic())))


if __name__ == "__main__":
    main()
