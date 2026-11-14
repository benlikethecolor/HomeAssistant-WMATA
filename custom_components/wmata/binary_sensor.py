"""On/off signals for automations: due soon, service alerts and last trains."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DUE_SOON, DEFAULT_DUE_SOON, DOMAIN
from .sensor import WmataBoardSensor


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    service = entry.data["service_type"]
    if service == "commute":
        async_add_entities([WmataCommuteAlertSensor(coordinator)])
    elif service in ("train", "bus"):
        sensors = [
            WmataDueSoonSensor(coordinator, entry),
            WmataAlertSensor(coordinator),
        ]
        if service == "train":
            sensors += [
                WmataLastTrainSensor(coordinator),
                WmataElevatorSensor(coordinator),
            ]
        async_add_entities(sensors)


class WmataStationBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Shares the station or stop's device and polling."""

    _attr_has_entity_name = True
    key = ""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        board = WmataBoardSensor(coordinator)
        self._attr_unique_id = f"{board.unique_id}_{self.key}"
        self._attr_device_info = board.device_info


class WmataDueSoonSensor(WmataStationBinarySensor):
    """Turn on when a numeric prediction is within the configured threshold."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:clock-fast"
    key = "due_soon"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
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


class WmataAlertSensor(WmataStationBinarySensor):
    """On while WMATA reports a delay or alert on a line or route that stops here."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Service alert"
    _unrecorded_attributes = frozenset({"alerts"})
    key = "alert"

    @property
    def is_on(self):
        return bool(self.coordinator.alerts_for())

    @property
    def extra_state_attributes(self):
        alerts = self.coordinator.alerts_for()
        return {
            "alerts": alerts,
            # Handy in a notification without a template loop.
            "summary": " ".join(alert["description"] for alert in alerts) or None,
        }


class WmataLastTrainSensor(WmataStationBinarySensor):
    """On while one of the trains on the board is the last of the night."""

    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:weather-night"
    _attr_name = "Last train"
    _unrecorded_attributes = frozenset({"trains"})
    key = "last_train"

    @property
    def last_trains(self):
        arrivals = self.coordinator.data.arrivals if self.coordinator.data else []
        return [a for a in arrivals if a.get("last_train")]

    @property
    def is_on(self):
        return bool(self.last_trains)

    @property
    def extra_state_attributes(self):
        return {
            "trains": [
                {
                    "line": a["line"],
                    "line_name": a["line_name"],
                    "destination": a["destination"],
                    "direction": a["direction"],
                    "minutes": a["minutes"],
                }
                for a in self.last_trains
            ]
        }


class WmataElevatorSensor(WmataStationBinarySensor):
    """On while an elevator at this station is out of service."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:elevator-passenger-off-outline"
    _attr_name = "Elevator outage"
    _unrecorded_attributes = frozenset({"elevators", "escalators"})
    key = "elevator_outage"

    def _units(self, kind):
        outages = self.coordinator.data.outages if self.coordinator.data else []
        return [unit for unit in outages if unit["type"] == kind]

    @property
    def is_on(self):
        return bool(self._units("elevator"))

    @property
    def extra_state_attributes(self):
        # Escalators break often enough that they don't drive the state.
        return {
            "elevators": self._units("elevator"),
            "escalators": self._units("escalator"),
        }


class WmataCommuteAlertSensor(CoordinatorEntity, BinarySensorEntity):
    """On while an alert affects a line on the commute, in either direction."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Service alert"
    _unrecorded_attributes = frozenset({"alerts"})

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"wmata_commute_{coordinator.home.lower()}_{coordinator.work.lower()}_alert"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"commute_{coordinator.home}_{coordinator.work}")},
            name=f"WMATA {coordinator.commute_name}",
            manufacturer="WMATA",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def alerts(self):
        trips = (self.coordinator.data or {}).get("trips", {})
        found = {}
        for trip in trips.values():
            for alert in (trip or {}).get("alerts", []):
                found.setdefault(alert["id"] or alert["description"], alert)
        return list(found.values())

    @property
    def is_on(self):
        return bool(self.alerts)

    @property
    def extra_state_attributes(self):
        alerts = self.alerts
        return {
            "alerts": alerts,
            "summary": " ".join(alert["description"] for alert in alerts) or None,
        }
