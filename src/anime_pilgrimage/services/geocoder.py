"""Real async geocoding via OpenStreetMap Nominatim + Photon with SQLite caching."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from pathlib import Path

import httpx
from pydantic import BaseModel

from anime_pilgrimage.config import Settings, get_settings
from anime_pilgrimage.models import Coordinates, PilgrimageLocation

logger = logging.getLogger(__name__)

_HIT_CACHE_TTL_SECONDS = 90 * 24 * 3600  # 90 days for verified hits
_MISS_CACHE_TTL_SECONDS = 24 * 3600  # 24 hours for definitive misses (never outages)
_JAPAN_BOUNDS = (20.0, 46.5, 122.0, 154.0)  # (min_lat, max_lat, min_lng, max_lng)
_PLACEHOLDER_EMAILS = {"your_email@example.com", "example@example.com", "user@example.com"}


class _GeocoderProviderError(RuntimeError):
    """Raised on transient HTTP/network errors so outages are never cached as misses."""


class GeocodeResult(BaseModel):
    """Normalized geocoding output."""

    coordinates: Coordinates
    display_name: str = ""
    city: str = ""
    prefecture: str = ""
    provider: str = "nominatim"


class GeocoderService:
    """Rate-limited, cached geocoder backed by OSM Nominatim with Photon fallback."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    PHOTON_URL = "https://photon.komoot.io/api/"

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
        cache_path: Path | None = None,
        min_request_interval: float = 1.05,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client
        self._owns_client = http_client is None
        self._cache_path = cache_path or self.settings.cache_db_path
        self._min_interval = min_request_interval
        self._rate_lock = asyncio.Lock()
        self._last_nominatim_ts = 0.0
        self._init_cache()

    def _init_cache(self) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._cache_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS geocode_cache (
                    query_key TEXT PRIMARY KEY,
                    payload TEXT,
                    updated_at REAL NOT NULL
                )
                """
            )

    def _get_cached(self, query_key: str) -> tuple[bool, GeocodeResult | None]:
        with sqlite3.connect(self._cache_path) as conn:
            row = conn.execute(
                "SELECT payload, updated_at FROM geocode_cache WHERE query_key = ?",
                (query_key,),
            ).fetchone()
        if not row:
            return False, None
        payload, updated_at = row
        ttl = _MISS_CACHE_TTL_SECONDS if payload is None else _HIT_CACHE_TTL_SECONDS
        if time.time() - updated_at > ttl:
            return False, None
        if payload is None:
            return True, None
        try:
            return True, GeocodeResult.model_validate_json(payload)
        except Exception:
            return False, None

    def _set_cached(self, query_key: str, result: GeocodeResult | None) -> None:
        payload = result.model_dump_json() if result is not None else None
        with sqlite3.connect(self._cache_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO geocode_cache (query_key, payload, updated_at)
                VALUES (?, ?, ?)
                """,
                (query_key, payload, time.time()),
            )

    def build_user_agent(self) -> str:
        """Build a Nominatim-compliant User-Agent without sending placeholder emails."""
        user_agent = self.settings.nominatim_user_agent.strip() or "AnimePilgrimageTripPlanner/0.2"
        email = self.settings.nominatim_email.strip()
        if email and "@" in email and email.lower() not in _PLACEHOLDER_EMAILS:
            return f"{user_agent} ({email})"
        return user_agent

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=12.0,
                headers={"User-Agent": self.build_user_agent(), "Accept-Language": "en,ja"},
            )
        return self._http_client

    @staticmethod
    def _is_in_japan(lat: float, lng: float) -> bool:
        min_lat, max_lat, min_lng, max_lng = _JAPAN_BOUNDS
        return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng

    async def _query_nominatim(
        self, query: str, *, prefer_japan: bool = True
    ) -> GeocodeResult | None:
        async with self._rate_lock:
            elapsed = time.monotonic() - self._last_nominatim_ts
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_nominatim_ts = time.monotonic()

            client = await self._get_client()
            params: dict[str, str | int] = {
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 3,
            }
            if prefer_japan:
                params["countrycodes"] = "jp"

            response = await client.get(self.NOMINATIM_URL, params=params)
            if response.status_code != 200:
                raise _GeocoderProviderError(
                    f"Nominatim HTTP {response.status_code} for {query!r}"
                )

            items = response.json()
            if not items:
                return None

            best = items[0]
            lat = float(best["lat"])
            lng = float(best["lon"])
            if prefer_japan and not self._is_in_japan(lat, lng):
                return None

            address = best.get("address") or {}
            city = (
                address.get("city")
                or address.get("town")
                or address.get("village")
                or address.get("suburb")
                or address.get("city_district")
                or ""
            )
            prefecture = address.get("state") or address.get("province") or ""

            return GeocodeResult(
                coordinates=Coordinates(lat=lat, lng=lng),
                display_name=best.get("display_name", ""),
                city=city,
                prefecture=prefecture,
                provider="nominatim",
            )

    async def _query_photon(
        self, query: str, *, prefer_japan: bool = True
    ) -> GeocodeResult | None:
        client = await self._get_client()
        params: dict[str, str | int | float] = {"q": query, "limit": 5}
        if prefer_japan:
            params["lat"] = 35.6762
            params["lon"] = 139.6503

        response = await client.get(self.PHOTON_URL, params=params)
        if response.status_code != 200:
            raise _GeocoderProviderError(f"Photon HTTP {response.status_code} for {query!r}")

        features = (response.json() or {}).get("features") or []
        for feature in features:
            coords = (feature.get("geometry") or {}).get("coordinates")
            if not coords or len(coords) < 2:
                continue
            lng, lat = float(coords[0]), float(coords[1])
            props = feature.get("properties") or {}

            if prefer_japan:
                country_code = str(props.get("countrycode") or "").strip().upper()
                if country_code:
                    if country_code != "JP":
                        continue
                elif not self._is_in_japan(lat, lng):
                    continue

            return GeocodeResult(
                coordinates=Coordinates(lat=lat, lng=lng),
                display_name=", ".join(
                    p
                    for p in [props.get("name"), props.get("city"), props.get("state")]
                    if p
                ),
                city=props.get("city") or props.get("district") or "",
                prefecture=props.get("state") or "",
                provider="photon",
            )
        return None

    async def geocode(self, query: str, *, prefer_japan: bool = True) -> GeocodeResult | None:
        """Geocode a query string with cache and Nominatim -> Photon fallback.

        Transient provider errors (429/5xx/timeouts) are logged and NEVER cached as misses.
        """
        cleaned = " ".join(query.split()).strip()
        if not cleaned:
            return None

        cache_key = f"{'jp:' if prefer_japan else 'any:'}{cleaned.lower()}"
        found, cached = self._get_cached(cache_key)
        if found:
            return cached

        result: GeocodeResult | None = None
        provider_failed = False

        try:
            result = await self._query_nominatim(cleaned, prefer_japan=prefer_japan)
        except Exception as exc:
            provider_failed = True
            logger.warning(
                "Nominatim error for %r (%s: %r)", cleaned, type(exc).__name__, exc
            )

        if result is None:
            try:
                result = await self._query_photon(cleaned, prefer_japan=prefer_japan)
            except Exception as exc:
                provider_failed = True
                logger.warning(
                    "Photon error for %r (%s: %r)", cleaned, type(exc).__name__, exc
                )

        # Cache hits always; cache misses ONLY when both providers answered cleanly without error
        if result is not None or not provider_failed:
            self._set_cached(cache_key, result)

        return result

    async def geocode_location(
        self, location: PilgrimageLocation, *, prefer_japan: bool = True
    ) -> PilgrimageLocation:
        """Attempt up to 3 high-signal queries to attach real coordinates to a location."""
        if location.coordinates is not None:
            return location

        candidates: list[str] = []
        if location.japanese_name:
            if location.city:
                candidates.append(f"{location.japanese_name} {location.city}")
            else:
                candidates.append(location.japanese_name)

        if location.real_world_address:
            candidates.append(location.real_world_address)
        elif location.city or location.prefecture:
            region = ", ".join(p for p in (location.city, location.prefecture) if p)
            candidates.append(f"{location.name}, {region}, Japan")

        candidates.append(f"{location.name}, Japan" if prefer_japan else location.name)

        seen: set[str] = set()
        unique_candidates: list[str] = []
        for query in candidates:
            norm = query.strip().lower()
            if norm and norm not in seen:
                seen.add(norm)
                unique_candidates.append(query)

        for query in unique_candidates[:3]:
            result = await self.geocode(query, prefer_japan=prefer_japan)
            if result is not None:
                updates: dict[str, object] = {"coordinates": result.coordinates}
                if not location.real_world_address and result.display_name:
                    updates["real_world_address"] = result.display_name
                if not location.city and result.city:
                    updates["city"] = result.city
                if not location.prefecture and result.prefecture:
                    updates["prefecture"] = result.prefecture
                return location.model_copy(update=updates)

        return location

    async def aclose(self) -> None:
        if self._http_client is not None and self._owns_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> GeocoderService:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()
