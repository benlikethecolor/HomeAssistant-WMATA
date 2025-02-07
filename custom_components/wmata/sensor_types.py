from .const import LINE_NAME_MAP
from .coordinator import WmataCoordinator
from collections.abc import Callable
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription
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
# routeid: route name
# directiontext: direction of the bus
# vehicleid: bus identifier, disabled by default
# tripid: trip identifier, disabled by default
BUS_SENSOR_TYPES: tuple[WmataSensorEntityDescription, ...] = (
    WmataSensorEntityDescription(
        key="bus_1_time",
        name="Bus 1 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_buses[0]["Minutes"],
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
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
        key="train_1_time",
        name="Train 1 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[0]["Min"] if coord.data.next_trains[0]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="train_1_line",
        name="Train 1 Line",
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[0]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_1_destination",
        name="Train 1 Destination",
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[0]["DestinationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_1_car",
        name="Train 1 Car",
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[0]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_1_group",
        name="Train 1 Group",
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[0]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key="train_2_time",
        name="Train 2 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[1]["Min"] if coord.data.next_trains[1]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="train_2_line",
        name="Train 2 Line",
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[1]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_2_destination",
        name="Train 2 Destination",
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[1]["DestinationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_2_car",
        name="Train 2 Car",
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[1]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_2_group",
        name="Train 2 Group",
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[1]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key="train_3_time",
        name="Train 3 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[2]["Min"] if coord.data.next_trains[2]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="train_3_line",
        name="Train 3 Line",
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[2]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_3_destination",
        name="Train 3 Destination",
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[2]["DestinationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_3_car",
        name="Train 3 Car",
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[2]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_3_group",
        name="Train 3 Group",
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[2]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key="train_4_time",
        name="Train 4 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[3]["Min"] if coord.data.next_trains[3]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="train_4_line",
        name="Train 4 Line",
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[3]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_4_destination",
        name="Train 4 Destination",
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[3]["DestinationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_4_car",
        name="Train 4 Car",
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[3]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_4_group",
        name="Train 4 Group",
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[3]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key="train_5_time",
        name="Train 5 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[4]["Min"] if coord.data.next_trains[4]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="train_5_line",
        name="Train 5 Line",
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[4]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_5_destination",
        name="Train 5 Destination",
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[4]["DestinationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_5_car",
        name="Train 5 Car",
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[4]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_5_group",
        name="Train 5 Group",
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[4]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key="train_6_time",
        name="Train 6 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[5]["Min"] if coord.data.next_trains[5]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="train_6_line",
        name="Train 6 Line",
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[5]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_6_destination",
        name="Train 6 Destination",
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[5]["DestinationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_6_car",
        name="Train 6 Car",
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[5]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_6_group",
        name="Train 6 Group",
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[5]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
)

