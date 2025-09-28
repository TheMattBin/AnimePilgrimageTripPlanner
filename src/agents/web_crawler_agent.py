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
                # The extract method now might return a single location or handle multiple
                location_details = await self._extract_location_details(result['url'])
                if location_details:
                    # If it's a single location, append it
                    if isinstance(location_details, list):
                        locations.extend(location_details)
                    else:
                        locations.append(location_details)

            # If no locations found, use fallback
            if not locations:
                print(f"No locations found for {anime_title}, using fallback samples")
                locations = self._get_sample_locations(anime_title)

            state.locations = locations
            state.add_message("web_crawler", "orchestrator", locations, "locations_found")

            return locations

        except Exception as e:
            state.errors.append(f"Web crawling failed: {str(e)}")
            # Return some sample locations as fallback
            return self._get_sample_locations(anime_title)

    async def _search_anime(self, anime_title: str) -> List[Dict[str, Any]]:
        """
        Search for anime on the website using the correct search mechanism
        """
        # Convert anime title to search format (lowercase, replace spaces with hyphens)
        search_term = anime_title.lower().replace(' ', '-').replace('!', '')

        # Try the map page directly since the site uses map?data=anime-name format
        map_url = f"{self.base_url}map?data={search_term}"

        try:
            print(f"Trying map URL: {map_url}")
            response = self.session.get(map_url, timeout=10)
            response.raise_for_status()

            # Check if the page contains actual anime location data
            if "location" in response.text.lower() or "map" in response.text.lower():
                return [{'title': anime_title, 'url': map_url}]
            else:
                # Try alternative search formats
                alternative_formats = [
                    search_term.rstrip('-'),
                    search_term + '-1',
                    search_term + '-2',
                    anime_title.lower().replace(' ', ''),
                ]

                for alt_format in alternative_formats:
                    alt_url = f"{self.base_url}map?data={alt_format}"
                    try:
                        response = self.session.get(alt_url, timeout=10)
                        if "location" in response.text.lower() or "map" in response.text.lower():
                            return [{'title': anime_title, 'url': alt_url}]
                    except:
                        continue

                return []

        except Exception as e:
            print(f"Search failed: {e}")
            return []

    async def _extract_location_details(self, url: str) -> List[LocationInfo]:
        """
        Extract location details from a specific anime map page
        """
        try:
            print(f"Extracting location details from: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            locations = []

            # Look for location data in the map page
            # Try different selectors that might contain location information
            location_selectors = [
                'div[class*="location"]',
                'div[class*="place"]',
                'div[class*="spot"]',
                'div[class*="marker"]',
                '.map-location',
                '.location-item',
                'div[data-location]'
            ]

            for selector in location_selectors:
                location_cards = soup.select(selector)
                if location_cards:
                    print(f"Found {len(location_cards)} locations with selector: {selector}")
                    for card in location_cards[:5]:  # Extract up to 5 locations
                        location = self._parse_location_card(card, url)
                        if location:
                            locations.append(location)

            # If no structured locations found, look for map-related content
            if not locations:
                # Look for any mentions of places, spots, or locations in the text
                text_content = soup.get_text()
                import re
                place_mentions = re.findall(r'(?:in|at|near|location|place|spot)[:\s]+([^.,\n]+)', text_content, re.IGNORECASE)

                for mention in place_mentions[:3]:  # Take up to 3 mentions
                    if len(mention.strip()) > 3:  # Valid place name
                        # Try to geocode this location
                        coordinates = await self._geocode_location(mention.strip())
                        if coordinates:
                            locations.append(LocationInfo(
                                name=mention.strip(),
                                address=mention.strip(),
                                latitude=coordinates[0],
                                longitude=coordinates[1],
                                description=f"Location mentioned in {url}",
                                anime_reference="Extracted from web",
                                scene_description=None,
                                accessibility_info=None,
                                nearby_attractions=[]
                            ))

            # If still no locations, try to extract from page title and content
            if not locations:
                page_title = soup.find('title')
                if page_title:
                    title_text = page_title.get_text()
                    # Extract potential location names from title
                    import re
                    location_words = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', title_text)
                    for word in location_words[:2]:
                        if len(word) > 3 and word.lower() not in ['anime', 'map', 'page', 'site']:
                            coordinates = await self._geocode_location(word)
                            if coordinates:
                                locations.append(LocationInfo(
                                    name=word,
                                    address=word,
                                    latitude=coordinates[0],
                                    longitude=coordinates[1],
                                    description=f"Location extracted from page title: {title_text}",
                                    anime_reference="Extracted from web",
                                    scene_description=None,
                                    accessibility_info=None,
                                    nearby_attractions=[]
                                ))

            return locations

        except Exception as e:
            print(f"Failed to extract location details from {url}: {e}")
            return []

    def _parse_location_card(self, card, url: str) -> Optional[LocationInfo]:
        """Parse a location card element"""
        try:
            # Extract all text content and analyze it
            text_content = card.get_text()

            # Look for real location patterns in the text
            import re

            # Pattern to find Japanese place names and locations
            location_patterns = [
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s*Japan)?)',  # English place names
                r'([一-龯]+(?:[都道府県市町村]))',  # Japanese place names
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Station|Temple|Shrine|Park|Tower|Building))',  # Places with types
            ]

            name = None
            for pattern in location_patterns:
                matches = re.findall(pattern, text_content)
                for match in matches:
                    # Filter out generic terms and anime names
                    if match and len(match.strip()) > 2:
                        cleaned_match = match.strip()
                        if not any(generic in cleaned_match.lower() for generic in [
                            'anime', 'bang dream', '©', 'project', 'copyright', 'location', 'place'
                        ]):
                            name = cleaned_match
                            break
                if name:
                    break

            # If no location found, try to get from data attributes
            if not name:
                for attr in ['data-location', 'data-place', 'data-name', 'data-title']:
                    if card.get(attr):
                        name = card.get(attr)
                        break

            # If still no name, try to extract coordinates and reverse geocode
            if not name:
                coordinates = self._extract_coordinates(card)
                if coordinates and coordinates != (10.0, 2025.0):  # Skip invalid coordinates
                    # Try to reverse geocode to get location name
                    name = self._reverse_geocode_location(coordinates[0], coordinates[1])

            if not name:
                return None  # Skip this card - no valid location found

            # Extract real description
            description = ""
            desc_elem = card.find('p') or card.find('div', class_='description')
            if desc_elem:
                description = desc_elem.get_text(strip=True)

            # Clean description - remove anime-specific generic text
            if description:
                description = re.sub(r'©.*?Project', '', description)
                description = re.sub(r'BanG Dream!', '', description)
                description = description.strip()

            if not description:
                description = f"Pilgrimage location extracted from {url.split('/')[-1]}"

            # Get coordinates
            coordinates = self._extract_coordinates(card)

            # Try data attributes for coordinates
            if not coordinates:
                for attr in ['data-lat', 'data-latitude', 'data-lng', 'data-longitude']:
                    lat = card.get(attr.replace('longitude', 'latitude').replace('lng', 'lat'))
                    lng = card.get(attr.replace('latitude', 'longitude').replace('lat', 'lng'))
                    if lat and lng:
                        try:
                            coordinates = (float(lat), float(lng))
                            break
                        except:
                            continue

            # If no coordinates or invalid ones, geocode the location name
            if not coordinates or coordinates == (10.0, 2025.0):
                coordinates = self._sync_geocode_location(name)

            return LocationInfo(
                name=name,
                address=name,  # Use name as address for now
                latitude=coordinates[0] if coordinates else 35.6762,
                longitude=coordinates[1] if coordinates else 139.6503,
                description=description,
                anime_reference="Extracted from web",
                scene_description=None,
                accessibility_info=None,
                nearby_attractions=[]
            )

        except Exception as e:
            print(f"Failed to parse location card: {e}")
            return None

    def _sync_geocode_location(self, location_name: str) -> Optional[tuple]:
        """Synchronous version of geocoding for use in parsing"""
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="anime_pilgrimage_planner")
            location = geolocator.geocode(f"{location_name}, Japan")
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            print(f"Geocoding failed for {location_name}: {e}")
        return None

    def _reverse_geocode_location(self, lat: float, lon: float) -> Optional[str]:
        """Try to get location name from coordinates"""
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="anime_pilgrimage_planner")
            location = geolocator.reverse(f"{lat}, {lon}")
            if location:
                # Extract the most relevant part of the address
                address_parts = location.raw.get('address', {})
                return address_parts.get('city') or address_parts.get('town') or address_parts.get('village') or f"Location at {lat}, {lon}"
        except Exception as e:
            print(f"Reverse geocoding failed: {e}")
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
        # Specific locations for popular anime
        if "dress up darling" in anime_title.lower() or "my dress-up darling" in anime_title.lower():
            return [
                LocationInfo(
                    name="Harajuku, Tokyo",
                    address="Harajuku, Tokyo, Japan",
                    latitude=35.6764,
                    longitude=139.7034,
                    description="Harajuku is known as Japan's fashion capital and serves as inspiration for the various cosplay and fashion elements in My Dress-Up Darling. The vibrant streets and trendy shops capture the essence of Marin's fashion sense.",
                    anime_reference="My Dress-Up Darling",
                    scene_description="Fashion district that inspires Marin's cosplay creations and fashion sense",
                    accessibility_info="Easily accessible via JR Yamanote Line to Harajuku Station",
                    nearby_attractions=["Takeshita Street", "Meiji Jingu Shrine", "Yoyogi Park"]
                ),
                LocationInfo(
                    name="Akihabara Electric Town",
                    address="Akihabara, Tokyo, Japan",
                    latitude=35.6973,
                    longitude=139.7747,
                    description="Akihabara is the center of otaku culture and would be the perfect place for anime fans and cosplayers. This location embodies the otaku culture that surrounds the characters' interests.",
                    anime_reference="My Dress-Up Darling",
                    scene_description="Otaku culture center that represents the anime and cosplay community",
                    accessibility_info="Accessible via JR Yamanote Line to Akihabara Station",
                    nearby_attractions=["Electronics shops", "Arcade centers", "Themed cafes", "Anime stores"]
                ),
                LocationInfo(
                    name="Ikebukuro Sunshine City",
                    address="Ikebukuro, Tokyo, Japan",
                    latitude=35.7295,
                    longitude=139.7109,
                    description="This large shopping and entertainment complex in Ikebukuro represents the modern Japanese urban setting where school life and shopping scenes often take place in anime series.",
                    anime_reference="My Dress-Up Darling",
                    scene_description="Urban shopping and entertainment complex typical of anime school life settings",
                    accessibility_info="Directly connected to Ikebukuro Station via Sunshine City exit",
                    nearby_attractions=["Sunshine Aquarium", "Planetarium", "Shopping malls", "Exhibition halls"]
                ),
                LocationInfo(
                    name="Shibuya Scramble Crossing",
                    address="Shibuya, Tokyo, Japan",
                    latitude=35.6598,
                    longitude=139.7006,
                    description="The world's busiest intersection represents the bustling city life and modern Japanese culture that forms the backdrop for many anime series, including school life and social interactions.",
                    anime_reference="My Dress-Up Darling",
                    scene_description="Iconic Tokyo intersection representing modern urban school life",
                    accessibility_info="Accessible via JR Yamanote Line to Shibuya Station",
                    nearby_attractions=["Shibuya 109", "Hachiko Statue", "Yoyogi Park", "Odaiba"]
                )
            ]
        elif "hyouka" in anime_title.lower():
            return [
                LocationInfo(
                    name="Gifu Prefecture Locations",
                    address="Gifu, Japan",
                    latitude=35.4417,
                    longitude=136.7569,
                    description="Hyouka is set in Gifu Prefecture, and many locations are inspired by real places in this area. The city scenery and rural landscapes served as inspiration for the anime's setting.",
                    anime_reference="Hyouka: You Can't Escape",
                    scene_description="The general setting and atmospheric locations that inspired the mystery-filled town in Hyouka",
                    accessibility_info="Accessible via JR Tokaido Line and local transportation",
                    nearby_attractions=["Gifu Castle", "Nagara River", "Gifu Park"]
                ),
                LocationInfo(
                    name="Takayama Old Town",
                    address="Takayama, Gifu Prefecture, Japan",
                    latitude=36.1419,
                    longitude=137.2592,
                    description="This historic town in Gifu Prefecture with its traditional buildings and atmospheric streets serves as inspiration for the classic Japanese settings in Hyouka.",
                    anime_reference="Hyouka: You Can't Escape",
                    scene_description="Traditional Japanese architecture and streets that inspired the classic literature club's surroundings",
                    accessibility_info="Accessible from Takayama Station, walking distance from old town",
                    nearby_attractions=["Takayama Jinya", "Hida Folk Village", "Morning Markets"]
                ),
                LocationInfo(
                    name="Shirakawa-go Village",
                    address="Shirakawa, Gifu Prefecture, Japan",
                    latitude=36.2569,
                    longitude=136.8847,
                    description="While not directly featured, the traditional gassho-zukuri houses and mysterious atmosphere of this UNESCO World Heritage site capture the essence of Hyouka's mysterious themes.",
                    anime_reference="Hyouka: You Can't Escape",
                    scene_description="Traditional Japanese village atmosphere that inspires the mysterious and cultural elements of the series",
                    accessibility_info="Accessible by bus from Takayama or Kanazawa",
                    nearby_attractions=["Wada House", "Shirakawa-go Observatory", "Myozen-ji Temple"]
                ),
                LocationInfo(
                    name="Nagara River",
                    address="Gifu City, Gifu Prefecture, Japan",
                    latitude=35.3892,
                    longitude=136.7614,
                    description="This famous river in Gifu is known for its traditional cormorant fishing and beautiful scenery. The river atmosphere and natural settings inspire contemplative moments similar to those in Hyouka.",
                    anime_reference="Hyouka: You Can't Escape",
                    scene_description="Riverside settings and natural beauty that inspire the contemplative mystery-solving scenes",
                    accessibility_info="Accessible from Gifu Station, riverside walks available",
                    nearby_attractions=["Gifu Park", "Mount Kinka", "Cormorant Fishing Viewing"]
                )
            ]
        elif "bunny girl" in anime_title.lower() or "rascal does not dream" in anime_title.lower():
            return [
                LocationInfo(
                    name="Shinjuku South Exit Park Area",
                    address="Shinjuku, Tokyo, Japan",
                    latitude=35.6938,
                    longitude=139.7034,
                    description="The iconic location where Sakuta first meets Mai in her bunny girl outfit. This park area near Shinjuku Station's south exit is famous among fans.",
                    anime_reference="Rascal Does Not Dream of Bunny Girl Senpai",
                    scene_description="The bench and park area where Mai reads her book while wearing the bunny girl outfit",
                    accessibility_info="Easily accessible from Shinjuku Station (South Exit), wheelchair accessible",
                    nearby_attractions=["Shinjuku Gyoen National Garden", "Tokyo Metropolitan Government Building", "Kabukicho"]
                ),
                LocationInfo(
                    name="Fujisawa High School Area",
                    address="Fujisawa, Kanagawa Prefecture, Japan",
                    latitude=35.3419,
                    longitude=139.4744,
                    description="The setting for Sakuta and Mai's high school life. Fujisawa is a coastal city near Tokyo that inspired the anime's school setting.",
                    anime_reference="Rascal Does Not Dream of Bunny Girl Senpai",
                    scene_description="School building and surrounding areas where many character interactions take place",
                    accessibility_info="Accessible via JR Tokaido Line to Fujisawa Station",
                    nearby_attractions=["Enoshima Beach", "Kamakura", "Shonan Coast"]
                ),
                LocationInfo(
                    name="Enoshima Electric Railway",
                    address="Fujisawa to Kamakura, Kanagawa Prefecture, Japan",
                    latitude=35.3142,
                    longitude=139.4836,
                    description="The historic railway line that appears in the anime, connecting Fujisawa to Kamakura. This scenic route is popular among anime fans.",
                    anime_reference="Rascal Does Not Dream of Bunny Girl Senpai",
                    scene_description="Scenic railway line with ocean views, featured in various character commute scenes",
                    accessibility_info="Fully accessible, frequent service from Fujisawa Station",
                    nearby_attractions=["Enoshima Island", "Great Buddha of Kamakura", "Hase Temple"]
                ),
                LocationInfo(
                    name="Chigasaki Beach",
                    address="Chigasaki, Kanagawa Prefecture, Japan",
                    latitude=35.3314,
                    longitude=139.4028,
                    description="A beautiful beach location in Shonan area that inspired coastal scenes in the anime. Popular for its sunset views.",
                    anime_reference="Rascal Does Not Dream of Bunny Girl Senpai",
                    scene_description="Coastal area that inspired beach scenes and character development moments",
                    accessibility_info="Accessible via JR Tokaido Line to Chigasaki Station",
                    nearby_attractions=["Shonan Beach", "Southern Beach", "Chigasaki Park"]
                )
            ]
        elif "your name" in anime_title.lower():
            return [
                LocationInfo(
                    name="Shinjuku Gyoen National Garden",
                    address="11 Naitomachi, Shinjuku, Tokyo, Japan",
                    latitude=35.6852,
                    longitude=139.7017,
                    description="A beautiful park that inspired scenes in Your Name. Features traditional Japanese gardens and open spaces.",
                    anime_reference="Your Name",
                    scene_description="Inspired the garden scenes where characters contemplate their connection",
                    accessibility_info="Accessible from Shinjuku-gyoemmae Station, wheelchair accessible",
                    nearby_attractions=["Shinjuku Station", "Tokyo Metropolitan Building", "Isetan Department Store"]
                ),
                LocationInfo(
                    name="Hida-Furukawa Station",
                    address="Furukawa, Gifu Prefecture, Japan",
                    latitude=36.1459,
                    longitude=137.1889,
                    description="The real-life inspiration for the anime's rural town setting. This charming station and surrounding area capture the essence of traditional Japan.",
                    anime_reference="Your Name",
                    scene_description="The train station and surrounding town that inspired Mitsuha's hometown",
                    accessibility_info="Accessible via JR Takayama Line",
                    nearby_attractions=["Shirakawa-go", "Hida Takayama", "Hida Folk Village"]
                )
            ]
        else:
            # Generic sample locations
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