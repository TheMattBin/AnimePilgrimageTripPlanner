"""Tests for GeocoderService (Nominatim, Photon fallback, outage caching, JP filtering, UA)."""

from __future__ import annotations

from pathlib import Path

import httpx

from anime_pilgrimage.config import Settings
from anime_pilgrimage.models import PilgrimageLocation
from anime_pilgrimage.services.geocoder import GeocoderService


async def test_geocoder_nominatim_and_cache(tmp_path: Path):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if "nominatim.openstreetmap.org" in str(request.url):
            return httpx.Response(
                200,
                json=[
                    {
                        "lat": "35.6852",
                        "lon": "139.7219",
                        "display_name": "須賀神社, 四谷, 新宿区, 東京都, Japan",
                        "address": {"city": "Shinjuku", "state": "Tokyo"},
                    }
                ],
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        geocoder = GeocoderService(
            http_client=client,
            cache_path=tmp_path / "cache.sqlite3",
            min_request_interval=0.0,
        )
        loc = PilgrimageLocation(
            name="Suga Shrine",
            japanese_name="須賀神社",
            anime_title="Your Name",
            city="Shinjuku",
        )
        enriched = await geocoder.geocode_location(loc)
        assert enriched.coordinates is not None
        assert abs(enriched.coordinates.lat - 35.6852) < 1e-4
        assert enriched.prefecture == "Tokyo"
        assert calls == 1

        # Second call with same query hits SQLite cache
        enriched2 = await geocoder.geocode_location(loc)
        assert enriched2.coordinates == enriched.coordinates
        assert calls == 1


async def test_geocoder_does_not_cache_provider_outages(tmp_path: Path):
    """Regression test for Bug 2: 503/429 outages must not be cached as misses."""
    outage = True

    def handler(request: httpx.Request) -> httpx.Response:
        if outage:
            return httpx.Response(503)
        if "nominatim.openstreetmap.org" in str(request.url):
            return httpx.Response(
                200,
                json=[
                    {
                        "lat": "35.6852",
                        "lon": "139.7219",
                        "display_name": "須賀神社, 新宿区, 東京都",
                        "address": {"city": "Shinjuku", "state": "Tokyo"},
                    }
                ],
            )
        return httpx.Response(200, json={"features": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        geocoder = GeocoderService(
            http_client=client,
            cache_path=tmp_path / "cache.sqlite3",
            min_request_interval=0.0,
        )
        first = await geocoder.geocode("須賀神社 新宿")
        assert first is None

        # After recovery, the same query must succeed instead of returning a cached None
        outage = False
        second = await geocoder.geocode("須賀神社 新宿")
        assert second is not None
        assert abs(second.coordinates.lat - 35.6852) < 1e-4


async def test_geocoder_photon_rejects_non_japan_countrycode(tmp_path: Path):
    """Photon fallback must check countrycode == JP, rejecting Korea/Russia inside the bounding box."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "nominatim.openstreetmap.org" in str(request.url):
            return httpx.Response(200, json=[])
        if "photon.komoot.io" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "features": [
                        {
                            # Seoul falls inside Japan's lat/lng rectangle but has countrycode KR
                            "geometry": {"coordinates": [126.9780, 37.5665]},
                            "properties": {
                                "name": "Some Shrine",
                                "city": "Seoul",
                                "countrycode": "KR",
                            },
                        },
                        {
                            "geometry": {"coordinates": [137.2522, 36.1461]},
                            "properties": {
                                "name": "Hida-Furukawa Station",
                                "city": "Hida",
                                "state": "Gifu",
                                "countrycode": "JP",
                            },
                        },
                    ]
                },
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        geocoder = GeocoderService(
            http_client=client,
            cache_path=tmp_path / "cache.sqlite3",
            min_request_interval=0.0,
        )
        res = await geocoder.geocode("Hida-Furukawa Station", prefer_japan=True)
        assert res is not None
        assert res.provider == "photon"
        assert res.city == "Hida"
        assert res.prefecture == "Gifu"


def test_user_agent_excludes_placeholder_email(tmp_path: Path):
    placeholder_settings = Settings(
        nominatim_user_agent="AnimePilgrimageTripPlanner/0.2",
        nominatim_email="your_email@example.com",
    )
    g1 = GeocoderService(settings=placeholder_settings, cache_path=tmp_path / "c1.sqlite3")
    assert "your_email@example.com" not in g1.build_user_agent()

    real_settings = Settings(
        nominatim_user_agent="AnimePilgrimageTripPlanner/0.2",
        nominatim_email="traveler@real-domain.org",
    )
    g2 = GeocoderService(settings=real_settings, cache_path=tmp_path / "c2.sqlite3")
    assert "traveler@real-domain.org" in g2.build_user_agent()
