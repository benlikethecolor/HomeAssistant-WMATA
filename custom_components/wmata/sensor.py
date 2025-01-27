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


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the WMATA sensor platform."""
    runtime_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = runtime_data.coordinator

    sensors = []
    for i in range(4):
        sensors.append(WmataSensor(coordinator, i))
    async_add_entities(sensors, False)


class WmataSensor(CoordinatorEntity[WmataCoordinator], SensorEntity):
    """Representation of a WMATA sensor."""

    def __init__(self, coordinator: WmataCoordinator, train_index: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"Train {train_index + 1}"
        self._attr_native_unit_of_measurement = "minutes"
        self.train_index = train_index
        self._attr_unique_id = f"{coordinator.unique_id}_train_{train_index + 1}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data and len(self.coordinator.data.next_trains) > self.train_index:
            next_train = self.coordinator.data.next_trains[self.train_index]["Min"]
            if next_train in ["BRD", "ARR"]:
                return 0
            try:
                return int(next_train)
            except ValueError:
                return None
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = {}
        if self.coordinator.data and len(self.coordinator.data.next_trains) > self.train_index:
            next_train = self.coordinator.data.next_trains[self.train_index]
            attributes["train_line"] = next_train.get("Line")
        return attributes


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
        attributes={},
    ),
    WmataSensorEntityDescription(
        key="train_1_line",
        name="Train 1 Line",
        icon="mdi:train",
        state_class=SensorStateClass.TOTAL,
        value=lambda coord: LINE_NAME_MAP[coord.data.next_trains[0]["Line"]],
        attributes={},
    ),
    WmataSensorEntityDescription(
        key="train_1_destination",
        name="Train 1 Destination",
        icon="mdi:location-enter",
        state_class=SensorStateClass.TOTAL,
        value=lambda coord: coord.data.next_trains[0]["Destination"],
        attributes={},
    ),
)
