"""Free anime metadata lookup via Jikan (MyAnimeList) API with local SQLite cache."""

from __future__ import annotations

import logging
import re
import sqlite3
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from anime_pilgrimage.config import Settings, get_settings

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 days
_MIN_MATCH_SCORE = 0.85


def _normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9\u3040-\u30ff\u4e00-\u9fff]+", "", text.lower())


def _tokenize_latin(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _title_similarity(query: str, candidate: str) -> float:
    nq = _normalize_title(query)
    nc = _normalize_title(candidate)
    if not nq or not nc:
        return 0.0
    if nq == nc:
        return 1.0

    char_ratio = SequenceMatcher(None, nq, nc).ratio()

    # For Latin multi-word titles, require token-level agreement too so unrelated phrases
    # sharing one word (e.g. "My Family" vs "Spy x Family") cannot pass on suffix overlap.
    q_words = _tokenize_latin(query)
    c_words = _tokenize_latin(candidate)
    if q_words and c_words:
        q_set, c_set = set(q_words), set(c_words)
        jaccard = len(q_set & c_set) / len(q_set | c_set)
        score = 0.5 * char_ratio + 0.5 * jaccard
        # Accept shortened titles whose words are the exact opening prefix of the official
        # title (e.g. "My Teen Romantic Comedy" -> "My Teen Romantic Comedy SNAFU").
        if (
            len(q_words) >= 2
            and len(q_words) < len(c_words)
            and c_words[: len(q_words)] == q_words
            and len(q_words) / len(c_words) >= 0.6
        ):
            score = max(score, 0.90)
        return score

    return char_ratio


class AnimeMetadata(BaseModel):
    """Canonical metadata for an anime title."""

    canonical_title: str
    japanese_title: str = ""
    alternate_titles: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    media_type: str = ""
    synopsis: str = ""
    match_score: float = Field(default=1.0, ge=0.0, le=1.0)


class AnimeMetadataService:
    """Enriches anime titles with official English/Japanese names using Jikan API."""

    JIKAN_SEARCH_URL = "https://api.jikan.moe/v4/anime"

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
        cache_path: Path | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client
        self._owns_client = http_client is None
        self._cache_path = cache_path or self.settings.cache_db_path
        self._init_cache()

    def _init_cache(self) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._cache_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS anime_metadata_cache (
                    query_key TEXT PRIMARY KEY,
                    payload TEXT,
                    updated_at REAL NOT NULL
                )
                """
            )

    def _get_cached(self, key: str) -> tuple[bool, AnimeMetadata | None]:
        with sqlite3.connect(self._cache_path) as conn:
            row = conn.execute(
                "SELECT payload, updated_at FROM anime_metadata_cache WHERE query_key = ?",
                (key,),
            ).fetchone()
        if not row:
            return False, None
        payload, updated_at = row
        if time.time() - updated_at > _CACHE_TTL_SECONDS:
            return False, None
        if payload is None:
            return True, None
        try:
            return True, AnimeMetadata.model_validate_json(payload)
        except Exception:
            return False, None

    def _set_cached(self, key: str, metadata: AnimeMetadata | None) -> None:
        payload = metadata.model_dump_json() if metadata is not None else None
        with sqlite3.connect(self._cache_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO anime_metadata_cache (query_key, payload, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, payload, time.time()),
            )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": self.settings.nominatim_user_agent},
            )
        return self._http_client

    @staticmethod
    def _select_best_match(
        query: str, items: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], float] | None:
        """Select the highest-scoring Jikan item only if it genuinely matches `query`."""
        best_item: dict[str, Any] | None = None
        best_score = 0.0

        for item in items:
            candidate_titles = [
                item.get("title"),
                item.get("title_english"),
                item.get("title_japanese"),
                *(item.get("title_synonyms") or []),
            ]
            item_score = max(
                (_title_similarity(query, t) for t in candidate_titles if t),
                default=0.0,
            )
            if item_score > best_score:
                best_score = item_score
                best_item = item

        if best_item is None or best_score < _MIN_MATCH_SCORE:
            return None
        return best_item, best_score

    async def lookup_checked(self, title: str) -> tuple[AnimeMetadata | None, bool]:
        """Look up canonical anime metadata and distinguish outages from clean misses.

        Returns `(metadata, is_transient_error)`:
        - `(metadata, False)`: confirmed match (cached or fresh HTTP 200)
        - `(None, False)`: definitive no-match (HTTP 200 with no matching anime)
        - `(None, True)`: transient outage/error (HTTP != 200, timeout, connection error)
        """
        cleaned = title.strip()
        if not cleaned:
            return None, False

        key = cleaned.lower()
        found, cached = self._get_cached(key)
        if found:
            return cached, False

        try:
            client = await self._get_client()
            response = await client.get(
                self.JIKAN_SEARCH_URL,
                params={"q": cleaned, "limit": 5, "sfw": "true"},
            )
            if response.status_code != 200:
                logger.warning(
                    "Jikan lookup for %r returned HTTP %d", cleaned, response.status_code
                )
                return None, True

            data = response.json().get("data") or []
            matched = self._select_best_match(cleaned, data)
            if matched is None:
                # Definitive miss (HTTP 200 with no closely matching anime)
                self._set_cached(key, None)
                return None, False

            best, score = matched
            canonical = best.get("title_english") or best.get("title") or cleaned
            japanese = best.get("title_japanese") or ""
            alternates: list[str] = []
            for candidate in [
                best.get("title"),
                best.get("title_english"),
                *(best.get("title_synonyms") or []),
            ]:
                if candidate and candidate != canonical and candidate not in alternates:
                    alternates.append(candidate)

            genres = [g["name"].lower() for g in (best.get("genres") or []) if g.get("name")]
            synopsis = (best.get("synopsis") or "").strip()
            if len(synopsis) > 400:
                synopsis = synopsis[:397].rstrip() + "..."

            metadata = AnimeMetadata(
                canonical_title=canonical,
                japanese_title=japanese,
                alternate_titles=alternates[:5],
                genres=genres,
                media_type=(best.get("type") or "").lower(),
                synopsis=synopsis,
                match_score=round(score, 3),
            )
            self._set_cached(key, metadata)
            return metadata, False

        except Exception as exc:
            logger.warning(
                "Jikan lookup failed for %r (%s: %r)", cleaned, type(exc).__name__, exc
            )
            return None, True

    async def lookup(self, title: str) -> AnimeMetadata | None:
        """Look up canonical anime metadata by title (returns None on miss or error)."""
        metadata, _ = await self.lookup_checked(title)
        return metadata

    async def aclose(self) -> None:
        if self._http_client is not None and self._owns_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> AnimeMetadataService:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()
