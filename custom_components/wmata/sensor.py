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


@dataclass
class WmataSensorRequiredKeysMixin:
    value: Callable[[WmataCoordinator], Any]
    attributes: Callable[[WmataCoordinator], Any]


@dataclass
class WmataSensorEntityDescription(SensorEntityDescription, WmataSensorRequiredKeysMixin):
    """A class that describes sensor entities."""


SENSOR_TYPES: tuple[WmataSensorEntityDescription, ...] = (
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_1_time" % (coord.station),
        name=lambda coord: "%s Train 1 Time" % (coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[0]["Min"] if coord.data.next_trains[0]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_1_line" % (coord.station),
        name=lambda coord: "%s Train 1 Line" % (coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[0]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_1_destination" % (coord.station),
        name=lambda coord: "%s Train 1 Destination" % (coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[0]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_1_car" % (coord.station),
        name=lambda coord: "%s Train 1 Car" % (coord.station),
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[0]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_1_group" % (coord.station),
        name=lambda coord: "%s Train 1 Group" % (coord.station),
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[0]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_2_time" % (coord.station),
        name=lambda coord: "%s Train 2 Time" % (coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[1]["Min"] if coord.data.next_trains[1]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_2_line" % (coord.station),
        name=lambda coord: "%s Train 2 Line" % (coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[1]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_2_destination" % (coord.station),
        name=lambda coord: "%s Train 2 Destination" % (coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[1]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_2_car" % (coord.station),
        name=lambda coord: "%s Train 2 Car" % (coord.station),
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[1]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_2_group" % (coord.station),
        name=lambda coord: "%s Train 2 Group" % (coord.station),
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[1]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_3_time" % (coord.station),
        name=lambda coord: "%s Train 3 Time" % (coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[2]["Min"] if coord.data.next_trains[2]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_3_line" % (coord.station),
        name=lambda coord: "%s Train 3 Line" % (coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[2]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_3_destination" % (coord.station),
        name=lambda coord: "%s Train 3 Destination" % (coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[2]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_3_car" % (coord.station),
        name=lambda coord: "%s Train 3 Car" % (coord.station),
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[2]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_3_group" % (coord.station),
        name=lambda coord: "%s Train 3 Group" % (coord.station),
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[2]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_4_time" % (coord.station),
        name=lambda coord: "%s Train 4 Time" % (coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[3]["Min"] if coord.data.next_trains[3]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_4_line" % (coord.station),
        name=lambda coord: "%s Train 4 Line" % (coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[3]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_4_destination" % (coord.station),
        name=lambda coord: "%s Train 4 Destination" % (coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[3]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_4_car" % (coord.station),
        name=lambda coord: "%s Train 4 Car" % (coord.station),
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[3]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_4_group" % (coord.station),
        name=lambda coord: "%s Train 4 Group" % (coord.station),
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[3]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_5_time" % (coord.station),
        name=lambda coord: "%s Train 5 Time" % (coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[4]["Min"] if coord.data.next_trains[4]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_5_line" % (coord.station),
        name=lambda coord: "%s Train 5 Line" % (coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[4]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_5_destination" % (coord.station),
        name=lambda coord: "%s Train 5 Destination" % (coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[4]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_5_car" % (coord.station),
        name=lambda coord: "%s Train 5 Car" % (coord.station),
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[4]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_5_group" % (coord.station),
        name=lambda coord: "%s Train 5 Group" % (coord.station),
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[4]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_6_time" % (coord.station),
        name=lambda coord: "%s Train 6 Time" % (coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[5]["Min"] if coord.data.next_trains[5]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_6_line" % (coord.station),
        name=lambda coord: "%s Train 6 Line" % (coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[5]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_6_destination" % (coord.station),
        name=lambda coord: "%s Train 6 Destination" % (coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[5]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_6_car" % (coord.station),
        name=lambda coord: "%s Train 6 Car" % (coord.station),
        icon="mdi:train-car-passenger-door",
        value=lambda coord: coord.data.next_trains[5]["Car"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key=lambda coord: "wmata_%s_train_6_group" % (coord.station),
        name=lambda coord: "%s Train 6 Group" % (coord.station),
        icon="mdi:transit-transfer",
        value=lambda coord: coord.data.next_trains[5]["Group"],
        attributes=lambda coord: {},
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the WMATA sensor platform."""
    # runtime_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = hass.data[DOMAIN][entry.entry_id].coordinator

    sensors = []

    for description in SENSOR_TYPES:
        sensors.append(WmataSensor(coordinator, description))
    # for i in range(4):
    #     sensors.append(WmataSensor(coordinator, i))
    async_add_entities(sensors, False)


class WmataSensor(CoordinatorEntity[WmataCoordinator], SensorEntity):
    """Representation of a WMATA sensor."""
    _attr_has_entity_name = True
    entity_description = WmataSensorEntityDescription

    def __init__(self, coordinator: WmataCoordinator, description: WmataSensorEntityDescription) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        self.entity_description = description

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""

        self._attr_native_value = self.entity_description.value(
            self.coordinator)
        self._attr_extra_state_attributes = {}

        self.async_write_ha_state()

        self._attr_extra_state_attributes = self.entity_description.attributes(
            self.coordinator)

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.entity_description.value(self.coordinator) is not None
