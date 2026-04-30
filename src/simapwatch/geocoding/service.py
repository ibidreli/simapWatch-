"""Geocode award addresses and persist coordinates."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
import urllib.parse
import urllib.request
from typing import Protocol

from simapwatch.repository import SqliteAwardRepository


@dataclass(frozen=True)
class GeocodingResult:
    status: str
    lat: float | None
    lon: float | None


@dataclass(frozen=True)
class GeocodingStats:
    updated_rows: int
    queried_addresses: int
    skipped_rows: int


class Geocoder(Protocol):
    def geocode(self, query: str) -> GeocodingResult:
        ...


class GeoAdminGeocoder:
    """Geocoder using the official Swiss geo.admin.ch SearchServer."""

    def __init__(self, timeout_seconds: int = 20, delay_seconds: float = 0.2):
        self._timeout_seconds = timeout_seconds
        self._delay_seconds = delay_seconds
        self._user_agent = "simapWatch/1.0 (educational project)"

    def geocode(self, query: str) -> GeocodingResult:
        params = urllib.parse.urlencode(
            {
                "searchText": query,
                "type": "locations",
                "origins": "address,zipcode,gazetteer,gg25",
                "limit": 1,
                "sr": 4326,
            }
        )
        request = urllib.request.Request(
            f"https://api3.geo.admin.ch/rest/services/api/SearchServer?{params}",
            headers={"User-Agent": self._user_agent},
        )
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        time.sleep(self._delay_seconds)

        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return GeocodingResult(status="not_found", lat=None, lon=None)

        first = results[0]
        attrs = first.get("attrs") if isinstance(first, dict) else None
        if not isinstance(attrs, dict):
            return GeocodingResult(status="not_found", lat=None, lon=None)

        x = attrs.get("x")
        y = attrs.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return GeocodingResult(status="not_found", lat=None, lon=None)

        # Inference from geo.admin SearchServer with sr=4326: x=longitude, y=latitude.
        return GeocodingResult(status="ok", lat=float(y), lon=float(x))


def geocode_missing_awards(repository: SqliteAwardRepository, geocoder: Geocoder) -> GeocodingStats:
    rows = repository.list_awards()
    updated_rows = 0
    queried_addresses = 0
    skipped_rows = 0
    cache: dict[tuple[str, str], GeocodingResult] = {}

    for row in rows:
        award_row_id = str(row["award_row_id"])
        for side in ("winner", "procurement_office"):
            address = row.get(f"{side}_address")
            if not isinstance(address, str) or not address.strip():
                skipped_rows += 1
                continue

            query = address.strip()
            current_query = row.get(f"{side}_geocode_query")
            current_status = row.get(f"{side}_geocode_status")
            current_lat = row.get(f"{side}_lat")
            current_lon = row.get(f"{side}_lon")

            if current_query == query and current_status == "ok" and current_lat is not None and current_lon is not None:
                skipped_rows += 1
                continue
            if current_query == query and current_status == "not_found":
                skipped_rows += 1
                continue

            cache_key = (side, query)
            if cache_key not in cache:
                cache[cache_key] = geocoder.geocode(query)
                queried_addresses += 1
            result = cache[cache_key]

            repository.update_award_geocoding(
                award_row_id,
                side=side,
                query=query,
                status=result.status,
                lat=result.lat,
                lon=result.lon,
            )
            updated_rows += 1

    return GeocodingStats(
        updated_rows=updated_rows,
        queried_addresses=queried_addresses,
        skipped_rows=skipped_rows,
    )
