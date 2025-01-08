from .const import HEADERS, URL
from dataclasses import dataclass
from enum import StrEnum
from random import choice, randrange
import logging
import requests

_LOGGER = logging.getLogger(__name__)


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

class WmataAPI:
    def __init__(self, api_key):
        self.api_key: str = api_key
        self.connected: bool = False
    
    def validate_api_key(self) -> bool:
        output = requests.get(headers={"api_key": self.api_key}, url="https://api.wmata.com/Misc/Validate")
        
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
                name=self.get_device_name(device.get("id"), device.get("type")),
                state=self.get_device_value(device.get("id"), device.get("type")),
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


def get_next_buses_at_stop(stop_code: str):
    output = requests.get(
        headers=HEADERS, 
        url="%s/NextBusService.svc/json/jPredictions?StopID=%s" % (URL, stop_code)
    )
    
    bus_predictions = [bus for bus in output.json()["Predictions"]]
    
    print(bus_predictions)
    
    for bus in bus_predictions:
        print(bus["RouteID"])
        print(bus["DirectionText"])
        print(bus["Minutes"])
        print()
    
    return bus_predictions


def get_next_trains_at_station(station_code: str):
    output = requests.get(
        headers=HEADERS,
        url="%s/StationPrediction.svc/json/GetPrediction/%s" % (URL, station_code)
    )
    
    train_predictions = [train["Destination"] for train in output.json()["Trains"]]
    
    print(train_predictions)
    
    for train in train_predictions:
        print(train["Destination"])
        print(train["Line"])
        print(train["LocationName"])
        print(train["Min"])
        print()
        
    return train_predictions
