"""WMATA rail and bus arrivals."""

from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .const import CONF_JOURNEYS, DOMAIN
from .coordinator import WmataCoordinator
from .frontend import async_setup_card
from .train_map import MapCoordinator
from .websocket import async_register

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR]


async def async_setup(hass, config) -> bool:
    """Register the bundled dashboard card once for this integration."""
    async_register(hass)
    await async_setup_card(hass)
    return True


async def async_migrate_entry(hass, entry) -> bool:
    """Replace numbered slots with a complete board; preserve locations and keys."""
    if entry.version > 2:
        return False
    if entry.version == 1:
        data = {
            k: v
            for k, v in entry.data.items()
            if k not in ("lines", "routes", "prediction_count")
        }
        options = {
            k: v
            for k, v in entry.options.items()
            if k not in ("lines", "routes", "prediction_count")
        }
        options.setdefault(CONF_JOURNEYS, [])
        hass.config_entries.async_update_entry(
            entry, data=data, options=options, version=2
        )
    return True


async def async_setup_entry(hass, entry) -> bool:
    """Load predictions before forwarding platform setup."""
    coordinator = (
        MapCoordinator if entry.data["service_type"] == "map" else WmataCoordinator
    )(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass, entry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
