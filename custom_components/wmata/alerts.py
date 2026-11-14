"""Service alerts: rail and bus incidents, and elevator and escalator outages.

WMATA's incident feeds are advisory. Nothing here is allowed to break an
arrival board, so malformed rows are dropped rather than raised.
"""

import re
from datetime import datetime

from .const import LINE_NAME_MAP, STATION_CODE_MAP
from .schedules import ZONE


def _eastern(value) -> str | None:
    """WMATA reports local time without an offset."""
    try:
        return datetime.fromisoformat(value).replace(tzinfo=ZONE).isoformat()
    except (TypeError, ValueError):
        return None


def _text(value) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def base_route(route) -> str | None:
    """D34, D34v1 and D34*2 are the same route as far as an alert goes."""
    if not isinstance(route, str) or not route.strip():
        return None
    return re.split(r"[*/]|v\d", route.strip())[0].upper()


def rail_alert(raw: dict) -> dict | None:
    """LinesAffected looks like 'RD;' or 'BL; OR; SV;'."""
    description = _text(raw.get("Description"))
    lines = [
        line
        for line in dict.fromkeys(
            re.findall(r"[A-Z]{2}", str(raw.get("LinesAffected") or "").upper())
        )
        if line in LINE_NAME_MAP
    ]
    if not description or not lines:
        return None
    return {
        "id": _text(raw.get("IncidentID")),
        "type": (_text(raw.get("IncidentType")) or "Alert").lower(),
        "lines": lines,
        "routes": [],
        "description": description,
        "updated_at": _eastern(raw.get("DateUpdated")),
    }


def bus_alert(raw: dict) -> dict | None:
    description = _text(raw.get("Description"))
    affected = raw.get("RoutesAffected")
    routes = list(
        dict.fromkeys(
            route
            for route in map(base_route, affected if isinstance(affected, list) else [])
            if route
        )
    )
    if not description or not routes:
        return None
    return {
        "id": _text(raw.get("IncidentID")),
        "type": (_text(raw.get("IncidentType")) or "Alert").lower(),
        "lines": [],
        "routes": routes,
        "description": description,
        "updated_at": _eastern(raw.get("DateUpdated")),
    }


def unit_outage(raw: dict) -> dict | None:
    """One elevator or escalator that is out of service."""
    code = raw.get("StationCode")
    kind = str(raw.get("UnitType") or "").lower()
    if code not in STATION_CODE_MAP or kind not in ("elevator", "escalator"):
        return None
    return {
        "unit": _text(raw.get("UnitName")),
        "type": kind,
        "station_code": code,
        "location": _text(raw.get("LocationDescription")),
        "reason": _text(raw.get("SymptomDescription")),
        "since": _eastern(raw.get("DateOutOfServ")),
        "estimated_return": _eastern(raw.get("EstimatedReturnToService")),
    }


def alerts_for(alerts, lines=(), routes=()) -> list[dict]:
    """Alerts that touch any of the given rail lines or bus routes."""
    lines = set(lines)
    routes = {route for route in map(base_route, routes) if route}
    return [
        alert
        for alert in alerts or []
        if lines.intersection(alert["lines"]) or routes.intersection(alert["routes"])
    ]
