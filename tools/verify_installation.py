"""Exercise fresh installation or v1 upgrade from the distributable ZIP."""

import argparse
import asyncio
import json
import logging
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from build_release import build

ROOT = Path(__file__).resolve().parents[1]


async def verify(scenario):
    from homeassistant import loader
    from homeassistant.bootstrap import async_from_config_dict
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import device_registry, entity_registry

    logging.basicConfig(level=logging.WARNING)
    with tempfile.TemporaryDirectory(prefix="wmata-install-") as folder:
        config_dir = Path(folder)
        archive = build(config_dir / "wmata.zip")
        with zipfile.ZipFile(archive) as package:
            assert all(
                name.startswith("custom_components/wmata/")
                for name in package.namelist()
            )
            package.extractall(config_dir)
        sys.path.insert(0, folder)
        hass = HomeAssistant(folder)
        loader.async_setup(hass)
        fixture = json.loads((ROOT / "tests/fixtures/wmata_api.json").read_text())
        import custom_components.wmata
        from custom_components.wmata.api import WmataApi

        assert Path(custom_components.wmata.__file__).is_relative_to(config_dir)

        async def response(client, path, params):
            key = "StationPrediction" if path.startswith("StationPrediction") else path
            if client.headers["api_key"] != "fixture-key":
                raise AssertionError("Unexpected credential in isolated test")
            assert key in fixture, key
            return fixture[key]

        try:
            with patch.object(WmataApi, "_request", response):
                result = await async_from_config_dict(
                    {
                        "homeassistant": {
                            "latitude": 38.9,
                            "longitude": -77.0,
                            "elevation": 0,
                            "unit_system": "us_customary",
                            "time_zone": "America/New_York",
                        },
                        "http": {"server_host": "127.0.0.1", "server_port": 8123},
                        "frontend": {},
                        "lovelace": {"mode": "storage"},
                    },
                    hass,
                )
                assert result is hass, "HA bootstrap failed"

                async def wait_loaded(entry):
                    await hass.async_block_till_done()
                    assert entry.state.value == "loaded", (entry.state, entry.reason)

                async def add(service, location=None):
                    flow = await hass.config_entries.flow.async_init(
                        "wmata", context={"source": "user"}
                    )
                    assert flow["step_id"] == "user"
                    flow = await hass.config_entries.flow.async_configure(
                        flow["flow_id"],
                        {"api_key": "fixture-key", "service_type": service},
                    )
                    if service != "map":
                        assert flow["step_id"] == "location"
                        flow = await hass.config_entries.flow.async_configure(
                            flow["flow_id"], {"id": location}
                        )
                    assert flow["type"] == "create_entry", flow
                    entry = flow["result"]
                    await wait_loaded(entry)
                    return entry

                if scenario == "clean":
                    rail = await add("train", "a01")
                    await add("bus", "1001051")
                    network = await add("map")
                    options = await hass.config_entries.options.async_init(
                        rail.entry_id
                    )
                    options = await hass.config_entries.options.async_configure(
                        options["flow_id"], {"next_step_id": "add_journey"}
                    )
                    options = await hass.config_entries.options.async_configure(
                        options["flow_id"],
                        {
                            "name": "Red to Glenmont",
                            "lines": ["RD"],
                            "destinations": ["B11"],
                            "rail_direction": "any",
                        },
                    )
                    assert options["type"] == "create_entry"
                    await wait_loaded(rail)
                    assert len(rail.options["journeys"]) == 1
                    map_options = await hass.config_entries.options.async_init(
                        network.entry_id
                    )
                    assert map_options["step_id"] == "settings"
                    await hass.config_entries.options.async_configure(
                        map_options["flow_id"], {"scan_interval": 60}
                    )
                    await wait_loaded(network)
                    assert network.runtime_data.update_interval.total_seconds() == 60
                    assert network.runtime_data.data["trains"][0]["geo_point"]
                    assert (
                        network.runtime_data.data["trains"][1]["position_type"]
                        == "nearby"
                    )
                    assert network.runtime_data.data["trains"][2]["geo_point"] is None
                else:
                    rail = ConfigEntry(
                        domain="wmata",
                        title="Old Metro Center",
                        data={
                            "api_key": "fixture-key",
                            "service_type": "train",
                            "id": "A01",
                            "lines": ["RD"],
                        },
                        options={
                            "prediction_count": 6,
                            "lines": ["RD"],
                            "scan_interval": 60,
                        },
                        version=1,
                        minor_version=1,
                        source="user",
                        unique_id="A01",
                        discovery_keys={},
                        subentries_data=[],
                    )
                    with patch.object(
                        hass.config_entries,
                        "async_setup",
                        AsyncMock(return_value=False),
                    ):
                        await hass.config_entries.async_add(rail)
                    registry = entity_registry.async_get(hass)
                    legacy = registry.async_get_or_create(
                        "sensor",
                        "wmata",
                        "wmata_a01_train_1",
                        config_entry=rail,
                        suggested_object_id="old_metro_train",
                    )
                    assert await hass.config_entries.async_setup(rail.entry_id)
                    await wait_loaded(rail)
                    assert rail.version == 2
                    assert rail.data["api_key"] == "fixture-key"
                    assert rail.options["scan_interval"] == 60
                    assert "prediction_count" not in rail.options
                    assert registry.async_get(legacy.entity_id) is None

                registry = entity_registry.async_get(hass)
                assert hass.states.get("sensor.wmata_a01_arrivals").state == "4"
                assert (
                    hass.states.get("sensor.wmata_a01_arrivals").attributes[
                        "arrival_count"
                    ]
                    == 2
                )
                devices = device_registry.async_get(hass)
                assert any(
                    device.manufacturer == "WMATA"
                    for device in device_registry.async_entries_for_config_entry(
                        devices, rail.entry_id
                    )
                )
                from custom_components.wmata.diagnostics import (
                    async_get_config_entry_diagnostics,
                )

                diagnostics = await async_get_config_entry_diagnostics(hass, rail)
                assert diagnostics["coordinator_loaded"]
                assert diagnostics["arrivals"]["count"] == 2
                assert "fixture-key" not in json.dumps(diagnostics)
                from homeassistant.components import frontend

                modules = hass.data[frontend.DATA_EXTRA_MODULE_URL].urls
                assert any(
                    "/wmata/wmata-station-card.js?v=" in module for module in modules
                )
                # Inspect the registered HTTP routes without creating a second web server.
                paths = [str(route.resource) for route in hass.http.app.router.routes()]
                assert any("/wmata/geo_routes.json" in path for path in paths)
                assert any("/wmata/vendor" in path for path in paths)
                for entry in list(hass.config_entries.async_entries("wmata")):
                    assert await hass.config_entries.async_unload(entry.entry_id)
                    assert await hass.config_entries.async_setup(entry.entry_id)
                    await wait_loaded(entry)
                print(
                    json.dumps(
                        {
                            "scenario": scenario,
                            "result": "passed",
                            "archive_files": len(zipfile.ZipFile(archive).namelist()),
                            "entities": sum(
                                len(
                                    entity_registry.async_entries_for_config_entry(
                                        registry, entry.entry_id
                                    )
                                )
                                for entry in hass.config_entries.async_entries("wmata")
                            ),
                        }
                    )
                )
        finally:
            await hass.async_stop(force=True)
            sys.path.remove(folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["clean", "upgrade"], required=True)
    asyncio.run(verify(parser.parse_args().scenario))
