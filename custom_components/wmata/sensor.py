"""One station board and optional saved journeys, without numbered slots."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_JOURNEYS, DOMAIN
from .coordinator import WmataCoordinator
from .predictions import filter_arrivals

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Reconcile only this entry's entities, including removed saved journeys."""
    coordinator = entry.runtime_data
    if entry.data["service_type"] == "map":
        async_add_entities([NetworkMapSensor(coordinator)])
        return
    sensors = [WmataBoardSensor(coordinator)]
    sensors.extend(
        WmataJourneySensor(coordinator, journey)
        for journey in entry.options.get(CONF_JOURNEYS, [])
    )
    active = {sensor.unique_id for sensor in sensors}
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            entity.platform == DOMAIN
            and entity.domain == "sensor"
            and entity.unique_id not in active
        ):
            registry.async_remove(entity.entity_id)
    async_add_entities(sensors)


class WmataBoardSensor(CoordinatorEntity[WmataCoordinator], SensorEntity):
    """Primary value is the next ETA; arrivals hold the entire live board."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = SensorDeviceClass.DURATION
    _unrecorded_attributes = frozenset({"arrivals", "updated_at", "next_arrival"})

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"wmata_{coordinator.service_type}_{coordinator.location.lower()}_board"
        )
        self.entity_id = f"sensor.wmata_{coordinator.location.lower()}_arrivals"
        self._attr_name = "Arrivals"
        self._attr_icon = (
            "mdi:subway" if coordinator.service_type == "train" else "mdi:bus"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, f"{coordinator.service_type}_{coordinator.location}")
            },
            name=f"WMATA {coordinator.location_name}",
            manufacturer="WMATA",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def arrivals(self) -> list[dict]:
        return self.coordinator.data.arrivals if self.coordinator.data else []

    @property
    def native_value(self) -> int | None:
        return next(
            (a["minutes"] for a in self.arrivals if a["minutes"] is not None), None
        )

    @property
    def extra_state_attributes(self) -> dict:
        arrivals = self.arrivals
        return {
            "schema_version": 1,
            "board_type": "station",
            "station_name": self.coordinator.location_name,
            "location_id": self.coordinator.location,
            "service_type": self.coordinator.service_type,
            "poll_interval": int(self.coordinator.update_interval.total_seconds()),
            "station_codes": self.coordinator.codes
            if self.coordinator.service_type == "train"
            else [],
            "arrivals": arrivals,
            "arrival_count": len(arrivals),
            "served_lines": self.coordinator.served_lines,
            "next_arrival": arrivals[0] if arrivals else None,
            "updated_at": self.coordinator.data.updated_at
            if self.coordinator.data
            else None,
        }


class WmataJourneySensor(WmataBoardSensor):
    """A named subset of a station board, updated without extra requests."""

    def __init__(self, coordinator, journey: dict) -> None:
        super().__init__(coordinator)
        self.journey = journey
        self._attr_unique_id = (
            f"wmata_{coordinator.service_type}_{coordinator.location.lower()}"
            f"_journey_{journey['id']}"
        )
        # HA derives the entity ID from the station and journey name on first use.
        self.entity_id = None
        self._attr_name = journey["name"]
        self._attr_icon = "mdi:map-marker-path"

    @property
    def arrivals(self) -> list[dict]:
        return filter_arrivals(super().arrivals, self.journey)

    @property
    def extra_state_attributes(self) -> dict:
        return {
            **super().extra_state_attributes,
            "board_type": "journey",
            "journey_name": self.journey["name"],
            "filters": {
                k: v for k, v in self.journey.items() if k not in ("id", "name")
            },
        }


class NetworkMapSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Trains"
    _attr_device_info = DeviceInfo(
        identifiers={(DOMAIN, "network")},
        name="WMATA network",
        manufacturer="WMATA",
        entry_type=DeviceEntryType.SERVICE,
    )
    _attr_unique_id = "wmata_network_trains"
    _attr_icon = "mdi:train"
    _unrecorded_attributes = frozenset({"paths", "trains", "updated_at"})

    @property
    def native_value(self):
        return len(self.coordinator.data["trains"])

    @property
    def extra_state_attributes(self):
        return self.coordinator.data
