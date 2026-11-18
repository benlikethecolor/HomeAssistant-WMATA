"""Map WMATA circuit occupancy onto bundled schematic and geographic routes."""

import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path

from homeassistant.const import CONF_API_KEY
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import APIAuthError, APIConnectionError, WmataApi
from .const import CONF_INTERVAL, DEFAULT_SCAN_INTERVAL
from .predictions import destination_name
from .schematic import STATIONS


@dataclass
class NetworkGeometry:
    """A circuit can have a different drawn position for each shared line."""

    schematic: dict
    geographic: dict
    paths: list[dict]
    route_circuits: set[int]


def read_shapes():
    """Read bundled assets in HA's executor."""
    directory = Path(__file__).parent
    return tuple(
        json.loads((directory / name).read_text())
        for name in ("route_shapes.json", "geo_shapes.json")
    )


def segment_curve(shapes, line, origin, destination):
    """Reuse the same shape for either track direction."""
    curve = shapes.get(f"{line}/{origin}/{destination}")
    if curve is not None:
        return curve
    return list(reversed(shapes.get(f"{line}/{destination}/{origin}", [])))


def build_geometry(shapes, geo_shapes, routes, track_circuits):
    """Locate revenue circuits, then attach connected side-track circuits."""
    schematic, geographic, paths = {}, {}, []
    for route in routes:
        circuits = route["TrackCircuits"]
        line = route["LineCode"]
        anchors = [
            (index, circuit["StationCode"])
            for index, circuit in enumerate(circuits)
            if circuit.get("StationCode") in STATIONS
        ]
        if route["TrackNum"] == 1:
            paths.append(
                {"line": line, "points": [STATIONS[code] for _, code in anchors]}
            )
        for (start, origin), (end, destination) in pairwise(anchors):
            for dataset, positions in ((shapes, schematic), (geo_shapes, geographic)):
                curve = segment_curve(dataset, line, origin, destination)
                if not curve:
                    continue
                for index in range(start, end + 1):
                    fraction = (index - start) / (end - start)
                    point = curve[round((len(curve) - 1) * fraction)]
                    positions.setdefault(circuits[index]["CircuitId"], {})[line] = point

    route_ids = set(schematic) | set(geographic)
    if not route_ids:
        raise ValueError("No circuits match the bundled map geometry")
    neighbors = defaultdict(set)
    for circuit in track_circuits:
        origin = circuit["CircuitId"]
        for side in circuit["Neighbors"]:
            for adjacent in side["CircuitIds"]:
                neighbors[origin].add(adjacent)
                neighbors[adjacent].add(origin)

    # Breadth-first expansion gives side tracks their nearest known circuit.
    known = set(route_ids)
    pending = deque(sorted(known))
    while pending:
        origin = pending.popleft()
        for adjacent in sorted(neighbors[origin]):
            if adjacent in known:
                continue
            known.add(adjacent)
            for positions in (schematic, geographic):
                if origin in positions:
                    positions[adjacent] = positions[origin]
            pending.append(adjacent)
    return NetworkGeometry(schematic, geographic, paths, route_ids)


def mapped_train(train, geometry):
    """Preserve unlocatable trains without assigning an invented location."""
    circuit = train.get("CircuitId")
    line = train.get("LineCode")
    schematic = geometry.schematic.get(circuit, {})
    geographic = geometry.geographic.get(circuit, {})
    point = schematic.get(line) or next(iter(schematic.values()), None)
    geo_point = geographic.get(line) or next(iter(geographic.values()), None)
    position_type = "unknown"
    if circuit in geometry.route_circuits:
        position_type = "route"
    elif point or geo_point:
        position_type = "nearby"
    destination_code = train.get("DestinationStationCode")
    return {
        "id": train.get("TrainId"),
        "line": line,
        "track_lines": sorted(set(schematic) | set(geographic)),
        "circuit": circuit,
        "service": train.get("ServiceType"),
        "position_type": position_type,
        "destination_code": destination_code,
        "destination": destination_name(destination_code, None),
        "point": point,
        "geo_point": geo_point,
    }


class MapCoordinator(DataUpdateCoordinator):
    """One network poll serves every map card and its station popups."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name="WMATA train map",
            config_entry=entry,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.api = WmataApi(
            async_get_clientsession(hass), entry.data[CONF_API_KEY], hass=hass
        )
        self.geometry = None

    async def _async_update_data(self):
        try:
            if self.geometry is None:
                shapes, geo_shapes = await self.hass.async_add_executor_job(read_shapes)
                routes = await self.api.standard_routes()
                circuits = await self.api.track_circuits()
                self.geometry = build_geometry(shapes, geo_shapes, routes, circuits)
            positions = await self.api.train_positions()
            return {
                "paths": self.geometry.paths,
                "trains": [mapped_train(train, self.geometry) for train in positions],
                "updated_at": datetime.now(UTC).isoformat(),
            }
        except APIAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (APIConnectionError, OSError, KeyError, TypeError, ValueError) as err:
            raise UpdateFailed(f"Unable to update the WMATA train map: {err}") from err
