"""Asynchronous WMATA API client. Credentials only travel in HTTPS headers."""

from __future__ import annotations

import asyncio
import csv
import math
import re
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import aiohttp

from .const import URL
from .schedules import ZONE, RailSchedule


class APIAuthError(Exception):
    """The API key is invalid or no longer authorized."""


class APIConnectionError(Exception):
    """The API cannot currently provide valid data."""


class InvalidLocation(Exception):
    """The station or stop does not exist."""


@dataclass
class RequestState:
    """Coordinate startup bursts and rate-limit cooldown across locations."""

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    next_request: float = 0
    blocked_until: float = 0
    stations: list[dict[str, Any]] | None = None
    stations_expiry: float = 0
    rail_times: dict[tuple[str, str], float] | None = None
    rail_times_expiry: float = 0
    rail_times_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    schedule: RailSchedule | None = None
    schedule_expiry: float = 0
    schedule_date: str = ""
    schedule_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class WmataApi:
    """Small client sharing Home Assistant's managed HTTP session."""

    def __init__(
        self, session: aiohttp.ClientSession, api_key: str, *, hass=None
    ) -> None:
        self.session = session
        self._hass = hass
        self.headers = {"api_key": api_key}
        if hass is None:
            self._state = RequestState()
        else:
            clients = hass.data.setdefault("wmata_request_state", {})
            digest = sha256(api_key.encode()).hexdigest()
            self._state = clients.setdefault(digest, RequestState())

    async def get(self, path: str, **params: str) -> dict[str, Any]:
        """Request JSON without exposing credentials or response bodies in errors."""
        async with self._state.lock:
            await self._pace()
            return await self._request(path, params)

    async def _pace(self):
        loop = asyncio.get_running_loop()
        if self._state.blocked_until > loop.time():
            raise APIConnectionError("WMATA API rate limit cooldown is active")
        delay = self._state.next_request - loop.time()
        if delay > 0:
            await asyncio.sleep(delay)
        self._state.next_request = loop.time() + 0.6

    def _check_status(self, response):
        if response.status in (401, 403):
            raise APIAuthError("WMATA rejected the API key")
        if response.status == 429:
            try:
                retry_after = float(response.headers.get("Retry-After", "60"))
            except (ValueError, TypeError):
                retry_after = 60
            self._state.blocked_until = asyncio.get_running_loop().time() + max(
                1, min(retry_after, 300)
            )
            raise APIConnectionError("WMATA API rate limit exceeded; retrying later")
        if response.status != 200:
            raise APIConnectionError(f"WMATA returned HTTP {response.status}")

    async def _request(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        try:
            async with self.session.get(
                f"{URL}/{path}",
                headers=self.headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                self._check_status(response)
                data = await response.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise APIConnectionError("Unable to read WMATA API response") from err
        if not isinstance(data, dict):
            raise APIConnectionError("WMATA returned an invalid response")
        return data

    async def standard_routes(self) -> list[dict[str, Any]]:
        return self._items(
            await self.get("TrainPositions/StandardRoutes", contentType="json"),
            "StandardRoutes",
        )

    async def track_circuits(self) -> list[dict[str, Any]]:
        return self._items(
            await self.get("TrainPositions/TrackCircuits", contentType="json"),
            "TrackCircuits",
        )

    async def train_positions(self) -> list[dict[str, Any]]:
        return self._items(
            await self.get("TrainPositions/TrainPositions", contentType="json"),
            "TrainPositions",
        )

    async def validate_service(self, service: str) -> None:
        """Check access to every endpoint required for the selected service."""
        if service in ("train", "commute"):
            await self.stations()
        elif service == "bus":
            self._items(await self.get("Bus.svc/json/jRoutes"), "Routes")
        elif service == "map":
            routes = await self.standard_routes()
            circuits = await self.track_circuits()
            if not routes or not circuits:
                raise APIConnectionError(
                    "WMATA network metadata is temporarily unavailable"
                )
            await self.train_positions()
        else:
            raise InvalidLocation("Unknown WMATA service")

    async def stations(self) -> list[dict[str, Any]]:
        now = asyncio.get_running_loop().time()
        if self._state.stations is None or now >= self._state.stations_expiry:
            stations = self._items(
                await self.get("Rail.svc/json/jStations"), "Stations"
            )
            if any(
                not isinstance(s.get("Code"), str) or not isinstance(s.get("Name"), str)
                for s in stations
            ):
                raise APIConnectionError("WMATA returned an invalid station catalog")
            self._state.stations = stations
            self._state.stations_expiry = now + 3600
        return self._state.stations

    async def trains(self, codes: list[str]) -> list[dict[str, Any]]:
        return self._items(
            await self.get(
                "StationPrediction.svc/json/GetPrediction/" + ",".join(codes)
            ),
            "Trains",
        )

    async def rail_times(self) -> dict[tuple[str, str], float] | None:
        """Share WMATA's scheduled travel times; retry failures after five minutes."""
        async with self._state.rail_times_lock:
            now = asyncio.get_running_loop().time()
            if now < self._state.rail_times_expiry:
                return self._state.rail_times
            self._state.rail_times_expiry = now + 300
            rows = self._items(
                await self.get("Rail.svc/json/jSrcStationToDstStationInfo"),
                "StationToStationInfos",
            )
            times = {
                (row["SourceStation"], row["DestinationStation"]): row["RailTime"]
                for row in rows
                if isinstance(row.get("SourceStation"), str)
                and isinstance(row.get("DestinationStation"), str)
                and type(row.get("RailTime")) in (int, float)
                and math.isfinite(row["RailTime"])
                and 0 < row["RailTime"] <= 240
            }
            if not times:
                raise APIConnectionError("WMATA travel times are unavailable")
            self._state.rail_times = times
            self._state.rail_times_expiry = now + 86400
            return times

    async def _download_rail_schedule(self):
        async with self._state.lock:
            await self._pace()
            try:
                async with self.session.get(
                    f"{URL}/gtfs/rail-gtfs-static.zip",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=40),
                ) as response:
                    self._check_status(response)
                    data = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        data.extend(chunk)
                        if len(data) > 20000000:
                            raise APIConnectionError(
                                "Rail timetable exceeds size limit"
                            )
                    return bytes(data)
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                raise APIConnectionError("Unable to download rail timetable") from err

    async def rail_schedule(self):
        """Cache official schedules per subscription; parsing never blocks HA."""
        async with self._state.schedule_lock:
            now = asyncio.get_running_loop().time()
            day = datetime.now(UTC).astimezone(ZONE).date().isoformat()
            if now < self._state.schedule_expiry and self._state.schedule_date == day:
                return self._state.schedule
            self._state.schedule_date = day
            self._state.schedule_expiry = now + 300
            content = await self._download_rail_schedule()
            try:
                if self._hass is not None:
                    schedule = await self._hass.async_add_executor_job(
                        RailSchedule, content
                    )
                else:
                    schedule = await asyncio.to_thread(RailSchedule, content)
            except (
                ValueError,
                KeyError,
                OSError,
                UnicodeError,
                zipfile.BadZipFile,
                csv.Error,
            ) as err:
                raise APIConnectionError("Unable to read rail timetable") from err
            self._state.schedule = schedule
            self._state.schedule_expiry = now + 21600
            return schedule

    async def buses(self, stop: str) -> list[dict[str, Any]]:
        return self._items(
            await self.get("NextBusService.svc/json/jPredictions", StopID=stop),
            "Predictions",
        )

    async def nearby_stops(
        self, latitude: float, longitude: float, radius: int
    ) -> list[dict[str, Any]]:
        """List bus stops within a radius in metres, dropping unusable rows."""
        stops = self._items(
            await self.get(
                "Bus.svc/json/jStops",
                Lat=f"{latitude:.4f}",
                Lon=f"{longitude:.4f}",
                Radius=str(radius),
            ),
            "Stops",
        )
        return [
            stop
            for stop in stops
            if isinstance(stop.get("StopID"), str)
            and re.fullmatch(r"\d{7}", stop["StopID"])
            and isinstance(stop.get("Name"), str)
            and all(
                type(stop.get(key)) in (int, float) and math.isfinite(stop[key])
                for key in ("Lat", "Lon")
            )
        ]

    async def stop_name(self, stop: str) -> str:
        data = await self.get("Bus.svc/json/jStopSchedule", StopID=stop)
        info = data.get("Stop")
        if not isinstance(info, dict) or not info.get("Name"):
            raise InvalidLocation("Unknown bus stop")
        return str(info["Name"])

    @staticmethod
    def _items(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
        items = data.get(key)
        if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
            raise APIConnectionError("WMATA returned an invalid prediction list")
        return items
