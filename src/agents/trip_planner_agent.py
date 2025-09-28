from typing import List, Dict, Any
import math
from datetime import datetime, timedelta
from .core_types import LocationInfo, TripPlan, WorkflowState

class TripPlannerAgent:
    def __init__(self):
        self.average_travel_speed = 50  # km/h for planning purposes
        self.daily_travel_time = 8  # hours per day for sightseeing

    async def create_trip_plan(self, anime_title: str, locations: List[LocationInfo], state: WorkflowState) -> TripPlan:
        """
        Create a comprehensive trip plan based on anime locations
        """
        try:
            # Optimize route
            optimized_route = self._optimize_route(locations)

            # Create daily itinerary
            itinerary = self._create_itinerary(optimized_route)

            # Calculate estimates
            total_distance = self._calculate_total_distance(optimized_route)
            duration = self._estimate_duration(len(locations))
            budget = self._estimate_budget(len(locations), duration)

            # Generate travel tips
            tips = self._generate_travel_tips(locations, anime_title)

            trip_plan = TripPlan(
                anime_title=anime_title,
                locations=optimized_route,
                itinerary=itinerary,
                estimated_duration=duration,
                total_distance=total_distance,
                budget_estimate=budget,
                travel_tips=tips
            )

            state.trip_plan = trip_plan
            state.add_message("trip_planner", "orchestrator", trip_plan, "trip_plan_created")

            return trip_plan

        except Exception as e:
            state.errors.append(f"Trip planning failed: {str(e)}")
            raise

    def _optimize_route(self, locations: List[LocationInfo]) -> List[LocationInfo]:
        """
        Simple route optimization using nearest neighbor algorithm
        """
        if len(locations) <= 1:
            return locations

        optimized = [locations[0]]  # Start with first location
        remaining = locations[1:]

        while remaining:
            current = optimized[-1]
            nearest = min(remaining, key=lambda loc: self._calculate_distance(current, loc))
            optimized.append(nearest)
            remaining.remove(nearest)

        return optimized

    def _calculate_distance(self, loc1: LocationInfo, loc2: LocationInfo) -> float:
        """
        Calculate distance between two locations using Haversine formula
        """
        lat1, lon1 = math.radians(loc1.latitude), math.radians(loc1.longitude)
        lat2, lon2 = math.radians(loc2.latitude), math.radians(loc2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in kilometers
        r = 6371
        return c * r

    def _calculate_total_distance(self, locations: List[LocationInfo]) -> float:
        """
        Calculate total distance for the entire route
        """
        if len(locations) < 2:
            return 0.0

        total_distance = 0.0
        for i in range(len(locations) - 1):
            total_distance += self._calculate_distance(locations[i], locations[i + 1])

        return round(total_distance, 2)

    def _create_itinerary(self, locations: List[LocationInfo]) -> List[Dict[str, Any]]:
        """
        Create daily itinerary
        """
        itinerary = []
        current_date = datetime.now() + timedelta(days=7)  # Start one week from now

        for i, location in enumerate(locations):
            day_number = i + 1
            date = current_date + timedelta(days=i-1)

            daily_plan = {
                "day": day_number,
                "date": date.strftime("%Y-%m-%d"),
                "location": location.name,
                "address": location.address,
                "activities": [
                    f"Visit {location.name}",
                    f"Explore anime-related scenes and locations",
                    f"Take photos and enjoy the atmosphere"
                ],
                "estimated_time": "4-6 hours",
                "travel_from_previous": self._get_travel_info(locations, i),
                "accommodation_suggestion": f"Hotel near {location.name}" if i < len(locations) - 1 else None,
                "meals": [
                    "Local breakfast",
                    "Lunch at nearby restaurant",
                    "Dinner featuring local cuisine"
                ]
            }

            itinerary.append(daily_plan)

        return itinerary

    def _get_travel_info(self, locations: List[LocationInfo], current_index: int) -> Dict[str, Any]:
        """
        Get travel information between locations
        """
        if current_index == 0:
            return {"method": "Flight to Japan", "time": "Varies by origin"}

        prev_location = locations[current_index - 1]
        current_location = locations[current_index]
        distance = self._calculate_distance(prev_location, current_location)

        return {
            "method": "Train/Bus" if distance < 300 else "Domestic Flight",
            "distance": f"{distance:.1f} km",
            "estimated_time": f"{max(1, distance / 50):.1f} hours"
        }

    def _estimate_duration(self, num_locations: int) -> str:
        """
        Estimate trip duration based on number of locations
        """
        if num_locations <= 2:
            return "2-3 days"
        elif num_locations <= 4:
            return "4-6 days"
        elif num_locations <= 6:
            return "1 week"
        else:
            return f"{num_locations // 2 + 1} weeks"

    def _estimate_budget(self, num_locations: int, duration: str) -> Dict[str, float]:
        """
        Estimate trip budget
        """
        # Rough estimates in USD
        base_costs = {
            "accommodation": num_locations * 80,  # $80 per location per night
            "transportation": num_locations * 30,  # $30 per location travel
            "food": num_locations * 50,  # $50 per location for meals
            "activities": num_locations * 20,  # $20 per location for activities
            "miscellaneous": num_locations * 15  # $15 per location miscellaneous
        }

        total = sum(base_costs.values())
        base_costs["total"] = total

        return base_costs

    def _generate_travel_tips(self, locations: List[LocationInfo], anime_title: str) -> List[str]:
        """
        Generate travel tips for the anime pilgrimage
        """
        tips = [
            f"Best time to visit: Spring (March-May) or Autumn (September-November)",
            f"Consider purchasing a Japan Rail Pass for convenient travel between locations",
            f"Download offline maps as some pilgrimage sites may be in remote areas",
            f"Learn basic Japanese phrases for better interaction with locals",
            f"Respect local customs and private property when visiting filming locations",
            f"Carry a power bank for your devices when exploring outdoor locations",
            f"Check weather forecasts and dress appropriately for outdoor activities",
            f"Consider staying in traditional ryokan for authentic Japanese experience"
        ]

        return tips