"""High-level async orchestrator for the Anime Pilgrimage Trip Planner."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from anime_pilgrimage.agents.web_crawler import AgenticWebCrawler
from anime_pilgrimage.components.query_analyzer import QueryAnalyzer
from anime_pilgrimage.components.query_interface import QueryInterface
from anime_pilgrimage.components.response_generator import ResponseGenerator
from anime_pilgrimage.components.scene_analyzer import SceneAnalyzer
from anime_pilgrimage.components.trip_planner import TripPlanner
from anime_pilgrimage.config import Settings, get_settings
from anime_pilgrimage.llm.openrouter import OpenRouterClient
from anime_pilgrimage.models import (
    AnimeIdentification,
    GeneratedResponse,
    QueryAnalysis,
    SceneAnalysis,
    TripPreferences,
    UserQuery,
)
from anime_pilgrimage.services.anime_metadata import AnimeMetadataService
from anime_pilgrimage.services.geocoder import GeocoderService
from anime_pilgrimage.services.search import WebSearchService

logger = logging.getLogger(__name__)


class AnimePilgrimagePlanner:
    """End-to-end async planner facade shared by CLI, FastAPI, and TypeScript UI."""

    def __init__(
        self,
        settings: Settings | None = None,
        llm_client: OpenRouterClient | None = None,
        metadata_service: AnimeMetadataService | None = None,
        search_service: WebSearchService | None = None,
        geocoder: GeocoderService | None = None,
    ) -> None:
        self.settings = settings or get_settings()

        self._owns_llm = llm_client is None
        self.llm_client = llm_client or OpenRouterClient(settings=self.settings)

        self._owns_metadata = metadata_service is None
        self.metadata_service = metadata_service or AnimeMetadataService(settings=self.settings)

        self._owns_search = search_service is None
        self.search_service = search_service or WebSearchService(settings=self.settings)

        self._owns_geocoder = geocoder is None
        self.geocoder = geocoder or GeocoderService(settings=self.settings)

        self.query_interface = QueryInterface()
        self.query_analyzer = QueryAnalyzer(
            llm_client=self.llm_client,
            metadata_service=self.metadata_service,
        )
        self.scene_analyzer = SceneAnalyzer(
            llm_client=self.llm_client,
            metadata_service=self.metadata_service,
        )
        self.crawler = AgenticWebCrawler(
            settings=self.settings,
            llm_client=self.llm_client,
            search_service=self.search_service,
            geocoder=self.geocoder,
        )
        self.trip_planner = TripPlanner()
        self.response_generator = ResponseGenerator(llm_client=self.llm_client)

    async def analyze_scene(
        self,
        image_source: bytes | Path | str,
        *,
        content_type: str | None = None,
        filename: str | None = None,
        hint: str = "",
    ) -> SceneAnalysis:
        """Analyze an anime screenshot or location photo using OpenRouter VLM."""
        return await self.scene_analyzer.analyze_image(
            image_source,
            content_type=content_type,
            filename=filename,
            hint=hint,
        )

    async def process_query(self, user_input: str) -> GeneratedResponse:
        """Run a natural-language query through the full pilgrimage planning pipeline."""
        logger.info("Processing query: %r", user_input)

        try:
            user_query = self.query_interface.process_query(user_input)
            if user_query is None:
                return self.response_generator.generate_error_response(
                    "Invalid query. Please specify an anime title or pilgrimage trip request."
                )

            query_analysis = await self.query_analyzer.analyze_query(user_query)
            logger.info(
                "Identified anime (%s): %s",
                query_analysis.analysis_source,
                [a.anime_title for a in query_analysis.identified_anime],
            )

            needs_clarification = not query_analysis.identified_anime or all(
                anime.disambiguation_needed for anime in query_analysis.identified_anime
            )
            if needs_clarification:
                return self.response_generator.generate_clarification_response(query_analysis)

            return await self._plan_from_analysis(query_analysis)

        except Exception as exc:
            logger.exception("Unhandled error while processing query")
            return self.response_generator.generate_error_response(
                f"An unexpected error occurred: {exc}"
            )

    async def process_image_query(
        self,
        image_source: bytes | Path | str,
        *,
        prompt: str = "",
        content_type: str | None = None,
        filename: str | None = None,
    ) -> GeneratedResponse:
        """Identify an anime scene via OpenRouter VLM and build a full pilgrimage itinerary."""
        logger.info("Processing image pilgrimage query (prompt=%r)", prompt)
        try:
            scene = await self.analyze_scene(
                image_source,
                content_type=content_type,
                filename=filename,
                hint=prompt,
            )

            if not scene.identified_anime.strip():
                fallback_query = UserQuery(
                    original_text=prompt or "[uploaded anime screenshot]",
                    normalized_text=prompt or "[uploaded anime screenshot]",
                    query_type="image_pilgrimage",
                    confidence=max(0.2, scene.confidence),
                )
                analysis = QueryAnalysis(
                    original_query=fallback_query,
                    identified_anime=[],
                    locations_mentioned=[scene.city_or_region] if scene.city_or_region else [],
                    disambiguation_questions=[
                        "I couldn't confidently identify the anime from this image. "
                        "Which anime is this screenshot from?"
                    ],
                    analysis_confidence=scene.confidence,
                    analysis_source="hybrid",
                )
                clarification = self.response_generator.generate_clarification_response(analysis)
                return clarification.model_copy(update={"scene_analysis": scene})

            # Parse optional user trip preferences (duration, budget, pace) deterministically
            # without spending an extra LLM round-trip on the optional image prompt.
            trip_prefs = TripPreferences()
            extra_locations: list[str] = []
            if prompt.strip():
                parsed_prompt = self.query_interface.process_query(prompt)
                if parsed_prompt is not None:
                    rule_analysis, _ = self.query_analyzer._analyze_rule_based(parsed_prompt)
                    trip_prefs = rule_analysis.trip_preferences
                    extra_locations = rule_analysis.locations_mentioned

            locations_mentioned = list(
                dict.fromkeys(
                    loc
                    for loc in [scene.city_or_region, *extra_locations]
                    if loc and loc.strip()
                )
            )
            seed_queries = self.scene_analyzer.build_search_queries(scene)

            synthetic_text = (
                f"Anime pilgrimage for {scene.identified_anime}"
                + (f" ({scene.landmark_guess})" if scene.landmark_guess else "")
                + (f" — {prompt.strip()}" if prompt.strip() else "")
            )
            query_analysis = QueryAnalysis(
                original_query=UserQuery(
                    original_text=synthetic_text,
                    normalized_text=synthetic_text,
                    query_type="image_pilgrimage",
                    confidence=max(0.5, scene.confidence),
                    metadata={"source": "vlm_screenshot"},
                ),
                identified_anime=[
                    AnimeIdentification(
                        anime_title=scene.identified_anime.strip(),
                        japanese_title=scene.japanese_title.strip(),
                        confidence=max(0.5, scene.confidence),
                        keywords=scene.visual_clues[:6],
                        context=synthetic_text,
                        disambiguation_needed=False,
                    )
                ],
                extracted_keywords=scene.visual_clues[:8],
                locations_mentioned=locations_mentioned,
                trip_preferences=trip_prefs,
                analysis_confidence=round(max(0.5, scene.confidence), 3),
                analysis_source="hybrid",
                seed_queries=seed_queries,
            )

            response = await self._plan_from_analysis(query_analysis)
            return response.model_copy(
                update={
                    "scene_analysis": scene,
                    "metadata": {**response.metadata, "input_mode": "image"},
                }
            )

        except Exception as exc:
            logger.exception("Unhandled error while processing image query")
            return self.response_generator.generate_error_response(str(exc))

    async def _plan_from_analysis(self, query_analysis: QueryAnalysis) -> GeneratedResponse:
        locations = await self.crawler.crawl_anime_locations(query_analysis)
        logger.info("Discovered %d pilgrimage locations", len(locations))

        if not locations:
            titles = ", ".join(a.anime_title for a in query_analysis.identified_anime)
            return self.response_generator.generate_error_response(
                f"No pilgrimage locations could be retrieved for {titles}. "
                "Try a more specific anime title or check your network/OpenRouter configuration."
            )

        travel_plan = self.trip_planner.generate_travel_plan(locations, query_analysis)
        return await self.response_generator.generate_response(
            travel_plan, query_analysis, locations
        )

    async def aclose(self) -> None:
        """Release all owned async network clients."""
        if self._owns_llm:
            await self.llm_client.aclose()
        if self._owns_metadata:
            await self.metadata_service.aclose()
        if self._owns_search:
            await self.search_service.aclose()
        if self._owns_geocoder:
            await self.geocoder.aclose()

    async def __aenter__(self) -> AnimePilgrimagePlanner:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()
