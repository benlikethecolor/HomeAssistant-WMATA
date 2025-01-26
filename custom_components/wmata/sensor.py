from .const import DOMAIN
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the WMATA sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id].coordinator
    async_add_entities([WmataSensor(coordinator)])


class WmataSensor(CoordinatorEntity, SensorEntity):
    """Representation of a WMATA sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "WMATA Sensor"
        self._attr_native_unit_of_measurement = "minutes"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data and self.coordinator.data.next_trains:
            return self.coordinator.data.next_trains[0]["Min"]
        return None
