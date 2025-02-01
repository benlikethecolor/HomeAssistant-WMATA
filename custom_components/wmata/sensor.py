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

# TODO: add a sensor for the number of cars coord.data.next_trains[0]["Car"]
# TODO: add a sensor for group (describes which track the train is on) coord.data.next_trains[0]["Group"]
# TODO: add the group sensor as inactive by default by adding the parameter entity_registry_enabled_default=False

SENSOR_TYPES: tuple[WmataSensorEntityDescription, ...] = (
    WmataSensorEntityDescription(
        key="wmata_%s_train_1_time" % (lambda coord: coord.station),
        name="%s Train 1 Time" % (lambda coord: coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[0]["Min"] if coord.data.next_trains[0]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_1_line" % (lambda coord: coord.station),
        name="%s Train 1 Line" % (lambda coord: coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[0]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_1_destination" % (lambda coord: coord.station),
        name="%s Train 1 Destination" % (lambda coord: coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[0]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_2_time" % (lambda coord: coord.station),
        name="%s Train 2 Time" % (lambda coord: coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[1]["Min"] if coord.data.next_trains[1]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_2_line" % (lambda coord: coord.station),
        name="%s Train 2 Line" % (lambda coord: coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[1]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_2_destination" % (lambda coord: coord.station),
        name="%s Train 2 Destination" % (lambda coord: coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[1]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_3_time" % (lambda coord: coord.station),
        name="%s Train 3 Time" % (lambda coord: coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[2]["Min"] if coord.data.next_trains[2]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_3_line" % (lambda coord: coord.station),
        name="%s Train 3 Line" % (lambda coord: coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[2]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_3_destination" % (lambda coord: coord.station),
        name="%s Train 3 Destination" % (lambda coord: coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[2]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_4_time" % (lambda coord: coord.station),
        name="%s Train 4 Time" % (lambda coord: coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[3]["Min"] if coord.data.next_trains[3]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_4_line" % (lambda coord: coord.station),
        name="%s Train 4 Line" % (lambda coord: coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[3]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_4_destination" % (lambda coord: coord.station),
        name="%s Train 4 Destination" % (lambda coord: coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[3]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_5_time" % (lambda coord: coord.station),
        name="%s Train 5 Time" % (lambda coord: coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[4]["Min"] if coord.data.next_trains[4]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_5_line" % (lambda coord: coord.station),
        name="%s Train 5 Line" % (lambda coord: coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[4]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_5_destination" % (lambda coord: coord.station),
        name="%s Train 5 Destination" % (lambda coord: coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[4]["LocationName"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_6_time" % (lambda coord: coord.station),
        name="%s Train 6 Time" % (lambda coord: coord.station),
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[5]["Min"] if coord.data.next_trains[5]["Min"] not in [
            None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
        native_unit_of_measurement="minutes",
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_6_line" % (lambda coord: coord.station),
        name="%s Train 6 Line" % (lambda coord: coord.station),
        icon="mdi:train",
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[5]["Line"]],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="wmata_%s_train_6_destination" % (lambda coord: coord.station),
        name="%s Train 6 Destination" % (lambda coord: coord.station),
        icon="mdi:location-enter",
        value=lambda coord: coord.data.next_trains[5]["LocationName"],
        attributes=lambda coord: {},
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
