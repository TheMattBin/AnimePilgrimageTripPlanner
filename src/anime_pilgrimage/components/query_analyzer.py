"""Query Analysis & Anime Identification powered by OpenRouter LLM + Jikan metadata."""

from __future__ import annotations

import logging
import re
from typing import Literal

from pydantic import BaseModel, Field

from anime_pilgrimage.llm.openrouter import OpenRouterClient, OpenRouterError
from anime_pilgrimage.models import (
    AnimeIdentification,
    QueryAnalysis,
    TripPreferences,
    UserQuery,
)
from anime_pilgrimage.services.anime_metadata import AnimeMetadataService

logger = logging.getLogger(__name__)

_HAS_CJK_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
_JIKAN_CONFIRM_THRESHOLD = 0.85


def _alias_matches(alias: str, text_lower: str) -> bool:
    """Match CJK aliases directly and ASCII/Latin aliases on whole-word boundaries."""
    if _HAS_CJK_RE.search(alias):
        return alias in text_lower
    pattern = rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])"
    return bool(re.search(pattern, text_lower))


class _LLMAnimeItem(BaseModel):
    anime_title: str = Field(..., description="Canonical English or romaji anime title")
    japanese_title: str = Field(default="", description="Official Japanese title if known")
    alternate_titles: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    keywords: list[str] = Field(default_factory=list)
    disambiguation_needed: bool = Field(default=False)


class _LLMQueryExtraction(BaseModel):
    identified_anime: list[_LLMAnimeItem] = Field(default_factory=list)
    locations_mentioned: list[str] = Field(default_factory=list)
    extracted_keywords: list[str] = Field(default_factory=list)
    duration_days: int | None = Field(default=None, ge=1, le=30)
    duration_label: str | None = Field(default=None)
    travel_style: Literal["budget", "backpacker", "standard", "luxury"] = "standard"
    group_size: Literal["solo", "couple", "family", "group", "unknown"] = "unknown"
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"
    transport_preference: str | None = Field(default=None)
    special_requests: list[str] = Field(default_factory=list)
    disambiguation_questions: list[str] = Field(default_factory=list)


# Fallback seed catalog used only when OpenRouter is unavailable/unconfigured
_FALLBACK_ANIME_CATALOG: dict[str, dict[str, object]] = {
    "Your Name": {
        "japanese_title": "君の名は。",
        "aliases": ["your name", "kimi no na wa", "君の名は"],
        "keywords": ["makoto shinkai", "tokyo", "hida", "takayama", "romance"],
    },
    "Attack on Titan": {
        "japanese_title": "進撃の巨人",
        "aliases": ["attack on titan", "shingeki no kyojin", "aot", "進撃の巨人"],
        "keywords": ["oita", "hita", "action", "dark fantasy"],
    },
    "Spirited Away": {
        "japanese_title": "千と千尋の神隠し",
        "aliases": ["spirited away", "sen to chihiro", "千と千尋の神隠し"],
        "keywords": ["studio ghibli", "fantasy", "bathhouse", "dogo onsen"],
    },
    "Bocchi the Rock!": {
        "japanese_title": "ぼっち・ざ・ろっく！",
        "aliases": ["bocchi the rock", "bocchi", "ぼっち・ざ・ろっく"],
        "keywords": ["shimokitazawa", "live house", "music", "tokyo"],
    },
    "Rascal Does Not Dream of Bunny Girl Senpai": {
        "japanese_title": "青春ブタ野郎はバニーガール先輩の夢を見ない",
        "aliases": ["bunny girl senpai", "rascal does not dream", "seishun buta", "aobuta"],
        "keywords": ["enoshima", "fujisawa", "kamakura", "shonan"],
    },
    "Sound! Euphonium": {
        "japanese_title": "響け！ユーフォニアム",
        "aliases": ["sound euphonium", "hibike euphonium", "響け！ユーフォニアム"],
        "keywords": ["uji", "kyoto", "kyoto animation", "music"],
    },
    "Hyouka": {
        "japanese_title": "氷菓",
        "aliases": ["hyouka", "氷菓"],
        "keywords": ["takayama", "gifu", "kyoto animation", "mystery"],
    },
    "Slam Dunk": {
        "japanese_title": "スラムダンク",
        "aliases": ["slam dunk", "スラムダンク"],
        "keywords": ["kamakura", "kamakurakokomae", "enoden", "basketball"],
    },
    "Suzume": {
        "japanese_title": "すずめの戸締まり",
        "aliases": ["suzume", "suzume no tojimari", "すずめの戸締まり"],
        "keywords": ["makoto shinkai", "kyushu", "oita", "tokyo", "road trip"],
    },
    "Weathering with You": {
        "japanese_title": "天気の子",
        "aliases": ["weathering with you", "tenki no ko", "天気の子"],
        "keywords": ["makoto shinkai", "tokyo", "shinjuku", "roppongi"],
    },
}

_KNOWN_LOCATIONS = [
    "Tokyo",
    "Kyoto",
    "Osaka",
    "Nara",
    "Kobe",
    "Yokohama",
    "Nagoya",
    "Sapporo",
    "Fukuoka",
    "Shinjuku",
    "Shibuya",
    "Harajuku",
    "Akihabara",
    "Shimokitazawa",
    "Ginza",
    "Asakusa",
    "Roppongi",
    "Ikebukuro",
    "Hida",
    "Takayama",
    "Gifu",
    "Oita",
    "Hita",
    "Kumamoto",
    "Kamakura",
    "Enoshima",
    "Fujisawa",
    "Uji",
    "Hakone",
    "Kanazawa",
    "Hiroshima",
    "Sendai",
    "Japan",
]

_KNOWN_LOCATIONS_ALTERNATION = "|".join(re.escape(loc) for loc in _KNOWN_LOCATIONS)

_TITLE_CONNECTORS = (
    r"in|on|the|of|a|an|to|and|no|wa|ga|ni|wo|with|does|not|is|from|for|by|at"
)
_TITLE_PHRASE = (
    rf"[A-Z][\w'!:&-]+(?:\s+(?:[A-Z][\w'!:&-]+|(?:{_TITLE_CONNECTORS})\b)){{0,7}}"
)

_PREAMBLE_RE = re.compile(
    r"^(?:i\s+(?:want|would\s+like|'d\s+like|wanna)\s+to\s+)?"
    r"(?:plan|create|make|show\s+me|find|give\s+me|visit|see|explore)\s+"
    r"(?:(?:a|an|the)\s+)?"
    r"(?:(?:\d+\s*[- ]?(?:days?|weeks?)|weekend|day|budget|luxury|backpacker|standard|relaxed|packed)\s+)*"
    r"(?:(?:trip|tour|itinerary|pilgrimage|visit)\s+(?:to|for|of|about)\s+)?",
    re.IGNORECASE,
)

_TRAILING_LOCATION_OR_TIME_RE = re.compile(
    rf"\s+(?:(?:in|to|at|around|near)\s+(?:{_KNOWN_LOCATIONS_ALTERNATION})\b.*|"
    r"(?:for\s+\d+\s*[- ]?(?:days?|weeks?)|over\s+(?:a\s+)?weekend|for\s+a\s+day\s+trip).*)$",
    re.IGNORECASE,
)


class QueryAnalyzer:
    """Analyzes user pilgrimage queries using OpenRouter structured LLM + Jikan enrichment."""

    def __init__(
        self,
        llm_client: OpenRouterClient | None = None,
        metadata_service: AnimeMetadataService | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.metadata_service = metadata_service

    async def _analyze_with_llm(self, user_query: UserQuery) -> QueryAnalysis | None:
        if self.llm_client is None or not self.llm_client.is_configured:
            return None

        system_prompt = (
            "You are an expert anime pilgrimage (seichi junrei / 聖地巡礼) travel analyst.\n"
            "Extract anime titles, target real-world regions/cities, trip duration, travel style, "
            "group size, pace, and keywords from the user's request.\n"
            "Rules:\n"
            "- Always normalize anime titles to their well-known English title and include the "
            "official Japanese title (`japanese_title`) when known.\n"
            "- Convert duration phrases cleanly: 'day trip' -> duration_days=1, 'weekend' -> 2, "
            "'1 week' -> 7, '2 weeks and 3 days' -> 17.\n"
            "- Only populate `disambiguation_questions` if NO specific anime can be determined "
            "OR the anime reference itself is genuinely ambiguous. Do NOT ask optional follow-up "
            "questions about trip length or budget when an anime is clearly identified."
        )
        prompt = f'User query: "{user_query.normalized_text}"'

        try:
            extracted = await self.llm_client.generate_structured(
                prompt,
                _LLMQueryExtraction,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=1024,
            )
        except OpenRouterError as exc:
            logger.warning("OpenRouter query analysis failed, falling back to rules: %s", exc)
            return None

        identified = [
            AnimeIdentification(
                anime_title=item.anime_title.strip(),
                japanese_title=item.japanese_title.strip(),
                alternate_titles=item.alternate_titles,
                confidence=item.confidence,
                keywords=item.keywords,
                context=user_query.original_text,
                disambiguation_needed=item.disambiguation_needed,
            )
            for item in extracted.identified_anime
            if item.anime_title.strip()
        ]

        disambiguation_questions = list(extracted.disambiguation_questions)
        if not identified and not disambiguation_questions:
            disambiguation_questions.append(
                "Which anime title(s) would you like to visit real-world locations from?"
            )

        avg_conf = (
            sum(a.confidence for a in identified) / len(identified)
            if identified
            else 0.35
        )
        overall_conf = min(user_query.confidence, avg_conf) if identified else 0.35

        return QueryAnalysis(
            original_query=user_query,
            identified_anime=identified,
            extracted_keywords=extracted.extracted_keywords,
            locations_mentioned=extracted.locations_mentioned,
            trip_preferences=TripPreferences(
                duration_days=extracted.duration_days,
                duration_label=extracted.duration_label,
                travel_style=extracted.travel_style,
                group_size=extracted.group_size,
                pace=extracted.pace,
                transport_preference=extracted.transport_preference,
                special_requests=extracted.special_requests,
            ),
            disambiguation_questions=disambiguation_questions,
            analysis_confidence=round(overall_conf, 3),
            analysis_source="llm",
        )

    def _extract_duration_rule_based(self, text: str) -> tuple[int | None, str | None]:
        text_lower = text.lower()
        if match := re.search(
            r"\b(\d+)\s*[- ]?weeks?(?:\s*(?:and|,)?\s*(\d+)\s*[- ]?days?)?\b",
            text_lower,
        ):
            weeks = int(match.group(1))
            extra_days = int(match.group(2)) if match.group(2) else 0
            total_days = max(1, min(30, weeks * 7 + extra_days))
            label = (
                f"{weeks} weeks {extra_days} days" if extra_days else f"{weeks} weeks"
            )
            return total_days, label

        if match := re.search(r"\b(\d+)\s*[- ]?days?\b", text_lower):
            days = max(1, min(30, int(match.group(1))))
            return days, f"{days} days"
        if match := re.search(r"(\d+)\s*日間", text):
            days = max(1, min(30, int(match.group(1))))
            return days, f"{days} days"
        if match := re.search(r"\d+泊(\d+)日", text):
            days = max(1, min(30, int(match.group(1))))
            return days, f"{days} days"
        if re.search(r"\bweekend\b", text_lower):
            return 2, "weekend"
        if re.search(r"\bday\s*trip\b", text_lower):
            return 1, "day_trip"
        return None, None

    def _extract_travel_style_rule_based(
        self, text: str
    ) -> Literal["budget", "backpacker", "standard", "luxury"]:
        text_lower = text.lower()
        if any(w in text_lower for w in ("backpack", "backpacker", "hostel", "capsule")):
            return "backpacker"
        if any(w in text_lower for w in ("budget", "cheap", "affordable", "economical")):
            return "budget"
        if any(w in text_lower for w in ("luxury", "premium", "high-end", "ryokan", "first class")):
            return "luxury"
        return "standard"

    def _extract_group_size_rule_based(
        self, text: str
    ) -> Literal["solo", "couple", "family", "group", "unknown"]:
        text_lower = text.lower()
        if any(w in text_lower for w in ("solo", "alone", "by myself")):
            return "solo"
        if any(w in text_lower for w in ("couple", "partner", "girlfriend", "boyfriend", "wife", "husband")):
            return "couple"
        if any(w in text_lower for w in ("family", "kids", "children")):
            return "family"
        if any(w in text_lower for w in ("friends", "group")):
            return "group"
        return "unknown"

    def _extract_pace_rule_based(self, text: str) -> Literal["relaxed", "balanced", "packed"]:
        text_lower = text.lower()
        if any(w in text_lower for w in ("relaxed", "slow", "chill", "leisurely")):
            return "relaxed"
        if any(w in text_lower for w in ("packed", "intense", "fast-paced", "everything", "as many")):
            return "packed"
        return "balanced"

    @staticmethod
    def _extract_regex_candidates(text: str) -> list[str]:
        """Extract candidate Title-Case anime phrases without blocking words like My/Your/Kids."""
        body = _PREAMBLE_RE.sub("", text).strip()
        stop_words = {
            "Tokyo",
            "Kyoto",
            "Osaka",
            "Japan",
            "Plan",
            "Trip",
            "Visit",
            "Show",
            "Create",
            "Anime",
            "Pilgrimage",
            "Budget",
            "Luxury",
            "Weekend",
        }
        patterns = [
            # "locations from Your Lie in April in Tokyo"
            re.compile(
                rf"(?:locations?|spots?|places?|pilgrimage|scenes?)\s+(?:from|for|of)\s+({_TITLE_PHRASE})"
            ),
            # "My Neighbor Totoro locations" / "Kids on the Slope pilgrimage"
            re.compile(
                rf"\b({_TITLE_PHRASE})\s+(?:locations?|pilgrimage|spots?|places?|anime|tour)\b"
            ),
            # Leading phrase after preamble: "My Family to Kyoto" / "Your Lie in April in Tokyo"
            re.compile(rf"^({_TITLE_PHRASE})"),
        ]

        candidates: list[str] = []
        seen: set[str] = set()
        for pattern in patterns:
            for match in pattern.finditer(body):
                raw = match.group(1).strip(" .,!?")
                cleaned = _TRAILING_LOCATION_OR_TIME_RE.sub("", raw).strip(" .,!?")
                # Trim trailing dangling connector if the regex captured one
                cleaned = re.sub(
                    rf"\s+(?:{_TITLE_CONNECTORS})$", "", cleaned, flags=re.IGNORECASE
                ).strip()
                if (
                    len(cleaned) < 3
                    or cleaned in stop_words
                    or cleaned.lower() in seen
                ):
                    continue
                seen.add(cleaned.lower())
                candidates.append(cleaned)
        return candidates

    def _analyze_rule_based(
        self, user_query: UserQuery
    ) -> tuple[QueryAnalysis, set[str]]:
        """Run deterministic fallback analysis; returns `(analysis, unverified_titles)`."""
        text = user_query.normalized_text
        text_lower = text.lower()

        identified: list[AnimeIdentification] = []
        unverified_titles: set[str] = set()
        seen_titles: set[str] = set()

        # 1. Built-in seed catalog (whole-word boundaries for ASCII aliases)
        for canonical, meta in _FALLBACK_ANIME_CATALOG.items():
            aliases: list[str] = meta["aliases"]  # type: ignore[assignment]
            if any(_alias_matches(alias, text_lower) for alias in aliases):
                seen_titles.add(canonical.lower())
                identified.append(
                    AnimeIdentification(
                        anime_title=canonical,
                        japanese_title=str(meta["japanese_title"]),
                        alternate_titles=[
                            str(a) for a in aliases if str(a).lower() != canonical.lower()
                        ],
                        confidence=0.9,
                        keywords=[str(k) for k in meta["keywords"]],  # type: ignore[union-attr]
                        context=user_query.original_text,
                        disambiguation_needed=False,
                    )
                )

        # 2. Extract candidate titles for unknown anime; must be confirmed by Jikan (>= 0.85)
        if not identified:
            for candidate in self._extract_regex_candidates(text):
                if candidate.lower() in seen_titles:
                    continue
                seen_titles.add(candidate.lower())
                unverified_titles.add(candidate.lower())
                identified.append(
                    AnimeIdentification(
                        anime_title=candidate,
                        confidence=0.65,
                        context=user_query.original_text,
                        disambiguation_needed=False,
                    )
                )

        locations = [
            loc
            for loc in _KNOWN_LOCATIONS
            if re.search(rf"\b{re.escape(loc.lower())}\b", text_lower)
        ]

        duration_days, duration_label = self._extract_duration_rule_based(text)
        preferences = TripPreferences(
            duration_days=duration_days,
            duration_label=duration_label,
            travel_style=self._extract_travel_style_rule_based(text),
            group_size=self._extract_group_size_rule_based(text),
            pace=self._extract_pace_rule_based(text),
        )

        keywords: list[str] = []
        for anime in identified:
            for kw in anime.keywords:
                if kw not in keywords:
                    keywords.append(kw)

        disambiguation_questions: list[str] = []
        if not identified:
            disambiguation_questions.append(
                "Which specific anime title(s) would you like to visit real-world locations from?"
            )

        confidence = (
            min(user_query.confidence, max(a.confidence for a in identified))
            if identified
            else 0.3
        )

        analysis = QueryAnalysis(
            original_query=user_query,
            identified_anime=identified,
            extracted_keywords=keywords,
            locations_mentioned=locations,
            trip_preferences=preferences,
            disambiguation_questions=disambiguation_questions,
            analysis_confidence=round(confidence, 3),
            analysis_source="rule_based",
        )
        return analysis, unverified_titles

    async def _enrich_with_metadata(
        self,
        analysis: QueryAnalysis,
        *,
        unverified_titles: set[str] | None = None,
    ) -> QueryAnalysis:
        unverified = unverified_titles or set()
        if not analysis.identified_anime:
            return analysis

        enriched_list: list[AnimeIdentification] = []
        for anime in analysis.identified_anime:
            is_unverified = anime.anime_title.lower() in unverified

            # Skip Jikan for already-confirmed titles that already have a Japanese title
            if not is_unverified and anime.japanese_title:
                enriched_list.append(anime)
                continue

            if self.metadata_service is None:
                if not is_unverified:
                    enriched_list.append(anime)
                continue

            if isinstance(self.metadata_service, AnimeMetadataService):
                meta, is_outage = await self.metadata_service.lookup_checked(anime.anime_title)
            else:
                meta = await self.metadata_service.lookup(anime.anime_title)
                is_outage = False

            # On a transient Jikan outage (timeout / 429 / 5xx), keep regex-extracted titles
            # at lower confidence (~0.6) instead of dropping every title.
            if is_outage:
                if is_unverified:
                    enriched_list.append(anime.model_copy(update={"confidence": 0.6}))
                else:
                    enriched_list.append(anime)
                continue

            # Enforce the 0.85 cutoff uniformly across every Jikan field so partial
            # matches never leak japanese_title, synopsis, or alternate_titles.
            if meta is None or meta.match_score < _JIKAN_CONFIRM_THRESHOLD:
                if not is_unverified:
                    enriched_list.append(anime)
                continue

            merged_alternates = list(
                dict.fromkeys([*anime.alternate_titles, *meta.alternate_titles])
            )
            merged_keywords = list(dict.fromkeys([*anime.keywords, *meta.genres]))
            updated_conf = (
                max(0.85, round(meta.match_score, 3))
                if is_unverified
                else min(0.95, round(anime.confidence + 0.05, 3))
            )

            enriched_list.append(
                anime.model_copy(
                    update={
                        "anime_title": meta.canonical_title or anime.anime_title,
                        "japanese_title": meta.japanese_title or anime.japanese_title,
                        "alternate_titles": merged_alternates[:6],
                        "keywords": merged_keywords[:10],
                        "synopsis": anime.synopsis or meta.synopsis,
                        "confidence": updated_conf,
                    }
                )
            )

        disambiguation = list(analysis.disambiguation_questions)
        if not enriched_list and not disambiguation:
            disambiguation.append(
                "Which specific anime title(s) would you like to visit real-world locations from?"
            )

        new_conf = (
            min(analysis.original_query.confidence, max(a.confidence for a in enriched_list))
            if enriched_list
            else 0.3
        )
        return analysis.model_copy(
            update={
                "identified_anime": enriched_list,
                "disambiguation_questions": disambiguation,
                "analysis_confidence": round(new_conf, 3),
            }
        )

    async def analyze_query(self, user_query: UserQuery) -> QueryAnalysis:
        """Analyze a user query using OpenRouter LLM with rule-based fallback and Jikan enrichment."""
        analysis = await self._analyze_with_llm(user_query)
        unverified_titles: set[str] = set()
        if analysis is None:
            analysis, unverified_titles = self._analyze_rule_based(user_query)

        return await self._enrich_with_metadata(
            analysis, unverified_titles=unverified_titles
        )
