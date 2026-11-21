"""High-level async orchestrator for the Anime Pilgrimage Trip Planner."""

from __future__ import annotations

import logging
from typing import Any

from anime_pilgrimage.agents.web_crawler import AgenticWebCrawler
from anime_pilgrimage.components.query_analyzer import QueryAnalyzer
from anime_pilgrimage.components.query_interface import QueryInterface
from anime_pilgrimage.components.response_generator import ResponseGenerator
from anime_pilgrimage.components.trip_planner import TripPlanner
from anime_pilgrimage.config import Settings, get_settings
from anime_pilgrimage.llm.openrouter import OpenRouterClient
from anime_pilgrimage.models import GeneratedResponse
from anime_pilgrimage.services.anime_metadata import AnimeMetadataService
from anime_pilgrimage.services.geocoder import GeocoderService
from anime_pilgrimage.services.search import WebSearchService

logger = logging.getLogger(__name__)


class AnimePilgrimagePlanner:
    """End-to-end async planner facade shared by CLI and future API/TypeScript UI."""

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
        self.crawler = AgenticWebCrawler(
            settings=self.settings,
            llm_client=self.llm_client,
            search_service=self.search_service,
            geocoder=self.geocoder,
        )
        self.trip_planner = TripPlanner()
        self.response_generator = ResponseGenerator(llm_client=self.llm_client)

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

        except Exception as exc:
            logger.exception("Unhandled error while processing query")
            return self.response_generator.generate_error_response(
                f"An unexpected error occurred: {exc}"
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
