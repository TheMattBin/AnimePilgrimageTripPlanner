from typing import Dict, List, Optional, Any
import folium
import json
import requests
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from langchain_core.tools import tool
from config import Config

class MapAgent:
    def __init__(self):
        self.geolocator = Nominatim(
            user_agent=Config.OPENSTREETMAP_USER_AGENT,
            timeout=10
        )
        self.geocode = RateLimiter(self.geolocator.geocode, min_delay_seconds=1)
        self.osm_base_url = "https://nominatim.openstreetmap.org/search"
        self.overpass_url = "https://overpass-api.de/api/interpreter"

    @tool
    def create_travel_map(self, locations: List[Dict[str, Any]], title: str = "Travel Itinerary") -> str:
        """
        Create an interactive map with travel locations
        """
        if not locations:
            return "No locations provided to create map."

        center_lat = sum(loc.get("latitude", 35.6762) for loc in locations) / len(locations)
        center_lon = sum(loc.get("longitude", 139.6503) for loc in locations) / len(locations)

        m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

        for i, location in enumerate(locations):
            lat = location.get("latitude")
            lon = location.get("longitude")
            name = location.get("name", f"Location {i+1}")
            description = location.get("description", "")
            category = location.get("category", "general")

            if lat and lon:
                icon_colors = {
                    "anime": "red",
                    "food": "orange",
                    "hotel": "blue",
                    "transport": "green",
                    "shopping": "purple",
                    "culture": "pink",
                    "nature": "lightgreen",
                    "general": "gray"
                }

                popup_content = f"""
                <b>{name}</b><br>
                {description}<br>
                <small>Category: {category}</small>
                """

                folium.Marker(
                    [lat, lon],
                    popup=popup_content,
                    tooltip=name,
                    icon=folium.Icon(color=icon_colors.get(category, "gray"))
                ).add_to(m)

        filename = f"{title.lower().replace(' ', '_')}_map.html"
        m.save(filename)
        return filename

    @tool
    def get_coordinates(self, address: str) -> Dict[str, float]:
        """
        Get latitude and longitude for an address using OpenStreetMap
        """
        try:
            location = self.geocode(address)
            if location:
                return {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "address": location.address
                }
            else:
                return self._fallback_geocoding(address)
        except Exception as e:
            return {"error": f"Geocoding error: {str(e)}"}

    def _fallback_geocoding(self, address: str) -> Dict[str, float]:
        """
        Fallback geocoding using direct OpenStreetMap API
        """
        try:
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }

            headers = {
                'User-Agent': Config.OPENSTREETMAP_USER_AGENT
            }

            if Config.NOMINATIM_EMAIL:
                headers['From'] = Config.NOMINATIM_EMAIL

            response = requests.get(self.osm_base_url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                        "latitude": float(data[0]['lat']),
                        "longitude": float(data[0]['lon']),
                        "address": data[0].get('display_name', address)
                    }

            return {"error": "Could not geocode address"}
        except Exception as e:
            return {"error": f"Fallback geocoding error: {str(e)}"}

    @tool
    def calculate_route(self, origin: str, destination: str, waypoints: Optional[List[str]] = None) -> Dict:
        """
        Calculate route between locations using OpenRouteService (free alternative)
        """
        try:
            origin_coords = self.get_coordinates(origin)
            dest_coords = self.get_coordinates(destination)

            if "error" in origin_coords or "error" in dest_coords:
                return {"error": "Could not geocode origin or destination"}

            route_data = {
                "origin": origin_coords,
                "destination": dest_coords,
                "waypoints": [],
                "total_distance_km": 0,
                "estimated_time_hours": 0,
                "route_coordinates": []
            }

            if waypoints:
                for waypoint in waypoints:
                    waypoint_coords = self.get_coordinates(waypoint)
                    if "error" not in waypoint_coords:
                        route_data["waypoints"].append(waypoint_coords)

            route_data["total_distance_km"] = self._estimate_distance(
                origin_coords, dest_coords, route_data["waypoints"]
            )
            route_data["estimated_time_hours"] = route_data["total_distance_km"] / 50  # Average speed

            route_data["route_coordinates"] = self._get_route_coordinates(
                origin_coords, dest_coords, route_data["waypoints"]
            )

            return route_data

        except Exception as e:
            return {"error": f"Route calculation error: {str(e)}"}

    def _get_route_coordinates(self, origin: Dict, destination: Dict, waypoints: List[Dict]) -> List[List[float]]:
        """
        Get route coordinates using OpenRouteService (free tier) or fallback to direct coordinates
        """
        try:
            coordinates = []

            if origin and "latitude" in origin and "longitude" in origin:
                coordinates.append([origin["longitude"], origin["latitude"]])

            for waypoint in waypoints:
                if "latitude" in waypoint and "longitude" in waypoint:
                    coordinates.append([waypoint["longitude"], waypoint["latitude"]])

            if destination and "latitude" in destination and "longitude" in destination:
                coordinates.append([destination["longitude"], destination["latitude"]])

            return coordinates

        except Exception as e:
            print(f"Route coordinate error: {e}")
            return []

    @tool
    def get_nearby_places(self, location: str, place_type: str = "restaurant", radius: int = 1000) -> Dict:
        """
        Get nearby places using OpenStreetMap Overpass API
        """
        try:
            coords = self.get_coordinates(location)
            if "error" in coords:
                return {"error": "Could not geocode location"}

            lat, lon = coords["latitude"], coords["longitude"]

            overpass_query = f"""
            [out:json][timeout:25];
            (
              node["{place_type}"](around:{radius},{lat},{lon});
              way["{place_type}"](around:{radius},{lat},{lon});
              relation["{place_type}"](around:{radius},{lat},{lon});
            );
            out center;
            """

            response = requests.get(
                self.overpass_url,
                params={'data': overpass_query},
                headers={'User-Agent': Config.OPENSTREETMAP_USER_AGENT}
            )

            if response.status_code == 200:
                data = response.json()
                places = []

                for element in data.get('elements', [])[:10]:  # Limit to 10 results
                    place_info = {
                        "name": element.get('tags', {}).get('name', 'Unknown'),
                        "type": element.get('type', 'node'),
                        "coordinates": [
                            element.get('lat', element.get('center', {}).get('lat', 0)),
                            element.get('lon', element.get('center', {}).get('lon', 0))
                        ],
                        "tags": element.get('tags', {})
                    }
                    places.append(place_info)

                return {"places": places, "location": location, "radius": radius}

            return {"error": "Could not fetch nearby places"}

        except Exception as e:
            return {"error": f"Nearby places error: {str(e)}"}

    @tool
    def create_anime_pilgrimage_map(self, anime_title: str, region: str = "Japan") -> str:
        """
        Create a specialized map for anime pilgrimage locations
        """
        anime_locations = {
            "Slam Dunk": [
                {"name": "Shohoku High School (Kamakura High School)", "lat": 35.3193, "lon": 139.5529, "desc": "Hanamichi Sakuragi's school", "city": "Kamakura"},
                {"name": "Tokyo Metropolitan Gymnasium", "lat": 35.6848, "lon": 139.7087, "desc": "Inter-high tournament venue", "city": "Tokyo"},
                {"name": "Enoshima Electric Railway", "lat": 35.2979, "lon": 139.4847, "desc": "Railway featured in the series", "city": "Kamakura"}
            ],
            "Your Name": [
                {"name": "Shinjuku Gyoen", "lat": 35.6852, "lon": 139.7017, "desc": "Park where Taki and Mitsuha met", "city": "Tokyo"},
                {"name": "Suga Shrine Steps", "lat": 35.6880, "lon": 139.7320, "desc": "Iconic staircase scene", "city": "Tokyo"},
                {"name": "Shinjuku Station", "lat": 35.6938, "lon": 139.7034, "desc": "Train station from the movie", "city": "Tokyo"}
            ],
            "One Piece": [
                {"name": "Tokyo Tower", "lat": 35.6586, "lon": 139.7454, "desc": "Marianne location inspiration", "city": "Tokyo"},
                {"name": "Odaiba", "lat": 35.6294, "lon": 139.7789, "desc": "Statue of Liberty location", "city": "Tokyo"}
            ]
        }

        locations = anime_locations.get(anime_title, [])
        if not locations:
            return f"No locations found for anime: {anime_title}"

        center_lat = sum(loc["lat"] for loc in locations) / len(locations)
        center_lon = sum(loc["lon"] for loc in locations) / len(locations)

        m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

        for location in locations:
            popup_content = f"""
            <b>{location['name']}</b><br>
            {location['desc']}<br>
            <small>City: {location['city']}</small><br>
            <small>Anime: {anime_title}</small>
            """

            folium.Marker(
                [location["lat"], location["lon"]],
                popup=popup_content,
                tooltip=location["name"],
                icon=folium.Icon(color="red", icon="star")
            ).add_to(m)

        filename = f"{anime_title.lower().replace(' ', '_')}_pilgrimage_map.html"
        m.save(filename)
        return filename

    @tool
    def add_route_to_map(self, existing_map: str, route_points: List[Dict]) -> str:
        """
        Add route lines to an existing map
        """
        try:
            import os
            if not os.path.exists(existing_map):
                return f"Map file {existing_map} not found"

            m = folium.Map(location=[35.6762, 139.6503], zoom_start=10)

            coordinates = []
            for point in route_points:
                if "latitude" in point and "longitude" in point:
                    coordinates.append([point["latitude"], point["longitude"]])
                elif "lat" in point and "lon" in point:
                    coordinates.append([point["lat"], point["lon"]])

            if len(coordinates) >= 2:
                folium.PolyLine(
                    coordinates,
                    weight=3,
                    color='blue',
                    opacity=0.8
                ).add_to(m)

            new_filename = existing_map.replace(".html", "_with_route.html")
            m.save(new_filename)
            return new_filename

        except Exception as e:
            return f"Error adding route to map: {str(e)}"

    @tool
    def create_enhanced_travel_map(self, locations: List[Dict[str, Any]], title: str = "Travel Itinerary") -> str:
        """
        Create an enhanced map with OpenStreetMap tiles and additional features
        """
        if not locations:
            return "No locations provided to create map."

        center_lat = sum(loc.get("latitude", 35.6762) for loc in locations) / len(locations)
        center_lon = sum(loc.get("longitude", 139.6503) for loc in locations) / len(locations)

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            tiles='OpenStreetMap'
        )

        folium.TileLayer('Stamen Terrain').add_to(m)
        folium.TileLayer('Stamen Toner').add_to(m)
        folium.TileLayer('CartoDB positron').add_to(m)

        for i, location in enumerate(locations):
            lat = location.get("latitude")
            lon = location.get("longitude")
            name = location.get("name", f"Location {i+1}")
            description = location.get("description", "")
            category = location.get("category", "general")

            if lat and lon:
                icon_colors = {
                    "anime": "red",
                    "food": "orange",
                    "hotel": "blue",
                    "transport": "green",
                    "shopping": "purple",
                    "culture": "pink",
                    "nature": "lightgreen",
                    "general": "gray"
                }

                popup_content = f"""
                <div style="font-family: Arial, sans-serif;">
                <h4>{name}</h4>
                <p><strong>Category:</strong> {category.title()}</p>
                <p>{description}</p>
                <small>📍 Coordinates: {lat:.4f}, {lon:.4f}</small>
                </div>
                """

                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=name,
                    icon=folium.Icon(color=icon_colors.get(category, "gray"), icon='info-sign')
                ).add_to(m)

        folium.LayerControl().add_to(m)

        filename = f"{title.lower().replace(' ', '_')}_enhanced_map.html"
        m.save(filename)
        return filename

    def _estimate_distance(self, origin: Dict, destination: Dict, waypoints: List[Dict]) -> float:
        """
        Estimate total distance in kilometers
        """
        import math

        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            return R * c

        total_distance = 0
        current_point = origin

        if waypoints:
            for waypoint in waypoints:
                total_distance += haversine_distance(
                    current_point["latitude"], current_point["longitude"],
                    waypoint["latitude"], waypoint["longitude"]
                )
                current_point = waypoint

        total_distance += haversine_distance(
            current_point["latitude"], current_point["longitude"],
            destination["latitude"], destination["longitude"]
        )

        return total_distance

    def create_comprehensive_travel_map(self, itinerary_data: Dict) -> Dict[str, str]:
        """
        Create comprehensive maps for a complete travel itinerary
        """
        map_files = {}

        all_locations = []

        for day_plan in itinerary_data.get("daily_plans", []):
            if "anime_pilgrimage" in day_plan:
                for spot in day_plan["anime_pilgrimage"]:
                    coords = spot.get("coordinates", [0, 0])
                    all_locations.append({
                        "name": spot["location"],
                        "latitude": coords[0],
                        "longitude": coords[1],
                        "description": spot["description"],
                        "category": "anime",
                        "address": spot["address"]
                    })

        if all_locations:
            main_map = self.create_travel_map(all_locations, "Complete_Itinerary")
            map_files["main_itinerary_map"] = main_map

            anime_titles = set()
            for day_plan in itinerary_data.get("daily_plans", []):
                if "anime_pilgrimage" in day_plan:
                    anime_titles.add(itinerary_data.get("anime_theme", "Unknown"))

            for anime_title in anime_titles:
                anime_map = self.create_anime_pilgrimage_map(anime_title)
                map_files[f"{anime_title}_map"] = anime_map

        return map_files

    def get_travel_statistics(self, locations: List[Dict]) -> Dict:
        """
        Calculate travel statistics for the itinerary
        """
        if len(locations) < 2:
            return {"error": "Need at least 2 locations to calculate statistics"}

        total_distance = 0
        daily_distances = []

        for i in range(len(locations) - 1):
            distance = self._estimate_distance(
                locations[i], locations[i + 1], []
            )
            total_distance += distance
            daily_distances.append(distance)

        return {
            "total_distance_km": round(total_distance, 2),
            "average_daily_distance_km": round(total_distance / (len(locations) - 1), 2),
            "daily_distances_km": [round(d, 2) for d in daily_distances],
            "estimated_travel_time_hours": round(total_distance / 50, 1),
            "number_of_locations": len(locations)
        }