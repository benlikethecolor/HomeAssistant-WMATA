"""config flow for wmata integration"""


from __future__ import annotations
from .const import DOMAIN
from .coordinator import APIAuthError, WmataCoordinator
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_API_KEY, CONF_ID, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from typing import Any
import logging
import voluptuous as vol


_LOGGER = logging.getLogger(__name__)

# Add a constant for the type of service
CONF_SERVICE_TYPE = "service_type"

# required data during user setup
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_SERVICE_TYPE): vol.In(["bus", "train"]),
        vol.Required(CONF_ID): str
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    called during user setup to validate input
    """
    # TODO: when adding user variables for local bus stop or train station, validate these inputs as well

    # api = WmataCoordinator(hass, data)

    # try:
    #     await api.async_validate_api_key()

    # except APIAuthError as err:
    #     raise InvalidAuth from err

    return {"title": f"WMATA Integration - {data[CONF_ID]}"}


class WmataConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WMATA Integration"""

    VERSION = 1
    _input_data: dict[str, Any]

    async def async_step_configure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""

        # called when you initiate adding an integration via the UI
        errors: dict[str, str] = {}

        if user_input is not None:
            # the form has been filled in and submitted, so process the data provided

            try:
                # validate that the setup data is valid and if not handle errors
                # errors["base"] values must match the values in your strings.json file
                info = await validate_input(self.hass, user_input)

            except CannotConnect:
                errors["base"] = "cannot_connect"

            except InvalidAuth:
                errors["base"] = "invalid_auth"

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                # validation was successful, create a unique id for this instance of your integration and the config entry

                await self.async_set_unique_id(info.get("title"))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        # show initial form
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""

        return await self.async_step_configure(user_input)

    # TODO: this does work, however it does not alter the original, just create another instance
    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""

        self.config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        return await self.async_step_configure(user_input)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
