#!/usr/bin/env python3
"""
Enhanced Anime Pilgrimage API Client
Integrates multiple anime pilgrimage data sources for comprehensive location discovery
"""

import requests
import json
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, quote
import time
from dataclasses import dataclass
from core.config import Config
from .anitabi_client import AnitabiClient, BangumiInfo, AnitabiLocation
from .animepilgrimage_web_client import AnimePilgrimageWebClient, WebLocation


@dataclass
class AnimeLocation:
    """Data class for anime pilgrimage location"""
    name: str
    real_location: str
    description: str
    coordinates: List[float]  # [lat, lon]
    city: str
    prefecture: str
    anime_title: str
    scene_description: str
    source: str  # Data source
    url: Optional[str] = None


class AnimePilgrimageAPI:
    """
    Client for accessing anime pilgrimage location data from multiple sources
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Home-Assist-Trip-Planner/1.0'
        })

        # Initialize specialized clients
        self.anitabi_client = AnitabiClient()
        self.web_client = AnimePilgrimageWebClient()

        # Rate limiting
        self.rate_limit_delay = 1.0  # seconds between requests
        self.last_request_time = 0

    def _respect_rate_limit(self):
        """Respect rate limiting for API calls"""
        current_time = time.time()
        if current_time - self.last_request_time < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - (current_time - self.last_request_time))
        self.last_request_time = time.time()

    def search_animepilgrimage(self, anime_title: str) -> List[AnimeLocation]:
        """
        Search for anime locations using real web scraping of animepilgrimage.com
        """
        locations = []

        try:
            print(f"[API] Using real web scraping for animepilgrimage.com: {anime_title}")

            # Use the real web scraping client
            web_locations = self.web_client.search_anime_locations(anime_title)

            if not web_locations:
                print(f"[API] No locations found via web scraping for: {anime_title}")
                return []

            # Convert WebLocation objects to AnimeLocation objects
            for web_loc in web_locations:
                # Extract city and prefecture from address
                city = "Unknown"
                prefecture = "Unknown"
                if web_loc.address:
                    address_parts = web_loc.address.split(",")
                    if len(address_parts) >= 2:
                        city = address_parts[-2].strip() if address_parts[-2].strip() else "Unknown"
                    if len(address_parts) >= 3:
                        prefecture = address_parts[-3].strip() if address_parts[-3].strip() else "Unknown"

                location = AnimeLocation(
                    name=web_loc.name,
                    real_location=web_loc.address,
                    description=web_loc.description,
                    coordinates=[web_loc.latitude or 0, web_loc.longitude or 0],
                    city=city,
                    prefecture=prefecture,
                    anime_title=web_loc.anime_title,
                    scene_description=web_loc.scene_description,
                    source="animepilgrimage.com",
                    url=web_loc.source_url
                )
                locations.append(location)

            print(f"[API] Found {len(locations)} real locations from animepilgrimage.com web scraping")

        except Exception as e:
            print(f"[ERROR] AnimePilgrimage web scraping error: {e}")

        return locations

    def search_anitabi(self, anime_title: str) -> List[AnimeLocation]:
        """
        Search for anime locations using real anitabi.cn API with bangumi IDs
        """
        locations = []

        try:
            print(f"[API] Using real anitabi.cn API for: {anime_title}")

            # Use the real anitabi client
            bangumi_list, anitabi_locations = self.anitabi_client.search_anime_locations(anime_title)

            if not anitabi_locations:
                print(f"[API] No locations found in anitabi.cn for: {anime_title}")
                return []

            # Convert AnitabiLocation objects to AnimeLocation objects
            for anitabi_loc in anitabi_locations:
                # Parse address to extract city and prefecture
                address_parts = anitabi_loc.address.split(",")
                city = address_parts[-2].strip() if len(address_parts) >= 2 else "Unknown"
                prefecture = address_parts[-3].strip() if len(address_parts) >= 3 else "Unknown"

                location = AnimeLocation(
                    name=anitabi_loc.name,
                    real_location=anitabi_loc.address,
                    description=anitabi_loc.description,
                    coordinates=[anitabi_loc.latitude, anitabi_loc.longitude],
                    city=city,
                    prefecture=prefecture,
                    anime_title=anime_title,
                    scene_description=f"Appears in: {', '.join(anitabi_loc.episodes)}",
                    source="anitabi.cn",
                    url=f"https://anitabi.cn/location/{anitabi_loc.id}"
                )
                locations.append(location)

            print(f"[API] Found {len(locations)} real locations from anitabi.cn")

        except Exception as e:
            print(f"[ERROR] Anitabi API error: {e}")

        return locations

    def search_wikidata(self, anime_title: str) -> List[AnimeLocation]:
        """
        Search for anime locations using Wikidata/SPARQL queries
        This can provide real data about anime filming locations
        """
        locations = []

        try:
            self._respect_rate_limit()

            # SPARQL query for anime filming locations
            sparql_query = """
            SELECT ?anime ?location ?locationLabel ?coord ?countryLabel ?description WHERE {
              ?anime wdt:P31 wd:Q202866;  # Instance of anime
                     rdfs:label ?animeLabel.
              ?location wdt:P31 wd.QQ190107;  # Instance of filming location
                        wdt:P625 ?coord;  # Coordinates
                        wdt:P17 ?country;  # Country
                        rdfs:label ?locationLabel;
                        schema:description ?description.

              ?anime wdt:P840 ?location.  # Has filming location

              FILTER(LANG(?animeLabel) = "en")
              FILTER(LANG(?locationLabel) = "en")
              FILTER(LANG(?description) = "en")
              FILTER(CONTAINS(LCASE(?animeLabel), LCASE("%s")))
            }
            LIMIT 10
            """ % anime_title.lower().replace(" ", "_")

            # Wikidata SPARQL endpoint
            url = "https://query.wikidata.org/sparql"
            params = {
                "query": sparql_query,
                "format": "json"
            }

            response = self.session.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                for result in data.get("results", {}).get("bindings", []):
                    coord = result.get("coord", {}).get("value", "Point(0 0)")
                    # Parse coordinate string "Point(lat lon)"
                    if coord.startswith("Point("):
                        coords = coord[6:-1].split()
                        lat, lon = float(coords[0]), float(coords[1])
                    else:
                        lat, lon = 0, 0

                    location = AnimeLocation(
                        name=result.get("locationLabel", {}).get("value", "Unknown"),
                        real_location=result.get("locationLabel", {}).get("value", "Unknown"),
                        description=result.get("description", {}).get("value", "No description available"),
                        coordinates=[lat, lon],
                        city="Unknown",  # Would need additional parsing
                        prefecture="Unknown",
                        anime_title=anime_title,
                        scene_description="Filming location from Wikidata",
                        source="wikidata",
                        url=None
                    )
                    locations.append(location)

        except Exception as e:
            print(f"[ERROR] Wikidata API error: {e}")

        return locations

    def search_all_sources(self, anime_title: str) -> List[AnimeLocation]:
        """
        Search all available data sources for anime pilgrimage locations
        """
        all_locations = []

        print(f"[API] Searching all sources for: {anime_title}")

        # Search all sources
        sources = [
            (self.search_animepilgrimage, "animepilgrimage.com"),
            (self.search_anitabi, "anitabi.cn"),
            (self.search_wikidata, "wikidata")
        ]

        for search_func, source_name in sources:
            try:
                print(f"[API] Searching {source_name}...")
                locations = search_func(anime_title)
                all_locations.extend(locations)
                print(f"[API] Found {len(locations)} locations from {source_name}")
            except Exception as e:
                print(f"[ERROR] {source_name} search failed: {e}")

        # Remove duplicates based on coordinates and name
        unique_locations = self._deduplicate_locations(all_locations)

        print(f"[API] Total unique locations found: {len(unique_locations)}")
        return unique_locations

    def _deduplicate_locations(self, locations: List[AnimeLocation]) -> List[AnimeLocation]:
        """
        Remove duplicate locations based on coordinates and name similarity
        """
        unique_locations = []
        seen_coords = set()
        seen_names = set()

        for location in locations:
            # Create coordinate key with some tolerance
            coord_key = (round(location.coordinates[0], 3), round(location.coordinates[1], 3))
            name_key = location.name.lower().strip()

            if coord_key not in seen_coords and name_key not in seen_names:
                unique_locations.append(location)
                seen_coords.add(coord_key)
                seen_names.add(name_key)

        return unique_locations

    def get_anime_list(self) -> List[str]:
        """
        Get list of available anime from all sources
        """
        try:
            # Get popular anime from anitabi.cn
            popular_anime = self.anitabi_client.get_popular_anime(limit=20)

            if popular_anime:
                anime_titles = [anime.title for anime in popular_anime if anime.title]
                print(f"[API] Got {len(anime_titles)} anime from anitabi.cn")
                return anime_titles

        except Exception as e:
            print(f"[ERROR] Could not get anime list from anitabi.cn: {e}")

        # Fallback to basic list
        return [
            "Slam Dunk", "Your Name", "One Piece", "Naruto", "Attack on Titan",
            "Demon Slayer", "My Hero Academia", "Dragon Ball Z", "Sailor Moon",
            "Death Note", "Fullmetal Alchemist", "Steins;Gate", "Re:Zero",
            "Bunny Girl Senpai", "Weathering with You", "Silent Voice"
        ]

    def to_dict_format(self, locations: List[AnimeLocation]) -> Dict[str, Any]:
        """
        Convert AnimeLocation objects to dictionary format compatible with existing system
        """
        result = {
            "anime_title": locations[0].anime_title if locations else "Unknown",
            "total_locations": len(locations),
            "sources": list(set(loc.source for loc in locations)),
            "locations": {}
        }

        # Group by city/prefecture
        for location in locations:
            region = f"{location.city}, {location.prefecture}"
            if region not in result["locations"]:
                result["locations"][region] = []

            result["locations"][region].append({
                "name": location.name,
                "real_location": location.real_location,
                "description": location.description,
                "coordinates": location.coordinates,
                "city": location.city,
                "prefecture": location.prefecture,
                "scene_description": location.scene_description,
                "source": location.source,
                "url": location.url,
                "activities": ["Visit filming location", "Take photos", "Experience anime atmosphere"]
            })

        return result