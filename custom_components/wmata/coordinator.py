from .const import DEFAULT_SCAN_INTERVAL, HEADERS, URL
from dataclasses import dataclass
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_ID
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import logging
import aiohttp

_LOGGER = logging.getLogger(__name__)

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
        self.api_key = config_entry[CONF_API_KEY]
        self.station = config_entry[CONF_ID]
        self.stop = ""
        
        # TODO: do we need to confirm that the API works or is that covered in the config_flow?
        # doing it here anyways for now 
        self.connected: bool = False
        _LOGGER.debug(f"API key: {self.api_key}")
        _LOGGER.debug(f"API key type: {type(self.api_key)}")
        hass.async_create_task(self.async_validate_api_key())

        # set variables from options.  You need a default here incase options have not been set
        self.poll_interval = DEFAULT_SCAN_INTERVAL  # default to 1min

        # Initialize DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            # name=f"{DOMAIN} ({config_entry.unique_id})",
            name=f"{DOMAIN}",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.poll_interval),
        )
        
        # data formats:
        # next_buses = [{"RouteID": "D6", "DirectionText": "South", "Minutes": 5}, ...]
        # next_trains = [{"Destination": "Glenmont", "Line": "Red", "LocationName": "Glenmont", "Min": 3}, ...]
        self.next_buses = []
        self.next_trains = []
        
        # TODO: should be set by the user in the setup process
        self.stop = str
        self.station = str
        
    async def async_validate_api_key(self) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.wmata.com/Misc/Validate", headers={"api_key": self.api_key}) as response:
                _LOGGER.debug(f"API key validation response code: {response.status}")
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

            next_buses = await self.async_get_next_buses_at_stop(self.stop)
            next_trains = await self.async_get_next_trains_at_station(self.station)

        except APIAuthError as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err

        except Exception as err:
            # this will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        # what is returned here is stored in self.data by the DataUpdateCoordinator
        return APIData(next_buses=next_buses, next_trains=next_trains)

    async def async_get_next_buses_at_stop(self, stop_code: str) -> list:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{URL}/NextBusService.svc/json/jPredictions?StopID={stop_code}", headers=HEADERS) as response:
                bus_predictions = await response.json()
                return bus_predictions["Predictions"]

    async def async_get_next_trains_at_station(self, station_code: str) -> list:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{URL}/StationPrediction.svc/json/GetPrediction/{station_code}", headers=HEADERS) as response:
                train_predictions = await response.json()
                return train_predictions["Trains"]

class APIAuthError(Exception):
    """Exception class for auth error."""

class APIConnectionError(Exception):
    """Exception class for connection error."""
