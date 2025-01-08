"""Integration 101 Template integration using DataUpdateCoordinator."""
from .const import DEFAULT_SCAN_INTERVAL
from .wmata import WmataAPI, APIAuthError, Device, DeviceType
from dataclasses import dataclass
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import logging


_LOGGER = logging.getLogger(__name__)


@dataclass
class WmataAPIData:
    """Class to hold api data"""
    # TODO: modify to update when new data comes in on train distances

    controller_name: str


class WmataCoordinator(DataUpdateCoordinator):
    """My coordinator"""

    data: WmataAPIData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator"""

        # Set variables from values entered in config flow setup
        self.api_key = config_entry.data[CONF_API_KEY]

        # set variables from options.  You need a default here incase options have not been set
        self.poll_interval = DEFAULT_SCAN_INTERVAL # default to 1min

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            update_method=self.async_update_data,
            update_interval=timedelta(seconds=self.poll_interval),
        )

        # initialize your api here
        self.api = WmataAPI(api_key=self.api_key)

    async def async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        
        # TODO: add API call here to get station info
        
        try:
            if not self.api.connected:
                await self.hass.async_add_executor_job(self.api.validate_api_key)
            
            devices = await self.hass.async_add_executor_job(self.api.get_devices)
        
        except APIAuthError as err:
            _LOGGER.error(err)
            raise UpdateFailed(err) from err
        
        except Exception as err:
            # this will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        # what is returned here is stored in self.data by the DataUpdateCoordinator
        return WmataAPIData()
    
    def get_device_by_id(self, device_type: DeviceType, device_id: int) -> Device | None:
        """Return device by device id."""
        # called by the binary sensors and sensors to get their updated data from self.data
        try:
            return [device for device in self.data.devices if device.device_type == device_type and device.device_id == device_id][0]
        
        except IndexError:
            return None