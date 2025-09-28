from typing import Dict, List, Optional, Any
import json
import re
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_community.llms import HuggingFaceEndpoint
from config import Config

class ItineraryAgent:
    def __init__(self):
        self.llm = HuggingFaceEndpoint(
            repo_id=Config.HUGGINGFACE_MODEL_NAME,
            task="text-generation",
            max_length=2000,
            temperature=0.8,
        )

        self.seichi_junrei_locations = {
            "Slam Dunk": {
                "Kanagawa": {
                    "Shohoku High School": {
                        "real_location": "Kamakura High School",
                        "address": "Kamakura, Kanagawa Prefecture",
                        "description": "The iconic school where Hanamichi Sakuragi played basketball",
                        "coordinates": [35.3193, 139.5529],
                        "activities": ["Visit the school gate", "Take photos", "Explore Kamakura area"]
                    }
                },
                "Tokyo": {
                    "Tokyo Metropolitan Gymnasium": {
                        "address": "Sendagaya, Shibuya, Tokyo",
                        "description": "Inter-high tournament venue",
                        "coordinates": [35.6848, 139.7087],
                        "activities": ["Visit the gymnasium", "Watch basketball games", "Sports museum"]
                    }
                }
            },
            "Your Name": {
                "Tokyo": {
                    "Shinjuku Gyoen": {
                        "address": "Shinjuku, Tokyo",
                        "description": "Park where Taki and Mitsuha met",
                        "coordinates": [35.6852, 139.7017],
                        "activities": ["Walk through the park", "Visit the shrine", "Photography"]
                    },
                    "Suga Shrine Steps": {
                        "address": "Yotsuya, Tokyo",
                        "description": "Iconic staircase scene",
                        "coordinates": [35.6880, 139.7320],
                        "activities": ["Visit the shrine", "Take photos at the steps", "Explore the neighborhood"]
                    }
                }
            },
            "One Piece": {
                "Tokyo": {
                    "Tokyo Tower": {
                        "address": "Minato, Tokyo",
                        "description": "Marianne location inspiration",
                        "coordinates": [35.6586, 139.7454],
                        "activities": ["Climb the tower", "City views", "One Piece themed cafe"]
                    }
                }
            }
        }

    @tool
    def generate_itinerary(self, destination: str, duration: int, interests: List[str],
                          anime_theme: Optional[str] = None, budget_level: str = "medium") -> Dict:
        """
        Generate a comprehensive travel itinerary
        """
        base_itinerary = self._create_base_itinerary(destination, duration)

        if anime_theme:
            anime_locations = self.get_anime_locations(anime_theme, destination)
            base_itinerary = self._integrate_anime_locations(base_itinerary, anime_locations)

        return base_itinerary

    @tool
    def get_anime_locations(self, anime_title: str, region: str = "Japan") -> Dict:
        """
        Get anime pilgrimage locations for a specific anime
        """
        anime_data = self.seichi_junrei_locations.get(anime_title, {})
        region_locations = {}

        for location, details in anime_data.items():
            if region.lower() in location.lower():
                region_locations[location] = details

        return region_locations if region_locations else anime_data

    @tool
    def optimize_route(self, locations: List[Dict], start_point: str, end_point: str) -> Dict:
        """
        Optimize travel route between multiple locations
        """
        optimized_route = []
        current_location = start_point
        remaining_locations = locations.copy()

        while remaining_locations:
            nearest_location = min(remaining_locations,
                                key=lambda x: self._calculate_distance(current_location, x.get('address', '')))
            optimized_route.append(nearest_location)
            remaining_locations.remove(nearest_location)
            current_location = nearest_location.get('address', '')

        return {
            "optimized_route": optimized_route,
            "total_estimated_time": len(optimized_route) * 2.5  # hours per location
        }

    def _create_base_itinerary(self, destination: str, duration: int) -> Dict:
        """
        Create a base itinerary template
        """
        itinerary = {
            "destination": destination,
            "duration_days": duration,
            "daily_plans": []
        }

        common_activities = [
            "Explore local cuisine",
            "Visit cultural landmarks",
            "Shopping in popular districts",
            "Relax at parks or gardens",
            "Experience nightlife or entertainment"
        ]

        for day in range(1, duration + 1):
            daily_plan = {
                "day": day,
                "theme": f"Day {day} - Exploring {destination}",
                "morning": {
                    "activity": common_activities[(day-1) % len(common_activities)],
                    "time": "09:00 - 12:00",
                    "estimated_cost": "$30-50"
                },
                "afternoon": {
                    "activity": common_activities[day % len(common_activities)],
                    "time": "13:00 - 17:00",
                    "estimated_cost": "$40-70"
                },
                "evening": {
                    "activity": "Dinner and relaxation",
                    "time": "18:00 - 21:00",
                    "estimated_cost": "$25-45"
                },
                "estimated_daily_total": "$95-165"
            }
            itinerary["daily_plans"].append(daily_plan)

        return itinerary

    def _integrate_anime_locations(self, itinerary: Dict, anime_locations: Dict) -> Dict:
        """
        Integrate anime pilgrimage locations into the itinerary
        """
        all_anime_spots = []
        for city, locations in anime_locations.items():
            for spot_name, spot_info in locations.items():
                all_anime_spots.append({
                    "name": spot_name,
                    "city": city,
                    "info": spot_info
                })

        spots_per_day = max(1, len(all_anime_spots) // len(itinerary["daily_plans"]))

        for i, daily_plan in enumerate(itinerary["daily_plans"]):
            start_idx = i * spots_per_day
            end_idx = start_idx + spots_per_day
            day_spots = all_anime_spots[start_idx:end_idx]

            if day_spots:
                daily_plan["anime_pilgrimage"] = []
                for spot in day_spots:
                    daily_plan["anime_pilgrimage"].append({
                        "location": spot["name"],
                        "address": spot["info"]["address"],
                        "description": spot["info"]["description"],
                        "activities": spot["info"]["activities"],
                        "coordinates": spot["info"]["coordinates"],
                        "best_time": "09:00 - 12:00" if len(daily_plan["anime_pilgrimage"]) == 0 else "13:00 - 17:00"
                    })

                daily_plan["theme"] = f"Day {i+1} - Anime Pilgrimage in {daily_plan['anime_pilgrimage'][0]['city']}"
                daily_plan["estimated_daily_total"] = "$120-200"

        return itinerary

    def _calculate_distance(self, location1: str, location2: str) -> float:
        """
        Simple distance calculation (mock implementation)
        """
        return abs(hash(location1) - hash(location2)) % 100

    def process_itinerary_query(self, query: str, flight_info: Optional[Dict] = None,
                               weather_info: Optional[Dict] = None) -> str:
        """
        Process itinerary planning queries using the LLM
        """
        context = ""
        if flight_info:
            context += f"Flight Information: {json.dumps(flight_info, indent=2)}\n"
        if weather_info:
            context += f"Weather Information: {json.dumps(weather_info, indent=2)}\n"

        messages = [
            HumanMessage(content=f"""
            You are an expert travel itinerary planner specializing in anime pilgrimage (Seichi Junrei).
            Analyze the following query and create a detailed travel plan:

            {context}
            Query: {query}

            Please extract and return in JSON format:
            - destination: Main destination
            - duration: Trip duration in days
            - interests: List of interests/hobbies
            - anime_theme: Specific anime for pilgrimage (if mentioned)
            - budget_level: Budget level (budget/medium/luxury)
            - special_requirements: Any special requirements
            - departure_location: Where they're traveling from
            """)
        ]

        response = self.llm.invoke(messages)

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group())

                itinerary = self.generate_itinerary(
                    destination=params.get('destination', 'Japan'),
                    duration=params.get('duration', 7),
                    interests=params.get('interests', []),
                    anime_theme=params.get('anime_theme'),
                    budget_level=params.get('budget_level', 'medium')
                )

                return self._format_itinerary(itinerary, params.get('anime_theme'))
            else:
                return "I couldn't parse the itinerary query. Please provide more specific information about destination, duration, and interests."

        except Exception as e:
            return f"Error processing itinerary query: {str(e)}"

    def _format_itinerary(self, itinerary: Dict, anime_theme: Optional[str] = None) -> str:
        """
        Format itinerary for display
        """
        result = f"🗺️ **{itinerary['duration_days']}-Day Travel Plan for {itinerary['destination']}**\n\n"

        if anime_theme:
            result += f"🎌 **Special Theme: {anime_theme} Pilgrimage**\n\n"

        for day_plan in itinerary["daily_plans"]:
            result += f"### Day {day_plan['day']}: {day_plan['theme']}\n\n"

            if "anime_pilgrimage" in day_plan:
                result += "🎬 **Anime Pilgrimage Locations:**\n"
                for spot in day_plan["anime_pilgrimage"]:
                    result += f"- **{spot['location']}** ({spot['address']})\n"
                    result += f"  Description: {spot['description']}\n"
                    result += f"  Activities: {', '.join(spot['activities'])}\n"
                    result += f"  Best time: {spot['best_time']}\n\n"

            result += "**Regular Activities:**\n"
            result += f"🌅 **Morning** ({day_plan['morning']['time']}): {day_plan['morning']['activity']} - {day_plan['morning']['estimated_cost']}\n"
            result += f"🌞 **Afternoon** ({day_plan['afternoon']['time']}): {day_plan['afternoon']['activity']} - {day_plan['afternoon']['estimated_cost']}\n"
            result += f"🌙 **Evening** ({day_plan['evening']['time']}): {day_plan['evening']['activity']} - {day_plan['evening']['estimated_cost']}\n"
            result += f"💰 **Daily Total**: {day_plan['estimated_daily_total']}\n\n"

        return result

    def get_recommendations(self, destination: str, interests: List[str],
                           weather_preferences: Optional[Dict] = None) -> Dict:
        """
        Get personalized recommendations based on interests and weather
        """
        recommendations = {
            "destination": destination,
            "interests": interests,
            "recommendations": []
        }

        interest_mapping = {
            "food": ["Try local street food markets", "Visit traditional restaurants", "Take cooking classes"],
            "culture": ["Visit museums and temples", "Attend cultural festivals", "Explore historic districts"],
            "nature": ["Visit parks and gardens", "Hiking trails", "Sc viewpoints"],
            "shopping": ["Shopping districts", "Local markets", "Department stores"],
            "entertainment": ["Theme parks", "Game centers", "Live performances"]
        }

        for interest in interests:
            for key, activities in interest_mapping.items():
                if key in interest.lower():
                    recommendations["recommendations"].extend(activities)

        if weather_preferences:
            if weather_preferences.get("prefer_indoor"):
                indoor_activities = ["Museums", "Shopping malls", "Indoor attractions", "Cafes"]
                recommendations["recommendations"].extend(indoor_activities)

        return recommendations