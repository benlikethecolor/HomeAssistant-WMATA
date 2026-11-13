"""Serve and load the card bundled with the integration."""

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig

from .const import CARD_VERSION

CARD_PATH = "/wmata/wmata-station-card.js"


async def async_setup_card(hass):
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_PATH,
                str(Path(__file__).parent / "www" / "wmata-station-card.js"),
                False,
            ),
            StaticPathConfig(
                "/wmata/vendor", str(Path(__file__).parent / "www" / "vendor"), True
            ),
            StaticPathConfig(
                "/wmata/geo_routes.json",
                str(Path(__file__).parent / "www" / "geo_routes.json"),
                False,
            ),
            StaticPathConfig(
                "/wmata/system-map.png",
                str(Path(__file__).parent / "www" / "system-map.png"),
                True,
            ),
        ]
    )
    add_extra_js_url(hass, f"{CARD_PATH}?v={CARD_VERSION}")
