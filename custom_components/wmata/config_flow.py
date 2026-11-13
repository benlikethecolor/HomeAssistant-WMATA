"""UI setup, credential repair and options for independent WMATA locations."""

from __future__ import annotations

import re
from uuid import uuid4

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_ID
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import APIAuthError, APIConnectionError, InvalidLocation, WmataApi
from .const import (
    CONF_INTERVAL,
    CONF_JOURNEYS,
    CONF_LINES,
    CONF_ROUTES,
    CONF_SERVICE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LINE_NAME_MAP,
    STATION_CODE_MAP,
    station_codes,
)

KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        )
    }
)


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

    async def async_step_user(self, user_input=None):
        errors = {}
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
                return await self.async_step_location()
        schema = vol.Schema(
            {
                **KEY_SCHEMA.schema,
                vol.Required(
                    CONF_SERVICE_TYPE, default="train"
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value="train", label="Metrorail"),
                            selector.SelectOptionDict(value="bus", label="Metrobus"),
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

    async def async_step_location(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = await validate_location(
                    self.hass, {**self._setup_data, **user_input}
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
                        return self.async_abort(reason="already_configured")
                codes = data.get("station_codes", [data[CONF_ID]])
                await self.async_set_unique_id(
                    f"{data[CONF_SERVICE_TYPE]}:{','.join(codes)}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data["location_name"], data=data)
        if self._setup_data[CONF_SERVICE_TYPE] == "train":
            # Show each physical station once; custom codes permit either platform.
            choices = {}
            for code, name in STATION_CODE_MAP.items():
                choices.setdefault(name, code)
            location_selector = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=code,
                            label=f"{name} ({'/'.join(station_codes(code))})",
                        )
                        for name, code in sorted(choices.items())
                    ],
                    custom_value=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
            schema = vol.Schema(
                {
                    vol.Required(CONF_ID): location_selector,
                }
            )
        else:
            schema = vol.Schema({vol.Required(CONF_ID): str})
        return self.async_show_form(
            step_id="location", data_schema=schema, errors=errors
        )

    async def async_step_reconfigure(self, user_input=None):
        return await self._credentials("reconfigure", user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._credentials("reauth_confirm", user_input)

    async def _credentials(self, step_id, user_input):
        errors = {}
        entry = (
            self._get_reauth_entry()
            if step_id == "reauth_confirm"
            else self._get_reconfigure_entry()
        )
        if user_input is not None:
            try:
                data = await validate_location(self.hass, {**entry.data, **user_input})
            except APIAuthError:
                errors["base"] = "invalid_auth"
            except APIConnectionError:
                errors["base"] = "cannot_connect"
            except InvalidLocation:
                errors["base"] = "invalid_location"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=data,
                    reason="reauth_successful"
                    if step_id == "reauth_confirm"
                    else "reconfigure_successful",
                )
        return self.async_show_form(
            step_id=step_id, data_schema=KEY_SCHEMA, errors=errors
        )


class WmataOptionsFlow(OptionsFlow):
    """Manage named journeys without duplicating the station's polling."""

    async def async_step_init(self, user_input=None):
        if self.config_entry.data[CONF_SERVICE_TYPE] == "map":
            return await self.async_step_settings(user_input)
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "add_journey", "edit_journey", "remove_journey"],
        )

    def _save(self, **updates):
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **updates}
        )

    async def async_step_settings(self, user_input=None):
        if user_input is not None:
            return self._save(**user_input)
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=15, max=300)),
                }
            ),
        )

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
