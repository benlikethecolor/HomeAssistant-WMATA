from .coordinator import WmataCoordinator
from collections.abc import Callable
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription
from typing import Any
from homeassistant.const import STATE_UNKNOWN


@dataclass
class WmataSensorRequiredKeysMixin:
    value: Callable[[WmataCoordinator], Any]
    attributes: Callable[[WmataCoordinator], dict]


@dataclass
class WmataSensorEntityDescription(SensorEntityDescription, WmataSensorRequiredKeysMixin):
    """A class that describes WMATA sensor entities."""


def make_bus_sensor(i: int) -> WmataSensorEntityDescription:
    return WmataSensorEntityDescription(
        key=f"bus_{i+1}",
        name=f"Bus {i+1}",
        icon="mdi:bus",
        value=lambda coord, i=i: (
            coord.data.next_buses[i]["Minutes"]
            if len(coord.data.next_buses) > i else STATE_UNKNOWN
        ),
        attributes=lambda coord, i=i: (
            {
                "Route": coord.data.next_buses[i]["RouteID"],
                "Direction": coord.data.next_buses[i]["DirectionText"],
                "Vehicle": coord.data.next_buses[i]["VehicleID"],
                "Trip": coord.data.next_buses[i]["TripID"],
            } if len(coord.data.next_buses) > i else {}
        ),
    )


def make_train_sensor(i: int) -> WmataSensorEntityDescription:
    return WmataSensorEntityDescription(
        key=f"train_{i+1}",
        name=f"Train {i+1}",
        icon="mdi:subway",
        value=lambda coord, i=i: (
            coord.data.next_trains[i]["Min"]
            if len(coord.data.next_trains) > i and coord.data.next_trains[i]["Min"] not in [None, "ARR", "BRD"]
            else STATE_UNKNOWN
        ),
        attributes=lambda coord, i=i: (
            {
                "Line": coord.data.next_trains[i]["Line"],
                "Destination": coord.data.next_trains[i]["DestinationName"],
                "Car": coord.data.next_trains[i]["Car"],
                "Group": coord.data.next_trains[i]["Group"],
            } if len(coord.data.next_trains) > i else {}
        ),
    )


BUS_SENSOR_TYPES: tuple[WmataSensorEntityDescription, ...] = tuple(
    make_bus_sensor(i) for i in range(6)
)

TRAIN_SENSOR_TYPES: tuple[WmataSensorEntityDescription, ...] = tuple(
    make_train_sensor(i) for i in range(6)
)

