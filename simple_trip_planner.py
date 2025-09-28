#!/usr/bin/env python3
"""
Simplified Multi-Agent Trip Planning System
Specializing in Anime Pilgrimage (Seichi Junrei) Travel
"""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from agents import FlightAgent, WeatherAgent, ItineraryAgent, MapAgent
from llm_integration import LLMManager
from config import Config

class SimpleTripPlanner:
    """
    Simplified trip planning system without complex LangGraph workflows
    """

    def __init__(self):
        self.llm_manager = LLMManager()
        self.flight_agent = FlightAgent()
        self.weather_agent = WeatherAgent()
        self.itinerary_agent = ItineraryAgent()
        self.map_agent = MapAgent()

    def parse_query_with_llm(self, query: str) -> Dict[str, Any]:
        """Parse the user query using LLM"""
        llm = self.llm_manager.get_model()
        if not llm:
            return self._fallback_parse_query(query)

        system_message = """
        You are a trip planning assistant. Analyze the user's query and extract key information:

        Return a JSON object with:
        - origin: Origin location
        - destination: Destination location
        - duration: Trip duration in days
        - departure_date: Departure date (YYYY-MM-DD) or null
        - return_date: Return date (YYYY-MM-DD) or null
        - interests: List of interests
        - anime_theme: Specific anime for pilgrimage (if mentioned)
        - budget_level: Budget level (budget/medium/luxury)
        - special_requirements: Any special requirements
        - needs_flight: Boolean - if flight search needed
        - needs_weather: Boolean - if weather check needed
        - needs_maps: Boolean - if map creation needed
        """

        try:
            response = llm.invoke([
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Parse this trip planning query: {query}"}
            ])

            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

        except Exception as e:
            print(f"[ERROR] LLM parsing failed: {e}")

        return self._fallback_parse_query(query)

    def _fallback_parse_query(self, query: str) -> Dict[str, Any]:
        """Fallback parsing using simple keyword matching"""
        parsed = {
            "origin": "Taiwan",
            "destination": "Japan",
            "duration": 7,
            "departure_date": None,
            "return_date": None,
            "interests": ["anime", "culture", "sightseeing"],
            "anime_theme": None,
            "budget_level": "medium",
            "special_requirements": [],
            "needs_flight": True,
            "needs_weather": True,
            "needs_maps": True
        }

        # Extract anime theme
        if "slam dunk" in query.lower():
            parsed["anime_theme"] = "Slam Dunk"
        elif "your name" in query.lower():
            parsed["anime_theme"] = "Your Name"
        elif "one piece" in query.lower():
            parsed["anime_theme"] = "One Piece"

        # Extract duration
        duration_match = re.search(r'(\d+)-?days?', query.lower())
        if duration_match:
            parsed["duration"] = int(duration_match.group(1))

        # Extract origin and destination
        if "from" in query.lower() and "to" in query.lower():
            parts = query.lower().split("from")
            if len(parts) > 1:
                to_parts = parts[1].split("to")
                if len(to_parts) > 1:
                    parsed["origin"] = to_parts[0].strip()
                    parsed["destination"] = to_parts[1].strip()

        return parsed

    def plan_trip(self, query: str) -> Dict[str, Any]:
        """Plan a complete trip using sequential agent calls"""
        print("[PLANNER] Starting trip planning...")

        # Step 1: Parse query
        print("[STEP 1] Parsing query...")
        parsed_data = self.parse_query_with_llm(query)
        print(f"[PARSED] {json.dumps(parsed_data, indent=2)}")

        result = {
            "query": query,
            "parsed_data": parsed_data,
            "flight_info": {},
            "weather_info": {},
            "itinerary": {},
            "maps": {},
            "anime_map": "",
            "travel_stats": {},
            "recommendations": []
        }

        # Step 2: Search flights if needed
        if parsed_data.get("needs_flight", False):
            print("[STEP 2] Searching flights...")
            try:
                origin = parsed_data.get("origin", "")
                destination = parsed_data.get("destination", "")
                departure_date = parsed_data.get("departure_date") or "2024-12-01"

                if origin and destination:
                    # Call the agent method directly
                    flight_result = self.flight_agent._mock_flight_search(
                        origin=origin,
                        destination=destination,
                        departure_date=departure_date
                    )
                    result["flight_info"] = flight_result
                    print("[FLIGHTS] Flight search completed")
            except Exception as e:
                print(f"[ERROR] Flight search failed: {e}")
                result["flight_info"] = {"error": str(e)}

        # Step 3: Check weather if needed
        if parsed_data.get("needs_weather", False):
            print("[STEP 3] Checking weather...")
            try:
                destination = parsed_data.get("destination", "")
                duration = parsed_data.get("duration", 7)

                if destination:
                    # Call the agent methods directly
                    current_weather = self.weather_agent._mock_weather_data(destination)
                    forecast = self.weather_agent._mock_forecast_data(destination, duration)
                    best_days = {}  # Simplified for now

                    result["weather_info"] = {
                        "current": current_weather,
                        "forecast": forecast,
                        "best_travel_days": best_days
                    }
                    print("[WEATHER] Weather check completed")
            except Exception as e:
                print(f"[ERROR] Weather check failed: {e}")
                result["weather_info"] = {"error": str(e)}

        # Step 4: Plan itinerary
        print("[STEP 4] Planning itinerary...")
        try:
            destination = parsed_data.get("destination", "Japan")
            duration = parsed_data.get("duration", 7)
            interests = parsed_data.get("interests", [])
            anime_theme = parsed_data.get("anime_theme")
            budget_level = parsed_data.get("budget_level", "medium")

            # Call the agent method directly
            itinerary = self.itinerary_agent._create_base_itinerary(destination, duration)

            if anime_theme:
                anime_locations = self.itinerary_agent.get_anime_locations(anime_theme, destination)
                itinerary = self.itinerary_agent._integrate_anime_locations(itinerary, anime_locations)

            result["itinerary"] = itinerary
            print("[ITINERARY] Itinerary planning completed")
        except Exception as e:
            print(f"[ERROR] Itinerary planning failed: {e}")
            result["itinerary"] = {"error": str(e)}

        # Step 5: Create maps if needed
        if parsed_data.get("needs_maps", True):
            print("[STEP 5] Creating maps...")
            try:
                itinerary = result.get("itinerary", {})
                anime_theme = parsed_data.get("anime_theme")

                if anime_theme:
                    # Create anime map directly
                    from typing import Dict
                    anime_locations = {
                        "Slam Dunk": [
                            {"name": "Shohoku High School (Kamakura High School)", "lat": 35.3193, "lon": 139.5529, "desc": "Hanamichi Sakuragi's school", "city": "Kamakura"},
                            {"name": "Tokyo Metropolitan Gymnasium", "lat": 35.6848, "lon": 139.7087, "desc": "Inter-high tournament venue", "city": "Tokyo"}
                        ]
                    }

                    locations = anime_locations.get(anime_theme, [])
                    if locations:
                        import folium
                        center_lat = sum(loc["lat"] for loc in locations) / len(locations)
                        center_lon = sum(loc["lon"] for loc in locations) / len(locations)

                        m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

                        for location in locations:
                            popup_content = f"""
                            <b>{location['name']}</b><br>
                            {location['desc']}<br>
                            <small>City: {location['city']}</small>
                            """

                            folium.Marker(
                                [location["lat"], location["lon"]],
                                popup=popup_content,
                                tooltip=location["name"],
                                icon=folium.Icon(color="red", icon="star")
                            ).add_to(m)

                        anime_map_file = f"{anime_theme.lower().replace(' ', '_')}_pilgrimage_map.html"
                        m.save(anime_map_file)
                        result["anime_map"] = anime_map_file
                        print(f"[MAPS] Anime map created: {anime_map_file}")

                comprehensive_maps = self.map_agent.create_comprehensive_travel_map(itinerary)
                result["maps"] = comprehensive_maps
                print(f"[MAPS] Comprehensive maps created: {len(comprehensive_maps)} maps")

                # Calculate travel statistics
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
                    result["travel_stats"] = stats
                    print(f"[STATS] Travel statistics calculated")

            except Exception as e:
                print(f"[ERROR] Map creation failed: {e}")
                result["maps"] = {"error": str(e)}

        # Step 6: Generate recommendations
        print("[STEP 6] Generating recommendations...")
        result["recommendations"] = self._generate_recommendations(result, parsed_data)
        print("[RECOMMENDATIONS] Recommendations generated")

        print("[PLANNER] Trip planning completed!")
        return result

    def _generate_recommendations(self, result: Dict[str, Any], parsed_data: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []

        # Weather recommendations
        if result.get("weather_info"):
            weather = result["weather_info"]
            if "best_travel_days" in weather:
                recommendations.append("Best travel days based on weather: Check the forecast data")

        # Flight recommendations
        if result.get("flight_info"):
            flight = result["flight_info"]
            if isinstance(flight, dict) and "data" in flight:
                recommendations.append("Multiple flight options available - compare prices and schedules")

        # Anime-specific recommendations
        if parsed_data.get("anime_theme"):
            recommendations.append(f"Don't forget to bring a camera for your {parsed_data['anime_theme']} pilgrimage!")
            recommendations.append("Consider learning basic Japanese phrases for better interaction with locals")

        # General travel recommendations
        recommendations.extend([
            "Pack comfortable walking shoes for extensive sightseeing",
            "Consider getting a JR Pass for convenient train travel in Japan",
            "Download offline maps and translation apps before your trip",
            "Make hotel reservations in advance, especially during peak seasons",
            "Try local cuisine at each destination",
            "Respect local customs and traditions"
        ])

        return recommendations

    def format_response_for_display(self, response: Dict[str, Any]) -> str:
        """Format the response for user-friendly display"""
        if "error" in response:
            return f"[ERROR] Error: {response['error']}"

        output = f"*** Trip Planning Complete ***\n\n"
        output += f"Query: {response.get('query', 'Unknown')}\n\n"

        # Flight information
        if response.get("flight_info"):
            flight_info = response["flight_info"]
            if isinstance(flight_info, dict) and "data" in flight_info:
                output += self.flight_agent._format_flight_results(flight_info)
            elif "error" not in flight_info:
                output += f"[FLIGHTS] Flight information available\n\n"

        # Weather information
        if response.get("weather_info"):
            weather_info = response["weather_info"]
            if isinstance(weather_info, dict) and "current" in weather_info:
                output += self.weather_agent._format_current_weather(weather_info["current"])
            elif "error" not in weather_info:
                output += f"[WEATHER] Weather information available\n\n"

        # Itinerary
        if response.get("itinerary"):
            itinerary = response["itinerary"]
            if "error" not in itinerary:
                output += self.itinerary_agent._format_itinerary(
                    itinerary,
                    response.get("parsed_data", {}).get("anime_theme")
                )

        # Travel statistics
        if response.get("travel_stats"):
            stats = response["travel_stats"]
            output += "\n[TRAVEL STATS]\n"
            output += f"- Total distance: {stats.get('total_distance_km', 0)} km\n"
            output += f"- Estimated travel time: {stats.get('estimated_travel_time_hours', 0)} hours\n"
            output += f"- Number of locations: {stats.get('number_of_locations', 0)}\n\n"

        # Recommendations
        if response.get("recommendations"):
            output += "\n[RECOMMENDATIONS]\n"
            for rec in response["recommendations"]:
                output += f"- {rec}\n"

        # Maps created
        if response.get("maps"):
            output += "\n[MAPS CREATED]\n"
            for map_name, map_file in response["maps"].items():
                output += f"- {map_name}: {map_file}\n"

        if response.get("anime_map"):
            output += f"- Anime Pilgrimage Map: {response['anime_map']}\n"

        return output

def main():
    """Main function for testing"""
    try:
        Config.validate_config()
        planner = SimpleTripPlanner()

        # Test with the Taiwan to Japan Slam Dunk example
        query = "7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Slam Dunk"
        print(f"[TEST] Planning trip: {query}")
        print("=" * 60)

        result = planner.plan_trip(query)

        print("\n" + "=" * 60)
        print("[RESULT] Trip Planning Result:")
        print("=" * 60)

        formatted_output = planner.format_response_for_display(result)
        print(formatted_output)

        return result

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    main()