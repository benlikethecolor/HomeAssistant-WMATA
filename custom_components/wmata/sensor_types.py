from .const import LINE_NAME_MAP
from .coordinator import WmataCoordinator
from collections.abc import Callable
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import UnitOfTime
from typing import Any


@dataclass
class WmataSensorRequiredKeysMixin:
    value: Callable[[WmataCoordinator], Any]
    attributes: Callable[[WmataCoordinator], Any]


@dataclass
class WmataSensorEntityDescription(SensorEntityDescription, WmataSensorRequiredKeysMixin):
    """A class that describes sensor entities."""


# tuple of all sensors that will then be each called in async_setup_entry
# might be able to refine this to only do the five types, and then have a loop to create the 6 sensors for each type but this works for now
# types:
# minutes: minutes until train arrives
# route: route name
# direction: direction of the bus
# vehicle: bus identifier, disabled by default
# trip: trip identifier, disabled by default
BUS_SENSOR_TYPES: tuple[WmataSensorEntityDescription, ...] = (
    WmataSensorEntityDescription(
        key="bus_1",
        name="Bus 1",
        icon="mdi:bus",
        value=lambda coord: coord.data.next_buses[0]["Minutes"] if len(
            coord.data.next_buses) > 0 else 0,
        attributes=lambda coord: {
            "Route": coord.data.next_buses[0]["RouteID"],
            "Direction": coord.data.next_buses[0]["DirectionText"],
            "Vehicle": coord.data.next_buses[0]["VehicleID"],
            "Trip": coord.data.next_buses[0]["TripID"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="bus_2",
        name="Bus 2",
        icon="mdi:bus",
        value=lambda coord: coord.data.next_buses[1]["Minutes"] if len(
            coord.data.next_buses) > 1 else 0,
        attributes=lambda coord: {
            "Route": coord.data.next_buses[1]["RouteID"],
            "Direction": coord.data.next_buses[1]["DirectionText"],
            "Vehicle": coord.data.next_buses[1]["VehicleID"],
            "Trip": coord.data.next_buses[1]["TripID"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="bus_3",
        name="Bus 3",
        icon="mdi:bus",
        value=lambda coord: coord.data.next_buses[2]["Minutes"] if len(
            coord.data.next_buses) > 2 else 0,
        attributes=lambda coord: {
            "Route": coord.data.next_buses[2]["RouteID"],
            "Direction": coord.data.next_buses[2]["DirectionText"],
            "Vehicle": coord.data.next_buses[2]["VehicleID"],
            "Trip": coord.data.next_buses[2]["TripID"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="bus_4",
        name="Bus 4",
        icon="mdi:bus",
        value=lambda coord: coord.data.next_buses[3]["Minutes"] if len(
            coord.data.next_buses) > 3 else 0,
        attributes=lambda coord: {
            "Route": coord.data.next_buses[3]["RouteID"],
            "Direction": coord.data.next_buses[3]["DirectionText"],
            "Vehicle": coord.data.next_buses[3]["VehicleID"],
            "Trip": coord.data.next_buses[3]["TripID"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="bus_5",
        name="Bus 5",
        icon="mdi:bus",
        value=lambda coord: coord.data.next_buses[4]["Minutes"] if len(
            coord.data.next_buses) > 4 else 0,
        attributes=lambda coord: {
            "Route": coord.data.next_buses[4]["RouteID"],
            "Direction": coord.data.next_buses[4]["DirectionText"],
            "Vehicle": coord.data.next_buses[4]["VehicleID"],
            "Trip": coord.data.next_buses[4]["TripID"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="bus_6",
        name="Bus 6",
        icon="mdi:bus",
        value=lambda coord: coord.data.next_buses[5]["Minutes"] if len(
            coord.data.next_buses) > 5 else 0,
        attributes=lambda coord: {
            "Route": coord.data.next_buses[5]["RouteID"],
            "Direction": coord.data.next_buses[5]["DirectionText"],
            "Vehicle": coord.data.next_buses[5]["VehicleID"],
            "Trip": coord.data.next_buses[5]["TripID"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
)

# tuple of all sensors that will then be each called in async_setup_entry
# might be able to refine this to only do the five types, and then have a loop to create the 6 sensors for each type but this works for now
# types:
# time: minutes until train arrives
# line: color of the line
# destination: destination of the train (which direction it's going in)
# car: number of train cars on the train
# group: group of the train, used for what track a train is on at multiple track stations. not useful for most stations, so including it disabled by default
TRAIN_SENSOR_TYPES: tuple[WmataSensorEntityDescription, ...] = (
    WmataSensorEntityDescription(
        key="train_1",
        name="Train 1",
        icon="mdi:subway",
        value=lambda coord: coord.data.next_trains[0]["Min"] if len(
            coord.data.next_trains) > 0 and coord.data.next_trains[0]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {
            "Line": coord.data.next_trains[0]["Line"],
            "Destination": coord.data.next_trains[0]["DestinationName"],
            "Car": coord.data.next_trains[0]["Car"],
            "Group": coord.data.next_trains[0]["Group"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="train_2",
        name="Train 2",
        icon="mdi:subway",
        value=lambda coord: coord.data.next_trains[1]["Min"] if len(
            coord.data.next_trains) > 1 and coord.data.next_trains[1]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {
            "Line": coord.data.next_trains[1]["Line"],
            "Destination": coord.data.next_trains[1]["DestinationName"],
            "Car": coord.data.next_trains[1]["Car"],
            "Group": coord.data.next_trains[1]["Group"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="train_3",
        name="Train 3",
        icon="mdi:subway",
        value=lambda coord: coord.data.next_trains[2]["Min"] if len(
            coord.data.next_trains) > 2 and coord.data.next_trains[2]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {
            "Line": coord.data.next_trains[2]["Line"],
            "Destination": coord.data.next_trains[2]["DestinationName"],
            "Car": coord.data.next_trains[2]["Car"],
            "Group": coord.data.next_trains[2]["Group"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="train_4",
        name="Train 4",
        icon="mdi:subway",
        value=lambda coord: coord.data.next_trains[3]["Min"] if len(
            coord.data.next_trains) > 3 and coord.data.next_trains[3]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {
            "Line": coord.data.next_trains[3]["Line"],
            "Destination": coord.data.next_trains[3]["DestinationName"],
            "Car": coord.data.next_trains[3]["Car"],
            "Group": coord.data.next_trains[3]["Group"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="train_5",
        name="Train 5",
        icon="mdi:subway",
        value=lambda coord: coord.data.next_trains[4]["Min"] if len(
            coord.data.next_trains) > 4 and coord.data.next_trains[4]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {
            "Line": coord.data.next_trains[4]["Line"],
            "Destination": coord.data.next_trains[4]["DestinationName"],
            "Car": coord.data.next_trains[4]["Car"],
            "Group": coord.data.next_trains[4]["Group"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
    WmataSensorEntityDescription(
        key="train_6",
        name="Train 6",
        icon="mdi:subway",
        value=lambda coord: coord.data.next_trains[5]["Min"] if len(
            coord.data.next_trains) > 5 and coord.data.next_trains[5]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {
            "Line": coord.data.next_trains[5]["Line"],
            "Destination": coord.data.next_trains[5]["DestinationName"],
            "Car": coord.data.next_trains[5]["Car"],
            "Group": coord.data.next_trains[5]["Group"],
        },
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class="duration",
        state_class="measurement",
    ),
)
