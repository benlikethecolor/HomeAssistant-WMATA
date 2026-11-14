"""Exercise fresh installation or v1 upgrade from the distributable ZIP."""

import argparse
import asyncio
import json
import logging
import sys
import tempfile
import zipfile
from inspect import signature, unwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from build_release import build

ROOT = Path(__file__).resolve().parents[1]
NEXT_TRAIN = "sensor.wmata_commute_to_union_station_next_train"
TRAVEL_TIME = "sensor.wmata_commute_to_union_station_travel_time"


async def verify(scenario):
    from homeassistant import loader
    from homeassistant.bootstrap import async_from_config_dict
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
    from homeassistant.core import CoreState, HomeAssistant
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
        # The blueprint is imported by hand in real life; here it is copied in.
        blueprint = "blueprints/automation/wmata/time_to_leave.yaml"
        (config_dir / blueprint).parent.mkdir(parents=True)
        (config_dir / blueprint).write_text((ROOT / blueprint).read_text())
        sys.path.insert(0, folder)
        hass = HomeAssistant(folder)
        loader.async_setup(hass)
        fixture = json.loads((ROOT / "tests/fixtures/wmata_api.json").read_text())
        import custom_components.wmata
        from custom_components.wmata.api import APIConnectionError, WmataApi

        assert Path(custom_components.wmata.__file__).is_relative_to(config_dir)

        async def response(client, path, params):
            key = "StationPrediction" if path.startswith("StationPrediction") else path
            if client.headers["api_key"] != "fixture-key":
                raise AssertionError("Unexpected credential in isolated test")
            if path == "Rail.svc/json/jSrcStationToDstStationInfo":
                from custom_components.wmata.directions import ROUTES

                return {
                    "StationToStationInfos": [
                        {"SourceStation": a, "DestinationStation": b, "RailTime": 2}
                        for route in ROUTES.values()
                        for path in (route, tuple(reversed(route)))
                        for a, b in zip(path, path[1:], strict=False)
                    ]
                }
            if path.startswith("StationPrediction"):
                codes = set(path.rsplit("/", 1)[-1].split(","))
                trains = [
                    row
                    for row in fixture["StationPrediction"]["Trains"]
                    if row["LocationCode"] in codes
                ]
                for aliases, location in (
                    ({"B01", "F01"}, "F01"),
                    ({"D03", "F03"}, "F03"),
                ):
                    if codes.intersection(aliases):
                        trains.extend(
                            [
                                {
                                    "Line": "YL",
                                    "LocationCode": location,
                                    "DestinationCode": "C15",
                                    "Min": "6",
                                },
                                {
                                    "Line": "GR",
                                    "LocationCode": location,
                                    "DestinationCode": "F11",
                                    "Min": "3",
                                },
                            ]
                        )
                return {"Trains": trains}
            assert key in fixture, key
            return fixture[key]

        try:
            with (
                patch.object(WmataApi, "_request", response),
                patch.object(
                    WmataApi,
                    "_download_rail_schedule",
                    side_effect=APIConnectionError("Timetable not in fixture"),
                ),
            ):
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
                        "automation": [
                            {
                                "id": "time_to_leave",
                                "alias": "Time to leave",
                                "use_blueprint": {
                                    "path": "wmata/time_to_leave.yaml",
                                    "input": {
                                        "next_train": NEXT_TRAIN,
                                        "travel_time": TRAVEL_TIME,
                                        "lead_time": 4,
                                        "start_time": "00:00:00",
                                        "end_time": "23:59:59",
                                        "weekdays": [
                                            "mon",
                                            "tue",
                                            "wed",
                                            "thu",
                                            "fri",
                                            "sat",
                                            "sun",
                                        ],
                                        "quiet_period": 0,
                                        "actions": [
                                            {
                                                "event": "wmata_time_to_leave",
                                                "event_data": {
                                                    "message": "{{ message }}",
                                                    "minutes": "{{ minutes }}",
                                                },
                                            }
                                        ],
                                    },
                                },
                            }
                        ],
                    },
                    hass,
                )
                assert result is hass, "HA bootstrap failed"
                # Automations only attach their triggers once HA reports started.
                hass.set_state(CoreState.running)
                hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
                await hass.async_block_till_done()
                reminders = []
                hass.bus.async_listen("wmata_time_to_leave", reminders.append)

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
                        (
                            {
                                "credential_source": rail.entry_id,
                                "service_type": service,
                            }
                            if hass.config_entries.async_entries("wmata")
                            else {"api_key": "fixture-key", "service_type": service}
                        ),
                    )
                    if service == "bus":
                        # Leave the ID empty and search around a pin instead.
                        assert flow["step_id"] == "bus_stop"
                        flow = await hass.config_entries.flow.async_configure(
                            flow["flow_id"],
                            {"near": {"latitude": 38.9, "longitude": -77.03}},
                        )
                        assert flow["step_id"] == "nearby_stop", flow
                        choices = [
                            option["value"]
                            for option in flow["data_schema"]
                            .schema["id"]
                            .config["options"]
                        ]
                        assert choices == [location, "1001195", "search_again"]
                    if service == "commute":
                        assert flow["step_id"] == "commute"
                        home, work = location
                        flow = await hass.config_entries.flow.async_configure(
                            flow["flow_id"], {"home": home, "work": work}
                        )
                    elif service != "map":
                        assert flow["step_id"] == (
                            "location" if service == "train" else "nearby_stop"
                        )
                        flow = await hass.config_entries.flow.async_configure(
                            flow["flow_id"], {"id": location}
                        )
                    assert flow["type"] == "create_entry", flow
                    entry = flow["result"]
                    await wait_loaded(entry)
                    return entry

                if scenario == "clean":
                    rail = await add("train", "A01")
                    await add("bus", "1001051")
                    network = await add("map")
                    commute = await add("commute", ("A01", "B03"))
                    assert commute.title == "Metro Center \u2194 Union Station"
                    # Red toward Glenmont in 4 minutes, then three 2 minute hops.
                    travel = hass.states.get(
                        "sensor.wmata_commute_to_union_station_travel_time"
                    )
                    assert travel.state == "10", travel
                    assert travel.attributes["board_type"] == "commute"
                    assert travel.attributes["transfers"] == 0
                    assert (
                        hass.states.get(
                            "sensor.wmata_commute_to_union_station_next_train"
                        ).state
                        == "4"
                    )
                    # Nothing in the fixture leaves Union Station, so no guess is made.
                    assert (
                        hass.states.get(
                            "sensor.wmata_commute_to_metro_center_travel_time"
                        ).state
                        == "unknown"
                    )
                    # The train is 4 minutes out and the blueprint's lead time is
                    # 4, so the reminder goes out once with both numbers in it.
                    await hass.async_block_till_done()
                    assert hass.states.get("automation.time_to_leave") is not None
                    assert len(reminders) == 1, reminders
                    assert reminders[0].data["minutes"] == 4
                    assert " ".join(reminders[0].data["message"].split()) == (
                        "Time to leave. Your train leaves in 4 min and "
                        "you'd arrive in about 10 min."
                    ), reminders[0].data
                    # The fixture reports a Red Line delay, a bus delay on D34 and
                    # a broken elevator at Metro Center.
                    alert = hass.states.get(
                        "binary_sensor.wmata_metro_center_service_alert"
                    )
                    assert alert.state == "on", alert
                    assert [a["lines"] for a in alert.attributes["alerts"]] == [["RD"]]
                    board = hass.states.get("sensor.wmata_metro_center_arrivals")
                    assert len(board.attributes["alerts"]) == 1
                    assert board.attributes["outages"][0]["type"] == "elevator"
                    assert (
                        hass.states.get(
                            "binary_sensor.wmata_fixture_bus_stop_service_alert"
                        ).state
                        == "on"
                    )
                    commute_alert = hass.states.get(
                        "binary_sensor.wmata_commute_service_alert"
                    )
                    assert commute_alert.state == "on", commute_alert
                    assert travel.attributes["alerts"][0]["id"] == "RD-1"
                    assert travel.attributes["last_train"] is False
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
                    trip = await hass.config_entries.options.async_init(rail.entry_id)
                    trip = await hass.config_entries.options.async_configure(
                        trip["flow_id"], {"next_step_id": "add_trip"}
                    )
                    trip = await hass.config_entries.options.async_configure(
                        trip["flow_id"], {"target_station": "C15"}
                    )
                    assert trip["step_id"] == "trip_confirm"
                    assert trip["description_placeholders"]["transfers"] == "1"
                    await hass.config_entries.options.async_configure(
                        trip["flow_id"], {}
                    )
                    await wait_loaded(rail)
                    trip_states = [
                        state
                        for state in hass.states.async_all("sensor")
                        if state.attributes.get("eta_type") == "boarding"
                    ]
                    assert len(trip_states) == 1
                    # Two routes tie on transfers/stops; the fixture has a different
                    # boarding prediction at each legitimate interchange.
                    interchange = trip_states[0].attributes["journey_route"]["legs"][0][
                        "to_name"
                    ]
                    assert (
                        trip_states[0].state
                        == {"Gallery Pl-Chinatown": "4", "L'Enfant Plaza": "7"}[
                            interchange
                        ]
                    )
                    assert trip_states[0].attributes["arrival_count"] == 1
                    assert (
                        trip_states[0].attributes["journey_route"]["destination_name"]
                        == "Huntington"
                    )
                    assert (
                        "Change to Yellow"
                        in trip_states[0].attributes["route_description"]
                    )
                    from custom_components.wmata.websocket import journey_arrivals

                    connection = MagicMock()
                    connection.user.permissions.check_entity.return_value = True
                    await unwrap(journey_arrivals)(
                        hass,
                        connection,
                        {"id": 99, "entity_id": trip_states[0].entity_id},
                    )
                    legs = connection.send_result.call_args.args[1]["legs"]
                    assert len(legs) == 2 and all(leg["available"] for leg in legs)
                    assert len(legs[1]["arrivals"]) == 1
                    assert legs[1]["arrivals"][0]["minutes"] == 6
                    assert legs[1]["arrivals"][0]["line"] == "YL"
                    assert all(leg["ride_minutes"] > 0 for leg in legs)
                    from custom_components.wmata.websocket import (
                        plan_trip,
                        planner_stations,
                    )

                    map_state = next(
                        state
                        for state in hass.states.async_all("sensor")
                        if state.attributes.get("paths")
                    )
                    count_before = len(hass.config_entries.async_entries("wmata"))
                    await unwrap(planner_stations)(
                        hass, connection, {"id": 100, "entity_id": map_state.entity_id}
                    )
                    assert any(
                        station["name"] == "Metro Center"
                        for station in connection.send_result.call_args.args[1][
                            "stations"
                        ]
                    )
                    await unwrap(plan_trip)(
                        hass,
                        connection,
                        {
                            "id": 101,
                            "entity_id": map_state.entity_id,
                            "origin": "A01",
                            "destination": "B03",
                        },
                    )
                    preview = connection.send_result.call_args.args[1]
                    assert preview["scheduled_ride_minutes"] > 0
                    assert preview["legs"][0]["arrivals"][0]["minutes"] == 4
                    assert (
                        len(hass.config_entries.async_entries("wmata")) == count_before
                    )
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
                        **(
                            {"subentries_data": []}
                            if "subentries_data" in signature(ConfigEntry).parameters
                            else {}
                        ),
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
                    retained_board = registry.async_get_or_create(
                        "sensor",
                        "wmata",
                        "wmata_train_a01_board",
                        config_entry=rail,
                        suggested_object_id="wmata_a01_arrivals",
                    )
                    assert await hass.config_entries.async_setup(rail.entry_id)
                    await wait_loaded(rail)
                    assert hass.states.get(retained_board.entity_id) is not None
                    assert rail.version == 2
                    assert rail.data["api_key"] == "fixture-key"
                    assert rail.options["scan_interval"] == 60
                    assert "prediction_count" not in rail.options
                    assert registry.async_get(legacy.entity_id) is None

                if scenario == "clean":
                    # Move the commute's work station through Reconfigure. The old
                    # sensors go and new ones appear on the same entry.
                    moved = await hass.config_entries.flow.async_init(
                        "wmata",
                        context={"source": "reconfigure", "entry_id": commute.entry_id},
                    )
                    assert moved["step_id"] == "reconfigure", moved
                    moved = await hass.config_entries.flow.async_configure(
                        moved["flow_id"], {"home": "A01", "work": "A02"}
                    )
                    assert moved["reason"] == "reconfigure_successful", moved
                    await wait_loaded(commute)
                    assert commute.title == "Metro Center \u2194 Farragut North"
                    assert commute.unique_id == "commute:A01:A02"
                    assert (
                        hass.states.get(
                            "sensor.wmata_commute_to_union_station_travel_time"
                        )
                        is None
                    )
                    assert (
                        hass.states.get(
                            "sensor.wmata_commute_to_farragut_north_travel_time"
                        )
                        is not None
                    )
                    assert (
                        len(
                            device_registry.async_entries_for_config_entry(
                                device_registry.async_get(hass), commute.entry_id
                            )
                        )
                        == 1
                    )
                registry = entity_registry.async_get(hass)
                board_id = (
                    "sensor.wmata_metro_center_arrivals"
                    if scenario == "clean"
                    else retained_board.entity_id
                )
                assert hass.states.get(board_id).state == "4"
                assert hass.states.get(board_id).attributes["arrival_count"] == 2
                if scenario == "clean":
                    entities = entity_registry.async_entries_for_config_entry(
                        registry, rail.entry_id
                    )
                    eastbound = next(
                        e
                        for e in entities
                        if e.unique_id.endswith("journey_line_OR_eastbound")
                    )
                    due = next(
                        e for e in entities if e.unique_id.endswith("board_due_soon")
                    )
                    assert eastbound.disabled_by is not None
                    assert due.disabled_by is not None
                    assert hass.states.get(eastbound.entity_id) is None
                    registry.async_update_entity(eastbound.entity_id, disabled_by=None)
                    registry.async_update_entity(due.entity_id, disabled_by=None)
                    await hass.config_entries.async_reload(rail.entry_id)
                    await wait_loaded(rail)
                    assert hass.states.get(eastbound.entity_id).state == "7"
                    assert hass.states.get(due.entity_id).state == "on"
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
