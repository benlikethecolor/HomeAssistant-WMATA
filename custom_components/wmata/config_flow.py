"""UI setup, credential repair and options for independent WMATA locations."""

from __future__ import annotations

import re
from uuid import uuid4

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_ID, UnitOfLength
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.location import distance

from .api import APIAuthError, APIConnectionError, InvalidLocation, WmataApi
from .const import (
    CONF_DUE_SOON,
    CONF_INTERVAL,
    CONF_JOURNEYS,
    CONF_LINES,
    CONF_ROUTES,
    CONF_SERVICE_TYPE,
    CONF_TRANSFER_BUFFER,
    DEFAULT_DUE_SOON,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRANSFER_BUFFER,
    DOMAIN,
    LINE_NAME_MAP,
    STATION_CODE_MAP,
    station_codes,
)
from .journeys import STATIONS_BY_NAME, describe_route, plan_journey

KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        )
    }
)

# Bus stop search: a pin on a map, then the closest stops to it.
METRO_CENTER = (38.8983, -77.0281)
SERVICE_AREA_METERS = 80000
NEARBY_RADIUS_METERS = 800
NEARBY_LIMIT = 15
SEARCH_AGAIN = "search_again"


def search_start(hass) -> dict[str, float]:
    """Start at home, or downtown when home is nowhere near Metrobus service."""
    latitude, longitude = hass.config.latitude, hass.config.longitude
    away = distance(latitude, longitude, *METRO_CENTER)
    if away is None or away > SERVICE_AREA_METERS:
        latitude, longitude = METRO_CENTER
    return {"latitude": latitude, "longitude": longitude}


def stop_label(hass, stop: dict, meters: float) -> str:
    """Name, routes, distance and the ID printed on the sign."""
    routes = list(
        dict.fromkeys(
            # WMATA lists pattern variants such as 10Av1 or D34*2 separately.
            re.split(r"[*/]|v\d", route)[0]
            for route in stop.get("Routes") or []
            if isinstance(route, str) and route
        )
    )
    if hass.config.units.length_unit == UnitOfLength.MILES:
        feet = meters * 3.28084
        away = (
            f"{round(feet / 50) * 50} ft"
            if feet < 1000
            else f"{meters / 1609.344:.1f} mi"
        )
    else:
        away = f"{round(meters / 10) * 10} m"
    served = ", ".join(routes[:6]) + (", …" if len(routes) > 6 else "")
    return " · ".join(
        part for part in (stop["Name"], served, away, f"#{stop['StopID']}") if part
    )


def station_selector(exclude: str | None = None):
    """Every station once, by name, in a list you can type into to search.

    Allowing a typed value is what makes the frontend show a searchable box
    rather than a plain list of nearly a hundred rows.
    """
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=code, label=name)
                for name, code in sorted(STATIONS_BY_NAME.items())
                if name != exclude
            ],
            custom_value=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def resolve_station(value) -> str | None:
    """Accept a listed choice, or a station name or code typed by hand."""
    text = str(value or "").strip()
    if text.upper() in STATION_CODE_MAP:
        return text.upper()
    names = {name.casefold(): code for name, code in STATIONS_BY_NAME.items()}
    return names.get(text.casefold())


def line_selector():
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=k, label=v)
                for k, v in LINE_NAME_MAP.items()
            ],
            multiple=True,
        )
    )


async def validate_location(hass, data):
    """Validate credentials and location against the actual service endpoints."""
    data = dict(data)
    data[CONF_API_KEY] = data[CONF_API_KEY].strip()
    data[CONF_ID] = data[CONF_ID].strip().upper()
    api = WmataApi(async_get_clientsession(hass), data[CONF_API_KEY], hass=hass)
    if data[CONF_SERVICE_TYPE] == "map":
        await api.validate_service("map")
        return {**data, "location_name": "Metrorail train map"}
    if data[CONF_SERVICE_TYPE] == "commute":
        await api.validate_service("commute")
        return data
    if data[CONF_SERVICE_TYPE] == "train":
        stations = await api.stations()
        station = next((s for s in stations if s.get("Code") == data[CONF_ID]), None)
        if not station:
            raise InvalidLocation
        codes = station_codes(data[CONF_ID])
        codes.extend(
            station[k]
            for k in ("StationTogether1", "StationTogether2")
            if station.get(k)
        )
        data["station_codes"] = sorted(set(codes))
        data["location_name"] = station["Name"]
        data["served_lines"] = sorted(
            {
                s[k]
                for s in stations
                if s.get("Code") in data["station_codes"]
                for k in ("LineCode1", "LineCode2", "LineCode3", "LineCode4")
                if s.get(k) in LINE_NAME_MAP
            }
        )
        await api.trains(data["station_codes"])
    else:
        if not re.fullmatch(r"\d{7}", data[CONF_ID]):
            raise InvalidLocation
        data["location_name"] = await api.stop_name(data[CONF_ID])
        await api.buses(data[CONF_ID])
    return data


class WmataConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure one station (all platforms) or one bus stop per entry."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WmataOptionsFlow()

    def _saved_keys(self):
        """Refer to saved credentials by entry, never by the key itself."""
        keys = {}
        seen = set()
        for entry in self._async_current_entries():
            key = entry.data.get(CONF_API_KEY)
            if key and key not in seen:
                keys[entry.entry_id] = entry
                seen.add(key)
        return keys

    async def async_step_api_key(self, user_input=None):
        if user_input is not None:
            return await self.async_step_user({**self._pending_service, **user_input})
        return self.async_show_form(step_id="api_key", data_schema=KEY_SCHEMA)

    async def async_step_user(self, user_input=None):
        errors = {}
        saved = self._saved_keys()
        if user_input is not None and CONF_API_KEY not in user_input:
            source = user_input.get("credential_source")
            if source == "new":
                self._pending_service = {
                    CONF_SERVICE_TYPE: user_input[CONF_SERVICE_TYPE]
                }
                return await self.async_step_api_key()
            if source not in saved:
                return self.async_abort(reason="credential_unavailable")
            user_input = {
                CONF_SERVICE_TYPE: user_input[CONF_SERVICE_TYPE],
                CONF_API_KEY: saved[source].data[CONF_API_KEY],
            }
        if user_input is not None:
            user_input = {**user_input, CONF_API_KEY: user_input[CONF_API_KEY].strip()}
            try:
                api = WmataApi(
                    async_get_clientsession(self.hass),
                    user_input[CONF_API_KEY].strip(),
                    hass=self.hass,
                )
                await api.validate_service(user_input[CONF_SERVICE_TYPE])
            except APIAuthError:
                errors["base"] = "invalid_auth"
            except APIConnectionError:
                errors["base"] = "cannot_connect"
            else:
                if user_input[CONF_SERVICE_TYPE] == "map":
                    await self.async_set_unique_id("network_map")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Metrorail train map",
                        data={**user_input, CONF_ID: "network"},
                    )
                self._setup_data = dict(user_input)
                if user_input[CONF_SERVICE_TYPE] == "bus":
                    return await self.async_step_bus_stop()
                if user_input[CONF_SERVICE_TYPE] == "commute":
                    return await self.async_step_commute()
                return await self.async_step_location()
        key_fields = KEY_SCHEMA.schema
        if saved and not (user_input and CONF_API_KEY in user_input and errors):
            key_fields = {
                vol.Required(
                    "credential_source", default=next(iter(saved))
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            *[
                                selector.SelectOptionDict(
                                    value=entry_id, label=f"Same key as {entry.title}"
                                )
                                for entry_id, entry in saved.items()
                            ],
                            selector.SelectOptionDict(
                                value="new", label="Enter a different API key"
                            ),
                        ]
                    )
                )
            }
        schema = vol.Schema(
            {
                **key_fields,
                vol.Required(
                    CONF_SERVICE_TYPE,
                    default=user_input.get(CONF_SERVICE_TYPE, "train")
                    if user_input
                    else "train",
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="train", label="Metrorail"),
                            selector.SelectOptionDict(value="bus", label="Metrobus"),
                            selector.SelectOptionDict(
                                value="commute", label="Commute between two stations"
                            ),
                            selector.SelectOptionDict(
                                value="map", label="Systemwide train map"
                            ),
                        ]
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={"api_key_url": "https://developer.wmata.com/"},
        )

    async def _add_location(self, location):
        """Create the entry for a station or stop, or say why it can't be added."""
        errors = {}
        try:
            data = await validate_location(
                self.hass, {**self._setup_data, CONF_ID: location}
            )
        except APIAuthError:
            errors["base"] = "invalid_auth"
        except APIConnectionError:
            errors["base"] = "cannot_connect"
        except InvalidLocation:
            errors[CONF_ID] = "invalid_location"
        else:
            for entry in self._async_current_entries():
                if entry.data.get(CONF_SERVICE_TYPE) != data[CONF_SERVICE_TYPE]:
                    continue
                old_id = entry.data.get(CONF_ID, "").strip().upper()
                if old_id == data[CONF_ID] or (
                    data[CONF_SERVICE_TYPE] == "train"
                    and old_id in data["station_codes"]
                ):
                    return self.async_abort(reason="already_configured"), errors
            codes = data.get("station_codes", [data[CONF_ID]])
            await self.async_set_unique_id(
                f"{data[CONF_SERVICE_TYPE]}:{','.join(codes)}"
            )
            self._abort_if_unique_id_configured()
            return (
                self.async_create_entry(title=data["location_name"], data=data),
                errors,
            )
        return None, errors

    async def async_step_location(self, user_input=None):
        """Pick a rail station by name."""
        errors = {}
        if user_input is not None:
            station = resolve_station(user_input[CONF_ID])
            if station is None:
                errors[CONF_ID] = "unknown_station"
            else:
                result, errors = await self._add_location(station)
                if result:
                    return result
        schema = vol.Schema({vol.Required(CONF_ID): station_selector()})
        return self.async_show_form(
            step_id="location", data_schema=schema, errors=errors
        )

    async def async_step_commute(self, user_input=None):
        """Two stations become travel-time sensors for the trip each way."""
        errors = {}
        if user_input is not None:
            home = resolve_station(user_input["home"])
            work = resolve_station(user_input["work"])
            if home is None:
                errors["home"] = "unknown_station"
            elif work is None:
                errors["work"] = "unknown_station"
            elif STATION_CODE_MAP[home] == STATION_CODE_MAP[work]:
                errors["work"] = "same_station"
            elif plan_journey(home, work) is None:
                errors["work"] = "no_route"
            else:
                # Either platform code of a transfer station means the same place.
                first, second = min(station_codes(home)), min(station_codes(work))
                await self.async_set_unique_id(f"commute:{first}:{second}")
                self._abort_if_unique_id_configured()
                name = (user_input.get("name") or "").strip() or "Commute"
                return self.async_create_entry(
                    title=f"{STATION_CODE_MAP[home]} ↔ {STATION_CODE_MAP[work]}",
                    data={
                        **self._setup_data,
                        CONF_ID: f"{first}-{second}",
                        "home": first,
                        "work": second,
                        "location_name": name,
                    },
                )
        stations = station_selector()
        chosen = user_input or {}
        return self.async_show_form(
            step_id="commute",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "home",
                        **({"default": chosen["home"]} if "home" in chosen else {}),
                    ): stations,
                    vol.Required(
                        "work",
                        **({"default": chosen["work"]} if "work" in chosen else {}),
                    ): stations,
                    vol.Optional(
                        "name", default=chosen.get("name", "Commute")
                    ): vol.All(str, vol.Length(max=60)),
                }
            ),
        )

    async def async_step_bus_stop(self, user_input=None):
        """Type a stop ID, or drop a pin to list the stops around it."""
        errors = {}
        near = search_start(self.hass)
        stop = ""
        if user_input is not None:
            near = user_input.get("near") or near
            stop = (user_input.get(CONF_ID) or "").strip()
            if stop:
                result, errors = await self._add_location(stop)
                if result:
                    return result
            else:
                try:
                    self._nearby = await self._stops_near(near)
                except APIAuthError:
                    errors["base"] = "invalid_auth"
                except APIConnectionError:
                    errors["base"] = "cannot_connect"
                else:
                    if self._nearby:
                        return await self.async_step_nearby_stop()
                    errors["near"] = "no_stops_nearby"
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ID, description={"suggested_value": stop}
                ): selector.TextSelector(),
                vol.Optional("near", default=near): selector.LocationSelector(),
            }
        )
        return self.async_show_form(
            step_id="bus_stop",
            data_schema=schema,
            errors=errors,
            description_placeholders={"bus_stop_url": "https://buseta.wmata.com/"},
        )

    async def _stops_near(self, point):
        """Closest stops first, leaving out any that are already set up."""
        api = WmataApi(
            async_get_clientsession(self.hass),
            self._setup_data[CONF_API_KEY],
            hass=self.hass,
        )
        latitude, longitude = point["latitude"], point["longitude"]
        configured = {
            entry.data.get(CONF_ID)
            for entry in self._async_current_entries()
            if entry.data.get(CONF_SERVICE_TYPE) == "bus"
        }
        ranked = sorted(
            (
                (distance(latitude, longitude, stop["Lat"], stop["Lon"]) or 0, stop)
                for stop in await api.nearby_stops(
                    latitude, longitude, NEARBY_RADIUS_METERS
                )
                if stop["StopID"] not in configured
            ),
            key=lambda item: (item[0], item[1]["StopID"]),
        )
        return {
            stop["StopID"]: stop_label(self.hass, stop, meters)
            for meters, stop in ranked[:NEARBY_LIMIT]
        }

    async def async_step_nearby_stop(self, user_input=None):
        """Choose one of the stops found around the pin."""
        errors = {}
        if user_input is not None:
            if user_input[CONF_ID] == SEARCH_AGAIN:
                return await self.async_step_bus_stop()
            result, errors = await self._add_location(user_input[CONF_ID])
            if result:
                return result
        schema = vol.Schema(
            {
                vol.Required(CONF_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            *[
                                selector.SelectOptionDict(value=stop, label=label)
                                for stop, label in self._nearby.items()
                            ],
                            selector.SelectOptionDict(
                                value=SEARCH_AGAIN,
                                label="None of these. Search somewhere else",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="nearby_stop",
            data_schema=schema,
            errors=errors,
            description_placeholders={"count": str(len(self._nearby))},
        )

    async def async_step_reconfigure(self, user_input=None):
        """Change the key, or point the entry at a different place."""
        entry = self._get_reconfigure_entry()
        service = entry.data[CONF_SERVICE_TYPE]
        current = entry.data.get(CONF_ID, "")
        errors = {}
        if user_input is not None:
            key = (user_input.get(CONF_API_KEY) or "").strip() or entry.data[
                CONF_API_KEY
            ]
            target = {}
            if service == "train":
                station = resolve_station(user_input.get("station", current))
                if station is None:
                    errors["station"] = "unknown_station"
                elif STATION_CODE_MAP[station] != STATION_CODE_MAP.get(current):
                    target = {CONF_ID: station}
            elif service == "bus":
                target = {CONF_ID: str(user_input.get("stop", current)).strip()}
            elif service == "commute":
                home = resolve_station(user_input.get("home", entry.data["home"]))
                work = resolve_station(user_input.get("work", entry.data["work"]))
                if home is None:
                    errors["home"] = "unknown_station"
                elif work is None:
                    errors["work"] = "unknown_station"
                elif STATION_CODE_MAP[home] == STATION_CODE_MAP[work]:
                    errors["work"] = "same_station"
                elif plan_journey(home, work) is None:
                    errors["work"] = "no_route"
                else:
                    first, second = min(station_codes(home)), min(station_codes(work))
                    target = {
                        CONF_ID: f"{first}-{second}",
                        "home": first,
                        "work": second,
                        "location_name": (user_input.get("name") or "").strip()
                        or entry.data.get("location_name", "Commute"),
                    }
            moved = target.get(CONF_ID, current) != current
            if moved and any(
                other.entry_id != entry.entry_id
                and other.data.get(CONF_SERVICE_TYPE) == service
                and (
                    other.data.get(CONF_ID) == target[CONF_ID]
                    or (
                        service == "train"
                        and other.data.get(CONF_ID) in station_codes(target[CONF_ID])
                    )
                )
                for other in self._async_current_entries()
            ):
                errors["base"] = "already_added"
            if not errors:
                try:
                    data = await validate_location(
                        self.hass, {**entry.data, **target, CONF_API_KEY: key}
                    )
                    shared = await self._entries_sharing_key(entry, key)
                except APIAuthError:
                    errors["base"] = "invalid_auth"
                except APIConnectionError:
                    errors["base"] = "cannot_connect"
                except InvalidLocation:
                    errors["base"] = "invalid_location"
                else:
                    self._update_shared_key(shared, key)
                    changes = {}
                    if moved:
                        changes = self._move_entry(entry, data)
                    return self.async_update_reload_and_abort(
                        entry, data=data, reason="reconfigure_successful", **changes
                    )
        fields = {
            vol.Optional(CONF_API_KEY): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            )
        }
        chosen = user_input or {}
        if service == "train":
            # The list holds one code per station; show the one for this entry.
            default = STATIONS_BY_NAME.get(STATION_CODE_MAP.get(current), current)
            fields[vol.Required("station", default=chosen.get("station", default))] = (
                station_selector()
            )
        elif service == "bus":
            fields[vol.Required("stop", default=chosen.get("stop", current))] = (
                selector.TextSelector()
            )
        elif service == "commute":
            for field in ("home", "work"):
                fields[
                    vol.Required(field, default=chosen.get(field, entry.data[field]))
                ] = station_selector()
            fields[
                vol.Optional(
                    "name",
                    default=chosen.get(
                        "name", entry.data.get("location_name", "Commute")
                    ),
                )
            ] = vol.All(str, vol.Length(max=60))
        return self.async_show_form(
            step_id="reconfigure", data_schema=vol.Schema(fields), errors=errors
        )

    def _move_entry(self, entry, data) -> dict:
        """Clear out the old place's entities and work out the entry's new identity."""
        entities = er.async_get(self.hass)
        for entity in er.async_entries_for_config_entry(entities, entry.entry_id):
            entities.async_remove(entity.entity_id)
        devices = dr.async_get(self.hass)
        for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
            devices.async_remove_device(device.id)
        service = data[CONF_SERVICE_TYPE]
        if service == "commute":
            return {
                "unique_id": f"commute:{data['home']}:{data['work']}",
                "title": (
                    f"{STATION_CODE_MAP[data['home']]} ↔ "
                    f"{STATION_CODE_MAP[data['work']]}"
                ),
            }
        codes = data.get("station_codes", [data[CONF_ID]])
        changes = {
            "unique_id": f"{service}:{','.join(codes)}",
            "title": data["location_name"],
        }
        journeys = []
        for journey in entry.options.get(CONF_JOURNEYS, []):
            if journey.get("kind") != "station_to_station":
                journeys.append(journey)
                continue
            # Keep the destination and plan it again from the new station.
            route = plan_journey(data[CONF_ID], journey["target_station"])
            if route:
                journeys.append({**journey, "route": route})
        if CONF_JOURNEYS in entry.options:
            changes["options"] = {**entry.options, CONF_JOURNEYS: journeys}
        return changes

    async def _entries_sharing_key(self, entry, key):
        """Other entries on the same key, checked against the replacement key."""
        if key == entry.data.get(CONF_API_KEY):
            return []
        shared = [
            other
            for other in self._async_current_entries()
            if other.entry_id != entry.entry_id
            and other.data.get(CONF_API_KEY) == entry.data.get(CONF_API_KEY)
        ]
        # Validate every affected service before changing any saved key.
        for other in shared:
            await validate_location(self.hass, {**other.data, CONF_API_KEY: key})
        return shared

    def _update_shared_key(self, shared, key):
        """A saved key represents the same subscription across entries."""
        for other in shared:
            self.hass.config_entries.async_update_entry(
                other, data={**other.data, CONF_API_KEY: key}
            )
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(other.entry_id)
            )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """WMATA rejected the key; ask for a working one."""
        errors = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                data = await validate_location(self.hass, {**entry.data, **user_input})
                shared = await self._entries_sharing_key(entry, data[CONF_API_KEY])
            except APIAuthError:
                errors["base"] = "invalid_auth"
            except APIConnectionError:
                errors["base"] = "cannot_connect"
            except InvalidLocation:
                errors["base"] = "invalid_location"
            else:
                self._update_shared_key(shared, data[CONF_API_KEY])
                return self.async_update_reload_and_abort(
                    entry, data=data, reason="reauth_successful"
                )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=KEY_SCHEMA, errors=errors
        )


class WmataOptionsFlow(OptionsFlow):
    """Manage named journeys without duplicating the station's polling."""

    async def async_step_init(self, user_input=None):
        if self.config_entry.data[CONF_SERVICE_TYPE] in ("map", "commute"):
            return await self.async_step_settings(user_input)
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "settings",
                *(
                    ["add_trip"]
                    if self.config_entry.data[CONF_SERVICE_TYPE] == "train"
                    else []
                ),
                "add_journey",
                "edit_journey",
                "remove_journey",
            ],
        )

    def _save(self, **updates):
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **updates}
        )

    async def async_step_settings(self, user_input=None):
        if user_input is not None:
            return self._save(**user_input)
        service = self.config_entry.data[CONF_SERVICE_TYPE]
        options = self.config_entry.options
        fields = {
            vol.Required(
                CONF_INTERVAL, default=options.get(CONF_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ): vol.All(vol.Coerce(int), vol.Range(min=15, max=300))
        }
        if service in ("train", "bus"):
            fields[
                vol.Required(
                    CONF_DUE_SOON, default=options.get(CONF_DUE_SOON, DEFAULT_DUE_SOON)
                )
            ] = vol.All(vol.Coerce(int), vol.Range(min=1, max=60))
        if service == "commute":
            fields[
                vol.Required(
                    CONF_TRANSFER_BUFFER,
                    default=options.get(CONF_TRANSFER_BUFFER, DEFAULT_TRANSFER_BUFFER),
                )
            ] = vol.All(vol.Coerce(int), vol.Range(min=1, max=30))
        return self.async_show_form(step_id="settings", data_schema=vol.Schema(fields))

    def _journeys(self):
        return list(self.config_entry.options.get(CONF_JOURNEYS, []))

    def _journey_schema(self, current):
        schema = {
            vol.Required("name", default=current.get("name", "")): vol.All(
                str, vol.Length(min=1, max=80)
            ),
        }
        if self.config_entry.data[CONF_SERVICE_TYPE] == "train":
            choices = {}
            for code, name in STATION_CODE_MAP.items():
                choices.setdefault(name, code)
            schema.update(
                {
                    vol.Optional(
                        CONF_LINES, default=current.get(CONF_LINES, [])
                    ): line_selector(),
                    vol.Optional(
                        "destinations", default=current.get("destinations", [])
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=code, label=name)
                                for name, code in sorted(choices.items())
                            ],
                            multiple=True,
                        )
                    ),
                    vol.Optional(
                        "rail_direction", default=current.get("rail_direction", "any")
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value="any", label="Any direction"
                                ),
                                selector.SelectOptionDict(
                                    value="Eastbound", label="Eastbound"
                                ),
                                selector.SelectOptionDict(
                                    value="Westbound", label="Westbound"
                                ),
                                selector.SelectOptionDict(
                                    value="Northbound", label="Northbound"
                                ),
                                selector.SelectOptionDict(
                                    value="Southbound", label="Southbound"
                                ),
                            ]
                        )
                    ),
                }
            )
        else:
            schema.update(
                {
                    vol.Optional(
                        CONF_ROUTES, default=", ".join(current.get(CONF_ROUTES, []))
                    ): str,
                    vol.Optional(
                        "direction_id", default=current.get("direction_id", "any")
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value="any", label="Either direction"
                                ),
                                selector.SelectOptionDict(
                                    value="0", label="Direction 0"
                                ),
                                selector.SelectOptionDict(
                                    value="1", label="Direction 1"
                                ),
                            ]
                        )
                    ),
                }
            )
        return vol.Schema(schema)

    async def async_step_add_trip(self, user_input=None):
        self._editing_id = None
        return await self._trip_form("add_trip", user_input)

    async def async_step_edit_trip(self, user_input=None):
        return await self._trip_form("edit_trip", user_input)

    async def _trip_form(self, step_id, user_input):
        if self.config_entry.data[CONF_SERVICE_TYPE] != "train":
            return self.async_abort(reason="rail_only")
        origin = self.config_entry.data[CONF_ID]
        origin_name = STATION_CODE_MAP[origin]
        current = next(
            (
                j
                for j in self._journeys()
                if j["id"] == getattr(self, "_editing_id", None)
            ),
            {},
        )
        errors = {}
        if user_input is not None:
            target = resolve_station(user_input["target_station"])
            route = plan_journey(origin, target) if target else None
            name = (
                user_input.get("name", "").strip()
                or f"To {STATION_CODE_MAP.get(target, 'destination')}"
            )
            if target is None:
                errors["target_station"] = "unknown_station"
            elif route is None:
                errors["base"] = "no_route"
            elif any(
                j["name"].casefold() == name.casefold() and j["id"] != self._editing_id
                for j in self._journeys()
            ):
                errors["name"] = "duplicate_name"
            else:
                self._pending_trip = {
                    "id": self._editing_id or uuid4().hex,
                    "name": name,
                    "kind": "station_to_station",
                    "target_station": target,
                    "route": route,
                }
                return await self.async_step_trip_confirm()
        return self.async_show_form(
            step_id=step_id,
            errors=errors,
            description_placeholders={"origin": origin_name},
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "target_station",
                        **(
                            {"default": current["target_station"]}
                            if current.get("target_station")
                            else {}
                        ),
                    ): station_selector(exclude=origin_name),
                    vol.Optional("name", default=current.get("name", "")): vol.All(
                        str, vol.Length(max=80)
                    ),
                }
            ),
        )

    async def async_step_trip_confirm(self, user_input=None):
        trip = self._pending_trip
        if user_input is not None:
            journeys = [
                trip if j["id"] == self._editing_id else j for j in self._journeys()
            ]
            if self._editing_id is None:
                journeys.append(trip)
            return self._save(**{CONF_JOURNEYS: journeys})
        route = trip["route"]
        return self.async_show_form(
            step_id="trip_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "origin": route["origin_name"],
                "destination": route["destination_name"],
                "route": describe_route(route),
                "transfers": str(route["transfers"]),
            },
        )

    async def async_step_add_journey(self, user_input=None):
        self._editing_id = None
        return await self._journey_form("add_journey", user_input)

    async def _journey_form(self, step_id, user_input):
        if self.config_entry.data[CONF_SERVICE_TYPE] == "map":
            return self.async_abort(reason="no_journeys")
        journeys = self._journeys()
        current = next((j for j in journeys if j["id"] == self._editing_id), {})
        errors = {}
        if user_input is not None:
            data = dict(user_input)
            data["name"] = data["name"].strip()
            if not data["name"]:
                errors["name"] = "invalid_name"
            elif any(
                j["name"].casefold() == data["name"].casefold()
                and j["id"] != self._editing_id
                for j in journeys
            ):
                errors["name"] = "duplicate_name"
            else:
                if CONF_ROUTES in data:
                    data[CONF_ROUTES] = list(
                        dict.fromkeys(
                            r.strip().upper()
                            for r in data[CONF_ROUTES].split(",")
                            if r.strip()
                        )
                    )
                data["id"] = self._editing_id or uuid4().hex
                journeys = [
                    data if j["id"] == self._editing_id else j for j in journeys
                ]
                if self._editing_id is None:
                    journeys.append(data)
                return self._save(**{CONF_JOURNEYS: journeys})
        return self.async_show_form(
            step_id=step_id, data_schema=self._journey_schema(current), errors=errors
        )

    async def _select_journey(self, step_id, user_input):
        journeys = self._journeys()
        if not journeys:
            return self.async_abort(reason="no_journeys")
        if user_input is not None:
            selected = user_input["journey_id"]
            if not any(j["id"] == selected for j in journeys):
                return self.async_abort(reason="journey_not_found")
            if step_id == "remove_journey":
                return self._save(
                    **{CONF_JOURNEYS: [j for j in journeys if j["id"] != selected]}
                )
            self._editing_id = selected
            current = next(j for j in journeys if j["id"] == selected)
            if current.get("kind") == "station_to_station":
                return await self.async_step_edit_trip()
            return await self.async_step_journey()
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required("journey_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=j["id"], label=j["name"]
                                )
                                for j in journeys
                            ]
                        )
                    ),
                }
            ),
        )

    async def async_step_edit_journey(self, user_input=None):
        return await self._select_journey("edit_journey", user_input)

    async def async_step_remove_journey(self, user_input=None):
        return await self._select_journey("remove_journey", user_input)

    async def async_step_journey(self, user_input=None):
        return await self._journey_form("journey", user_input)
