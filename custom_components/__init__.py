"""The wmata integration."""

from __future__ import annotations
from .const import DOMAIN
from .coordinator import WmataCoordinator
from collections.abc import Callable
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import logging

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: DataUpdateCoordinator
    cancel_update_listener: Callable


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up WMATA Integration from a config entry."""

    # data location
    hass.data.setdefault(DOMAIN, {})

    # initialize the coordinator that manages data updates
    coordinator = WmataCoordinator(hass, config_entry)

    # initial data load from API
    # async_config_entry_first_refresh -> no errors logged on failure
    await coordinator.async_config_entry_first_refresh()

    # test to see if api initialized correctly, else raise ConfigNotReady to make HA retry setup
    if not coordinator.api.connected:
        raise ConfigEntryNotReady

    # initialize a listener for config flow options changes
    # see config_flow for defining an options setting that shows up as configure on the integration
    cancel_update_listener = config_entry.add_update_listener(_async_update_listener)

    # add the coordinator and update listener to hass data to make accessible throughout your integration
    # note: this will change on HA2024.6 to save on the config entry. # TODO add the 2024.6 update
    hass.data[DOMAIN][config_entry.entry_id] = RuntimeData(coordinator, cancel_update_listener)

    # setup platforms (based on the list of entity types in PLATFORMS defined above)
    # this calls the async_setup method in each of your entity type files
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry):
    """Handle config options update."""
    # reload the integration when the options change.
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_remove_config_entry_device(hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry) -> bool:
    """Delete device if selected from UI."""
    # adding this function shows the delete device option in the UI
    # you may need to do some checks here before allowing devices to be removed
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # this is called when you remove your integration or shutdown HA
    # if you have created any custom services, they need to be removed here too

    # remove the config options update listener
    hass.data[DOMAIN][config_entry.entry_id].cancel_update_listener()

    # unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    # remove the config entry from the hass data object
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    # return that unloading was successful
    return unload_ok