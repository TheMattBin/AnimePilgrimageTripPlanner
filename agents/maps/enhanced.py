from typing import Dict, List, Optional, Any, Tuple
import folium
import json
import requests
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from datetime import datetime, timedelta
from jinja2 import Template
import base64
import io
from PIL import Image
import os
import math
from agents.search import SeichiSearchAgent


class EnhancedMapAgent:
    """
    Enhanced map agent with routes, schedules, and episode photos
    Streamlined version focused on single main map output
    """

    def __init__(self):
        self.geolocator = Nominatim(user_agent="enhanced_trip_planner", timeout=10)
        self.geocode = RateLimiter(self.geolocator.geocode, min_delay_seconds=1)
        self.seichi_search = SeichiSearchAgent()

        # Enhanced anime location database with episode references and photos
        self.enhanced_anime_locations = {
            "Slam Dunk": {
                "Kamakura": {
                    "Shohoku High School": {
                        "real_location": "Kanagawa Prefectural Kamakura High School",
                        "address": "Kamakura, Kanagawa Prefecture",
                        "coordinates": [35.3193, 139.5529],
                        "episodes": ["Episode 1-5", "Episode 31", "Episode 101"],
                        "scenes": ["School entrance", "Basketball court", "Roof top"],
                        "description": "The iconic school where Hanamichi Sakuragi played basketball",
                        "best_visit_time": "09:00-16:00",
                        "estimated_duration": "2-3 hours",
                        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Kanagawa_Prefectural_Kamakura_High_School.jpg/800px-Kanagawa_Prefectural_Kamakura_High_School.jpg",
                        "activities": ["Visit the school gate", "Take photos at basketball court", "Explore Kamakura area"]
                    },
                    "Enoshima Electric Railway": {
                        "real_location": "Enoshima Electric Railway",
                        "address": "Kamakura to Fujisawa line",
                        "coordinates": [35.2979, 139.4847],
                        "episodes": ["Episode 2", "Episode 45"],
                        "scenes": ["Train scenes", "Coastal views"],
                        "description": "Railway featured in the series with beautiful coastal views",
                        "best_visit_time": "10:00-17:00",
                        "estimated_duration": "1-2 hours",
                        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Enoshima_Electric_Railway_Type_1000.jpg/800px-Enoshima_Electric_Railway_Type_1000.jpg",
                        "activities": ["Train ride experience", "Coastal photography", "Visit Enoshima island"]
                    }
                },
                "Tokyo": {
                    "Tokyo Metropolitan Gymnasium": {
                        "real_location": "Tokyo Metropolitan Gymnasium",
                        "address": "Sendagaya, Shibuya, Tokyo",
                        "coordinates": [35.6848, 139.7087],
                        "episodes": ["Episode 26", "Episode 50-60"],
                        "scenes": ["Inter-high tournament", "Basketball games"],
                        "description": "Venue for the national high school basketball tournament",
                        "best_visit_time": "09:00-17:00",
                        "estimated_duration": "2-3 hours",
                        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Tokyo_Metropolitan_Gymnasium_2012.jpg/800px-Tokyo_Metropolitan_Gymnasium_2012.jpg",
                        "activities": ["Watch sporting events", "Take arena photos", "Visit nearby Yoyogi Park"]
                    },
                    "National Stadium": {
                        "real_location": "Japan National Stadium",
                        "address": "Kasumigaoka, Shinjuku, Tokyo",
                        "coordinates": [35.6784, 139.7104],
                        "episodes": ["Episode 101", "Final episodes"],
                        "scenes": ["Final championship game"],
                        "description": "Where the final championship games were held",
                        "best_visit_time": "09:00-17:00",
                        "estimated_duration": "1-2 hours",
                        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Japan_National_Stadium_%282019%29.jpg/800px-Japan_National_Stadium_%282019%29.jpg",
                        "activities": ["Stadium tour", "Sports museum visit", "Olympic park exploration"]
                    }
                }
            },
            "Your Name": {
                "Tokyo": {
                    "Suga Shrine Steps": {
                        "real_location": "Suga Shrine Steps",
                        "address": "Yotsuya, Shinjuku, Tokyo",
                        "coordinates": [35.6896, 139.7319],
                        "episodes": ["Movie scene"],
                        "scenes": ["Famous stairway meeting"],
                        "description": "The iconic red staircase where Taki and Mitsuha meet",
                        "best_visit_time": "Early morning (6:00-8:00)",
                        "estimated_duration": "30 minutes - 1 hour",
                        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Suga_Shrine_stairs.jpg/800px-Suga_Shrine_stairs.jpg",
                        "activities": ["Photograph the stairs", "Visit Suga Shrine", "Morning light photography"]
                    }
                }
            }
        }

    def _generate_generic_anime_locations(self, anime_title: str) -> Dict:
        """
        Generate generic anime pilgrimage locations for Japan
        """
        return {
            "Tokyo": {
                "Akihabara": {
                    "real_location": "Akihabara Electric Town",
                    "address": "Chiyoda, Tokyo",
                    "coordinates": [35.6977, 139.7707],
                    "episodes": [f"Various {anime_title} episodes"],
                    "scenes": ["Shopping districts", "Anime stores", "Arcades"],
                    "description": f"The heart of anime culture, perfect for {anime_title} pilgrimage",
                    "best_visit_time": "10:00-21:00",
                    "estimated_duration": "3-4 hours",
                    "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/Akihabara_2019.jpg/800px-Akihabara_2019.jpg",
                    "activities": ["Visit anime stores", "Try arcade games", "Explore electronics shops"]
                },
                "Shibuya Crossing": {
                    "real_location": "Shibuya Scramble Crossing",
                    "address": "Shibuya, Tokyo",
                    "coordinates": [35.6598, 139.7006],
                    "episodes": [f"Urban scenes in {anime_title}"],
                    "scenes": ["City life", "Modern Tokyo"],
                    "description": f"Iconic Tokyo crossing featured in many anime including {anime_title}",
                    "best_visit_time": "18:00-20:00",
                    "estimated_duration": "1-2 hours",
                    "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Shibuya_Crossing_in_2013.jpg/800px-Shibuya_Crossing_in_2013.jpg",
                    "activities": ["Photography", "People watching", "Shopping"]
                }
            },
            "Kyoto": {
                "Fushimi Inari Shrine": {
                    "real_location": "Fushimi Inari Taisha",
                    "address": "Kyoto, Kyoto Prefecture",
                    "coordinates": [34.9671, 135.7727],
                    "episodes": [f"Spiritual episodes in {anime_title}"],
                    "scenes": ["Temple visits", "Traditional Japan"],
                    "description": f"Beautiful shrine with thousands of torii gates, perfect for {anime_title} spiritual themes",
                    "best_visit_time": "08:00-17:00",
                    "estimated_duration": "2-3 hours",
                    "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Fushimi_Inari_Shrine_002.jpg/800px-Fushimi_Inari_Shrine_002.jpg",
                    "activities": ["Hike through torii gates", "Make wishes", "Traditional photography"]
                },
                "Gion District": {
                    "real_location": "Gion Historic District",
                    "address": "Higashiyama, Kyoto",
                    "coordinates": [35.0032, 135.7751],
                    "episodes": [f"Traditional episodes in {anime_title}"],
                    "scenes": ["Historic streets", "Traditional architecture"],
                    "description": f"Traditional geisha district, perfect for historical {anime_title} themes",
                    "best_visit_time": "16:00-19:00",
                    "estimated_duration": "2-3 hours",
                    "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Gion_at_night.jpg/800px-Gion_at_night.jpg",
                    "activities": ["Explore traditional streets", "Spot geishas", "Traditional tea houses"]
                }
            },
            "Osaka": {
                "Osaka Castle": {
                    "real_location": "Osaka Castle",
                    "address": "Chuo, Osaka",
                    "coordinates": [34.6873, 135.5262],
                    "episodes": [f"Historical episodes in {anime_title}"],
                    "scenes": ["Castle grounds", "Historical battles"],
                    "description": f"Impressive castle featured in historical {anime_title} episodes",
                    "best_visit_time": "09:00-17:00",
                    "estimated_duration": "2-3 hours",
                    "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/Osaka_Castle_in_2015.jpg/800px-Osaka_Castle_in_2015.jpg",
                    "activities": ["Castle tour", "Grounds exploration", "Historical learning"]
                },
                "Dotonbori": {
                    "real_location": "Dotonbori Street",
                    "address": "Chuo, Osaka",
                    "coordinates": [34.6686, 135.5028],
                    "episodes": [f"Modern city life in {anime_title}"],
                    "scenes": ["Night life", "Street food", "Neon lights"],
                    "description": f"Vibrant entertainment district featured in modern {anime_title} scenes",
                    "best_visit_time": "18:00-23:00",
                    "estimated_duration": "2-4 hours",
                    "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Dotonbori_202004.jpg/800px-Dotonbori_202004.jpg",
                    "activities": ["Street food", "Neon photography", "Entertainment"]
                }
            }
        }

    def create_main_anime_map(self, anime_title: str, trip_duration: int = 7,
                             start_date: str = "2024-12-01") -> str:
        """
        Create main enhanced anime pilgrimage map with all features
        Returns the main map file path
        """
        # Use hardcoded locations for supported anime, search for real locations for others
        if anime_title in self.enhanced_anime_locations:
            anime_data = self.enhanced_anime_locations[anime_title]
        else:
            # Search for real seichi junrei locations
            print(f"[MAP AGENT] Searching for real seichi locations for: {anime_title}")
            search_result = self.seichi_search.search_anime_locations(anime_title)
            anime_data = search_result.get("locations", {})

            # Handle case where anime_data is not in expected dictionary format
            if isinstance(anime_data, list):
                print(f"[MAP AGENT] Converting list data to dictionary format")
                # Convert list to expected dictionary structure
                temp_dict = {}
                for item in anime_data:
                    if isinstance(item, dict):
                        # Create a region key from city or use default
                        region = item.get("city", item.get("prefecture", "Unknown"))
                        if region not in temp_dict:
                            temp_dict[region] = {}
                        # Use name as key or generate one
                        name_key = item.get("name", f"location_{len(temp_dict[region])}")
                        temp_dict[region][name_key] = item
                anime_data = temp_dict

        # Collect all locations with their metadata
        all_locations = []
        for region, locations in anime_data.items():
            # Handle both dict and list formats
            if isinstance(locations, dict):
                # Expected format: {'location_name': {...}}
                for location_name, location_data in locations.items():
                    location_info = {
                        "name": location_name,
                        "real_name": location_data.get("real_location", location_name),
                        "region": region,
                        "coordinates": location_data.get("coordinates", [35.6762, 139.6503]),
                        "episodes": location_data.get("episodes", ["Unknown"]),
                        "scenes": location_data.get("scenes", ["Unknown scenes"]),
                        "description": location_data.get("description", "No description available"),
                        "best_visit_time": location_data.get("best_visit_time", "09:00-17:00"),
                        "estimated_duration": location_data.get("estimated_duration", "1-2 hours"),
                        "photo_url": location_data.get("photo_url", ""),
                        "activities": location_data.get("activities", ["Visit location"]),
                        "address": location_data.get("address", "Unknown address")
                    }
                    all_locations.append(location_info)
            elif isinstance(locations, list):
                # Handle list format: [{'name': '...', ...}, ...]
                for location_data in locations:
                    location_info = {
                        "name": location_data.get("name", "Unknown Location"),
                        "real_name": location_data.get("real_location", location_data.get("name", "Unknown")),
                        "region": region,
                        "coordinates": location_data.get("coordinates", [35.6762, 139.6503]),
                        "episodes": location_data.get("episodes", ["Unknown"]),
                        "scenes": location_data.get("scenes", ["Unknown scenes"]),
                        "description": location_data.get("description", "No description available"),
                        "best_visit_time": location_data.get("best_visit_time", "09:00-17:00"),
                        "estimated_duration": location_data.get("estimated_duration", "1-2 hours"),
                        "photo_url": location_data.get("photo_url", ""),
                        "activities": location_data.get("activities", ["Visit location"]),
                        "address": location_data.get("address", "Unknown address")
                    }
                    all_locations.append(location_info)

        # Optimize route and create schedule
        optimized_route = self._optimize_route(all_locations)
        scheduled_locations = self._create_schedule(optimized_route, start_date, trip_duration)

        # Create main enhanced map
        main_map_file = self._create_main_enhanced_map(scheduled_locations, anime_title)

        return main_map_file

    def _optimize_route(self, locations: List[Dict]) -> List[Dict]:
        """
        Optimize route using nearest neighbor algorithm
        """
        if len(locations) <= 1:
            return locations

        optimized = [locations[0]]
        remaining = locations[1:]

        while remaining:
            current = optimized[-1]
            nearest = min(remaining, key=lambda loc: self._calculate_distance(
                current["coordinates"], loc["coordinates"]
            ))
            optimized.append(nearest)
            remaining.remove(nearest)

        return optimized

    def _calculate_distance(self, coord1: List[float], coord2: List[float]) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        """
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def _create_schedule(self, locations: List[Dict], start_date: str, duration: int) -> List[Dict]:
        """
        Create schedule with visit times and durations
        """
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        schedule = []

        # Distribute locations across days
        locations_per_day = max(1, len(locations) // duration)

        for day in range(duration):
            day_start = start_datetime + timedelta(days=day)
            day_locations = locations[day*locations_per_day : (day+1)*locations_per_day]

            if not day_locations:
                break

            day_schedule = {
                "day": day + 1,
                "date": day_start.strftime("%Y-%m-%d"),
                "locations": []
            }

            # Add timing for each location
            for i, location in enumerate(day_locations):
                visit_time = self._get_best_visit_time(location, i == 0)
                location["visit_time"] = visit_time
                day_schedule["locations"].append(location)

            schedule.append(day_schedule)

        return schedule

    def _get_best_visit_time(self, location: Dict, is_first: bool = False) -> str:
        """
        Get best visit time for a location
        """
        if is_first:
            return "09:00"

        # Extract time from best_visit_time or default
        best_time = location.get("best_visit_time", "10:00-16:00")
        if "-" in best_time:
            return best_time.split("-")[0]
        return best_time

    def _create_main_enhanced_map(self, schedule: List[Dict], anime_title: str) -> str:
        """Create main enhanced map with all features integrated"""
        if not schedule:
            return "No locations to map"

        # Calculate center point
        all_coords = []
        for day in schedule:
            for loc in day["locations"]:
                all_coords.append(loc["coordinates"])

        center_lat = sum(coord[0] for coord in all_coords) / len(all_coords)
        center_lon = sum(coord[1] for coord in all_coords) / len(all_coords)

        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=9,
            tiles='OpenStreetMap'
        )

        # Add layer control
        folium.LayerControl().add_to(m)

        # Add location markers with enhanced popups
        for day in schedule:
            for loc in day["locations"]:
                popup_content = self._create_enhanced_popup(loc, anime_title)

                # Use different icons for different types of locations
                icon_color = "red" if "school" in loc["name"].lower() else "blue"
                if "gymnasium" in loc["name"].lower():
                    icon_color = "orange"
                elif "railway" in loc["name"].lower():
                    icon_color = "green"

                folium.Marker(
                    loc["coordinates"],
                    popup=popup_content,
                    tooltip=f"{loc['name']} ({loc['region']})",
                    icon=folium.Icon(color=icon_color, icon="star")
                ).add_to(m)

        # Add routes between locations
        if len(schedule) > 1:
            route_coords = []
            for day in schedule:
                for loc in day["locations"]:
                    route_coords.append(loc["coordinates"])

            if len(route_coords) > 1:
                folium.PolyLine(
                    route_coords,
                    color='red',
                    weight=3,
                    opacity=0.8,
                    tooltip='Optimized Route'
                ).add_to(m)

        # Add legend
        legend_html = f'''
        <div style="position: fixed;
                    top: 10px; right: 10px; width: 200px; height: auto;
                    background-color:white; border:2px solid grey; z-index:9999;
                    font-size:14px; padding:10px">
        <h4>{anime_title} Pilgrimage</h4>
        <i class="fa fa-map-marker" style="color:red"></i> Schools<br>
        <i class="fa fa-map-marker" style="color:orange"></i> Sports Venues<br>
        <i class="fa fa-map-marker" style="color:blue"></i> Other Locations<br>
        <i class="fa fa-map-marker" style="color:green"></i> Transportation<br>
        <hr>
        <small>Click markers for details</small>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # Save map
        filename = f"{anime_title.lower().replace(' ', '_')}_enhanced_main_map.html"
        m.save(filename)

        return filename

    def _create_enhanced_popup(self, location: Dict, anime_title: str) -> str:
        """Create enhanced popup with photos and detailed information"""
        popup_html = f"""
        <div style="width: 300px;">
            <h4>{location['name']}</h4>
            <p><em>{location['real_name']}</em></p>
            <p>{location['description']}</p>

            <h5>Episodes:</h5>
            <ul>
            {''.join(f'<li>{ep}</li>' for ep in location['episodes'])}
            </ul>

            <h5>Featured Scenes:</h5>
            <ul>
            {''.join(f'<li>{scene}</li>' for scene in location['scenes'])}
            </ul>

            <h5>Visit Information:</h5>
            <p><strong>Best Time:</strong> {location['best_visit_time']}</p>
            <p><strong>Duration:</strong> {location['estimated_duration']}</p>

            <h5>Activities:</h5>
            <ul>
            {''.join(f'<li>{activity}</li>' for activity in location['activities'])}
            </ul>

            <p><small>{location['address']}</small></p>
        </div>
        """
        return popup_html


def main():
    """Test the enhanced map agent"""
    print("[TEST] Testing Enhanced Map Agent...")

    try:
        agent = EnhancedMapAgent()

        # Test with Slam Dunk
        result = agent.create_main_anime_map("Slam Dunk", 7, "2024-12-01")

        if result.endswith(".html"):
            print(f"[SUCCESS] Main map created: {result}")
        else:
            print(f"[ERROR] {result}")

        return result

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return str(e)


if __name__ == "__main__":
    main()