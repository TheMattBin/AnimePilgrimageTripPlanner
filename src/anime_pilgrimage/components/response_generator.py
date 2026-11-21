"""Response Generator: renders deterministic itinerary markdown with optional OpenRouter polish."""

from __future__ import annotations

import logging

from anime_pilgrimage.llm.openrouter import OpenRouterClient, OpenRouterError
from anime_pilgrimage.models import (
    DailyItinerary,
    GeneratedResponse,
    PilgrimageLocation,
    QueryAnalysis,
    TravelPlan,
)

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Converts structured `TravelPlan` data into rich Markdown and API-ready responses."""

    def __init__(self, llm_client: OpenRouterClient | None = None) -> None:
        self.llm_client = llm_client

    async def _polish_introduction(
        self,
        travel_plan: TravelPlan,
        query_analysis: QueryAnalysis,
        fallback_intro: str,
    ) -> str:
        if self.llm_client is None or not self.llm_client.is_configured:
            return fallback_intro

        anime_names = ", ".join(a.anime_title for a in query_analysis.identified_anime)
        prompt = (
            f"Write an engaging, concise 2-3 sentence welcome introduction for a "
            f"{travel_plan.duration_days}-day {travel_plan.budget_level} anime pilgrimage itinerary "
            f"covering {travel_plan.total_locations} real-world spots from {anime_names} "
            f"in {travel_plan.destination}. Do NOT invent extra locations or prices."
        )
        try:
            polished = await self.llm_client.generate_text(
                prompt,
                system_prompt="You are an enthusiastic, accurate anime pilgrimage travel writer.",
                temperature=0.6,
                max_tokens=220,
            )
            return polished.strip() or fallback_intro
        except OpenRouterError as exc:
            logger.debug("LLM intro polish skipped: %s", exc)
            return fallback_intro

    @staticmethod
    def _default_introduction(
        travel_plan: TravelPlan, query_analysis: QueryAnalysis
    ) -> str:
        titles = [a.anime_title for a in query_analysis.identified_anime]
        anime_str = ", ".join(titles) if titles else "your favorite anime"
        return (
            f"Here is your {travel_plan.duration_days}-day {travel_plan.budget_level} anime "
            f"pilgrimage itinerary for **{anime_str}** across **{travel_plan.destination}**, "
            f"covering {travel_plan.total_locations} real-world locations with route timing, "
            "scene notes, and budget estimates."
        )

    @staticmethod
    def _format_day_markdown(day: DailyItinerary) -> str:
        lines = [
            f"### {day.title or f'Day {day.day}'}",
            "",
            f"- **Estimated Active Duration:** {(day.total_visit_time + day.total_travel_time) / 60:.1f} hours "
            f"({day.total_visit_time} min sightseeing, {day.total_travel_time} min transit)",
            f"- **Estimated Daily Spend (excl. lodging):** ¥{day.estimated_cost.get('total', 0):,.0f}",
            "",
        ]

        for stop in day.stops:
            loc = stop.location
            jp_suffix = f" ({loc.japanese_name})" if loc.japanese_name else ""
            time_window = (
                f"`{stop.arrival_time}–{stop.departure_time}`"
                if stop.arrival_time and stop.departure_time
                else ""
            )
            lines.append(f"**{stop.order}. {loc.name}{jp_suffix}** {time_window}".strip())
            if loc.real_world_address:
                lines.append(f"   - **Address:** {loc.real_world_address}")
            if loc.coordinates:
                lines.append(
                    f"   - **Coordinates:** {loc.coordinates.lat:.5f}, {loc.coordinates.lng:.5f}"
                )
            if loc.scene_description:
                ep = f" ({loc.episode_reference})" if loc.episode_reference else ""
                lines.append(f"   - **Anime Scene:** {loc.scene_description}{ep}")
            if loc.access_method:
                lines.append(f"   - **Access:** {loc.access_method}")
            if loc.photography_notes:
                lines.append(f"   - **Photo Tip:** {loc.photography_notes}")
            if stop.travel_to_next_minutes is not None:
                dist_part = (
                    f" ({stop.travel_to_next_km:.1f} km)" if stop.travel_to_next_km is not None else ""
                )
                mode_part = f" via {stop.travel_mode_to_next}" if stop.travel_mode_to_next else ""
                lines.append(
                    f"   - **Next Leg:** ~{stop.travel_to_next_minutes} min{mode_part}{dist_part}"
                )
            lines.append("")

        if day.notes:
            lines.append("**Day Notes:**")
            for note in day.notes:
                lines.append(f"- {note}")
            lines.append("")

        return "\n".join(lines)

    def render_markdown(
        self,
        travel_plan: TravelPlan,
        query_analysis: QueryAnalysis,
        locations: list[PilgrimageLocation],
        introduction: str,
    ) -> str:
        """Render the complete itinerary as clean GitHub-flavored Markdown."""
        sections: list[str] = [
            f"# {travel_plan.trip_title}",
            "",
            introduction,
            "",
            "## Trip Overview",
            f"- **Destination:** {travel_plan.destination}",
            f"- **Duration:** {travel_plan.duration_days} day(s)",
            f"- **Total Pilgrimage Spots:** {travel_plan.total_locations}",
            f"- **Travel Style:** {travel_plan.budget_level.title()}",
            f"- **Primary Transport:** {travel_plan.transportation_mode.replace('_', ' ').title()}",
            f"- **Estimated Total Cost:** ¥{travel_plan.total_estimated_cost.get('total', 0):,.0f}",
            "",
            "---",
            "",
            "## Day-by-Day Itinerary",
            "",
        ]

        for day in travel_plan.daily_itineraries:
            sections.append(self._format_day_markdown(day))
            sections.append("---")
            sections.append("")

        # Featured Locations Reference Table
        if locations:
            sections.extend(
                [
                    "## Location Reference & Verification Sources",
                    "",
                    "| # | Location | City / Area | Coordinates | Source |",
                    "|---|---|---|---|---|",
                ]
            )
            for idx, loc in enumerate(locations[:15], 1):
                area = ", ".join(p for p in (loc.city, loc.prefecture) if p) or loc.real_world_address or "Japan"
                coords = (
                    f"{loc.coordinates.lat:.4f}, {loc.coordinates.lng:.4f}"
                    if loc.coordinates
                    else "TBD"
                )
                source = loc.source_url or "N/A"
                sections.append(f"| {idx} | {loc.name} | {area} | {coords} | {source} |")
            sections.append("")

        # Budget breakdown
        sections.append("## Estimated Budget Breakdown (JPY)")
        for category, amount in travel_plan.total_estimated_cost.items():
            if category != "total":
                sections.append(f"- **{category.title()}:** ¥{amount:,.0f}")
        sections.append(
            f"- **Total Estimated Cost:** ¥{travel_plan.total_estimated_cost.get('total', 0):,.0f}"
        )
        sections.append("")

        # Practical info
        if travel_plan.accommodation_suggestions:
            sections.append("## Accommodation Suggestions")
            for item in travel_plan.accommodation_suggestions:
                sections.append(f"- {item}")
            sections.append("")

        if travel_plan.general_tips:
            sections.append("## Pilgrimage Tips & Etiquette")
            for tip in travel_plan.general_tips:
                sections.append(f"- {tip}")
            sections.append("")

        if travel_plan.emergency_contacts:
            sections.append("## Emergency Contacts (Japan)")
            for label, number in travel_plan.emergency_contacts.items():
                sections.append(f"- **{label.replace('_', ' ').title()}:** {number}")
            sections.append("")

        sections.append(
            "*Estimates are for trip planning guidance; always verify opening hours, transit schedules, and local photography rules.*"
        )
        return "\n".join(sections)

    def generate_clarification_response(
        self, query_analysis: QueryAnalysis
    ) -> GeneratedResponse:
        """Build a friendly clarification prompt when the anime/request is ambiguous."""
        questions = query_analysis.disambiguation_questions or [
            "Which specific anime title(s) would you like to visit locations from?",
            "How many days is your trip and which regions of Japan are you visiting?",
        ]
        intro = (
            "I'd love to plan your anime pilgrimage, but I need a bit more detail before searching."
        )
        body_lines = [
            "# Clarification Needed",
            "",
            intro,
            "",
            "## Questions",
            *[f"- {q}" for q in questions],
            "",
            "## Example Requests",
            '- "Plan a 3-day Your Name pilgrimage in Tokyo and Hida Takayama"',
            '- "Budget weekend trip for Bocchi the Rock! locations in Shimokitazawa"',
            '- "2 days visiting Sound! Euphonium spots in Uji, Kyoto"',
        ]
        markdown = "\n".join(body_lines)
        return GeneratedResponse(
            response_type="clarification",
            title="Clarification Needed",
            introduction=intro,
            main_content=markdown,
            markdown_content=markdown,
            summary="More details are needed to identify the anime or trip constraints.",
            disambiguation_needed=True,
            disambiguation_questions=questions,
            confidence=query_analysis.analysis_confidence,
            metadata={"requires_clarification": True},
        )

    def generate_error_response(self, error_message: str) -> GeneratedResponse:
        """Build a clean structured error response."""
        intro = f"Unable to generate a pilgrimage itinerary: {error_message}"
        markdown = "\n".join(
            [
                "# Unable to Generate Plan",
                "",
                intro,
                "",
                "## Tips for Better Results",
                "- Mention at least one specific anime title (English or Japanese).",
                "- Include preferred cities/regions and trip length if known.",
            ]
        )
        return GeneratedResponse(
            response_type="error",
            title="Unable to Generate Plan",
            introduction=intro,
            main_content=markdown,
            markdown_content=markdown,
            summary=error_message,
            confidence=0.1,
            metadata={"error": error_message},
        )

    async def generate_response(
        self,
        travel_plan: TravelPlan | None,
        query_analysis: QueryAnalysis,
        locations: list[PilgrimageLocation] | None = None,
        error: str | None = None,
    ) -> GeneratedResponse:
        """Produce the final `GeneratedResponse` containing structured data and Markdown."""
        if error:
            return self.generate_error_response(error)

        if query_analysis.disambiguation_questions and not travel_plan:
            return self.generate_clarification_response(query_analysis)

        if not travel_plan or not travel_plan.daily_itineraries:
            return self.generate_error_response("No valid itinerary could be generated.")

        loc_list = list(locations or [])
        default_intro = self._default_introduction(travel_plan, query_analysis)
        intro = await self._polish_introduction(travel_plan, query_analysis, default_intro)
        markdown = self.render_markdown(travel_plan, query_analysis, loc_list, intro)

        summary = (
            f"{travel_plan.duration_days}-day {travel_plan.budget_level} itinerary covering "
            f"{travel_plan.total_locations} pilgrimage spots in {travel_plan.destination} "
            f"(est. ¥{travel_plan.total_estimated_cost.get('total', 0):,.0f})."
        )

        return GeneratedResponse(
            response_type="itinerary",
            title=travel_plan.trip_title,
            introduction=intro,
            main_content=markdown,
            markdown_content=markdown,
            summary=summary,
            recommendations=travel_plan.general_tips,
            disambiguation_needed=False,
            confidence=query_analysis.analysis_confidence,
            travel_plan=travel_plan,
            locations=loc_list,
            metadata={
                "duration_days": travel_plan.duration_days,
                "total_locations": travel_plan.total_locations,
                "estimated_cost_jpy": travel_plan.total_estimated_cost.get("total", 0),
                "anime_count": len(query_analysis.identified_anime),
                "analysis_source": query_analysis.analysis_source,
            },
        )
