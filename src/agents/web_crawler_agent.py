import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import re
import time
from urllib.parse import urljoin, urlparse
from .core_types import LocationInfo, WorkflowState

class WebCrawlerAgent:
    def __init__(self):
        self.base_url = "https://www.animepilgrimage.com/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    async def search_anime_locations(self, anime_title: str, state: WorkflowState) -> List[LocationInfo]:
        """
        Search for anime pilgrimage locations on animepilgrimage.com
        """
        try:
            search_results = await self._search_anime(anime_title)
            locations = []

            for result in search_results:
                location_details = await self._extract_location_details(result['url'])
                if location_details:
                    locations.append(location_details)

            state.locations = locations
            state.add_message("web_crawler", "orchestrator", locations, "locations_found")

            return locations

        except Exception as e:
            state.errors.append(f"Web crawling failed: {str(e)}")
            # Return some sample locations as fallback
            return self._get_sample_locations(anime_title)

    async def _search_anime(self, anime_title: str) -> List[Dict[str, Any]]:
        """
        Search for anime on the website
        """
        search_url = f"{self.base_url}search/"
        params = {'q': anime_title}

        try:
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            results = []

            # Look for search results (adjust selectors based on actual website structure)
            search_items = soup.find_all('div', class_=re.compile(r'search-result|anime-item'))[:5]

            for item in search_items:
                title_elem = item.find('h3') or item.find('a')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    if link:
                        if not link.startswith('http'):
                            link = urljoin(self.base_url, link)
                        results.append({'title': title, 'url': link})

            return results

        except Exception as e:
            print(f"Search failed: {e}")
            return []

    async def _extract_location_details(self, url: str) -> Optional[LocationInfo]:
        """
        Extract location details from a specific anime page
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract location information (adjust based on actual website structure)
            location_cards = soup.find_all('div', class_=re.compile(r'location|place|spot'))

            if location_cards:
                # For demo purposes, extract the first location
                card = location_cards[0]

                name = card.find('h4') or card.find('h3')
                name = name.get_text(strip=True) if name else "Unknown Location"

                description = card.find('p') or card.find('div', class_='description')
                description = description.get_text(strip=True) if description else "No description available"

                # Look for coordinates or map information
                coordinates = self._extract_coordinates(card)

                if not coordinates:
                    # Use geocoding as fallback
                    coordinates = await self._geocode_location(name)

                return LocationInfo(
                    name=name,
                    address=self._extract_address(card) or name,
                    latitude=coordinates[0] if coordinates else 35.6762,
                    longitude=coordinates[1] if coordinates else 139.6503,
                    description=description,
                    anime_reference="Extracted from web",
                    scene_description=None,
                    accessibility_info=None,
                    nearby_attractions=[]
                )

        except Exception as e:
            print(f"Failed to extract location details from {url}: {e}")
            return None

    def _extract_coordinates(self, element) -> Optional[tuple]:
        """
        Extract coordinates from element text or attributes
        """
        text = element.get_text()
        # Look for coordinate patterns
        coord_patterns = [
            r'(\d+\.?\d*),\s*(\d+\.?\d*)',
            r'lat[:\s]+(\d+\.?\d*).*lon[:\s]+(\d+\.?\d*)',
            r'latitude[:\s]+(\d+\.?\d*).*longitude[:\s]+(\d+\.?\d*)'
        ]

        for pattern in coord_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    lat, lon = float(match.group(1)), float(match.group(2))
                    return (lat, lon)
                except:
                    continue

        return None

    def _extract_address(self, element) -> Optional[str]:
        """
        Extract address information from element
        """
        address_elem = element.find('div', class_='address') or element.find('p', class_='address')
        if address_elem:
            return address_elem.get_text(strip=True)
        return None

    async def _geocode_location(self, location_name: str) -> Optional[tuple]:
        """
        Geocode location name to coordinates (using free geocoding service)
        """
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="anime_pilgrimage_planner")

            location = geolocator.geocode(f"{location_name}, Japan")
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            print(f"Geocoding failed for {location_name}: {e}")

        return None

    def _get_sample_locations(self, anime_title: str) -> List[LocationInfo]:
        """
        Return sample locations for demonstration purposes
        """
        return [
            LocationInfo(
                name=f"{anime_title} Location 1",
                address="Tokyo, Japan",
                latitude=35.6762,
                longitude=139.6503,
                description=f"A famous location from {anime_title}",
                anime_reference=anime_title,
                scene_description="Iconic scene location",
                accessibility_info="Easily accessible by train",
                nearby_attractions=["Shopping district", "Local restaurants"]
            ),
            LocationInfo(
                name=f"{anime_title} Location 2",
                address="Kyoto, Japan",
                latitude=35.0116,
                longitude=135.7681,
                description=f"Another pilgrimage site from {anime_title}",
                anime_reference=anime_title,
                scene_description="Memorable background location",
                accessibility_info="Walking distance from station",
                nearby_attractions=["Historical temple", "Traditional gardens"]
            )
        ]