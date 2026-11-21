"""User Query Interface component: validates and normalizes natural language requests."""

from __future__ import annotations

import re
from typing import Any

from anime_pilgrimage.models import UserQuery

# Japanese terms must NOT use \b because kanji/kana are \w characters with no word boundaries.
_JAPANESE_INTENT_RE = re.compile(
    r"(?:聖地巡礼|聖地|ロケ地|アニメ|巡礼|旅行|観光|舞台|モデル地|マップ|神社|寺院|駅|"
    r"東京|京都|大阪|飛騨|高山|鎌倉|江ノ島|宇治|箱根|大分|日田|日本)"
)
_JAPANESE_LOCATION_RE = re.compile(
    r"(?:東京|京都|大阪|奈良|神戸|横浜|名古屋|札幌|福岡|新宿|渋谷|秋葉原|下北沢|"
    r"飛騨|高山|岐阜|大分|日田|鎌倉|江ノ島|藤沢|宇治|箱根|日本)"
)
_JAPANESE_ANIME_RE = re.compile(r"(?:聖地巡礼|聖地|ロケ地|アニメ|漫画|マンガ|映画|巡礼|舞台)")


class QueryInterface:
    """Accepts, validates, and normalizes anime pilgrimage trip requests."""

    def __init__(self) -> None:
        self._intent_patterns = [
            re.compile(r"\b(anime|manga|ova|ghibli|seichi|pilgrimage)\b", re.IGNORECASE),
            re.compile(r"\b(trip|itinerary|tour|travel|visit|plan|vacation|weekend|days?)\b", re.IGNORECASE),
            re.compile(r"\b(locations?|spots?|places?|shrine|station|scenes?|filming)\b", re.IGNORECASE),
            re.compile(
                r"\b(japan|tokyo|kyoto|osaka|hida|takayama|oita|kamakura|enoshima|uji|hakone|sapporo|nagoya|fukuoka)\b",
                re.IGNORECASE,
            ),
            _JAPANESE_INTENT_RE,
        ]

    def validate_query(self, text: str) -> bool:
        """Return True if the raw text looks like a valid anime/travel pilgrimage query."""
        if not text or len(text.strip()) < 3:
            return False

        stripped = text.strip()
        return any(pattern.search(stripped) for pattern in self._intent_patterns)

    def normalize_text(self, text: str) -> str:
        """Clean whitespace and control characters while preserving titles and Japanese text.

        Keeps apostrophes, colons, semicolons, ampersands, slashes, hyphens, and Unicode
        characters so anime titles like `Re:Zero`, `Steins;Gate`, `Komi Can't Communicate`,
        and `君の名は。` survive intact.
        """
        cleaned = text.strip()
        cleaned = re.sub(r"[\x00-\x1f\x7f]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    def extract_metadata(self, text: str) -> dict[str, Any]:
        """Extract lightweight structural metadata from normalized query text."""
        text_lower = text.lower()
        has_locations = bool(
            re.search(
                r"\b(tokyo|kyoto|osaka|nara|hida|takayama|oita|kamakura|enoshima|uji|japan)\b",
                text_lower,
            )
            or _JAPANESE_LOCATION_RE.search(text)
        )
        has_anime_terms = bool(
            re.search(r"\b(anime|manga|pilgrimage|seichi|ghibli|movie|series)\b", text_lower)
            or _JAPANESE_ANIME_RE.search(text)
        )
        return {
            "word_count": len(text.split()),
            "char_count": len(text),
            "has_japanese": bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text)),
            "has_locations": has_locations,
            "has_anime_terms": has_anime_terms,
            "time_mentions": re.findall(
                r"(?:\b\d+\s*[- ]?(?:days?|weeks?)\b|\bweekend\b|\bday\s+trip\b|\d+泊\d+日|\d+日間)",
                text_lower,
            ),
        }

    def process_query(self, raw_text: str) -> UserQuery | None:
        """Validate and convert raw user input into a structured `UserQuery`."""
        if not self.validate_query(raw_text):
            return None

        normalized = self.normalize_text(raw_text)
        metadata = self.extract_metadata(normalized)

        confidence = 0.55
        if metadata["has_anime_terms"]:
            confidence += 0.2
        if metadata["has_locations"]:
            confidence += 0.15
        if metadata["time_mentions"]:
            confidence += 0.1

        return UserQuery(
            original_text=raw_text,
            normalized_text=normalized,
            query_type="pilgrimage",
            confidence=min(confidence, 1.0),
            metadata=metadata,
        )
