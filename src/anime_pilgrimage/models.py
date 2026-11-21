"""Shared Pydantic v2 domain models for the Anime Pilgrimage Trip Planner.

Designed to be cleanly JSON-serializable via `.model_dump()` for both CLI output
and a future TypeScript web frontend / API layer.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """WGS84 geographic coordinates."""

    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")


class UserQuery(BaseModel):
    """Normalized user input."""

    original_text: str = Field(..., description="Original user query text")
    normalized_text: str = Field(..., description="Cleaned and normalized query text")
    query_type: str = Field(default="pilgrimage", description="Type of query")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Validation confidence")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extracted query metadata")


class TripPreferences(BaseModel):
    """Structured travel preferences parsed from the user's request."""

    duration_days: int | None = Field(default=None, ge=1, le=30, description="Requested trip length")
    duration_label: str | None = Field(default=None, description="Raw duration phrase if present")
    travel_style: Literal["budget", "backpacker", "standard", "luxury"] = Field(
        default="standard", description="Budget/comfort style"
    )
    group_size: Literal["solo", "couple", "family", "group", "unknown"] = Field(
        default="unknown", description="Traveler party type"
    )
    pace: Literal["relaxed", "balanced", "packed"] = Field(
        default="balanced", description="Daily sightseeing pace"
    )
    transport_preference: str | None = Field(
        default=None, description="Optional explicit transport mode preference"
    )
    special_requests: list[str] = Field(
        default_factory=list, description="Special interests or constraints"
    )


class AnimeIdentification(BaseModel):
    """Identified anime title and metadata."""

    anime_title: str = Field(..., description="Canonical English or romaji anime title")
    japanese_title: str = Field(default="", description="Official Japanese title (日本語)")
    alternate_titles: list[str] = Field(default_factory=list, description="Alternate/romaji titles")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score (0-1)")
    keywords: list[str] = Field(default_factory=list, description="Relevant themes or keywords")
    context: str = Field(default="", description="Context from user query")
    synopsis: str = Field(default="", description="Short anime summary if available")
    disambiguation_needed: bool = Field(
        default=False, description="Whether user clarification is needed"
    )


class QueryAnalysis(BaseModel):
    """Complete result of analyzing a user's pilgrimage request."""

    original_query: UserQuery
    identified_anime: list[AnimeIdentification] = Field(default_factory=list)
    extracted_keywords: list[str] = Field(default_factory=list)
    locations_mentioned: list[str] = Field(default_factory=list)
    trip_preferences: TripPreferences = Field(default_factory=TripPreferences)
    disambiguation_questions: list[str] = Field(default_factory=list)
    analysis_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall confidence in analysis"
    )
    analysis_source: Literal["llm", "rule_based", "hybrid"] = Field(
        default="llm", description="How the query analysis was produced"
    )


class PilgrimageLocation(BaseModel):
    """A real-world anime pilgrimage spot."""

    name: str = Field(..., description="Name of the real-world location")
    japanese_name: str = Field(default="", description="Japanese name for accurate navigation/geocoding")
    anime_title: str = Field(..., description="Associated anime title")
    city: str = Field(default="", description="City or ward (e.g., Shinjuku, Hida Takayama)")
    prefecture: str = Field(default="", description="Prefecture (e.g., Tokyo, Gifu, Kyoto)")
    real_world_address: str = Field(default="", description="Real-world street address")
    coordinates: Coordinates | None = Field(default=None, description="GPS coordinates")
    description: str = Field(default="", description="Description of the location")
    scene_description: str = Field(default="", description="Scene featured in the anime")
    episode_reference: str = Field(default="", description="Episode, movie timestamp, or arc")
    access_method: str = Field(default="", description="Nearest station and access instructions")
    nearby_attractions: list[str] = Field(default_factory=list, description="Nearby points of interest")
    best_visit_time: str = Field(default="", description="Recommended time of day/season")
    photography_notes: str = Field(default="", description="Camera angle or framing notes")
    etiquette_notes: str = Field(default="", description="Local rules or etiquette reminders")
    source_url: str = Field(default="", description="Verification source URL")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Data accuracy confidence")


class ScheduledStop(BaseModel):
    """A timed stop within a daily itinerary."""

    order: int = Field(..., ge=1, description="1-based stop sequence number")
    location: PilgrimageLocation
    arrival_time: str = Field(default="", description="Estimated arrival time (HH:MM)")
    departure_time: str = Field(default="", description="Estimated departure time (HH:MM)")
    visit_duration_minutes: int = Field(default=60, ge=10, description="Planned dwell time in minutes")
    activity: str = Field(default="", description="Suggested activity at this stop")
    travel_to_next_minutes: int | None = Field(
        default=None, description="Estimated transit minutes to the next stop"
    )
    travel_to_next_km: float | None = Field(
        default=None, description="Straight-line distance in km to the next stop"
    )
    travel_mode_to_next: str | None = Field(
        default=None, description="Suggested transit mode to the next stop"
    )


class DailyItinerary(BaseModel):
    """A single day's optimized sightseeing plan."""

    day: int = Field(..., ge=1, description="Day number")
    title: str = Field(default="", description="Theme or area title for the day")
    city_focus: str = Field(default="", description="Primary city or region for the day")
    date: str | None = Field(default=None, description="Optional calendar date")
    stops: list[ScheduledStop] = Field(default_factory=list, description="Detailed ordered stops")
    locations: list[str] = Field(default_factory=list, description="Ordered location names")
    activities: list[str] = Field(default_factory=list, description="Ordered activities")
    travel_times: list[int] = Field(
        default_factory=list, description="Travel times in minutes between consecutive stops"
    )
    total_travel_time: int = Field(default=0, ge=0, description="Total travel time in minutes")
    total_visit_time: int = Field(default=0, ge=0, description="Total visit time in minutes")
    estimated_cost: dict[str, float] = Field(default_factory=dict, description="Daily cost breakdown (JPY)")
    notes: list[str] = Field(default_factory=list, description="Day-specific notes and tips")


class TravelPlan(BaseModel):
    """Complete multi-day pilgrimage travel plan."""

    trip_title: str = Field(..., description="Title of the trip")
    destination: str = Field(..., description="Primary destination summary")
    regions: list[str] = Field(default_factory=list, description="Regions/cities covered")
    duration_days: int = Field(..., ge=0, description="Total trip duration in days")
    total_locations: int = Field(..., ge=0, description="Total number of scheduled locations")
    daily_itineraries: list[DailyItinerary] = Field(default_factory=list)
    total_estimated_cost: dict[str, float] = Field(
        default_factory=dict, description="Total cost breakdown (JPY)"
    )
    budget_level: str = Field(default="standard", description="Applied travel style / budget tier")
    transportation_mode: str = Field(default="mixed", description="Primary transportation mode")
    accommodation_suggestions: list[str] = Field(default_factory=list)
    general_tips: list[str] = Field(default_factory=list)
    emergency_contacts: dict[str, str] = Field(default_factory=dict)


class GeneratedResponse(BaseModel):
    """Final user-facing and API-ready response payload."""

    response_type: Literal["itinerary", "clarification", "error"]
    title: str = Field(..., description="Response title")
    introduction: str = Field(..., description="Opening summary")
    main_content: str = Field(..., description="Formatted markdown travel guide or message")
    markdown_content: str = Field(default="", description="Full exportable markdown document")
    summary: str = Field(..., description="Brief summary of the plan")
    recommendations: list[str] = Field(default_factory=list)
    disambiguation_needed: bool = Field(default=False)
    disambiguation_questions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    travel_plan: TravelPlan | None = Field(default=None)
    locations: list[PilgrimageLocation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
