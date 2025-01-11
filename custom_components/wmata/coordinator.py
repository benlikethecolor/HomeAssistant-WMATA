from .const import DEFAULT_SCAN_INTERVAL, HEADERS, URL
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from random import choice, randrange
import logging
import requests


_LOGGER = logging.getLogger(__name__)


@dataclass
class WmataAPIData:
    """Class to hold api data"""
    # TODO: modify to update when new data comes in on train distances

    controller_name: str


class DeviceType(StrEnum):
    """Device types."""

    TEMP_SENSOR = "temp_sensor"
    DOOR_SENSOR = "door_sensor"
    OTHER = "other"


DEVICES = [
    {"id": 1, "type": DeviceType.TEMP_SENSOR},
    {"id": 2, "type": DeviceType.TEMP_SENSOR},
    {"id": 3, "type": DeviceType.TEMP_SENSOR},
    {"id": 4, "type": DeviceType.TEMP_SENSOR},
    {"id": 1, "type": DeviceType.DOOR_SENSOR},
    {"id": 2, "type": DeviceType.DOOR_SENSOR},
    {"id": 3, "type": DeviceType.DOOR_SENSOR},
    {"id": 4, "type": DeviceType.DOOR_SENSOR},
]


@dataclass
class Device:
    """API device."""

    device_id: int
    device_unique_id: str
    device_type: DeviceType
    name: str
    state: int | bool


class WmataCoordinator(DataUpdateCoordinator):
    """My coordinator"""

    data: WmataAPIData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator"""

        # Set variables from values entered in config flow setup
        self.api_key = config_entry.data[CONF_API_KEY]

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

        # initialize your api here
        self.api = WmataAPI(api_key=self.api_key)
        self.next_buses = []
        self.next_trains = []
        self.station = str

    async def async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """

        # TODO: add API call here to get station info

        try:
            if not self.api.connected:
                await self.hass.async_add_executor_job(self.api.validate_api_key)

            devices = await self.hass.async_add_executor_job(self.api.get_devices)

        except APIAuthError as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err

        except Exception as err:
            # this will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        # what is returned here is stored in self.data by the DataUpdateCoordinator
        return WmataAPIData()

    async def get_next_buses_at_stop(stop_code: str) -> list:
        output = requests.get(
            headers=HEADERS,
            url="%s/NextBusService.svc/json/jPredictions?StopID=%s" % (
                URL, stop_code)
        )

        bus_predictions = [bus for bus in output.json()["Predictions"]]

        print(bus_predictions)

        for bus in bus_predictions:
            print(bus["RouteID"])
            print(bus["DirectionText"])
            print(bus["Minutes"])
            print()

        return bus_predictions

    async def get_next_trains_at_station(station_code: str) -> list:
        output = requests.get(
            headers=HEADERS,
            url="%s/StationPrediction.svc/json/GetPrediction/%s" % (
                URL, station_code)
        )

        train_predictions = [train["Destination"]
                             for train in output.json()["Trains"]]

        print(train_predictions)

        for train in train_predictions:
            print(train["Destination"])
            print(train["Line"])
            print(train["LocationName"])
            print(train["Min"])
            print()

        return train_predictions

    def get_device_by_id(self, device_type: DeviceType, device_id: int) -> Device | None:
        """Return device by device id."""
        # called by the binary sensors and sensors to get their updated data from self.data
        try:
            return [device for device in self.data.devices if device.device_type == device_type and device.device_id == device_id][0]

        except IndexError:
            return None


class WmataAPI:
    def __init__(self, api_key):
        self.api_key: str = api_key
        self.connected: bool = False

    def validate_api_key(self) -> bool:
        output = requests.get(
            headers={"api_key": self.api_key}, url="https://api.wmata.com/Misc/Validate")

        if output.status_code == 200:
            self.connected = True
            return True
        raise APIAuthError("Invalid API key")

    def get_devices(self) -> list[Device]:
        """Get devices on api."""
        return [
            Device(
                device_id=device.get("id"),
                device_unique_id=self.get_device_unique_id(
                    device.get("id"), device.get("type")
                ),
                device_type=device.get("type"),
                name=self.get_device_name(
                    device.get("id"), device.get("type")),
                state=self.get_device_value(
                    device.get("id"), device.get("type")),
            )
            for device in DEVICES
        ]

    def get_device_unique_id(self, device_id: str, device_type: DeviceType) -> str:
        """Return a unique device id."""
        if device_type == DeviceType.DOOR_SENSOR:
            return f"{self.controller_name}_D{device_id}"
        if device_type == DeviceType.TEMP_SENSOR:
            return f"{self.controller_name}_T{device_id}"
        return f"{self.controller_name}_Z{device_id}"

    def get_device_name(self, device_id: str, device_type: DeviceType) -> str:
        """Return the device name."""
        if device_type == DeviceType.DOOR_SENSOR:
            return f"DoorSensor{device_id}"
        if device_type == DeviceType.TEMP_SENSOR:
            return f"TempSensor{device_id}"
        return f"OtherSensor{device_id}"

    def get_device_value(self, device_id: str, device_type: DeviceType) -> int | bool:
        """Get device random value."""
        if device_type == DeviceType.DOOR_SENSOR:
            return choice([True, False])
        if device_type == DeviceType.TEMP_SENSOR:
            return randrange(15, 28)
        return randrange(1, 10)


class APIAuthError(Exception):
    """Exception class for auth error."""


class APIConnectionError(Exception):
    """Exception class for connection error."""


# TODO: https://developer.wmata.com/api-details#api=54763629281d83086473f231&operation=5476362a281d830c946a3d6c
# get bus schedule at stop
