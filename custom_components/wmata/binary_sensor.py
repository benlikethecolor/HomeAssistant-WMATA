"""Optional, easy-to-use arrival threshold for each station or stop."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DUE_SOON, DEFAULT_DUE_SOON
from .sensor import WmataBoardSensor


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data["service_type"] in ("train", "bus"):
        async_add_entities([WmataDueSoonSensor(entry.runtime_data, entry)])


class WmataDueSoonSensor(CoordinatorEntity, BinarySensorEntity):
    """Turn on when a numeric prediction is within the configured threshold."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:clock-fast"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        board = WmataBoardSensor(coordinator)
        self._attr_unique_id = board.unique_id + "_due_soon"
        self._attr_device_info = board.device_info
        self._attr_name = (
            "Train due soon" if coordinator.service_type == "train" else "Bus due soon"
        )
        self.threshold = entry.options.get(CONF_DUE_SOON, DEFAULT_DUE_SOON)

    @property
    def is_on(self):
        arrivals = self.coordinator.data.arrivals if self.coordinator.data else []
        return any(
            a["minutes"] is not None and a["minutes"] <= self.threshold
            for a in arrivals
        )

    @property
    def extra_state_attributes(self):
        return {"threshold_minutes": self.threshold}
