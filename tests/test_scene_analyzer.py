"""Tests for SceneAnalyzer VLM validation, encoding, Jikan enrichment, and image pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from anime_pilgrimage.components.scene_analyzer import (
    MAX_IMAGE_BYTES,
    ImageValidationError,
    SceneAnalyzer,
    validate_and_encode_image_bytes,
)
from anime_pilgrimage.config import Settings
from anime_pilgrimage.models import Coordinates, PilgrimageLocation, SceneAnalysis
from anime_pilgrimage.planner import AnimePilgrimagePlanner
from anime_pilgrimage.services.anime_metadata import AnimeMetadata

_PNG_HEADER = b"\x89PNG\r\n\x1a\nfake-png-body"


def test_validate_and_encode_image_bytes_sniffs_magic_and_rejects_bad_files():
    uri = validate_and_encode_image_bytes(_PNG_HEADER)
    assert uri.startswith("data:image/png;base64,")

    with pytest.raises(ImageValidationError, match="empty"):
        validate_and_encode_image_bytes(b"")

    with pytest.raises(ImageValidationError, match="Unsupported image format"):
        validate_and_encode_image_bytes(b"<html>not an image</html>", content_type="text/html")

    with pytest.raises(ImageValidationError, match="maximum allowed size"):
        validate_and_encode_image_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * MAX_IMAGE_BYTES)


async def test_scene_analyzer_enriches_with_jikan_and_builds_queries():
    fake_llm = AsyncMock()
    fake_llm.is_configured = True
    fake_llm.analyze_image.return_value = SceneAnalysis(
        identified_anime="Your Name",
        japanese_title="",
        confidence=0.92,
        landmark_guess="Suga Shrine Staircase",
        japanese_landmark="須賀神社",
        city_or_region="Shinjuku, Tokyo",
        visual_clues=["red handrail", "steep stone stairs", "blue sky"],
        camera_and_framing_tips="Stand near the top looking down the red handrail.",
        suggested_search_queries=["Your Name Suga Shrine real location"],
    )

    fake_meta = AsyncMock()
    fake_meta.lookup.return_value = AnimeMetadata(
        canonical_title="Your Name.",
        japanese_title="君の名は。",
        match_score=1.0,
    )

    analyzer = SceneAnalyzer(llm_client=fake_llm, metadata_service=fake_meta)
    scene = await analyzer.analyze_image(_PNG_HEADER, filename="stairs.png")

    assert scene.identified_anime == "Your Name."
    assert scene.japanese_title == "君の名は。"
    queries = analyzer.build_search_queries(scene)
    assert any("須賀神社" in q for q in queries)


async def test_planner_process_image_query_runs_full_pipeline():
    fake_llm = AsyncMock()
    fake_llm.is_configured = True
    fake_llm.analyze_image.return_value = SceneAnalysis(
        identified_anime="Your Name",
        japanese_title="君の名は。",
        confidence=0.94,
        landmark_guess="Suga Shrine",
        japanese_landmark="須賀神社",
        city_or_region="Tokyo",
        visual_clues=["red handrail", "shrine staircase"],
        suggested_search_queries=["君の名は 須賀神社 聖地巡礼"],
    )
    fake_llm.generate_text.return_value = "Welcome to your Your Name pilgrimage in Tokyo!"

    settings = Settings(openrouter_api_key="sk-or-test")
    async with AnimePilgrimagePlanner(settings=settings, llm_client=fake_llm) as planner:
        planner.crawler.crawl_anime_locations = AsyncMock(
            return_value=[
                PilgrimageLocation(
                    name="Suga Shrine",
                    japanese_name="須賀神社",
                    anime_title="Your Name",
                    city="Shinjuku",
                    prefecture="Tokyo",
                    real_world_address="5-6 Sugacho, Shinjuku-ku, Tokyo",
                    coordinates=Coordinates(lat=35.6852, lng=139.7219),
                    scene_description="Final reunion staircase",
                    source_url="https://example.com/suga",
                    confidence_score=0.95,
                )
            ]
        )

        response = await planner.process_image_query(
            _PNG_HEADER,
            prompt="1 day budget trip",
            content_type="image/png",
        )

    assert response.response_type == "itinerary"
    assert response.scene_analysis is not None
    assert response.scene_analysis.landmark_guess == "Suga Shrine"
    assert response.travel_plan is not None
    assert response.travel_plan.duration_days == 1
    assert response.metadata.get("input_mode") == "image"
