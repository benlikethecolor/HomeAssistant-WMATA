"""Travel-time estimates between two stations, in both directions."""

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.const import CONF_API_KEY
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import APIAuthError, APIConnectionError, WmataApi
from .const import (
    CONF_INTERVAL,
    CONF_TRANSFER_BUFFER,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRANSFER_BUFFER,
)
from .estimates import best_trip
from .journeys import candidate_journeys
from .station_predictions import async_station_predictions_many
from .websocket import trip_alternatives

DIRECTIONS = ("outbound", "return")


class CommuteCoordinator(DataUpdateCoordinator):
    """One WMATA request per poll covers every station on both trips."""

    def __init__(self, hass, entry):
        self.home = entry.data["home"]
        self.work = entry.data["work"]
        self.commute_name = entry.data.get("location_name", "Commute")
        self.buffer = entry.options.get(CONF_TRANSFER_BUFFER, DEFAULT_TRANSFER_BUFFER)
        self.api = WmataApi(
            async_get_clientsession(hass), entry.data[CONF_API_KEY], hass=hass
        )
        self._timetable_task = None
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=f"WMATA commute {self.home}-{self.work}",
            config_entry=entry,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    def stations(self, direction):
        """Origin and destination codes for a direction."""
        if direction == "outbound":
            return self.home, self.work
        return self.work, self.home

    async def _load_timetable(self):
        """Fetch the timetable off to the side, then refresh with it."""
        try:
            await self.api.rail_schedule()
        except (APIAuthError, APIConnectionError):
            return
        if self.api.rail_schedule_ready():
            await self.async_request_refresh()

    async def _async_update_data(self):
        # The timetable is a large download. Start from live trains alone
        # rather than making setup wait for it; it joins in once it has loaded.
        timetable = self.api.rail_schedule_ready()
        if not timetable and (
            self._timetable_task is None or self._timetable_task.done()
        ):
            self._timetable_task = self.hass.async_create_background_task(
                self._load_timetable(), "wmata rail timetable"
            )
        try:
            # Cached for an hour, so this mostly just notices a revoked key.
            await self.api.stations()
            routes = {
                direction: candidate_journeys(*self.stations(direction))
                for direction in DIRECTIONS
            }
            boarding = [
                leg["from"]
                for group in routes.values()
                for route in group
                for leg in route["legs"]
            ]
            station_data = await async_station_predictions_many(
                self.hass, self.api, boarding
            )
            if all(data is None for data in station_data.values()):
                raise UpdateFailed("WMATA predictions are unavailable")
            trips = {}
            for direction, group in routes.items():
                alternatives = await trip_alternatives(
                    self.hass, self.api, group, station_data, timetable
                )
                trips[direction] = best_trip(
                    alternatives, datetime.now(UTC).timestamp(), self.buffer
                )
            return {"trips": trips, "updated_at": datetime.now(UTC).isoformat()}
        except APIAuthError as err:
            raise ConfigEntryAuthFailed("WMATA API key is invalid") from err
        except APIConnectionError as err:
            raise UpdateFailed(str(err)) from err
