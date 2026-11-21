"""Agentic Web Crawler & Data Retriever powered by LangGraph + OpenRouter LLM."""

from __future__ import annotations

import logging
import re
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from anime_pilgrimage.config import Settings, get_settings
from anime_pilgrimage.llm.openrouter import OpenRouterClient, OpenRouterError
from anime_pilgrimage.models import PilgrimageLocation, QueryAnalysis
from anime_pilgrimage.services.geocoder import GeocoderService
from anime_pilgrimage.services.search import SearchResult, WebPage, WebSearchService

logger = logging.getLogger(__name__)


class CrawlerState(TypedDict, total=False):
    """Typed LangGraph workflow state for iterative pilgrimage discovery."""

    query_analysis: QueryAnalysis
    iteration: int
    max_iterations: int
    planned_queries: list[str]
    executed_queries: list[str]
    search_results: list[SearchResult]
    visited_urls: list[str]
    fetched_pages: list[WebPage]
    extracted_candidates: list[PilgrimageLocation]
    locations: list[PilgrimageLocation]


class _PlannedQueriesSchema(BaseModel):
    queries: list[str] = Field(default_factory=list, description="Targeted web search queries")


class _ExtractedLocationItem(BaseModel):
    name: str = Field(..., description="Specific real-world landmark/place name in English")
    japanese_name: str = Field(default="", description="Exact Japanese name (e.g., 須賀神社)")
    anime_title: str = Field(..., description="Associated anime title")
    city: str = Field(default="", description="City or Tokyo ward")
    prefecture: str = Field(default="", description="Japanese prefecture")
    real_world_address: str = Field(default="", description="Street address or station area")
    description: str = Field(default="", description="Brief description of the real-world place")
    scene_description: str = Field(default="", description="Memorable anime scene at this location")
    episode_reference: str = Field(default="", description="Episode or film moment")
    access_method: str = Field(default="", description="Nearest train station and walking minutes")
    best_visit_time: str = Field(default="", description="Best time of day to visit")
    photography_notes: str = Field(default="", description="Framing or camera tips")
    etiquette_notes: str = Field(default="", description="Local visitor etiquette")
    source_url: str = Field(default="", description="Exact Source URL from the provided documents")
    confidence_score: float = Field(default=0.75, ge=0.0, le=1.0)


class _LocationBatchSchema(BaseModel):
    locations: list[_ExtractedLocationItem] = Field(default_factory=list)


_NOISE_PLACE_WORDS = {
    "privacy",
    "policy",
    "terms",
    "login",
    "sign",
    "menu",
    "search",
    "home",
    "about",
    "contact",
    "copyright",
    "cookie",
    "english",
    "japanese",
    "subscribe",
    "newsletter",
    "comment",
    "share",
}


def _normalize_key(text: str) -> str:
    return re.sub(r"[^a-z0-9\u3040-\u30ff\u4e00-\u9fff]+", "", text.lower())


class AgenticWebCrawler:
    """Iterative LangGraph crawler that searches, extracts with LLM, refines, and geocodes."""

    def __init__(
        self,
        settings: Settings | None = None,
        llm_client: OpenRouterClient | None = None,
        search_service: WebSearchService | None = None,
        geocoder: GeocoderService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client
        self.search_service = search_service or WebSearchService(settings=self.settings)
        self._owns_search = search_service is None
        self.geocoder = geocoder or GeocoderService(settings=self.settings)
        self._owns_geocoder = geocoder is None
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        workflow = StateGraph(CrawlerState)

        workflow.add_node("plan_queries", self._plan_queries)
        workflow.add_node("search_and_fetch", self._search_and_fetch)
        workflow.add_node("extract_locations", self._extract_locations)
        workflow.add_node("merge_locations", self._merge_locations)
        workflow.add_node("geocode_locations", self._geocode_locations)

        workflow.add_edge(START, "plan_queries")
        workflow.add_edge("plan_queries", "search_and_fetch")
        workflow.add_edge("search_and_fetch", "extract_locations")
        workflow.add_edge("extract_locations", "merge_locations")
        workflow.add_conditional_edges(
            "merge_locations",
            self._should_continue,
            {
                "refine": "plan_queries",
                "geocode": "geocode_locations",
            },
        )
        workflow.add_edge("geocode_locations", END)

        return workflow.compile()

    def _default_queries_for_iteration(
        self, analysis: QueryAnalysis, iteration: int
    ) -> list[str]:
        queries: list[str] = []
        region_hint = " ".join(analysis.locations_mentioned[:2])

        for anime in analysis.identified_anime:
            title = anime.anime_title
            jp = anime.japanese_title

            if iteration == 0:
                if region_hint:
                    queries.append(f"{title} anime pilgrimage real locations {region_hint}")
                queries.append(f"{title} anime pilgrimage real life locations Japan guide")
                if jp:
                    queries.append(f"{jp} 聖地巡礼 マップ ロケ地")
                else:
                    queries.append(f"{title} 聖地巡礼 ロケ地")
            else:
                queries.append(f"{title} real life spots map shrines stations visit")
                if jp:
                    queries.append(f"{jp} 聖地巡礼 モデル地 一覧")
                elif anime.alternate_titles:
                    queries.append(f"{anime.alternate_titles[0]} real life locations pilgrimage")

        return list(dict.fromkeys(q.strip() for q in queries if q.strip()))[:6]

    async def _plan_queries(self, state: CrawlerState) -> dict[str, Any]:
        analysis = state["query_analysis"]
        iteration = state.get("iteration", 0)
        executed = set(state.get("executed_queries", []))
        current_locations = state.get("locations", [])

        planned: list[str] = []
        if iteration > 0 and self.llm_client and self.llm_client.is_configured:
            anime_summary = ", ".join(
                f"{a.anime_title} ({a.japanese_title})" if a.japanese_title else a.anime_title
                for a in analysis.identified_anime
            )
            found_names = [loc.name for loc in current_locations]
            prompt = (
                f"Anime: {anime_summary}\n"
                f"Target regions: {', '.join(analysis.locations_mentioned) or 'Japan'}\n"
                f"Already tried queries: {list(executed)}\n"
                f"Locations found so far ({len(found_names)}): {found_names}\n\n"
                "Generate 3-4 NEW, distinct search queries (mixing English pilgrimage blogs and "
                "Japanese 聖地巡礼 / ロケ地 queries) to discover additional iconic real-world spots."
            )
            try:
                result = await self.llm_client.generate_structured(
                    prompt,
                    _PlannedQueriesSchema,
                    system_prompt="You are an anime pilgrimage research planner.",
                    temperature=0.3,
                    max_tokens=400,
                )
                planned = [q.strip() for q in result.queries if q.strip() and q.strip() not in executed]
            except OpenRouterError as exc:
                logger.debug("LLM query refinement failed: %s", exc)

        if not planned:
            planned = [
                q
                for q in self._default_queries_for_iteration(analysis, iteration)
                if q not in executed
            ]

        logger.info("Crawler iteration %d planned %d queries", iteration + 1, len(planned))
        return {
            "planned_queries": planned[:4],
            "executed_queries": [*state.get("executed_queries", []), *planned[:4]],
            "iteration": iteration + 1,
        }

    async def _search_and_fetch(self, state: CrawlerState) -> dict[str, Any]:
        planned_queries = state.get("planned_queries", [])
        visited_urls = set(state.get("visited_urls", []))

        new_results: list[SearchResult] = []
        urls_to_fetch: list[str] = []

        for query in planned_queries:
            hits = await self.search_service.search(query, max_results=5)
            for hit in hits:
                new_results.append(hit)
                if hit.url not in visited_urls and hit.url not in urls_to_fetch:
                    urls_to_fetch.append(hit.url)

        remaining_page_budget = max(
            0, self.settings.crawler_max_pages - len(visited_urls)
        )
        urls_to_fetch = urls_to_fetch[: min(4, remaining_page_budget)]

        pages = await self.search_service.fetch_pages(urls_to_fetch, max_chars=4500)
        logger.info(
            "Fetched %d readable pages from %d search results",
            len(pages),
            len(new_results),
        )

        return {
            "search_results": [*state.get("search_results", []), *new_results],
            "visited_urls": [*visited_urls, *urls_to_fetch],
            "fetched_pages": pages,
        }

    @staticmethod
    def _build_allowed_anime_map(analysis: QueryAnalysis) -> dict[str, str]:
        """Map every normalized target anime title/alias/JP title -> canonical title."""
        allowed: dict[str, str] = {}
        for anime in analysis.identified_anime:
            canonical = anime.anime_title.strip()
            for candidate in [canonical, anime.japanese_title, *anime.alternate_titles]:
                norm = _normalize_key(candidate)
                if norm:
                    allowed[norm] = canonical
        return allowed

    @staticmethod
    def _match_target_anime(
        raw_anime: str, allowed_map: dict[str, str], single_default: str | None
    ) -> str | None:
        cleaned = raw_anime.strip()
        if not cleaned:
            return single_default
        norm = _normalize_key(cleaned)
        if norm in allowed_map:
            return allowed_map[norm]
        # Accept minor subtitle/punctuation variants where one clearly contains the other
        for allowed_norm, canonical in allowed_map.items():
            if len(allowed_norm) >= 4 and (allowed_norm in norm or norm in allowed_norm):
                return canonical
        return None

    @staticmethod
    def _validate_source_url(
        candidate_url: str,
        allowed_urls: set[str],
        *,
        is_knowledge_mode: bool,
    ) -> str:
        if is_knowledge_mode:
            return "openrouter-knowledge"
        cleaned = candidate_url.strip()
        if cleaned in allowed_urls:
            return cleaned
        # Strip trailing slash mismatch against provided document URLs
        stripped = cleaned.rstrip("/")
        for allowed in allowed_urls:
            if allowed.rstrip("/") == stripped:
                return allowed
        if len(allowed_urls) == 1:
            return next(iter(allowed_urls))
        return ""

    async def _extract_with_llm(
        self,
        analysis: QueryAnalysis,
        pages: list[WebPage],
        snippets: list[SearchResult],
    ) -> list[PilgrimageLocation]:
        assert self.llm_client is not None
        anime_list = ", ".join(
            f"{a.anime_title} ({a.japanese_title})" if a.japanese_title else a.anime_title
            for a in analysis.identified_anime
        )
        region_filter = (
            f"Prioritize locations in/near: {', '.join(analysis.locations_mentioned)}."
            if analysis.locations_mentioned
            else "Include iconic locations across Japan."
        )

        docs: list[str] = []
        allowed_urls: set[str] = set()
        for idx, page in enumerate(pages[:4], 1):
            allowed_urls.add(page.url)
            docs.append(
                f"[Document {idx}]\nURL: {page.url}\nTitle: {page.title}\nContent:\n{page.text[:3000]}"
            )
        if not docs and snippets:
            for idx, hit in enumerate(snippets[:8], 1):
                allowed_urls.add(hit.url)
                docs.append(
                    f"[Snippet {idx}]\nURL: {hit.url}\nTitle: {hit.title}\nSnippet: {hit.snippet}"
                )

        is_knowledge_mode = not docs
        if docs:
            corpus = "\n\n---\n\n".join(docs)
            prompt = (
                f"Target anime ONLY: {anime_list}\n"
                f"{region_filter}\n\n"
                "Extract real-world anime pilgrimage locations for the target anime ONLY from the "
                "documents below. Ignore spots belonging to other anime.\n"
                "For each location, copy the EXACT `URL:` value from the document into `source_url`.\n"
                "Do NOT invent fictional places, other anime, or URLs not listed below.\n\n"
                f"{corpus}"
            )
            system_prompt = (
                "You extract structured real-world anime pilgrimage landmarks from travel guides "
                "and web articles. Accuracy, target-anime filtering, and exact source URLs are critical."
            )
            confidence_cap = 0.95
        else:
            prompt = (
                f"Target anime ONLY: {anime_list}\n"
                f"{region_filter}\n\n"
                "No live web articles were reachable. Provide up to 8 well-verified, famous "
                "real-world anime pilgrimage locations for the target anime with accurate Japanese "
                "names, cities, prefectures, scene references, and station access. "
                "Set `source_url` to 'openrouter-knowledge' and `confidence_score` <= 0.65."
            )
            system_prompt = (
                "You are an expert on real-world Japanese anime pilgrimage locations (聖地巡礼). "
                "Only include locations you are confident genuinely exist and appear in the target anime."
            )
            confidence_cap = 0.65

        try:
            batch = await self.llm_client.generate_structured(
                prompt,
                _LocationBatchSchema,
                system_prompt=system_prompt,
                temperature=0.15,
                max_tokens=2400,
            )
        except OpenRouterError as exc:
            logger.warning("LLM location extraction failed: %s", exc)
            return []

        allowed_anime_map = self._build_allowed_anime_map(analysis)
        single_default = (
            analysis.identified_anime[0].anime_title
            if len(analysis.identified_anime) == 1
            else None
        )

        extracted: list[PilgrimageLocation] = []
        for item in batch.locations:
            name = item.name.strip()
            if len(name) < 3 or name.lower() in _NOISE_PLACE_WORDS:
                continue

            matched_anime = self._match_target_anime(
                item.anime_title, allowed_anime_map, single_default
            )
            if matched_anime is None:
                logger.debug(
                    "Dropping off-target location %r (anime=%r not in targets)",
                    name,
                    item.anime_title,
                )
                continue

            verified_url = self._validate_source_url(
                item.source_url,
                allowed_urls,
                is_knowledge_mode=is_knowledge_mode,
            )
            extracted.append(
                PilgrimageLocation(
                    name=name,
                    japanese_name=item.japanese_name.strip(),
                    anime_title=matched_anime,
                    city=item.city.strip(),
                    prefecture=item.prefecture.strip(),
                    real_world_address=item.real_world_address.strip(),
                    description=item.description.strip(),
                    scene_description=item.scene_description.strip(),
                    episode_reference=item.episode_reference.strip(),
                    access_method=item.access_method.strip(),
                    best_visit_time=item.best_visit_time.strip(),
                    photography_notes=item.photography_notes.strip(),
                    etiquette_notes=item.etiquette_notes.strip(),
                    source_url=verified_url,
                    confidence_score=min(item.confidence_score, confidence_cap),
                )
            )
        return extracted

    def _extract_heuristic(
        self,
        analysis: QueryAnalysis,
        pages: list[WebPage],
        snippets: list[SearchResult],
    ) -> list[PilgrimageLocation]:
        """Fallback heuristic extractor when OpenRouter is not configured."""
        landmark_re = re.compile(
            r"\b([A-Z][a-zA-Z0-9'&-]+(?:\s+[A-Z][a-zA-Z0-9'&-]+){0,3}\s+"
            r"(?:Shrine|Temple|Station|Park|Garden|Bridge|Tower|Building|Crossing|Stairs|Staircase|Library|Museum|Cafe|Observatory|Beach|Island|Dam|Hall|School|Street))\b"
        )
        default_anime = analysis.identified_anime[0].anime_title if analysis.identified_anime else "Anime"

        sources: list[tuple[str, str]] = [(p.url, p.text) for p in pages]
        if not sources:
            sources = [(s.url, f"{s.title}. {s.snippet}") for s in snippets]

        found: list[PilgrimageLocation] = []
        seen: set[str] = set()
        for url, text in sources:
            for match in landmark_re.finditer(text):
                name = match.group(1).strip()
                norm = name.lower()
                if norm in seen or any(w in norm.split() for w in _NOISE_PLACE_WORDS):
                    continue
                seen.add(norm)
                start = max(0, match.start() - 120)
                end = min(len(text), match.end() + 180)
                snippet = " ".join(text[start:end].split())
                found.append(
                    PilgrimageLocation(
                        name=name,
                        anime_title=default_anime,
                        description=snippet[:240],
                        source_url=url,
                        confidence_score=0.6,
                    )
                )
        return found[:12]

    async def _extract_locations(self, state: CrawlerState) -> dict[str, Any]:
        analysis = state["query_analysis"]
        pages = state.get("fetched_pages", [])
        snippets = state.get("search_results", [])

        if self.llm_client and self.llm_client.is_configured:
            candidates = await self._extract_with_llm(analysis, pages, snippets)
        else:
            candidates = self._extract_heuristic(analysis, pages, snippets)

        logger.info("Extracted %d candidate locations in this round", len(candidates))
        return {"extracted_candidates": candidates}

    @staticmethod
    def _location_dedupe_key(loc: PilgrimageLocation) -> str:
        return _normalize_key(loc.name)

    async def _merge_locations(self, state: CrawlerState) -> dict[str, Any]:
        existing = list(state.get("locations", []))
        candidates = state.get("extracted_candidates", [])

        merged_by_key: dict[str, PilgrimageLocation] = {
            self._location_dedupe_key(loc): loc for loc in existing
        }

        for cand in candidates:
            if cand.confidence_score < 0.35:
                continue
            key = self._location_dedupe_key(cand)
            if not key:
                continue
            prev = merged_by_key.get(key)
            if prev is None:
                merged_by_key[key] = cand
            else:
                merged_by_key[key] = prev.model_copy(
                    update={
                        "japanese_name": prev.japanese_name or cand.japanese_name,
                        "city": prev.city or cand.city,
                        "prefecture": prev.prefecture or cand.prefecture,
                        "real_world_address": prev.real_world_address or cand.real_world_address,
                        "description": prev.description
                        if len(prev.description) >= len(cand.description)
                        else cand.description,
                        "scene_description": prev.scene_description or cand.scene_description,
                        "episode_reference": prev.episode_reference or cand.episode_reference,
                        "access_method": prev.access_method or cand.access_method,
                        "best_visit_time": prev.best_visit_time or cand.best_visit_time,
                        "photography_notes": prev.photography_notes or cand.photography_notes,
                        "etiquette_notes": prev.etiquette_notes or cand.etiquette_notes,
                        "source_url": prev.source_url or cand.source_url,
                        "confidence_score": max(prev.confidence_score, cand.confidence_score),
                    }
                )

        sorted_locs = sorted(
            merged_by_key.values(),
            key=lambda item: item.confidence_score,
            reverse=True,
        )[:15]
        return {"locations": sorted_locs}

    def _should_continue(self, state: CrawlerState) -> Literal["refine", "geocode"]:
        locations = state.get("locations", [])
        iteration = state.get("iteration", 1)
        max_iterations = state.get("max_iterations", self.settings.crawler_max_iterations)

        if len(locations) < self.settings.crawler_min_locations and iteration < max_iterations:
            logger.info(
                "Only %d locations found (< %d); triggering refinement iteration %d/%d",
                len(locations),
                self.settings.crawler_min_locations,
                iteration + 1,
                max_iterations,
            )
            return "refine"
        return "geocode"

    async def _geocode_locations(self, state: CrawlerState) -> dict[str, Any]:
        locations = state.get("locations", [])
        geocoded: list[PilgrimageLocation] = []
        for loc in locations:
            geocoded.append(await self.geocoder.geocode_location(loc, prefer_japan=True))

        resolved_count = sum(1 for loc in geocoded if loc.coordinates is not None)
        logger.info("Geocoded %d/%d locations successfully", resolved_count, len(geocoded))
        return {"locations": geocoded}

    async def crawl_anime_locations(
        self, query_analysis: QueryAnalysis
    ) -> list[PilgrimageLocation]:
        """Run the iterative LangGraph discovery & geocoding workflow."""
        if not query_analysis.identified_anime:
            return []

        initial_state: CrawlerState = {
            "query_analysis": query_analysis,
            "iteration": 0,
            "max_iterations": self.settings.crawler_max_iterations,
            "planned_queries": [],
            "executed_queries": [],
            "search_results": [],
            "visited_urls": [],
            "fetched_pages": [],
            "extracted_candidates": [],
            "locations": [],
        }
        final_state = await self.graph.ainvoke(initial_state)
        return list(final_state.get("locations", []))

    async def aclose(self) -> None:
        if self._owns_search:
            await self.search_service.aclose()
        if self._owns_geocoder:
            await self.geocoder.aclose()

    async def __aenter__(self) -> AgenticWebCrawler:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()
