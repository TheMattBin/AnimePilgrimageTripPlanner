"""
Trip Planner & Route Generator Component
Generate detailed multi-day itineraries using the retrieved data.
"""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pydantic import BaseModel, Field
from collections import defaultdict

from src.agents.web_crawler import PilgrimageLocation
from src.components.query_analyzer import QueryAnalysis


@dataclass
class LocationNode:
    """Represents a location in the travel graph."""
    location: PilgrimageLocation
    coordinates: Tuple[float, float]  # (lat, lng)
    visit_duration: int  # minutes
    optimal_visit_time: str  # morning, afternoon, evening


class DailyItinerary(BaseModel):
    """Model for a single day's itinerary."""

    day: int = Field(..., description="Day number")
    date: Optional[str] = Field(default=None, description="Date of the day")
    locations: List[str] = Field(default_factory=list, description="Location names in order")
    activities: List[str] = Field(default_factory=list, description="Activities at each location")
    travel_times: List[int] = Field(default_factory=list, description="Travel times between locations (minutes)")
    total_travel_time: int = Field(default=0, description="Total travel time for the day (minutes)")
    total_visit_time: int = Field(default=0, description="Total visit time for the day (minutes)")
    estimated_cost: Dict[str, float] = Field(default_factory=dict, description="Estimated costs")
    notes: List[str] = Field(default_factory=list, description="Additional notes for the day")
    weather_considerations: List[str] = Field(default_factory=list, description="Weather-related considerations")


class TravelPlan(BaseModel):
    """Complete travel plan model."""

    trip_title: str = Field(..., description="Title of the trip")
    destination: str = Field(..., description="Main destination")
    duration_days: int = Field(..., description="Total trip duration in days")
    total_locations: int = Field(..., description="Total number of locations to visit")
    daily_itineraries: List[DailyItinerary] = Field(default_factory=list, description="Day-by-day itinerary")
    total_estimated_cost: Dict[str, float] = Field(default_factory=dict, description="Total estimated costs")
    transportation_mode: str = Field(default="mixed", description="Primary transportation mode")
    accommodation_suggestions: List[str] = Field(default_factory=list, description="Accommodation suggestions")
    general_tips: List[str] = Field(default_factory=list, description="General travel tips")
    emergency_contacts: Dict[str, str] = Field(default_factory=dict, description="Emergency contact information")


class TripPlanner:
    """
    Trip Planner & Route Generator
    Function: Generate detailed multi-day itineraries using the retrieved data.

    Capabilities:
    - Optimize travel routes between pilgrimage sites based on geography and travel time
    - Suggest activities and timing for each day
    - Offer user customizations like trip length, preferred transport modes, and pacing
    """

    def __init__(self):
        # Travel speed assumptions (km/hour)
        self.travel_speeds = {
            'walking': 5,
            'subway': 25,
            'train': 60,
            'bus': 30,
            'car': 40,
            'taxi': 35
        }

        # Visit duration by location type (minutes)
        self.visit_durations = {
            'temple': 45,
            'shrine': 40,
            'station': 30,
            'park': 60,
            'tower': 90,
            'bridge': 25,
            'building': 75,
            'museum': 120,
            'shopping': 120,
            'restaurant': 60,
            'default': 60
        }

        # Cost estimates (JPY)
        self.cost_estimates = {
            'transport_subway': 200,
            'transport_train': 500,
            'transport_bus': 250,
            'transport_taxi': 1500,
            'food_meal': 1500,
            'attraction_entry': 800,
            'accommodation_budget': 5000,
            'accommodation_mid': 12000,
            'accommodation_luxury': 25000
        }

    def calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.

        Args:
            coord1: (latitude, longitude) of first point
            coord2: (latitude, longitude) of second point

        Returns:
            Distance in kilometers
        """
        if not coord1 or not coord2:
            return 0.0

        lat1, lon1 = coord1
        lat2, lon2 = coord2

        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in kilometers
        return 6371 * c

    def calculate_travel_time(self, distance: float, mode: str = 'mixed') -> int:
        """
        Calculate travel time between locations.

        Args:
            distance: Distance in kilometers
            mode: Transportation mode

        Returns:
            Travel time in minutes
        """
        if distance < 0.5:  # Walking distance
            return int(distance / self.travel_speeds['walking'] * 60)

        if mode == 'mixed':
            # Use fastest available mode for distances > 0.5km
            speed = max(self.travel_speeds['subway'], self.travel_speeds['train'])
        else:
            speed = self.travel_speeds.get(mode, self.travel_speeds['train'])

        base_time = int(distance / speed * 60)

        # Add waiting/transfer time
        if mode in ['subway', 'train', 'bus']:
            base_time += 10  # Average waiting/transfer time
        elif mode == 'taxi':
            base_time += 5  # Call/wait time

        return base_time

    def estimate_visit_duration(self, location: PilgrimageLocation) -> int:
        """
        Estimate how long to spend at a location.

        Args:
            location: PilgrimageLocation object

        Returns:
            Duration in minutes
        """
        name_lower = location.name.lower()

        # Check location type keywords
        for location_type, duration in self.visit_durations.items():
            if location_type in name_lower:
                return duration

        # Adjust based on description length and complexity
        if len(location.description) > 200:
            return 90
        elif len(location.scene_description) > 100:
            return 75
        else:
            return self.visit_durations['default']

    def determine_optimal_visit_time(self, location: PilgrimageLocation) -> str:
        """
        Determine the best time to visit a location.

        Args:
            location: PilgrimageLocation object

        Returns:
            Optimal visit time (morning, afternoon, evening)
        """
        name_lower = location.name.lower()

        # Temples and shrines: morning is often best
        if any(keyword in name_lower for keyword in ['temple', 'shrine']):
            return 'morning'

        # Towers and viewpoints: late afternoon/evening for sunset
        if any(keyword in name_lower for keyword in ['tower', 'observatory', 'viewpoint']):
            return 'evening'

        # Parks and outdoor areas: morning or late afternoon
        if any(keyword in name_lower for keyword in ['park', 'garden', 'bridge']):
            return 'morning'

        # Shopping and entertainment: afternoon
        if any(keyword in name_lower for keyword in ['shop', 'store', 'mall', 'entertainment']):
            return 'afternoon'

        # Default: morning
        return 'morning'

    def cluster_locations_by_proximity(self, locations: List[PilgrimageLocation]) -> List[List[PilgrimageLocation]]:
        """
        Cluster locations by geographic proximity for efficient daily planning.

        Args:
            locations: List of pilgrimage locations

        Returns:
            List of location clusters
        """
        if not locations:
            return []

        # Create location nodes with coordinates
        location_nodes = []
        for loc in locations:
            if loc.coordinates:
                node = LocationNode(
                    location=loc,
                    coordinates=(loc.coordinates['lat'], loc.coordinates['lng']),
                    visit_duration=self.estimate_visit_duration(loc),
                    optimal_visit_time=self.determine_optimal_visit_time(loc)
                )
                location_nodes.append(node)

        if not location_nodes:
            # Fallback: return single cluster
            return [locations]

        # Simple clustering based on proximity
        clusters = []
        unvisited = set(range(len(location_nodes)))

        while unvisited:
            # Start a new cluster
            cluster = []
            center_idx = unvisited.pop()
            cluster.append(center_idx)

            # Find nearby locations
            center_coords = location_nodes[center_idx].coordinates

            # Sort remaining locations by distance from center
            nearby_distances = []
            for idx in unvisited:
                distance = self.calculate_distance(
                    center_coords,
                    location_nodes[idx].coordinates
                )
                nearby_distances.append((distance, idx))

            nearby_distances.sort()

            # Add nearby locations to cluster (within ~10km)
            for distance, idx in nearby_distances[:3]:  # Max 3 additional locations per cluster
                if distance <= 10:  # 10km radius
                    cluster.append(idx)
                    unvisited.remove(idx)

            # Convert indices back to location objects
            cluster_locations = [location_nodes[i].location for i in cluster]
            clusters.append(cluster_locations)

        return clusters

    def optimize_route_within_cluster(self, locations: List[PilgrimageLocation]) -> List[PilgrimageLocation]:
        """
        Optimize the order of visiting locations within a cluster.

        Args:
            locations: Cluster of pilgrimage locations

        Returns:
            Optimized order of locations
        """
        if len(locations) <= 2:
            return locations

        # Create a simple greedy TSP approximation
        remaining = locations.copy()
        optimized = [remaining.pop(0)]  # Start with first location

        while remaining:
            current_loc = optimized[-1]
            if not current_loc.coordinates:
                # No coordinates, just append next location
                optimized.append(remaining.pop(0))
                continue

            # Find closest remaining location
            min_distance = float('inf')
            closest_idx = 0

            for i, loc in enumerate(remaining):
                if loc.coordinates:
                    distance = self.calculate_distance(
                        (current_loc.coordinates['lat'], current_loc.coordinates['lng']),
                        (loc.coordinates['lat'], loc.coordinates['lng'])
                    )
                    if distance < min_distance:
                        min_distance = distance
                        closest_idx = i

            optimized.append(remaining.pop(closest_idx))

        return optimized

    def generate_daily_itinerary(
        self,
        locations: List[PilgrimageLocation],
        day_number: int,
        transportation_mode: str = 'mixed',
        budget_level: str = 'mid'
    ) -> DailyItinerary:
        """
        Generate a daily itinerary for a set of locations.

        Args:
            locations: List of locations for this day
            day_number: Day number in the trip
            transportation_mode: Primary transportation mode
            budget_level: Budget level (budget, mid, luxury)

        Returns:
            DailyItinerary object
        """
        if not locations:
            return DailyItinerary(day=day_number)

        # Optimize route
        optimized_locations = self.optimize_route_within_cluster(locations)

        # Calculate times and costs
        location_names = []
        activities = []
        travel_times = []
        total_visit_time = 0
        total_travel_time = 0

        for i, location in enumerate(optimized_locations):
            location_names.append(location.name)

            # Determine activity based on location
            activity = f"Visit {location.name}"
            if location.scene_description:
                activity += f" - See location from {location.anime_title}"
            activities.append(activity)

            # Visit duration
            visit_duration = self.estimate_visit_duration(location)
            total_visit_time += visit_duration

            # Travel time to next location
            if i < len(optimized_locations) - 1:
                next_loc = optimized_locations[i + 1]
                if location.coordinates and next_loc.coordinates:
                    distance = self.calculate_distance(
                        (location.coordinates['lat'], location.coordinates['lng']),
                        (next_loc.coordinates['lat'], next_loc.coordinates['lng'])
                    )
                    travel_time = self.calculate_travel_time(distance, transportation_mode)
                    travel_times.append(travel_time)
                    total_travel_time += travel_time

        # Estimate costs
        transport_key = f'transport_{transportation_mode}'
        transport_cost = total_travel_time / 60 * self.cost_estimates.get(transport_key, self.cost_estimates['transport_train'])
        food_cost = len(optimized_locations) * self.cost_estimates['food_meal']
        attraction_cost = len(optimized_locations) * self.cost_estimates['attraction_entry']

        estimated_cost = {
            'transportation': transport_cost,
            'food': food_cost,
            'attractions': attraction_cost,
            'total': transport_cost + food_cost + attraction_cost
        }

        # Generate notes
        notes = []
        if len(optimized_locations) > 3:
            notes.append("Busy day with multiple locations - consider starting early")

        # Check for optimal visit times
        morning_locations = [loc.name for loc in optimized_locations
                           if self.determine_optimal_visit_time(loc) == 'morning']
        if morning_locations:
            notes.append(f"Best to visit {', '.join(morning_locations[:2])} in the morning")

        return DailyItinerary(
            day=day_number,
            locations=location_names,
            activities=activities,
            travel_times=travel_times,
            total_travel_time=total_travel_time,
            total_visit_time=total_visit_time,
            estimated_cost=estimated_cost,
            notes=notes
        )

    def generate_travel_plan(
        self,
        locations: List[PilgrimageLocation],
        query_analysis: QueryAnalysis,
        duration_days: Optional[int] = None
    ) -> TravelPlan:
        """
        Generate a complete travel plan.

        Args:
            locations: List of all pilgrimage locations
            query_analysis: Query analysis results
            duration_days: Optional trip duration override

        Returns:
            Complete TravelPlan object
        """
        if not locations:
            return TravelPlan(
                trip_title="Anime Pilgrimage Trip",
                destination="Unknown",
                duration_days=0,
                total_locations=0
            )

        # Determine trip duration
        if duration_days is None:
            # Use preference from query or calculate based on locations
            duration_preference = query_analysis.trip_preferences.get('duration_preference')
            print(f"Debug - Duration preference found: {duration_preference}")

            if duration_preference:
                if 'day' in duration_preference.lower():
                    try:
                        duration_days = int(duration_preference.split()[0])
                        print(f"Debug - Extracted {duration_days} days from preference")
                    except:
                        print("Debug - Failed to parse days, using default 3")
                        duration_days = 3
                elif 'weekend' in duration_preference.lower():
                    duration_days = 2
                    print("Debug - Weekend detected, using 2 days")
                else:
                    duration_days = 3
                    print("Debug - Unknown preference, using default 3 days")
            else:
                # Calculate based on number of locations (2-3 locations per day)
                duration_days = max(1, len(locations) // 2 + (1 if len(locations) % 2 else 0))
                print(f"Debug - No preference, calculating {duration_days} days from {len(locations)} locations")

        print(f"Debug - Final trip duration: {duration_days} days")

        # Get preferences
        travel_style = query_analysis.trip_preferences.get('travel_style', 'standard')
        transportation_mode = 'mixed' if travel_style == 'standard' else 'taxi' if travel_style == 'luxury' else 'subway'

        # Cluster locations by proximity
        location_clusters = self.cluster_locations_by_proximity(locations)

        # Distribute clusters across days
        daily_clusters = []
        if len(location_clusters) <= duration_days:
            # One cluster per day maximum
            daily_clusters = location_clusters + [[]] * (duration_days - len(location_clusters))
        else:
            # Merge clusters for longer trips
            clusters_per_day = math.ceil(len(location_clusters) / duration_days)
            for i in range(duration_days):
                start_idx = i * clusters_per_day
                end_idx = min(start_idx + clusters_per_day, len(location_clusters))
                day_locations = []
                for cluster_idx in range(start_idx, end_idx):
                    day_locations.extend(location_clusters[cluster_idx])
                daily_clusters.append(day_locations)

        # Generate daily itineraries
        daily_itineraries = []
        total_cost = defaultdict(float)

        for day, day_locations in enumerate(daily_clusters, 1):
            if day_locations:  # Only create itineraries for days with locations
                itinerary = self.generate_daily_itinerary(
                    day_locations, day, transportation_mode, travel_style
                )
                daily_itineraries.append(itinerary)

                # Accumulate costs
                for category, cost in itinerary.estimated_cost.items():
                    total_cost[category] += cost

        # Determine main destination
        main_anime = query_analysis.identified_anime[0].anime_title if query_analysis.identified_anime else "Various Anime"
        mentioned_locations = query_analysis.locations_mentioned
        destination = mentioned_locations[0] if mentioned_locations else "Japan"

        # Generate suggestions and tips
        accommodation_suggestions = self._generate_accommodation_suggestions(travel_style, destination)
        general_tips = self._generate_general_tips(main_anime, travel_style)

        return TravelPlan(
            trip_title=f"{main_anime} Pilgrimage Trip",
            destination=destination,
            duration_days=len([it for it in daily_itineraries if it.locations]),
            total_locations=len(locations),
            daily_itineraries=daily_itineraries,
            total_estimated_cost=dict(total_cost),
            transportation_mode=transportation_mode,
            accommodation_suggestions=accommodation_suggestions,
            general_tips=general_tips,
            emergency_contacts={
                "police": "110",
                "ambulance": "119",
                "tourist_info": "+81-3-3201-3331"
            }
        )

    def _generate_accommodation_suggestions(self, travel_style: str, destination: str) -> List[str]:
        """Generate accommodation suggestions based on travel style."""
        suggestions = []

        if travel_style == 'budget':
            suggestions.extend([
                f"Consider hostels or guesthouses in {destination}",
                "Look for business hotels near major train stations",
                "Book accommodation well in advance for better rates"
            ])
        elif travel_style == 'luxury':
            suggestions.extend([
                f"Premium hotels in central {destination}",
                "Consider traditional ryokans for cultural experience",
                "Book rooms with city views for better experience"
            ])
        else:
            suggestions.extend([
                f"Mid-range hotels near {destination} attractions",
                "Consider locations near train stations for convenience",
                "Mix of business hotels and boutique accommodations"
            ])

        return suggestions

    def _generate_general_tips(self, anime_title: str, travel_style: str) -> List[str]:
        """Generate general travel tips."""
        tips = [
            f"Download offline maps before visiting {anime_title} locations",
            "Learn basic Japanese phrases for better local interaction",
            "Carry cash as some locations may not accept cards",
            "Purchase a Japan Rail Pass if traveling between cities",
            "Respect local customs and photography restrictions",
            "Visit popular locations early morning or late afternoon to avoid crowds"
        ]

        if travel_style == 'budget':
            tips.extend([
                "Use convenience stores for affordable meals",
                "Take advantage of free pilgrimage locations",
                "Use public transportation passes for savings"
            ])

        return tips


def main():
    """Demo function for testing the trip planner."""
    from src.agents.web_crawler import PilgrimageLocation

    # Create sample locations
    sample_locations = [
        PilgrimageLocation(
            name="Shinjuku Gyoen National Garden",
            anime_title="Your Name",
            real_world_address="11 Naitomachi, Shinjuku City, Tokyo",
            coordinates={'lat': 35.6852, 'lng': 139.7103},
            description="Large park and garden in central Tokyo",
            scene_description="Scene where Taki and Miki walk through the garden",
            source_url="sample1.com",
            confidence_score=0.9
        ),
        PilgrimageLocation(
            name="Suga Shrine",
            anime_title="Your Name",
            real_world_address="2-5-5 Motoasakusa, Taito City, Tokyo",
            coordinates={'lat': 35.7148, 'lng': 139.7967},
            description="Shinto shrine featured in the movie",
            scene_description="Staircase scene and shrine visit",
            source_url="sample2.com",
            confidence_score=0.95
        ),
        PilgrimageLocation(
            name="Tokyo Station",
            anime_title="Your Name",
            real_world_address="1 Chome Marunouchi, Chiyoda City, Tokyo",
            coordinates={'lat': 35.6812, 'lng': 139.7671},
            description="Major railway station in Tokyo",
            scene_description="Train station scenes",
            source_url="sample3.com",
            confidence_score=0.8
        )
    ]

    # Create sample query analysis
    from src.components.query_analyzer import QueryAnalysis, AnimeIdentification
    from src.components.query_interface import UserQuery

    user_query = UserQuery(
        original_text="I want to visit Your Name locations in Tokyo",
        normalized_text="I want to visit Your Name locations in Tokyo",
        confidence=0.9
    )

    anime_info = AnimeIdentification(
        anime_title="Your Name",
        confidence=0.9,
        keywords=["romance", "drama", "supernatural"],
        context="visit locations from Your Name",
        disambiguation_needed=False
    )

    query_analysis = QueryAnalysis(
        original_query=user_query,
        identified_anime=[anime_info],
        locations_mentioned=["Tokyo"],
        trip_preferences={"duration_preference": "2 days", "travel_style": "standard"},
        analysis_confidence=0.9
    )

    # Test trip planner
    planner = TripPlanner()
    travel_plan = planner.generate_travel_plan(sample_locations, query_analysis)

    print(f"🗓️  Generated Travel Plan: {travel_plan.trip_title}")
    print(f"📍 Destination: {travel_plan.destination}")
    print(f"⏱️  Duration: {travel_plan.duration_days} days")
    print(f"🎌 Total Locations: {travel_plan.total_locations}")

    print(f"\n💰 Estimated Total Cost: ¥{travel_plan.total_estimated_cost.get('total', 0):,.0f}")

    print(f"\n📅 Daily Itineraries:")
    for day in travel_plan.daily_itineraries:
        print(f"\nDay {day.day}:")
        print(f"  Locations: {', '.join(day.locations)}")
        print(f"  Total Time: {day.total_visit_time + day.total_travel_time} minutes")
        print(f"  Daily Cost: ¥{day.estimated_cost.get('total', 0):,.0f}")

    print(f"\n🏨 Accommodation Suggestions:")
    for suggestion in travel_plan.accommodation_suggestions:
        print(f"  • {suggestion}")

    print(f"\n💡 General Tips:")
    for tip in travel_plan.general_tips:
        print(f"  • {tip}")


if __name__ == "__main__":
    main()