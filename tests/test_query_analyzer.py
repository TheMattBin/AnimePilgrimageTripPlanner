"""Tests for QueryAnalyzer (LLM extraction, Jikan validation, whole-word aliases, durations)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import httpx

from anime_pilgrimage.components.query_analyzer import (
    QueryAnalyzer,
    _LLMAnimeItem,
    _LLMQueryExtraction,
)
from anime_pilgrimage.components.query_interface import QueryInterface
from anime_pilgrimage.services.anime_metadata import AnimeMetadata, AnimeMetadataService


async def test_query_analyzer_with_mock_openrouter_and_jikan():
    qi = QueryInterface()
    user_query = qi.process_query(
        "Plan a 3-day budget trip for Your Name in Tokyo and Hida Takayama"
    )
    assert user_query is not None

    fake_llm = AsyncMock()
    fake_llm.is_configured = True
    fake_llm.generate_structured.return_value = _LLMQueryExtraction(
        identified_anime=[_LLMAnimeItem(anime_title="Your Name", confidence=0.95)],
        locations_mentioned=["Tokyo", "Hida Takayama"],
        extracted_keywords=["romance", "pilgrimage"],
        duration_days=3,
        duration_label="3 days",
        travel_style="budget",
        group_size="solo",
        pace="balanced",
    )

    fake_meta = AsyncMock()
    fake_meta.lookup.return_value = AnimeMetadata(
        canonical_title="Your Name.",
        japanese_title="君の名は。",
        alternate_titles=["Kimi no Na wa."],
        genres=["drama", "supernatural"],
        synopsis="Two teenagers mysteriously swap bodies.",
        match_score=1.0,
    )

    analyzer = QueryAnalyzer(llm_client=fake_llm, metadata_service=fake_meta)
    analysis = await analyzer.analyze_query(user_query)

    assert analysis.analysis_source == "llm"
    assert analysis.trip_preferences.duration_days == 3
    assert analysis.trip_preferences.travel_style == "budget"
    assert len(analysis.identified_anime) == 1
    assert analysis.identified_anime[0].japanese_title == "君の名は。"
    assert analysis.disambiguation_questions == []


async def test_skips_jikan_when_llm_already_supplied_japanese_title():
    """Regression test for Bug 8: avoid redundant Jikan lookup when japanese_title is present."""
    qi = QueryInterface()
    user_query = qi.process_query("Your Name pilgrimage in Tokyo")
    assert user_query is not None

    fake_llm = AsyncMock()
    fake_llm.is_configured = True
    fake_llm.generate_structured.return_value = _LLMQueryExtraction(
        identified_anime=[
            _LLMAnimeItem(
                anime_title="Your Name",
                japanese_title="君の名は。",
                confidence=0.95,
            )
        ],
    )
    fake_meta = AsyncMock()

    analyzer = QueryAnalyzer(llm_client=fake_llm, metadata_service=fake_meta)
    await analyzer.analyze_query(user_query)

    fake_meta.lookup.assert_not_awaited()


async def test_jikan_rejects_unrelated_top_hit_and_fallback_ignores_my_family(tmp_path: Path):
    """Regression test for Bug 8: Jikan must verify match similarity and rule parser must not grab 'My Family'."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "title": "Spy x Family",
                        "title_english": "SPY x FAMILY",
                        "title_japanese": "SPY×FAMILY",
                        "title_synonyms": [],
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = AnimeMetadataService(http_client=client, cache_path=tmp_path / "cache.sqlite3")
        assert await service.lookup("My Family") is None

    qi = QueryInterface()
    q = qi.process_query("Plan a trip for My Family to Kyoto")
    assert q is not None
    analyzer = QueryAnalyzer(llm_client=None, metadata_service=None)
    analysis = await analyzer.analyze_query(q)
    assert analysis.identified_anime == []


async def test_alias_matching_uses_whole_words_not_substrings():
    """Regression test for Bug 9: 'chaotic' must not match 'aot'; 'Ghibli Museum' must not map to Spirited Away."""
    qi = QueryInterface()
    analyzer = QueryAnalyzer(llm_client=None, metadata_service=None)

    q_chaotic = qi.process_query("Plan a chaotic trip to Japan")
    assert q_chaotic is not None
    res_chaotic = await analyzer.analyze_query(q_chaotic)
    assert res_chaotic.identified_anime == []

    q_ghibli = qi.process_query("I want to visit the Ghibli Museum in Tokyo")
    assert q_ghibli is not None
    res_ghibli = await analyzer.analyze_query(q_ghibli)
    assert all(a.anime_title != "Spirited Away" for a in res_ghibli.identified_anime)

    q_aot = qi.process_query("Plan an AOT pilgrimage in Hita")
    assert q_aot is not None
    res_aot = await analyzer.analyze_query(q_aot)
    assert [a.anime_title for a in res_aot.identified_anime] == ["Attack on Titan"]


async def test_fallback_extracts_real_titles_with_my_your_kids_when_jikan_confirms():
    """Regression test: no word blocklist; regex candidates kept when Jikan confirms >= 0.85."""
    qi = QueryInterface()
    confirmed_catalog = {
        "my neighbor totoro": AnimeMetadata(
            canonical_title="My Neighbor Totoro",
            japanese_title="となりのトトロ",
            match_score=1.0,
        ),
        "my teen romantic comedy": AnimeMetadata(
            canonical_title="My Teen Romantic Comedy SNAFU",
            japanese_title="やはり俺の青春ラブコメはまちがっている。",
            match_score=0.90,
        ),
        "your lie in april": AnimeMetadata(
            canonical_title="Your Lie in April",
            japanese_title="四月は君の嘘",
            match_score=1.0,
        ),
        "kids on the slope": AnimeMetadata(
            canonical_title="Kids on the Slope",
            japanese_title="坂道のアポロン",
            match_score=1.0,
        ),
    }

    fake_meta = AsyncMock()
    fake_meta.lookup.side_effect = lambda title: confirmed_catalog.get(title.lower())

    analyzer = QueryAnalyzer(llm_client=None, metadata_service=fake_meta)

    cases = [
        ("Show me My Neighbor Totoro locations", "My Neighbor Totoro", "となりのトトロ"),
        ("Show me My Teen Romantic Comedy locations", "My Teen Romantic Comedy SNAFU", "やはり俺の青春ラブコメはまちがっている。"),
        ("Visit Your Lie in April locations in Tokyo", "Your Lie in April", "四月は君の嘘"),
        ("Plan a trip to Kids on the Slope locations", "Kids on the Slope", "坂道のアポロン"),
    ]
    for query_text, expected_title, expected_jp in cases:
        user_query = qi.process_query(query_text)
        assert user_query is not None
        analysis = await analyzer.analyze_query(user_query)
        assert len(analysis.identified_anime) == 1, f"Failed for {query_text!r}"
        assert analysis.identified_anime[0].anime_title == expected_title
        assert analysis.identified_anime[0].japanese_title == expected_jp

    # Unconfirmed phrase like "My Family" is dropped when Jikan rejects it
    q_bad = qi.process_query("Plan a trip for My Family to Kyoto")
    assert q_bad is not None
    res_bad = await analyzer.analyze_query(q_bad)
    assert res_bad.identified_anime == []
    assert res_bad.disambiguation_questions


async def test_partial_jikan_match_below_085_does_not_leak_fields():
    """Partial Jikan matches (< 0.85) must not leak japanese_title, synopsis, or alternates."""
    qi = QueryInterface()
    user_query = qi.process_query("Some Obscure Show pilgrimage in Tokyo")
    assert user_query is not None

    fake_llm = AsyncMock()
    fake_llm.is_configured = True
    fake_llm.generate_structured.return_value = _LLMQueryExtraction(
        identified_anime=[_LLMAnimeItem(anime_title="Some Obscure Show", confidence=0.8)]
    )

    fake_meta = AsyncMock()
    fake_meta.lookup.return_value = AnimeMetadata(
        canonical_title="Wrong Related Show",
        japanese_title="間違ったアニメ",
        alternate_titles=["Wrong Alias"],
        synopsis="Wrong synopsis",
        match_score=0.78,  # Below 0.85 cutoff
    )

    analyzer = QueryAnalyzer(llm_client=fake_llm, metadata_service=fake_meta)
    analysis = await analyzer.analyze_query(user_query)

    assert len(analysis.identified_anime) == 1
    anime = analysis.identified_anime[0]
    assert anime.anime_title == "Some Obscure Show"
    assert anime.japanese_title == ""
    assert anime.synopsis == ""
    assert anime.alternate_titles == []


async def test_jikan_outage_keeps_regex_titles_at_lower_confidence(tmp_path: Path):
    """Regression test: Jikan 503/timeout must keep extracted titles (~0.6), not drop them."""

    def outage_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    qi = QueryInterface()
    async with httpx.AsyncClient(transport=httpx.MockTransport(outage_handler)) as client:
        jikan = AnimeMetadataService(http_client=client, cache_path=tmp_path / "cache.sqlite3")
        analyzer = QueryAnalyzer(llm_client=None, metadata_service=jikan)

        for query_text, expected in [
            ("Show me Lucky Star locations in Saitama", "Lucky Star"),
            ("Show me My Neighbor Totoro locations", "My Neighbor Totoro"),
        ]:
            user_query = qi.process_query(query_text)
            assert user_query is not None
            analysis = await analyzer.analyze_query(user_query)
            assert [a.anime_title for a in analysis.identified_anime] == [expected]
            assert analysis.identified_anime[0].confidence == 0.6


async def test_jikan_accepts_opening_prefix_short_title(tmp_path: Path):
    """Regression test: 'My Teen Romantic Comedy' matches 'My Teen Romantic Comedy SNAFU' (>= 0.85)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "title": "Yahari Ore no Seishun Love Comedy wa Machigatteiru.",
                        "title_english": "My Teen Romantic Comedy SNAFU",
                        "title_japanese": "やはり俺の青春ラブコメはまちがっている。",
                        "title_synonyms": [],
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = AnimeMetadataService(http_client=client, cache_path=tmp_path / "cache.sqlite3")
        meta = await service.lookup("My Teen Romantic Comedy")

    assert meta is not None
    assert meta.match_score >= 0.85
    assert meta.canonical_title == "My Teen Romantic Comedy SNAFU"
    assert meta.japanese_title == "やはり俺の青春ラブコメはまちがっている。"


async def test_rule_based_fallback_parses_day_trip_weeks_and_compound_durations():
    qi = QueryInterface()
    analyzer = QueryAnalyzer(llm_client=None, metadata_service=None)

    q_day_trip = qi.process_query("Plan a day trip to Bocchi the Rock locations in Shimokitazawa")
    assert q_day_trip is not None
    res_day = await analyzer.analyze_query(q_day_trip)
    assert res_day.analysis_source == "rule_based"
    assert res_day.trip_preferences.duration_days == 1
    assert res_day.identified_anime[0].anime_title == "Bocchi the Rock!"
    assert res_day.identified_anime[0].japanese_title == "ぼっち・ざ・ろっく！"

    q_compound = qi.process_query("I want a 2 weeks and 3 days luxury pilgrimage for Your Name")
    assert q_compound is not None
    res_compound = await analyzer.analyze_query(q_compound)
    assert res_compound.trip_preferences.duration_days == 17
    assert res_compound.trip_preferences.travel_style == "luxury"
