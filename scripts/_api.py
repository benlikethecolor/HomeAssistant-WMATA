"""Shared request helper for the standalone WMATA API scripts.

Set your key in the WMATA_API_KEY environment variable first:

    export WMATA_API_KEY=your-key-here
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = "https://api.wmata.com"


def api_key() -> str:
    """Read the key from the environment; wmata_api is the older name."""
    key = os.environ.get("WMATA_API_KEY") or os.environ.get("wmata_api")
    if not key:
        sys.exit("Set the WMATA_API_KEY environment variable to your WMATA API key.")
    return key.strip()


def get(path: str, **params: str) -> dict:
    """Fetch one endpoint as JSON, exiting with a readable message on failure."""
    url = f"{URL}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"api_key": api_key()})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        if err.code in (401, 403):
            sys.exit("WMATA rejected the API key. Check your developer subscription.")
        if err.code == 429:
            sys.exit("WMATA rate limit reached. Wait a minute and try again.")
        sys.exit(f"WMATA returned HTTP {err.code} for {path}.")
    except (urllib.error.URLError, TimeoutError) as err:
        sys.exit(f"Couldn't reach WMATA: {err}")
    except ValueError:
        sys.exit(f"WMATA returned something other than JSON for {path}.")


def show(data) -> None:
    print(json.dumps(data, indent=2))
