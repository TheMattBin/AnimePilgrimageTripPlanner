"""Tests for FastAPI endpoints (/api/health, /api/plan, /api/scene/analyze, /api/plan/from-image)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx

from anime_pilgrimage.api import create_app
from anime_pilgrimage.config import Settings
from anime_pilgrimage.models import (
    Coordinates,
    PilgrimageLocation,
    SceneAnalysis,
)
from anime_pilgrimage.planner import AnimePilgrimagePlanner

_PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png"


async def test_api_health_and_text_plan():
    settings = Settings(openrouter_api_key="")
    async with AnimePilgrimagePlanner(settings=settings) as planner:
        planner.crawler.crawl_anime_locations = AsyncMock(
            return_value=[
                PilgrimageLocation(
                    name="Suga Shrine",
                    japanese_name="須賀神社",
                    anime_title="Your Name",
                    city="Shinjuku",
                    prefecture="Tokyo",
                    coordinates=Coordinates(lat=35.6852, lng=139.7219),
                    source_url="https://example.com/suga",
                )
            ]
        )
        app = create_app(settings=settings, planner=planner)
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                health = await client.get("/api/health")
                assert health.status_code == 200
                assert health.json()["status"] == "ok"

                plan_res = await client.post(
                    "/api/plan",
                    json={"query": "Plan a 1-day Your Name trip in Tokyo"},
                )
                assert plan_res.status_code == 200
                body = plan_res.json()
                assert body["response_type"] == "itinerary"
                assert body["travel_plan"]["total_locations"] == 1


async def test_api_scene_analyze_validates_uploads_and_returns_scene():
    fake_llm = AsyncMock()
    fake_llm.is_configured = True
    fake_llm.analyze_image.return_value = SceneAnalysis(
        identified_anime="Bocchi the Rock!",
        japanese_title="ぼっち・ざ・ろっく！",
        confidence=0.91,
        landmark_guess="Shimokitazawa Shelter",
        japanese_landmark="下北沢SHELTER",
        city_or_region="Setagaya, Tokyo",
        visual_clues=["live house stairs", "brick entrance"],
        camera_and_framing_tips="Capture from across the street facing the stairwell.",
        suggested_search_queries=["ぼっち・ざ・ろっく 下北沢SHELTER 聖地巡礼"],
    )

    settings = Settings(openrouter_api_key="sk-or-test")
    async with AnimePilgrimagePlanner(settings=settings, llm_client=fake_llm) as planner:
        app = create_app(settings=settings, planner=planner)
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                # Bad file type returns 400
                bad = await client.post(
                    "/api/scene/analyze",
                    files={"image": ("note.txt", b"plain text", "text/plain")},
                )
                assert bad.status_code == 400

                # Valid PNG returns SceneAnalysis
                ok = await client.post(
                    "/api/scene/analyze",
                    files={"image": ("scene.png", _PNG_BYTES, "image/png")},
                    data={"hint": "Shimokitazawa"},
                )
                assert ok.status_code == 200
                payload = ok.json()
                assert payload["identified_anime"] == "Bocchi the Rock!"
                assert payload["landmark_guess"] == "Shimokitazawa Shelter"
