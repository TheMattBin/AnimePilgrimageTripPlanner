"""Tests for AgenticWebCrawler LangGraph iterative loop, anime filtering, and URL verification."""

from __future__ import annotations

from unittest.mock import AsyncMock

from anime_pilgrimage.agents.web_crawler import (
    AgenticWebCrawler,
    _ExtractedLocationItem,
    _LocationBatchSchema,
    _PlannedQueriesSchema,
)
from anime_pilgrimage.config import Settings
from anime_pilgrimage.models import (
    AnimeIdentification,
    Coordinates,
    PilgrimageLocation,
    QueryAnalysis,
    UserQuery,
)
from anime_pilgrimage.services.search import SearchResult, WebPage


async def test_crawler_refines_when_too_few_locations_and_geocodes():
    settings = Settings(
        openrouter_api_key="sk-or-test",
        crawler_max_iterations=2,
        crawler_min_locations=3,
    )

    fake_llm = AsyncMock()
    fake_llm.is_configured = True

    extract_round = 0

    async def fake_structured(prompt, response_model, **kwargs):
        nonlocal extract_round
        if response_model is _PlannedQueriesSchema:
            return _PlannedQueriesSchema(queries=["君の名は 聖地巡礼 飛騨古川"])
        if response_model is _LocationBatchSchema:
            extract_round += 1
            if extract_round == 1:
                return _LocationBatchSchema(
                    locations=[
                        _ExtractedLocationItem(
                            name="Suga Shrine",
                            japanese_name="須賀神社",
                            anime_title="Your Name",
                            city="Shinjuku",
                            prefecture="Tokyo",
                            scene_description="Final staircase reunion scene",
                            source_url="https://example.com/tokyo",
                            confidence_score=0.95,
                        )
                    ]
                )
            return _LocationBatchSchema(
                locations=[
                    _ExtractedLocationItem(
                        name="Suga Shrine",
                        japanese_name="須賀神社",
                        anime_title="Your Name",
                        city="Shinjuku",
                        prefecture="Tokyo",
                        access_method="7 min walk from Yotsuya-Sanchome Station",
                        source_url="https://example.com/tokyo",
                        confidence_score=0.9,
                    ),
                    _ExtractedLocationItem(
                        name="Hida-Furukawa Station",
                        japanese_name="飛騨古川駅",
                        anime_title="Your Name",
                        city="Hida",
                        prefecture="Gifu",
                        scene_description="Taki arrives looking for Itomori",
                        source_url="https://example.com/hida",
                        confidence_score=0.92,
                    ),
                    _ExtractedLocationItem(
                        name="Shinjuku Police Station Intersection",
                        japanese_name="新宿警察署裏交差点",
                        anime_title="Your Name",
                        city="Shinjuku",
                        prefecture="Tokyo",
                        source_url="https://example.com/tokyo",
                        confidence_score=0.85,
                    ),
                ]
            )
        raise AssertionError(f"Unexpected schema {response_model}")

    fake_llm.generate_structured.side_effect = fake_structured

    fake_search = AsyncMock()
    fake_search.search.return_value = [
        SearchResult(title="Your Name Spots", url="https://example.com/tokyo", snippet="Suga Shrine"),
        SearchResult(title="Hida Guide", url="https://example.com/hida", snippet="Hida-Furukawa"),
    ]
    fake_search.fetch_pages.return_value = [
        WebPage(url="https://example.com/tokyo", title="Your Name Spots", text="Suga Shrine in Yotsuya..."),
        WebPage(url="https://example.com/hida", title="Hida Guide", text="Hida-Furukawa Station..."),
    ]

    fake_geocoder = AsyncMock()

    async def fake_geocode_loc(loc: PilgrimageLocation, prefer_japan: bool = True):
        return loc.model_copy(update={"coordinates": Coordinates(lat=35.685, lng=139.722)})

    fake_geocoder.geocode_location.side_effect = fake_geocode_loc

    analysis = QueryAnalysis(
        original_query=UserQuery(
            original_text="Your Name pilgrimage in Tokyo and Hida",
            normalized_text="Your Name pilgrimage in Tokyo and Hida",
        ),
        identified_anime=[
            AnimeIdentification(anime_title="Your Name", japanese_title="君の名は。")
        ],
        locations_mentioned=["Tokyo", "Hida"],
        analysis_confidence=0.9,
    )

    crawler = AgenticWebCrawler(
        settings=settings,
        llm_client=fake_llm,
        search_service=fake_search,
        geocoder=fake_geocoder,
    )
    locations = await crawler.crawl_anime_locations(analysis)

    assert extract_round == 2
    assert len(locations) == 3
    suga = next(loc for loc in locations if loc.name == "Suga Shrine")
    assert "Yotsuya-Sanchome" in suga.access_method
    assert suga.coordinates is not None


async def test_crawler_drops_other_anime_and_rejects_hallucinated_urls():
    """Regression test for Bug 7: reject off-target anime spots and unverified LLM URLs."""
    settings = Settings(
        openrouter_api_key="sk-or-test",
        crawler_max_iterations=1,
        crawler_min_locations=1,
    )

    fake_llm = AsyncMock()
    fake_llm.is_configured = True
    fake_llm.generate_structured.return_value = _LocationBatchSchema(
        locations=[
            _ExtractedLocationItem(
                name="Suga Shrine",
                anime_title="Your Name",
                source_url="https://verified-blog.example/your-name",
                confidence_score=0.95,
            ),
            _ExtractedLocationItem(
                name="Naruto Uzushio Bridge",
                anime_title="Naruto",  # Off-target anime from same blog!
                source_url="https://verified-blog.example/your-name",
                confidence_score=0.9,
            ),
            _ExtractedLocationItem(
                name="National Art Center Tokyo",
                anime_title="Your Name",
                source_url="https://hallucinated-url.example/fake",  # Not in provided docs!
                confidence_score=0.85,
            ),
        ]
    )

    fake_search = AsyncMock()
    fake_search.search.return_value = [
        SearchResult(title="Blog A", url="https://verified-blog.example/your-name", snippet="Suga"),
        SearchResult(title="Blog B", url="https://verified-blog.example/tokyo-guide", snippet="Art Center"),
    ]
    fake_search.fetch_pages.return_value = [
        WebPage(url="https://verified-blog.example/your-name", title="Blog A", text="Suga Shrine & Naruto..."),
        WebPage(url="https://verified-blog.example/tokyo-guide", title="Blog B", text="National Art Center..."),
    ]

    fake_geocoder = AsyncMock()
    fake_geocoder.geocode_location.side_effect = lambda loc, prefer_japan=True: loc

    analysis = QueryAnalysis(
        original_query=UserQuery(original_text="Your Name spots", normalized_text="Your Name spots"),
        identified_anime=[AnimeIdentification(anime_title="Your Name", japanese_title="君の名は。")],
        analysis_confidence=0.9,
    )

    crawler = AgenticWebCrawler(
        settings=settings,
        llm_client=fake_llm,
        search_service=fake_search,
        geocoder=fake_geocoder,
    )
    locations = await crawler.crawl_anime_locations(analysis)

    names = [loc.name for loc in locations]
    assert "Naruto Uzushio Bridge" not in names
    assert set(names) == {"Suga Shrine", "National Art Center Tokyo"}

    suga = next(loc for loc in locations if loc.name == "Suga Shrine")
    art = next(loc for loc in locations if loc.name == "National Art Center Tokyo")
    assert suga.source_url == "https://verified-blog.example/your-name"
    assert art.source_url == ""  # Hallucinated URL stripped
