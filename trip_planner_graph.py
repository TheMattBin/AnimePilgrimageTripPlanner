from typing import Dict, List, Optional, Any, Annotated
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agents import FlightAgent, WeatherAgent, ItineraryAgent, MapAgent
from llm_integration import LLMManager
from config import Config
import json

class TripPlannerGraph:
    """
    LangGraph-based multi-agent trip planning system
    """

    def __init__(self):
        self.llm_manager = LLMManager()
        self.flight_agent = FlightAgent()
        self.weather_agent = WeatherAgent()
        self.itinerary_agent = ItineraryAgent()
        self.map_agent = MapAgent()

        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow"""
        from typing import TypedDict

        class TripState(TypedDict):
            query: str
            parsed_data: Dict[str, Any]
            flight_info: Dict[str, Any]
            weather_info: Dict[str, Any]
            itinerary: Dict[str, Any]
            map_files: Dict[str, str]
            final_response: Dict[str, Any]

        workflow = StateGraph(TripState)

        workflow.add_node("parse_query", self._parse_query)
        workflow.add_node("flight_search", self._search_flights)
        workflow.add_node("weather_check", self._check_weather)
        workflow.add_node("itinerary_planning", self._plan_itinerary)
        workflow.add_node("map_creation", self._create_maps)
        workflow.add_node("finalize_response", self._finalize_response)

        workflow.add_edge(START, "parse_query")
        workflow.add_edge("parse_query", "flight_search")
        workflow.add_edge("parse_query", "weather_check")
        workflow.add_edge("flight_search", "itinerary_planning")
        workflow.add_edge("weather_check", "itinerary_planning")
        workflow.add_edge("itinerary_planning", "map_creation")
        workflow.add_edge("map_creation", "finalize_response")
        workflow.add_edge("finalize_response", END)

        return workflow.compile()

    def _parse_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and analyze the user's trip planning query"""
        query = state.get("query", "")

        llm = self.llm_manager.get_model()
        if not llm:
            return {"error": "No LLM available"}

        system_message = SystemMessage(content="""
        You are a trip planning assistant. Analyze the user's query and extract key information:

        Return a JSON object with:
        - origin: Origin location
        - destination: Destination location
        - duration: Trip duration in days
        - departure_date: Departure date (YYYY-MM-DD)
        - return_date: Return date (YYYY-MM-DD)
        - interests: List of interests
        - anime_theme: Specific anime for pilgrimage (if mentioned)
        - budget_level: Budget level (budget/medium/luxury)
        - special_requirements: Any special requirements
        - needs_flight: Boolean - if flight search needed
        - needs_weather: Boolean - if weather check needed
        - needs_maps: Boolean - if map creation needed
        """)

        human_message = HumanMessage(content=f"Parse this trip planning query: {query}")

        try:
            response = llm.invoke([system_message, human_message])

            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group())
                state.update(parsed_data)
            else:
                state["parse_error"] = "Could not parse query"

        except Exception as e:
            state["parse_error"] = f"Error parsing query: {str(e)}"

        return state

    def _search_flights(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Search for flights based on parsed query"""
        if not state.get("needs_flight", False):
            state["flight_info"] = {"message": "Flight search not requested"}
            return state

        try:
            origin = state.get("origin", "")
            destination = state.get("destination", "")
            departure_date = state.get("departure_date", "")
            return_date = state.get("return_date")

            if origin and destination and departure_date:
                flight_result = self.flight_agent.search_flights(
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date,
                    return_date=return_date
                )
                state["flight_info"] = flight_result
            else:
                state["flight_info"] = {"error": "Missing flight search parameters"}

        except Exception as e:
            state["flight_info"] = {"error": f"Flight search error: {str(e)}"}

        return state

    def _check_weather(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check weather conditions for destination"""
        if not state.get("needs_weather", False):
            state["weather_info"] = {"message": "Weather check not requested"}
            return state

        try:
            destination = state.get("destination", "")
            duration = state.get("duration", 7)

            if destination:
                current_weather = self.weather_agent.get_current_weather(destination)
                forecast = self.weather_agent.get_forecast(destination, days=duration)
                best_days = self.weather_agent.get_best_travel_days([destination])

                state["weather_info"] = {
                    "current": current_weather,
                    "forecast": forecast,
                    "best_travel_days": best_days
                }
            else:
                state["weather_info"] = {"error": "Missing destination for weather check"}

        except Exception as e:
            state["weather_info"] = {"error": f"Weather check error: {str(e)}"}

        return state

    def _plan_itinerary(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed travel itinerary"""
        try:
            destination = state.get("destination", "")
            duration = state.get("duration", 7)
            interests = state.get("interests", [])
            anime_theme = state.get("anime_theme")
            budget_level = state.get("budget_level", "medium")

            if destination and duration:
                itinerary = self.itinerary_agent.generate_itinerary(
                    destination=destination,
                    duration=duration,
                    interests=interests,
                    anime_theme=anime_theme,
                    budget_level=budget_level
                )

                state["itinerary"] = itinerary
            else:
                state["itinerary"] = {"error": "Missing destination or duration"}

        except Exception as e:
            state["itinerary"] = {"error": f"Itinerary planning error: {str(e)}"}

        return state

    def _create_maps(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create maps for the trip"""
        if not state.get("needs_maps", True):
            state["map_info"] = {"message": "Map creation not requested"}
            return state

        try:
            itinerary = state.get("itinerary", {})
            anime_theme = state.get("anime_theme")

            if itinerary:
                if anime_theme:
                    anime_map_file = self.map_agent.create_anime_pilgrimage_map(anime_theme)
                    state["anime_map"] = anime_map_file

                comprehensive_maps = self.map_agent.create_comprehensive_travel_map(itinerary)
                state["map_files"] = comprehensive_maps

                locations = []
                for day_plan in itinerary.get("daily_plans", []):
                    if "anime_pilgrimage" in day_plan:
                        for spot in day_plan["anime_pilgrimage"]:
                            coords = spot.get("coordinates", [0, 0])
                            locations.append({
                                "latitude": coords[0],
                                "longitude": coords[1],
                                "name": spot["location"],
                                "description": spot["description"]
                            })

                if locations:
                    stats = self.map_agent.get_travel_statistics(locations)
                    state["travel_stats"] = stats

            else:
                state["map_info"] = {"error": "No itinerary available for map creation"}

        except Exception as e:
            state["map_info"] = {"error": f"Map creation error: {str(e)}"}

        return state

    def _finalize_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create final comprehensive response"""
        response = {
            "query": state.get("query", ""),
            "summary": self._generate_summary(state),
            "flight_info": state.get("flight_info", {}),
            "weather_info": state.get("weather_info", {}),
            "itinerary": state.get("itinerary", {}),
            "maps": state.get("map_files", {}),
            "anime_map": state.get("anime_map", ""),
            "travel_stats": state.get("travel_stats", {}),
            "recommendations": self._generate_recommendations(state)
        }

        state["final_response"] = response
        return state

    def _generate_summary(self, state: Dict[str, Any]) -> str:
        """Generate a trip summary"""
        destination = state.get("destination", "Unknown")
        duration = state.get("duration", 7)
        anime_theme = state.get("anime_theme")

        summary = f"Your {duration}-day trip to {destination}"
        if anime_theme:
            summary += f" with a special focus on {anime_theme} pilgrimage"
        summary += " has been planned successfully!"

        return summary

    def _generate_recommendations(self, state: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []

        if state.get("weather_info"):
            weather = state["weather_info"]
            if "best_travel_days" in weather:
                recommendations.append("Best travel days based on weather: " + str(weather["best_travel_days"]))

        if state.get("flight_info"):
            flight = state["flight_info"]
            if isinstance(flight, dict) and "data" in flight:
                recommendations.append("Multiple flight options available - check the flight details for best prices and times.")

        if state.get("anime_theme"):
            recommendations.append("Don't forget to bring a camera for your anime pilgrimage!")
            recommendations.append("Consider learning basic Japanese phrases for better interaction with locals.")

        recommendations.extend([
            "Pack comfortable walking shoes for extensive sightseeing.",
            "Consider getting a JR Pass for convenient train travel in Japan.",
            "Download offline maps and translation apps before your trip.",
            "Make hotel reservations in advance, especially during peak seasons."
        ])

        return recommendations

    def plan_trip(self, query: str) -> Dict[str, Any]:
        """Plan a complete trip using the multi-agent system"""
        try:
            initial_state = {"query": query}
            result = self.graph.invoke(initial_state)
            return result.get("final_response", {})
        except Exception as e:
            return {"error": f"Trip planning error: {str(e)}"}

    def format_response_for_display(self, response: Dict[str, Any]) -> str:
        """Format the response for user-friendly display"""
        if "error" in response:
            return f"❌ Error: {response['error']}"

        output = f"🌟 **{response.get('summary', 'Trip Planning Complete')}**\n\n"

        if response.get("flight_info"):
            flight_info = response["flight_info"]
            if isinstance(flight_info, dict) and "data" in flight_info:
                output += self.flight_agent._format_flight_results(flight_info)
            else:
                output += f"✈️ **Flight Information**: {flight_info.get('message', 'No flight search performed')}\n\n"

        if response.get("weather_info"):
            weather_info = response["weather_info"]
            if isinstance(weather_info, dict) and "current" in weather_info:
                output += self.weather_agent._format_current_weather(weather_info["current"])
            else:
                output += f"🌤️ **Weather Information**: {weather_info.get('message', 'No weather check performed')}\n\n"

        if response.get("itinerary"):
            itinerary = response["itinerary"]
            output += self.itinerary_agent._format_itinerary(
                itinerary,
                response.get("query", "").lower().find("slam dunk") != -1 and "Slam Dunk" or None
            )

        if response.get("travel_stats"):
            stats = response["travel_stats"]
            output += "\n📊 **Travel Statistics**:\n"
            output += f"- Total distance: {stats.get('total_distance_km', 0)} km\n"
            output += f"- Estimated travel time: {stats.get('estimated_travel_time_hours', 0)} hours\n"
            output += f"- Number of locations: {stats.get('number_of_locations', 0)}\n\n"

        if response.get("recommendations"):
            output += "\n💡 **Recommendations**:\n"
            for rec in response["recommendations"]:
                output += f"- {rec}\n"

        if response.get("map_files"):
            output += "\n🗺️ **Maps Created**:\n"
            for map_name, map_file in response["map_files"].items():
                output += f"- {map_name}: {map_file}\n"

        if response.get("anime_map"):
            output += f"- Anime Pilgrimage Map: {response['anime_map']}\n"

        return output