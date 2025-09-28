#!/usr/bin/env python3
"""
Anitabi.cn API Client
Real API integration for anime pilgrimage location data using bangumi IDs
Based on common API patterns for anime pilgrimage databases
"""

import requests
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, quote
import time
from dataclasses import dataclass
from core.config import Config


@dataclass
class BangumiInfo:
    """Data class for bangumi (anime) information"""
    bangumi_id: int
    title: str
    title_cn: str
    title_jp: str
    cover: str
    summary: str
    episodes: int
    air_date: str
    rating: float
    tags: List[str]


@dataclass
class AnitabiLocation:
    """Data class for anitabi location information"""
    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    description: str
    episodes: List[str]
    images: List[str]
    tags: List[str]
    sources: List[str]
    created_at: str
    updated_at: str


class AnitabiClient:
    """
    Client for anitabi.cn API with real endpoints and bangumi ID integration
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Home-Assist-Trip-Planner/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

        # Base API URL
        self.base_url = "https://api.anitabi.cn"

        # Rate limiting
        self.rate_limit_delay = 0.5  # seconds between requests
        self.last_request_time = 0

        # Cache for bangumi searches
        self.bangumi_cache = {}
        self.location_cache = {}

    def _respect_rate_limit(self):
        """Respect rate limiting for API calls"""
        current_time = time.time()
        if current_time - self.last_request_time < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - (current_time - self.last_request_time))
        self.last_request_time = time.time()

    def search_bangumi(self, anime_title: str) -> List[BangumiInfo]:
        """
        Search for bangumi (anime) by title
        Returns list of matching anime with bangumi IDs
        """
        cache_key = f"search_{anime_title.lower()}"
        if cache_key in self.bangumi_cache:
            return self.bangumi_cache[cache_key]

        try:
            self._respect_rate_limit()

            # Search endpoint pattern
            search_url = f"{self.base_url}/bangumi/search"
            params = {
                "keyword": anime_title,
                "limit": 10
            }

            response = self.session.get(search_url, params=params)

            if response.status_code == 200:
                data = response.json()

                # Parse response based on common API patterns
                bangumi_list = []

                # Handle different response formats
                if isinstance(data, dict):
                    if "data" in data:
                        results = data["data"]
                    elif "results" in data:
                        results = data["results"]
                    elif "list" in data:
                        results = data["list"]
                    else:
                        results = data.get("bangumi", [])
                elif isinstance(data, list):
                    results = data
                else:
                    results = []

                for item in results:
                    bangumi = BangumiInfo(
                        bangumi_id=item.get("id", 0),
                        title=item.get("title", ""),
                        title_cn=item.get("title_cn", item.get("name_cn", "")),
                        title_jp=item.get("title_jp", item.get("name_jp", "")),
                        cover=item.get("cover", ""),
                        summary=item.get("summary", ""),
                        episodes=item.get("episodes", 0),
                        air_date=item.get("air_date", ""),
                        rating=item.get("rating", 0.0),
                        tags=item.get("tags", [])
                    )
                    bangumi_list.append(bangumi)

                # Cache the results
                self.bangumi_cache[cache_key] = bangumi_list

                print(f"[ANITABI] Found {len(bangumi_list)} bangumi matches for: {anime_title}")
                return bangumi_list

            elif response.status_code == 404:
                print(f"[ANITABI] No bangumi found for: {anime_title}")
                return []
            else:
                print(f"[ANITABI] API error {response.status_code}: {response.text}")
                return []

        except Exception as e:
            print(f"[ERROR] Anitabi search error: {e}")
            return []

    def get_bangumi_locations(self, bangumi_id: int) -> List[AnitabiLocation]:
        """
        Get all pilgrimage locations for a specific bangumi ID
        Returns detailed location information with coordinates
        """
        cache_key = f"locations_{bangumi_id}"
        if cache_key in self.location_cache:
            return self.location_cache[cache_key]

        try:
            self._respect_rate_limit()

            # Locations endpoint pattern
            locations_url = f"{self.base_url}/bangumi/{bangumi_id}/locations"

            response = self.session.get(locations_url)

            if response.status_code == 200:
                data = response.json()

                # Parse response based on common API patterns
                locations = []

                # Handle different response formats
                if isinstance(data, dict):
                    if "data" in data:
                        results = data["data"]
                    elif "locations" in data:
                        results = data["locations"]
                    elif "places" in data:
                        results = data["places"]
                    else:
                        results = data.get("list", [])
                elif isinstance(data, list):
                    results = data
                else:
                    results = []

                for item in results:
                    location = AnitabiLocation(
                        id=item.get("id", 0),
                        name=item.get("name", ""),
                        address=item.get("address", ""),
                        latitude=float(item.get("latitude", 0)),
                        longitude=float(item.get("longitude", 0)),
                        description=item.get("description", ""),
                        episodes=item.get("episodes", []),
                        images=item.get("images", []),
                        tags=item.get("tags", []),
                        sources=item.get("sources", []),
                        created_at=item.get("created_at", ""),
                        updated_at=item.get("updated_at", "")
                    )
                    locations.append(location)

                # Cache the results
                self.location_cache[cache_key] = locations

                print(f"[ANITABI] Found {len(locations)} locations for bangumi ID: {bangumi_id}")
                return locations

            elif response.status_code == 404:
                print(f"[ANITABI] No locations found for bangumi ID: {bangumi_id}")
                return []
            else:
                print(f"[ANITABI] API error {response.status_code}: {response.text}")
                return []

        except Exception as e:
            print(f"[ERROR] Anitabi locations error: {e}")
            return []

    def get_location_details(self, location_id: int) -> Optional[AnitabiLocation]:
        """
        Get detailed information for a specific location
        """
        try:
            self._respect_rate_limit()

            details_url = f"{self.base_url}/location/{location_id}"

            response = self.session.get(details_url)

            if response.status_code == 200:
                data = response.json()

                location = AnitabiLocation(
                    id=data.get("id", 0),
                    name=data.get("name", ""),
                    address=data.get("address", ""),
                    latitude=float(data.get("latitude", 0)),
                    longitude=float(data.get("longitude", 0)),
                    description=data.get("description", ""),
                    episodes=data.get("episodes", []),
                    images=data.get("images", []),
                    tags=data.get("tags", []),
                    sources=data.get("sources", []),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", "")
                )

                return location

            return None

        except Exception as e:
            print(f"[ERROR] Anitabi location details error: {e}")
            return None

    def search_anime_locations(self, anime_title: str) -> Tuple[List[BangumiInfo], List[AnitabiLocation]]:
        """
        Complete search workflow: find bangumi by title, then get all locations
        Returns both bangumi info and locations
        """
        print(f"[ANITABI] Starting search for: {anime_title}")

        # Step 1: Search for bangumi
        bangumi_list = self.search_bangumi(anime_title)

        if not bangumi_list:
            print(f"[ANITABI] No bangumi found for: {anime_title}")
            return [], []

        # Step 2: Get locations for the best match (first result)
        best_match = bangumi_list[0]
        print(f"[ANITABI] Best match: {best_match.title} (ID: {best_match.bangumi_id})")

        locations = self.get_bangumi_locations(best_match.bangumi_id)

        return bangumi_list, locations

    def get_popular_anime(self, limit: int = 20) -> List[BangumiInfo]:
        """
        Get popular anime with pilgrimage locations
        """
        try:
            self._respect_rate_limit()

            popular_url = f"{self.base_url}/bangumi/popular"
            params = {"limit": limit}

            response = self.session.get(popular_url, params=params)

            if response.status_code == 200:
                data = response.json()

                bangumi_list = []
                results = data.get("data", data.get("list", []))

                for item in results:
                    bangumi = BangumiInfo(
                        bangumi_id=item.get("id", 0),
                        title=item.get("title", ""),
                        title_cn=item.get("title_cn", item.get("name_cn", "")),
                        title_jp=item.get("title_jp", item.get("name_jp", "")),
                        cover=item.get("cover", ""),
                        summary=item.get("summary", ""),
                        episodes=item.get("episodes", 0),
                        air_date=item.get("air_date", ""),
                        rating=item.get("rating", 0.0),
                        tags=item.get("tags", [])
                    )
                    bangumi_list.append(bangumi)

                return bangumi_list

            return []

        except Exception as e:
            print(f"[ERROR] Anitabi popular anime error: {e}")
            return []

    def to_anime_location_format(self, locations: List[AnitabiLocation], anime_title: str) -> Dict[str, Any]:
        """
        Convert AnitabiLocation objects to system-compatible format
        """
        result = {
            "anime_title": anime_title,
            "total_locations": len(locations),
            "source": "anitabi.cn",
            "locations": {}
        }

        # Group by city/region
        for location in locations:
            # Extract city from address
            address_parts = location.address.split(",")
            city = address_parts[-2].strip() if len(address_parts) >= 2 else "Unknown"
            region = f"{city}, Japan"

            if region not in result["locations"]:
                result["locations"][region] = []

            result["locations"][region].append({
                "name": location.name,
                "real_location": location.address,
                "description": location.description,
                "coordinates": [location.latitude, location.longitude],
                "city": city,
                "prefecture": "Unknown",  # Would need more parsing
                "scene_description": f"Appears in: {', '.join(location.episodes)}",
                "source": "anitabi.cn",
                "url": f"https://anitabi.cn/location/{location.id}",
                "activities": ["Visit filming location", "Take photos", "Experience anime atmosphere"],
                "episodes": location.episodes,
                "images": location.images,
                "tags": location.tags
            })

        return result

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "bangumi_cache_size": len(self.bangumi_cache),
            "location_cache_size": len(self.location_cache)
        }