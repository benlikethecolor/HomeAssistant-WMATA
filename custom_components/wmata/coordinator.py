from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, STATION_CODE_MAP, URL
from dataclasses import dataclass
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import logging
import aiohttp

_LOGGER = logging.getLogger(__name__)

CONF_SERVICE_TYPE = "service_type"


@dataclass
class APIData:
    """Class to hold api data"""
    next_buses: list
    next_trains: list


class WmataCoordinator(DataUpdateCoordinator):
    """Base coordinator class"""

    data: APIData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator class"""

        # Set variables from values entered in config flow setup
        self.unique_id = config_entry.entry_id
        self.api_key = config_entry.data[CONF_API_KEY]
        self.service_type = config_entry.data[CONF_SERVICE_TYPE]
        self.headers = {"api_key": self.api_key}

        # bus settings
        if self.service_type == "bus":
            self.bus_stop = config_entry.data[CONF_ID]
            self.bus_stop_name = None

        # train settings
        elif self.service_type == "train":
            self.station = config_entry.data[CONF_ID]
            self.station_name = STATION_CODE_MAP[self.station]

        self.connected: bool = False
        _LOGGER.debug(f"API key: {self.api_key}")
        _LOGGER.debug(f"API key type: {type(self.api_key)}")

        # set variables from options.  You need a default here incase options have not been set
        self.poll_interval = DEFAULT_SCAN_INTERVAL  # default to 1min

        # Initialize DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.poll_interval),
        )

        # data formats:
        # next_buses = [{"RouteID": "S2", "DirectionText": "North to Silver Spring", "DirectionNum": "0", "Minutes": 3, "VehicleID": "5508", "TripID": "13291060"}, ...]
        # next_trains = [{"Destination": "Glenmont", "Line": "Red", "LocationName": "Glenmont", "Min": 3}, ...]
        self.next_buses = []
        self.next_trains = []

    async def async_initialize(self):
        """Asynchronously initialize additional attributes."""
        if self.service_type == "bus":
            data = await self.async_get_bus_data_at_stop(self.bus_stop)
            self.bus_stop_name = data["stop_name"]
            
            

    async def async_validate_api_key(self) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.wmata.com/Misc/Validate", headers=self.headers) as response:
                _LOGGER.debug(
                    f"API key validation response code: {response.status}")
                _LOGGER.debug(f"API key validation response: {response}")

                if response.status == 200:
                    _LOGGER.debug("API key successfully validated")
                    self.connected = True

                    return True

                raise APIAuthError("Invalid API key")

    async def async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """

        try:
            if not self.connected:
                await self.async_validate_api_key()

            if self.service_type == "train":
                next_trains = await self.async_get_next_trains_at_station(self.station)
                return APIData(next_trains=next_trains, next_buses=[])
            elif self.service_type == "bus":
                data = await self.async_get_bus_data_at_stop(self.bus_stop)
                next_buses = data["predictions"]
                return APIData(next_buses=next_buses, next_trains=[])

        except APIAuthError as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err

        except Exception as err:
            # this will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_get_next_trains_at_station(self, station_code: str) -> list:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{URL}/StationPrediction.svc/json/GetPrediction/{station_code}", headers=self.headers) as response:
                train_predictions = await response.json()

                return train_predictions["Trains"]

    async def async_get_bus_data_at_stop(self, stop_code: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{URL}/NextBusService.svc/json/jPredictions?StopID={stop_code}",
                headers=self.headers,
            ) as response:
                data = await response.json()

                return {
                    "stop_name": data.get("StopName"),
                    "predictions": data.get("Predictions", []),
                }



class APIAuthError(Exception):
    """Exception class for auth error."""


class APIConnectionError(Exception):
    """Exception class for connection error."""
