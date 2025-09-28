from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class AgentState(Enum):
    IDLE = "idle"
    ANALYZING_QUERY = "analyzing_query"
    IDENTIFYING_ANIME = "identifying_anime"
    FINDING_LOCATIONS = "finding_locations"
    CRAWLING_DATA = "crawling_data"
    PLANNING_TRIP = "planning_trip"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"

@dataclass
class AnimeInfo:
    title: str
    alternative_titles: List[str]
    genres: List[str]
    year: Optional[int] = None
    description: Optional[str] = None
    pilgrimage_locations: List[Dict[str, Any]] = None

@dataclass
class LocationInfo:
    name: str
    address: str
    latitude: float
    longitude: float
    description: str
    anime_reference: str
    scene_description: Optional[str] = None
    accessibility_info: Optional[str] = None
    nearby_attractions: List[str] = None

@dataclass
class TripPlan:
    anime_title: str
    locations: List[LocationInfo]
    itinerary: List[Dict[str, Any]]
    estimated_duration: str
    total_distance: Optional[float] = None
    budget_estimate: Optional[Dict[str, float]] = None
    travel_tips: List[str] = None

@dataclass
class AgentMessage:
    sender: str
    receiver: str
    content: Any
    message_type: str
    timestamp: str

class WorkflowState:
    def __init__(self):
        self.current_state = AgentState.IDLE
        self.user_query: str = ""
        self.anime_info: Optional[AnimeInfo] = None
        self.locations: List[LocationInfo] = []
        self.trip_plan: Optional[TripPlan] = None
        self.messages: List[AgentMessage] = []
        self.errors: List[str] = []

    def add_message(self, sender: str, receiver: str, content: Any, message_type: str):
        from datetime import datetime
        message = AgentMessage(
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
            timestamp=datetime.now().isoformat()
        )
        self.messages.append(message)

    def get_messages_for_agent(self, agent_name: str) -> List[AgentMessage]:
        return [msg for msg in self.messages if msg.receiver == agent_name]