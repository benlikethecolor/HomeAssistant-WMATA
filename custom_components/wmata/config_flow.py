"""config flow for wmata integration"""


from __future__ import annotations
from .const import DOMAIN
from .coordinator import WmataAPI, APIAuthError
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from typing import Any
import logging
import voluptuous as vol


_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY, description={"suggested_value": "1234567890"}): str
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    called during user setup to validate input
    """
    
    # TODO: when adding user variables for local bus stop or train station, validate these inputs as well
    
    api = WmataAPI(data[CONF_API_KEY])
    
    try:
        await hass.async_add_executor_job(api.validate_api_key())
    
    except APIAuthError as err:
        raise InvalidAuth from err
    
    return {"title": f"WMATA Integration - {data[CONF_HOST]}"}


class WmataConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WMATA Integration"""

    VERSION = 1
    _input_data: dict[str, Any]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""
        
        # this method displays a reconfigure option in the integration and is different to options
        # it can be used to reconfigure any of the data submitted when first installed
        # this is optional and can be removed if you do not want to allow reconfiguration
        errors: dict[str, str] = {}
        
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if user_input is not None:
            try:
                user_input[CONF_HOST] = config_entry.data[CONF_HOST]
                await validate_input(self.hass, user_input)
            
            except CannotConnect:
                errors["base"] = "cannot_connect"
            
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            
            else:
                return self.async_update_reload_and_abort(
                    config_entry,
                    unique_id=config_entry.unique_id,
                    data={**config_entry.data, **user_input},
                    reason="reconfigure_successful",
                )
        
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=config_entry.data[CONF_USERNAME]
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""