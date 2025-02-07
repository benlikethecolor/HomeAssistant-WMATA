import logging

from .const import DOMAIN, LINE_NAME_MAP
from .coordinator import WmataCoordinator
from collections.abc import Callable
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from typing import Any

_LOGGER = logging.getLogger(__name__)


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
# time: minutes until train arrives
# line: color of the line
# destination: destination of the train (which direction it's going in)
# car: number of train cars on the train
# group: group of the train, used for what track a train is on at multiple track stations. not useful for most stations, so including it disabled by default
SENSOR_TYPES: tuple[WmataSensorEntityDescription, ...] = (
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the WMATA sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id].coordinator

    sensors = []

    for description in SENSOR_TYPES:
        sensors.append(WmataSensor(coordinator, description))
    async_add_entities(sensors, False)


class WmataSensor(CoordinatorEntity[WmataCoordinator], SensorEntity):
    """Representation of a WMATA sensor."""
    _attr_has_entity_name = True
    entity_description = WmataSensorEntityDescription

    def __init__(self, coordinator: WmataCoordinator, description: WmataSensorEntityDescription) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        station = coordinator.station.lower()
        station_name = coordinator.station_name
        
        # _attr_name: name that appears in Home Assistant UI
        self._attr_name = f"{station_name} {description.name}"
        
        # _attr_unique_id: unique ID for the sensor, used to ensure only one instance of the sensor exists, not visible
        self._attr_unique_id = f"wmata_{station}_{description.key}"
        
        # entity_id: ID that appears in Home Assistant UI
        self.entity_id = f"sensor.wmata_{station}_{description.key}"
        
        self.entity_description = description

        # Log the values for debugging
        _LOGGER.debug("Initializing WmataSensor: station=%s, description.key=%s, unique_id=%s",
                      station, description.key, self._attr_unique_id)

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""

        self._attr_native_value = self.entity_description.value(
            self.coordinator
        )
        self._attr_extra_state_attributes = self.entity_description.attributes(
            self.coordinator
        )

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.entity_description.value(self.coordinator) is not None
