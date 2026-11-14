"""One station board and optional saved journeys, without numbered slots."""

import math
from copy import deepcopy
from datetime import UTC, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import parse_datetime

from .commute import DIRECTIONS
from .const import CONF_JOURNEYS, DOMAIN, LINE_NAME_MAP, STATION_CODE_MAP
from .coordinator import WmataCoordinator
from .directions import station_directions
from .journeys import describe_route
from .predictions import filter_arrivals

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Reconcile only this entry's entities, including removed saved journeys."""
    coordinator = entry.runtime_data
    if entry.data["service_type"] == "map":
        async_add_entities([NetworkMapSensor(coordinator)])
        return
    if entry.data["service_type"] == "commute":
        async_add_entities(
            WmataCommuteSensor(coordinator, direction, kind)
            for direction in DIRECTIONS
            for kind in ("travel_time", "next_train", "arrival")
        )
        return
    sensors = [WmataBoardSensor(coordinator)]
    sensors.extend(
        WmataJourneySensor(coordinator, journey)
        for journey in entry.options.get(CONF_JOURNEYS, [])
    )
    sensors.extend(
        WmataDetailSensor(coordinator, kind)
        for kind in ("destination", "line", "count", "updated")
    )
    if coordinator.service_type == "train":
        sensors.extend(
            WmataDirectionSensor(coordinator, line, direction)
            for line in coordinator.served_lines
            for direction in station_directions(line, coordinator.codes)
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
    _unrecorded_attributes = frozenset(
        {"arrivals", "updated_at", "next_arrival", "alerts", "outages"}
    )

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"wmata_{coordinator.service_type}_{coordinator.location.lower()}_board"
        )
        # HA derives readable IDs from device and entity names; existing registry
        # entries keep their IDs because unique_id is unchanged.
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
    def alerts(self) -> list[dict]:
        """Service alerts for the lines or routes that stop here."""
        return self.coordinator.alerts_for()

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
            "alerts": self.alerts,
            "outages": self.coordinator.data.outages if self.coordinator.data else [],
            "updated_at": self.coordinator.data.updated_at
            if self.coordinator.data
            else None,
        }


class WmataJourneySensor(WmataBoardSensor):
    """A named subset of a station board, updated without extra requests."""

    _unrecorded_attributes = WmataBoardSensor._unrecorded_attributes | {
        "journey_route",
        "route_description",
    }

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
    def alerts(self) -> list[dict]:
        """A journey cares about its own lines, including ones it transfers to."""
        route = self.journey.get("route")
        if route:
            lines = {line for leg in route["legs"] for line in leg["lines"]}
            return self.coordinator.alerts_for(lines=lines)
        if self.journey.get("lines") or self.journey.get("routes"):
            return self.coordinator.alerts_for(
                lines=self.journey.get("lines"), routes=self.journey.get("routes")
            )
        return super().alerts

    @property
    def extra_state_attributes(self) -> dict:
        route = deepcopy(self.journey.get("route"))
        if route:
            lines = sorted(
                {
                    arrival["line"]
                    for arrival in self.arrivals
                    if arrival.get("line") in LINE_NAME_MAP
                }
            )
            if lines:
                route["legs"][0]["lines"] = lines
        return {
            **super().extra_state_attributes,
            "board_type": "journey",
            "journey_name": self.journey["name"],
            **(
                {
                    "journey_route": route,
                    "route_description": describe_route(route),
                    "eta_type": "boarding",
                }
                if self.journey.get("kind") == "station_to_station"
                else {}
            ),
            "filters": {
                k: v
                for k, v in self.journey.items()
                if k not in ("id", "name", "route")
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


class WmataCommuteSensor(CoordinatorEntity, SensorEntity):
    """Estimated trip between two stations, usable in automations."""

    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"updated_at", "first_train", "alerts"})

    def __init__(self, coordinator, direction, kind) -> None:
        super().__init__(coordinator)
        self.direction = direction
        self.kind = kind
        self.origin, self.destination = coordinator.stations(direction)
        self._attr_unique_id = (
            f"wmata_commute_{coordinator.home.lower()}_{coordinator.work.lower()}"
            f"_{direction}_{kind}"
        )
        self._attr_name = (
            f"To {STATION_CODE_MAP[self.destination]} "
            + {
                "travel_time": "travel time",
                "next_train": "next train",
                "arrival": "arrival",
            }[kind]
        )
        self._attr_icon = {
            "travel_time": "mdi:timer-outline",
            "next_train": "mdi:subway",
            "arrival": "mdi:clock-check-outline",
        }[kind]
        if kind == "arrival":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        else:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"commute_{coordinator.home}_{coordinator.work}")},
            name=f"WMATA {coordinator.commute_name}",
            manufacturer="WMATA",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def trip(self) -> dict | None:
        data = self.coordinator.data
        return data["trips"].get(self.direction) if data else None

    @property
    def native_value(self):
        trip = self.trip
        if not trip:
            return None
        if self.kind == "next_train":
            if trip["departure"] is None:
                return None
            return max(0, math.ceil((trip["departure"] - trip["calculated_at"]) / 60))
        if trip["arrival"] is None:
            return None
        if self.kind == "arrival":
            return datetime.fromtimestamp(trip["arrival"], UTC)
        return max(0, math.ceil((trip["arrival"] - trip["calculated_at"]) / 60))

    @property
    def extra_state_attributes(self):
        # The travel-time sensor describes the trip; the others are plain values.
        if self.kind != "travel_time":
            return None
        trip = self.trip or {}
        train = trip.get("first_train") or {}
        return {
            "board_type": "commute",
            "direction": self.direction,
            "origin": self.origin,
            "origin_name": STATION_CODE_MAP[self.origin],
            "destination": self.destination,
            "destination_name": STATION_CODE_MAP[self.destination],
            "route_description": trip.get("route_description"),
            "transfers": trip.get("transfers"),
            "first_train": (
                {
                    "line": train.get("line"),
                    "line_name": train.get("line_name"),
                    "destination": train.get("destination"),
                }
                if train
                else None
            ),
            # True when part of the trip relies on the timetable, not live trains.
            "schedule_estimate": trip.get("schedule_estimate"),
            "last_train": bool(train.get("last_train")),
            "alerts": trip.get("alerts", []),
            "transfer_buffer": self.coordinator.buffer,
            "updated_at": self.coordinator.data["updated_at"]
            if self.coordinator.data
            else None,
        }


class WmataDetailSensor(WmataBoardSensor):
    """Optional scalar values for built-in HA cards and automations."""

    _attr_entity_registry_enabled_default = False
    _attr_native_unit_of_measurement = None
    _attr_device_class = None

    def __init__(self, coordinator, kind):
        super().__init__(coordinator)
        self.kind = kind
        self._attr_unique_id += f"_{kind}"
        self._attr_name = {
            "destination": "Next destination",
            "line": "Next line"
            if coordinator.service_type == "train"
            else "Next route",
            "count": "Arrival count",
            "updated": "Last update",
        }[kind]
        self._attr_icon = {
            "destination": "mdi:sign-direction",
            "line": "mdi:transit-connection-variant",
            "count": "mdi:counter",
            "updated": "mdi:clock-check-outline",
        }[kind]
        if kind == "updated":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        if self.kind == "updated":
            return (
                parse_datetime(self.coordinator.data.updated_at)
                if self.coordinator.data
                else None
            )
        if self.kind == "count":
            return len(self.arrivals)
        arrival = self.arrivals[0] if self.arrivals else {}
        if self.kind == "destination":
            return arrival.get("destination")
        return (
            arrival.get("line_name")
            if self.coordinator.service_type == "train"
            else arrival.get("route")
        )

    @property
    def extra_state_attributes(self):
        return None


class WmataDirectionSensor(WmataJourneySensor):
    """Ready-made ETAs: enable one, then use it in a numeric-state trigger."""

    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, line, direction):
        super().__init__(
            coordinator,
            {
                "id": f"line_{line}_{direction.lower()}",
                "name": f"{LINE_NAME_MAP[line]} {direction.lower()} arrival",
                "lines": [line],
                "rail_direction": direction,
            },
        )
