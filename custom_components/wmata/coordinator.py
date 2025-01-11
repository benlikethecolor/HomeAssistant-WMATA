from .const import DEFAULT_SCAN_INTERVAL, HEADERS, URL
from dataclasses import dataclass
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_ID
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import logging
import requests


_LOGGER = logging.getLogger(__name__)


@dataclass
class APIData:
    """Class to hold api data"""
    # TODO: modify to update when new data comes in on train distances
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
        self.async_validate_api_key(self.api_key)

        # set variables from options.  You need a default here incase options have not been set
        self.poll_interval = DEFAULT_SCAN_INTERVAL  # default to 1min

        # Initialize DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
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
        output = requests.get(
            headers={"api_key": self.api_key}, url="https://api.wmata.com/Misc/Validate")

        if output.status_code == 200:
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
                await self.hass.async_add_executor_job(self.async_validate_api_key)

            # devices = await self.hass.async_add_executor_job(self.api.get_devices)
            next_buses = await self.hass.async_add_executor_job(self.async_get_next_buses_at_stop, self.stop)
            next_trains = await self.hass.async_add_executor_job(self.async_get_next_trains_at_station, self.station)

        except APIAuthError as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err

        except Exception as err:
            # this will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        # what is returned here is stored in self.data by the DataUpdateCoordinator
        return APIData(next_buses=next_buses, next_trains=next_trains)

    async def async_get_next_buses_at_stop(stop_code: str) -> list:
        output = requests.get(
            headers=HEADERS,
            url="%s/NextBusService.svc/json/jPredictions?StopID=%s" % (
                URL, stop_code)
        )

        bus_predictions = [bus for bus in output.json()["Predictions"]]

        # print(bus_predictions)

        # for bus in bus_predictions:
        #     print(bus["RouteID"])
        #     print(bus["DirectionText"])
        #     print(bus["Minutes"])
        #     print()

        return bus_predictions

    async def async_get_next_trains_at_station(station_code: str) -> list:
        output = requests.get(
            headers=HEADERS,
            url="%s/StationPrediction.svc/json/GetPrediction/%s" % (
                URL, station_code)
        )

        train_predictions = [train["Destination"]
                             for train in output.json()["Trains"]]

        # print(train_predictions)

        # for train in train_predictions:
        #     print(train["Destination"])
        #     print(train["Line"])
        #     print(train["LocationName"])
        #     print(train["Min"])
        #     print()

        return train_predictions

    # def get_device_by_id(self, device_type: DeviceType, device_id: int) -> Device | None:
    #     """Return device by device id."""
    #     # called by the binary sensors and sensors to get their updated data from self.data
    #     try:
    #         return [device for device in self.data.devices if device.device_type == device_type and device.device_id == device_id][0]

    #     except IndexError:
    #         return None


class APIAuthError(Exception):
    """Exception class for auth error."""


class APIConnectionError(Exception):
    """Exception class for connection error."""


# TODO: https://developer.wmata.com/api-details#api=54763629281d83086473f231&operation=5476362a281d830c946a3d6c
# get bus schedule at stop
