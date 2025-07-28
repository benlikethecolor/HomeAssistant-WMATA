import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WmataCoordinator
from .sensor_types import (
    BUS_SENSOR_TYPES,
    TRAIN_SENSOR_TYPES,
    WmataSensorEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WMATA sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id].coordinator

    # Initialize the coordinator to fetch the bus stop/station name
    await coordinator.async_initialize()

    sensors = []

    if coordinator.service_type == "bus":
        for description in BUS_SENSOR_TYPES:
            sensors.append(WmataSensor(coordinator, description))
    elif coordinator.service_type == "train":
        for description in TRAIN_SENSOR_TYPES:
            sensors.append(WmataSensor(coordinator, description))

    async_add_entities(sensors, False)
    hass.data[DOMAIN][entry.entry_id].entities = sensors


class WmataSensor(CoordinatorEntity[WmataCoordinator], SensorEntity):
    """Representation of a WMATA sensor."""

    _attr_has_entity_name = True
    entity_description: WmataSensorEntityDescription

    def __init__(self, coordinator: WmataCoordinator, description: WmataSensorEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description

        if coordinator.service_type == "bus":
            location = coordinator.bus_stop.lower()
            location_name = coordinator.bus_stop_name
        elif coordinator.service_type == "train":
            location = coordinator.station.lower()
            location_name = coordinator.station_name

        self._attr_name = f"{location_name} {description.name}"
        self._attr_unique_id = f"wmata_{location}_{description.key}"
        self.entity_id = f"sensor.wmata_{location}_{description.key}"

        _LOGGER.debug(
            "Initializing WmataSensor: location=%s, description.key=%s, unique_id=%s",
            location,
            description.key,
            self._attr_unique_id,
        )

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.entity_description.value(self.coordinator)
        self._attr_extra_state_attributes = self.entity_description.attributes(self.coordinator)
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self.entity_description.value(self.coordinator)

    @property
    def native_unit_of_measurement(self):
        return UnitOfTime.MINUTES if isinstance(self.native_value, (int, float)) else None

    @property
    def device_class(self):
        return SensorDeviceClass.DURATION if isinstance(self.native_value, (int, float)) else None

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT if isinstance(self.native_value, (int, float)) else None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.native_value is not None
