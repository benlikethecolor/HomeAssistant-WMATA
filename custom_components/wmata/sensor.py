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


# async def async_setup_entry(hass, config_entry, async_add_entities):
#     """Set up the WMATA sensor platform."""
#     coordinator = hass.data[DOMAIN][config_entry.entry_id].coordinator
#     async_add_entities([WmataSensor(coordinator, i) for i in range(4)])


# class WmataSensor(CoordinatorEntity, SensorEntity):
#     """Representation of a WMATA sensor."""

#     def __init__(self, coordinator, train_index):
#         """Initialize the sensor."""
#         super().__init__(coordinator)
#         self._attr_name = f"Train {train_index + 1}"
#         self._attr_native_unit_of_measurement = "minutes"
#         self.train_index = train_index

#     @property
#     def native_value(self):
#         """Return the state of the sensor."""
#         if self.coordinator.data and len(self.coordinator.data.next_trains) > self.train_index:
#             next_train = self.coordinator.data.next_trains[self.train_index]["Min"]
#             if next_train in ["BRD", "ARR"]:
#                 return 0
#             else:
#                 return next_train
#         return None

#     @property
#     def extra_state_attributes(self):
#         """Return the state attributes."""
#         attributes = {}
#         if self.coordinator.data and len(self.coordinator.data.next_trains) > self.train_index:
#             next_train = self.coordinator.data.next_trains[self.train_index]
#             attributes["line"] = LINE_NAME_MAP[next_train["Line"]]
#             attributes["destination"] = next_train["Destination"]
#             attributes["location"] = next_train["LocationName"]
#             attributes["car"] = next_train["Car"]
#             attributes["group"] = next_train["Group"]
            
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
        state_class=SensorStateClass.TOTAL,
        value=lambda coord: coord.data.next_trains[0]["Min"] if coord.data.next_trains[0]["Min"] not in [None, "ARR", "BRD"] else 0,
    ),
    WmataSensorEntityDescription(
        key="train_1_line",
        name="Train 1 Line",
        icon="mdi:train",
        state_class=SensorStateClass.TOTAL,
        value=lambda coord: coord.data.next_trains[0]["Line"],
    ),
    WmataSensorEntityDescription(
        key="train_1_destination",
        name="Train 1 Destination",
        icon="mdi:location-enter",
        state_class=SensorStateClass.TOTAL,
        vvalue=lambda coord: coord.data.next_trains[0]["Destination"],
    ),
)


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []

    for description in SENSOR_TYPES:
        sensors.append(WmataSensor(coordinator, description))
    async_add_entities(sensors, False)


class WmataSensor(
    CoordinatorEntity[WmataCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    entity_description: WmataSensorEntityDescription

    def __init__(
            self,
            coordinator: WmataCoordinator,
            description: WmataSensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_device_info = 'test device info'
        self._attr_unique_id = f"{coordinator.unique_id}_{DOMAIN}_{description.key}"
        self.entity_description = description

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.entity_description.value(self.coordinator)
        self.async_write_ha_state()
        self._attr_extra_state_attributes = self.entity_description.attributes(self.coordinator)
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.entity_description.value(self.coordinator) is not None