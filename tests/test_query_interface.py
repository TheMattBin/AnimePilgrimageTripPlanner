"""Tests for QueryInterface validation and Unicode-safe normalization."""

from anime_pilgrimage.components.query_interface import QueryInterface


def test_preserves_special_anime_titles_and_japanese():
    qi = QueryInterface()
    q1 = qi.process_query("I want to visit Re:Zero and Steins;Gate spots in Akihabara!")
    assert q1 is not None
    assert "Re:Zero" in q1.normalized_text
    assert "Steins;Gate" in q1.normalized_text

    q2 = qi.process_query("君の名は。 聖地巡礼 東京 2 days")
    assert q2 is not None
    assert "君の名は。" in q2.normalized_text
    assert q2.metadata["has_japanese"] is True


def test_accepts_japanese_only_queries_without_spaces():
    """Regression test for Bug 1: no \\b word boundary around CJK terms."""
    qi = QueryInterface()
    q = qi.process_query("君の名は。の聖地巡礼をしたい")
    assert q is not None
    assert q.normalized_text == "君の名は。の聖地巡礼をしたい"
    assert q.metadata["has_japanese"] is True
    assert q.metadata["has_anime_terms"] is True

    q_loc = qi.process_query("東京でアニメのロケ地を2日間回りたい")
    assert q_loc is not None
    assert q_loc.metadata["has_locations"] is True
    assert q_loc.metadata["time_mentions"] == ["2日間"]


def test_rejects_empty_and_unrelated_queries():
    qi = QueryInterface()
    assert qi.process_query("") is None
    assert qi.process_query("hi") is None
    assert qi.process_query("What is 2 + 2?") is None
