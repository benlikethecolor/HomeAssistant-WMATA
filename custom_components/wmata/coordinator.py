"""Poll predictions once per station/stop for all its sensors."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_ID
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .alerts import alerts_for, base_route
from .api import APIAuthError, APIConnectionError, InvalidLocation, WmataApi
from .const import (
    CONF_INTERVAL,
    CONF_SERVICE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LINE_NAME_MAP,
    STATION_CODE_MAP,
    station_codes,
)
from .predictions import normalize_prediction, prediction_minutes

_LOGGER = logging.getLogger(__name__)


def sorted_predictions(items: list[dict], field: str) -> list[dict]:
    """Order both platforms by arrival time, unknown estimates last."""
    return sorted(
        items,
        key=lambda item: (
            prediction_minutes(item.get(field)) is None,
            prediction_minutes(item.get(field)) or 0,
        ),
    )


@dataclass
class APIData:
    next_buses: list[dict]
    next_trains: list[dict]
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    # Every current alert for this service, and this station's broken units.
    alerts: list[dict] = field(default_factory=list)
    outages: list[dict] = field(default_factory=list)

    @property
    def arrivals(self) -> list[dict]:
        service = "train" if self.next_trains else "bus"
        return [
            normalize_prediction(raw, service)
            for raw in self.next_trains or self.next_buses
        ]


class WmataCoordinator(DataUpdateCoordinator[APIData]):
    """One managed client and update loop per configured location."""

    def __init__(self, hass, config_entry: ConfigEntry) -> None:
        self.service_type = config_entry.data[CONF_SERVICE_TYPE]
        self.location = config_entry.data[CONF_ID]
        self.location_name = config_entry.data.get(
            "location_name", STATION_CODE_MAP.get(self.location, self.location)
        )
        self.codes = config_entry.data.get(
            "station_codes", station_codes(self.location)
        )
        self.served_lines = config_entry.data.get("served_lines", [])
        self.api = WmataApi(
            async_get_clientsession(hass), config_entry.data[CONF_API_KEY], hass=hass
        )
        self._metadata_loaded = False
        # Bus routes seen at this stop, so alerts still match between buses.
        self.routes: set[str] = set()
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.location}",
            config_entry=config_entry,
            update_interval=timedelta(
                seconds=config_entry.options.get(CONF_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> APIData:
        try:
            if not self._metadata_loaded:
                if self.service_type == "bus":
                    self.location_name = await self.api.stop_name(self.location)
                else:
                    stations = await self.api.stations()
                    selected = next(
                        (s for s in stations if s.get("Code") == self.location), None
                    )
                    if not selected:
                        raise InvalidLocation("Unknown station")
                    self.location_name = selected["Name"]
                    # WMATA publishes together codes for transfer station platforms.
                    self.codes = list(
                        dict.fromkeys(
                            [
                                *self.codes,
                                *[
                                    selected[k]
                                    for k in ("StationTogether1", "StationTogether2")
                                    if selected.get(k)
                                ],
                            ]
                        )
                    )
                    self.served_lines = sorted(
                        {
                            s[k]
                            for s in stations
                            if s.get("Code") in self.codes
                            for k in (
                                "LineCode1",
                                "LineCode2",
                                "LineCode3",
                                "LineCode4",
                            )
                            if s.get(k) in LINE_NAME_MAP
                        }
                    )
                self._metadata_loaded = True
            if self.service_type == "train":
                trains = await self.api.trains(self.codes)
                return APIData(
                    [],
                    sorted_predictions(trains, "Min"),
                    alerts=await self.api.rail_alerts(),
                    outages=[
                        unit
                        for unit in await self.api.unit_outages()
                        if unit["station_code"] in self.codes
                    ],
                )
            buses = await self.api.buses(self.location)
            self.routes.update(
                route
                for route in (base_route(b.get("RouteID")) for b in buses)
                if route
            )
            return APIData(
                sorted_predictions(buses, "Minutes"),
                [],
                alerts=await self.api.bus_alerts(),
            )
        except APIAuthError as err:
            raise ConfigEntryAuthFailed("WMATA API key is invalid") from err
        except (APIConnectionError, InvalidLocation) as err:
            raise UpdateFailed(str(err)) from err

    def alerts_for(self, lines=None, routes=None) -> list[dict]:
        """Alerts for the given lines or routes; by default, all that stop here."""
        if not self.data:
            return []
        if lines is None and routes is None:
            lines, routes = self.served_lines, self.routes
        return alerts_for(self.data.alerts, lines or (), routes or ())
