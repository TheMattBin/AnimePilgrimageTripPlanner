"""Tests for ResponseGenerator and full end-to-end AnimePilgrimagePlanner pipeline."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from anime_pilgrimage.components.response_generator import ResponseGenerator
from anime_pilgrimage.components.trip_planner import TripPlanner
from anime_pilgrimage.config import Settings
from anime_pilgrimage.models import (
    AnimeIdentification,
    Coordinates,
    PilgrimageLocation,
    QueryAnalysis,
    TripPreferences,
    UserQuery,
)
from anime_pilgrimage.planner import AnimePilgrimagePlanner


async def test_response_generator_renders_real_world_address_and_all_legs():
    locations = [
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
        ),
        PilgrimageLocation(
            name="Shinjuku Gyoen",
            japanese_name="新宿御苑",
            anime_title="Your Name",
            city="Shinjuku",
            prefecture="Tokyo",
            real_world_address="11 Naitomachi, Shinjuku-ku, Tokyo",
            coordinates=Coordinates(lat=35.6852, lng=139.7100),
            scene_description="Garden walk scene",
            source_url="https://example.com/gyoen",
            confidence_score=0.9,
        ),
    ]
    analysis = QueryAnalysis(
        original_query=UserQuery(original_text="Your Name in Tokyo", normalized_text="Your Name in Tokyo"),
        identified_anime=[AnimeIdentification(anime_title="Your Name")],
        locations_mentioned=["Tokyo"],
        trip_preferences=TripPreferences(duration_days=1, travel_style="standard"),
        analysis_confidence=0.9,
    )

    plan = TripPlanner().generate_travel_plan(locations, analysis)
    generator = ResponseGenerator(llm_client=None)
    response = await generator.generate_response(plan, analysis, locations)

    assert response.response_type == "itinerary"
    assert "5-6 Sugacho, Shinjuku-ku, Tokyo" in response.markdown_content
    assert "Next Leg:" in response.markdown_content
    serialized = json.dumps(response.model_dump(mode="json"))
    assert "Suga Shrine" in serialized


async def test_end_to_end_pipeline_with_mocked_services():
    settings = Settings(openrouter_api_key="")
    fake_search = AsyncMock()
    fake_search.search.return_value = []
    fake_search.fetch_pages.return_value = []

    fake_geocoder = AsyncMock()
    fake_geocoder.geocode_location.side_effect = lambda loc, prefer_japan=True: loc

    fake_meta = AsyncMock()
    fake_meta.lookup.return_value = None

    async with AnimePilgrimagePlanner(
        settings=settings,
        metadata_service=fake_meta,
        search_service=fake_search,
        geocoder=fake_geocoder,
    ) as planner:
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
                    scene_description="Staircase reunion",
                    source_url="https://example.com/suga",
                    confidence_score=0.95,
                ),
                PilgrimageLocation(
                    name="Hida-Furukawa Station",
                    japanese_name="飛騨古川駅",
                    anime_title="Your Name",
                    city="Hida",
                    prefecture="Gifu",
                    real_world_address="8-22 Furukawacho Kanamoricho, Hida, Gifu",
                    coordinates=Coordinates(lat=36.2367, lng=137.1897),
                    scene_description="Taki searches for Itomori",
                    source_url="https://example.com/hida",
                    confidence_score=0.92,
                ),
            ]
        )

        response = await planner.process_query(
            "Plan a 2-day budget pilgrimage for Your Name in Tokyo and Hida"
        )

    assert response.response_type == "itinerary"
    assert response.travel_plan is not None
    assert response.travel_plan.duration_days == 2
    assert response.travel_plan.budget_level == "budget"
    assert response.travel_plan.total_locations == 2
    assert "Hida-Furukawa Station" in response.markdown_content


async def test_optional_llm_question_does_not_cancel_identified_plan():
    """Regression test for Bug 6: stray LLM follow-up questions must not abort a clear anime match."""
    settings = Settings(openrouter_api_key="")
    async with AnimePilgrimagePlanner(settings=settings) as planner:
        planner.query_analyzer.analyze_query = AsyncMock(
            return_value=QueryAnalysis(
                original_query=UserQuery(
                    original_text="Your Name pilgrimage", normalized_text="Your Name pilgrimage"
                ),
                identified_anime=[
                    AnimeIdentification(
                        anime_title="Your Name",
                        japanese_title="君の名は。",
                        confidence=0.95,
                        disambiguation_needed=False,
                    )
                ],
                disambiguation_questions=["How many days would you like your trip to be?"],
                analysis_confidence=0.95,
            )
        )
        planner.crawler.crawl_anime_locations = AsyncMock(
            return_value=[
                PilgrimageLocation(
                    name="Suga Shrine",
                    anime_title="Your Name",
                    city="Shinjuku",
                    prefecture="Tokyo",
                    coordinates=Coordinates(lat=35.6852, lng=139.7219),
                    source_url="https://example.com/suga",
                )
            ]
        )

        response = await planner.process_query("Your Name pilgrimage")
        assert response.response_type == "itinerary"
        assert response.travel_plan is not None


async def test_all_ambiguous_matches_still_trigger_clarification():
    """Clarification still fires when every identified anime is flagged disambiguation_needed."""
    settings = Settings(openrouter_api_key="")
    async with AnimePilgrimagePlanner(settings=settings) as planner:
        planner.query_analyzer.analyze_query = AsyncMock(
            return_value=QueryAnalysis(
                original_query=UserQuery(
                    original_text="Fate pilgrimage in Japan",
                    normalized_text="Fate pilgrimage in Japan",
                ),
                identified_anime=[
                    AnimeIdentification(
                        anime_title="Fate",
                        confidence=0.45,
                        disambiguation_needed=True,
                    )
                ],
                disambiguation_questions=["Which Fate series (Fate/stay night, Fate/Zero)?"],
                analysis_confidence=0.45,
            )
        )

        response = await planner.process_query("Fate pilgrimage in Japan")
        assert response.response_type == "clarification"
        assert response.disambiguation_needed is True
