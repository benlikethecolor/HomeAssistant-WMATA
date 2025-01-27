from .const import DOMAIN
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the WMATA sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id].coordinator
    async_add_entities([WmataSensor(coordinator, i) for i in range(4)])


class WmataSensor(CoordinatorEntity, SensorEntity):
    """Representation of a WMATA sensor."""

    def __init__(self, coordinator, train_index):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"Train {train_index + 1}"
        self._attr_native_unit_of_measurement = "minutes"
        self.train_index = train_index

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data and len(self.coordinator.data.next_trains) > self.train_index:
            next_train = self.coordinator.data.next_trains[self.train_index]["Min"]
            if next_train in ["BRD", "ARR"]:
                return 0
            else:
                return next_train
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = {}
        if self.coordinator.data and len(self.coordinator.data.next_trains) > self.train_index:
            next_train = self.coordinator.data.next_trains[self.train_index]
            attributes["train_line"] = next_train["Line"]
        return attributes
