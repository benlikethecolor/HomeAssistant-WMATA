from .const import DOMAIN, LINE_NAME_MAP
from .coordinator import WmataCoordinator
from collections.abc import Callable
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from typing import Any

import logging

_LOGGER = logging.getLogger(__name__)

# class WmataSensor(CoordinatorEntity[WmataCoordinator], SensorEntity):
#     """Representation of a WMATA sensor."""

#     def __init__(self, coordinator: WmataCoordinator, train_index: int) -> None:
#         """Initialize the sensor."""
#         super().__init__(coordinator)
#         self._attr_name = f"Train {train_index + 1}"
#         self._attr_native_unit_of_measurement = "minutes"
#         self.train_index = train_index
#         self._attr_unique_id = f"{coordinator.unique_id}_train_{train_index + 1}"

#     @property
#     def native_value(self):
#         """Return the state of the sensor."""
#         if self.coordinator.data and len(self.coordinator.data.next_trains) > self.train_index:
#             next_train = self.coordinator.data.next_trains[self.train_index]["Min"]
#             if next_train in ["BRD", "ARR"]:
#                 return 0
#             try:
#                 return int(next_train)
#             except ValueError:
#                 return None
#         return None

#     @property
#     def extra_state_attributes(self):
#         """Return the state attributes."""
#         attributes = {}
#         if self.coordinator.data and len(self.coordinator.data.next_trains) > self.train_index:
#             next_train = self.coordinator.data.next_trains[self.train_index]
#             attributes["train_line"] = next_train.get("Line")
#             attributes["destination"] = next_train.get("Destination")
#         return attributes


@dataclass
class WmataSensorRequiredKeysMixin:
    value: Callable[[WmataCoordinator], Any]
    attributes: Callable[[WmataCoordinator], Any]


@dataclass
class WmataSensorEntityDescription(SensorEntityDescription, WmataSensorRequiredKeysMixin):
    """A class that describes sensor entities."""


SENSOR_TYPES: tuple[WmataSensorEntityDescription, ...] = (
    WmataSensorEntityDescription(
        key="train_1_time",
        name="Train 1 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[0]["Min"] if coord.data.next_trains[0]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
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
        value=lambda coord: coord.data.next_trains[0]["Destination"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_2_time",
        name="Train 2 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[1]["Min"] if coord.data.next_trains[1]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
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
        value=lambda coord: coord.data.next_trains[1]["Destination"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_3_time",
        name="Train 3 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[2]["Min"] if coord.data.next_trains[2]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
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
        value=lambda coord: coord.data.next_trains[2]["Destination"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_4_time",
        name="Train 4 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[3]["Min"] if coord.data.next_trains[3]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
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
        value=lambda coord: coord.data.next_trains[3]["Destination"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_5_time",
        name="Train 5 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[4]["Min"] if coord.data.next_trains[4]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
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
        value=lambda coord: coord.data.next_trains[4]["Destination"],
        attributes=lambda coord: {},
    ),
    WmataSensorEntityDescription(
        key="train_6_time",
        name="Train 6 Time",
        icon="mdi:timer-outline",
        value=lambda coord: coord.data.next_trains[5]["Min"] if coord.data.next_trains[5]["Min"] not in [None, "ARR", "BRD"] else 0,
        attributes=lambda coord: {},
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
        value=lambda coord: coord.data.next_trains[5]["Destination"],
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
        # self._attr_name = description.name
    
    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        
        self._attr_native_value = self.entity_description.value(self.coordinator)
        self._attr_extra_state_attributes = {}
        
        self.async_write_ha_state()
        self._attr_extra_state_attributes = self.entity_description.attributes(self.coordinator)
        self.async_write_ha_state()
    
    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.entity_description.value(self.coordinator) is not None
