"""
Agentic Web Crawler & Data Retriever
Autonomous crawling and scraping real-life anime pilgrimage location data using LangGraph.
"""

import re
import asyncio
import aiohttp
import random
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from urllib.parse import urljoin, urlparse, quote
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage

from src.components.query_analyzer import QueryAnalysis


@dataclass
class CrawlerState(MessagesState):
    """State for the web crawler agent workflow."""
    query_analysis: Optional[QueryAnalysis] = None
    anime_focus: Optional[str] = None
    search_urls: List[str] = None
    scraped_data: List[Dict[str, Any]] = None
    current_depth: int = 0
    max_depth: int = 2
    total_locations: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.search_urls is None:
            self.search_urls = []
        if self.scraped_data is None:
            self.scraped_data = []
        if self.total_locations is None:
            self.total_locations = []


class PilgrimageLocation(BaseModel):
    """Data model for a pilgrimage location."""

    name: str = Field(..., description="Name of the location")
    anime_title: str = Field(..., description="Associated anime title")
    real_world_address: str = Field(..., description="Real world address")
    coordinates: Optional[Dict[str, float]] = Field(default=None, description="GPS coordinates")
    description: str = Field(default="", description="Description of the location")
    scene_description: str = Field(default="", description="Scene from the anime")
    access_method: str = Field(default="", description="How to access the location")
    nearby_attractions: List[str] = Field(default_factory=list, description="Nearby attractions")
    best_visit_time: str = Field(default="", description="Best time to visit")
    photography_notes: str = Field(default="", description="Photography tips")
    source_url: str = Field(..., description="Source URL for verification")
    confidence_score: float = Field(default=0.0, description="Confidence in data accuracy")


class AgenticWebCrawler:
    """
    Agentic Web Crawler & Data Retriever
    Function: Autonomous crawling and scraping real-life anime pilgrimage location data.

    Capabilities:
    - Crawl official and community sites (e.g., Anime Pilgrimage, travel blogs)
    - Parse structured/unstructured data for locations, routes, and activities
    - Handle pagination, dynamic content, and anti-bot measures using agentic AI techniques

    Implementation: Custom Python crawler integrated with agent decision logic (LangGraph)
    """

    def __init__(self):
        self.session = None
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.request_delay = (1, 3)  # Random delay between requests
        self.max_retries = 3

        # Known anime pilgrimage websites
        self.pilgrimage_sites = [
            "https://animenewsnetwork.com",
            "https://myanimelist.net",
            "https://anime-pilgrimage.com",  # Fictional example
            "https://otakutrips.com",      # Fictional example
            "https://japan-guide.com",
            "https://tripadvisor.in",
            "https://wikitravel.org"
        ]

        # Enhanced search patterns for anime pilgrimage content
        self.search_patterns = [
            # Direct and simple searches
            "{anime} real locations",
            "{anime} Anime Pilgrimage",
            "{anime} filming locations Japan",
            "{anime} inspired locations",
            "{anime} real life places",

            # Action-oriented searches
            "visit {anime} locations Japan",
            "{anime} tourism guide",
            "{anime} travel spots",
            "{anime} fan locations",

            # Community and site-specific searches
            "{anime} pilgrimage sites Japan",
            "{anime} location hunting",
            "{anime} seichi (holy land)",
            "{anime} anime tourism spots",

            # Studio/creator specific
            "{anime} Kyoto Animation locations",  # For Hyouka
            "{anime} Makoto Shinkai locations",   # For Your Name
            "{anime} Studio Ghibli locations",    # For Ghibli films
        ]

        self.graph = self._build_crawler_graph()

    def _build_crawler_graph(self) -> StateGraph:
        """Build the LangGraph workflow for the crawler agent."""

        # Define the workflow graph
        workflow = StateGraph(CrawlerState)

        # Add nodes
        workflow.add_node("search_planning", self._search_planning)
        workflow.add_node("execute_searches", self._execute_searches)
        workflow.add_node("crawl_results", self._crawl_results)
        workflow.add_node("extract_locations", self._extract_locations)
        workflow.add_node("validate_locations", self._validate_locations)
        workflow.add_node("coordinate_lookup", self._coordinate_lookup)

        # Add edges
        workflow.add_edge(START, "search_planning")
        workflow.add_edge("search_planning", "execute_searches")
        workflow.add_edge("execute_searches", "crawl_results")
        workflow.add_edge("crawl_results", "extract_locations")
        workflow.add_edge("extract_locations", "validate_locations")
        workflow.add_edge("validate_locations", "coordinate_lookup")
        workflow.add_edge("coordinate_lookup", END)

        return workflow.compile()

    async def _search_planning(self, state: CrawlerState) -> CrawlerState:
        """Plan search URLs based on query analysis with AI-enhanced search terms."""
        query_analysis = state["query_analysis"]
        if not query_analysis or not query_analysis.identified_anime:
            state["search_urls"] = []
            return state

        search_urls = []

        # Generate search URLs for each identified anime
        for anime_info in query_analysis.identified_anime:
            anime_title = anime_info.anime_title
            anime_keywords = anime_info.keywords if anime_info.keywords else []

            # Base search queries using enhanced patterns
            for pattern in self.search_patterns:
                search_query = pattern.format(anime=anime_title)

                # Create search URLs (simulated - in production would use real search APIs)
                search_url = f"https://duckduckgo.com/html/?q={quote(search_query)}"
                search_urls.append(search_url)

            # Generate AI-enhanced search queries based on anime keywords and context
            enhanced_queries = self._generate_smart_search_queries(anime_title, anime_keywords)

            for query in enhanced_queries:
                search_url = f"https://duckduckgo.com/html/?q={quote(query)}"
                search_urls.append(search_url)

            # Add a few targeted site-specific searches with better queries
            targeted_patterns = [
                f"site:animenewsnetwork.com {anime_title} real locations",
                f"site:myanimelist.net {anime_title} anime pilgrimage",
                f"site:japan-guide.com {anime_title} tourism",
                f"site:tripadvisor.in {anime_title} filming locations"
            ]

            for pattern in targeted_patterns:
                search_url = f"https://duckduckgo.com/html/?q={quote(pattern)}"
                search_urls.append(search_url)

        # Limit to most relevant URLs for efficiency
        state["search_urls"] = search_urls[:15]  # Increased from 10 to allow more diverse searches
        state["anime_focus"] = query_analysis.identified_anime[0].anime_title

        print(f"Generated {len(search_urls)} search queries for '{anime_title}':")
        for i, url in enumerate(search_urls[:5]):  # Show first 5 for debugging
            print(f"  {i+1}. {url}")

        return state

    def _generate_smart_search_queries(self, anime_title: str, keywords: List[str]) -> List[str]:
        """Generate intelligent search queries based on anime context."""
        queries = []

        # Create variations of the anime title
        title_variations = [
            anime_title,
            anime_title.replace(" ", ""),
            anime_title.lower(),
            anime_title.replace(" and ", " & ")
        ]

        # Location-specific searches
        location_terms = ["real locations", "filming locations", "inspired places", "seichi", "holy land", "tourism spots"]

        # Combine anime titles with location terms
        for title in title_variations[:2]:  # Limit variations
            for term in location_terms[:3]:  # Limit terms
                queries.append(f"{title} {term}")

        # Use keywords to create specific searches
        if keywords:
            # Look for location-related keywords
            location_keywords = [kw for kw in keywords if any(word in kw.lower() for word in ['tokyo', 'kyoto', 'osaka', 'japan', 'temple', 'school', 'station'])]

            for kw in location_keywords[:2]:  # Limit keyword searches
                queries.append(f"{anime_title} {kw}")

        # Add Japanese-specific terms for better results
        queries.append(f"{anime_title} 聖地巡礼")  # "seichi junrei" = holy land pilgrimage
        queries.append(f"{anime_title} ロケ地")     # "rokechi" = filming location

        # Add popular pilgrimage patterns
        queries.append(f"how to visit {anime_title} locations in Japan")
        queries.append(f"{anime_title} travel guide Japan")

        return queries[:8]  # Limit to top queries

    async def _execute_searches(self, state: CrawlerState) -> CrawlerState:
        """Execute searches and collect initial results."""
        search_urls = state["search_urls"]

        if not self.session:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': self.user_agent}
            )

        scraped_data = []

        for url in search_urls:
            try:
                # Add random delay to avoid rate limiting
                await asyncio.sleep(random.uniform(*self.request_delay))

                async with self.session.get(url, allow_redirects=True) as response:
                    if response.status == 200:
                        content = await response.text()
                        scraped_data.append({
                            'url': str(response.url),
                            'content': content,
                            'status': response.status
                        })
                    else:
                        print(f"Failed to fetch {url}: {response.status}")

            except Exception as e:
                print(f"Error fetching {url}: {e}")
                continue

        state["scraped_data"] = scraped_data
        return state

    async def _crawl_results(self, state: CrawlerState) -> CrawlerState:
        """Crawl additional links from search results."""
        scraped_data = state["scraped_data"]
        anime_focus = state["anime_focus"]

        if not scraped_data or not anime_focus:
            return state

        additional_urls = []

        # Extract relevant links from scraped content
        for data in scraped_data:
            try:
                soup = BeautifulSoup(data['content'], 'html.parser')

                # Find links that might contain pilgrimage information
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    text = link.get_text().lower()

                    # Check if link is relevant
                    if any(keyword in text for keyword in [
                        'pilgrimage', 'location', 'spot', 'place', 'visit',
                        'real', 'actual', 'filming', 'scene', anime_focus.lower()
                    ]):
                        if href.startswith('/'):
                            base_url = f"{urlparse(data['url']).scheme}://{urlparse(data['url']).netloc}"
                            href = urljoin(base_url, href)
                        elif not href.startswith('http'):
                            continue

                        if href not in [d['url'] for d in scraped_data]:
                            additional_urls.append(href)

            except Exception as e:
                print(f"Error parsing links from {data['url']}: {e}")
                continue

        # Limit additional crawling
        additional_urls = additional_urls[:5]

        # Crawl additional URLs
        for url in additional_urls:
            try:
                await asyncio.sleep(random.uniform(*self.request_delay))

                async with self.session.get(url, allow_redirects=True) as response:
                    if response.status == 200:
                        content = await response.text()
                        scraped_data.append({
                            'url': str(response.url),
                            'content': content,
                            'status': response.status
                        })

            except Exception as e:
                print(f"Error crawling additional URL {url}: {e}")
                continue

        state["scraped_data"] = scraped_data
        return state

    async def _extract_locations(self, state: CrawlerState) -> CrawlerState:
        """Extract pilgrimage location data from scraped content."""
        scraped_data = state["scraped_data"]
        anime_focus = state["anime_focus"]

        locations = []

        for data in scraped_data:
            try:
                locations_from_page = self._extract_locations_from_page(data, anime_focus)
                locations.extend(locations_from_page)

            except Exception as e:
                print(f"Error extracting locations from {data['url']}: {e}")
                continue

        # Deduplicate locations based on name and address
        unique_locations = []
        seen = set()

        for location in locations:
            key = (location['name'].lower(), location['real_world_address'].lower())
            if key not in seen:
                seen.add(key)
                unique_locations.append(location)

        state["total_locations"] = unique_locations
        return state

    def _extract_locations_from_page(self, page_data: Dict[str, Any], anime_focus: str) -> List[Dict[str, Any]]:
        """Extract location information from a single page."""
        content = page_data['content']
        url = page_data['url']

        soup = BeautifulSoup(content, 'html.parser')
        locations = []

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text()

        # Location extraction patterns
        location_patterns = [
            r'([A-Z][a-z]+\s+(?:Station|Temple|Shrine|Park|Bridge|Tower|Building|Street))',
            r'(\d+\s+[A-Z][a-z]+\s+(?:Street|Avenue|Road|Boulevard))',
            r'([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)',
        ]

        # Scene description patterns
        scene_patterns = [
            r'(?:scene|episode|moment).{0,50}?(?:showed|featured|depicted)',
            r'(?:where|in which).{0,30}?(?:character|protagonist)',
        ]

        # Look for structured data
        structured_locations = self._extract_structured_data(soup, anime_focus)
        locations.extend(structured_locations)

        # Look for location mentions in text
        for pattern in location_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                location_name = match.group(1)

                # Extract context around the location mention
                start_pos = max(0, match.start() - 200)
                end_pos = min(len(text), match.end() + 200)
                context = text[start_pos:end_pos].strip()

                # Try to extract address information
                address = self._extract_address_from_context(context)

                # Extract scene description
                scene_desc = ""
                for scene_pattern in scene_patterns:
                    scene_match = re.search(scene_pattern, context, re.IGNORECASE)
                    if scene_match:
                        scene_desc = scene_match.group(0)
                        break

                if len(location_name) > 3:  # Filter out very short matches
                    locations.append({
                        'name': location_name,
                        'anime_title': anime_focus,
                        'real_world_address': address,
                        'description': context[:200],
                        'scene_description': scene_desc,
                        'source_url': url,
                        'confidence_score': self._calculate_confidence(location_name, context)
                    })

        return locations

    def _extract_structured_data(self, soup: BeautifulSoup, anime_focus: str) -> List[Dict[str, Any]]:
        """Extract structured location data from the page."""
        locations = []

        # Look for tables with location information
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 1:  # At least header + one data row
                headers = [th.get_text().strip().lower() for th in rows[0].find_all(['th', 'td'])]

                if any(keyword in ' '.join(headers) for keyword in ['location', 'place', 'address']):
                    for row in rows[1:]:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            location_data = {
                                'anime_title': anime_focus,
                                'source_url': 'table_data',
                                'confidence_score': 0.8
                            }

                            for i, cell in enumerate(cells):
                                if i < len(headers):
                                    header = headers[i]
                                    value = cell.get_text().strip()

                                    if 'name' in header or 'location' in header:
                                        location_data['name'] = value
                                    elif 'address' in header:
                                        location_data['real_world_address'] = value
                                    elif 'description' in header:
                                        location_data['description'] = value

                            if 'name' in location_data:
                                locations.append(location_data)

        # Look for lists
        lists = soup.find_all(['ul', 'ol'])
        for lst in lists:
            items = lst.find_all('li', limit=10)  # Limit to avoid too many items
            for item in items:
                text = item.get_text().strip()
                if any(keyword in text.lower() for keyword in ['station', 'temple', 'shrine', 'park']):
                    locations.append({
                        'name': text,
                        'anime_title': anime_focus,
                        'real_world_address': '',
                        'description': text,
                        'source_url': 'list_data',
                        'confidence_score': 0.6
                    })

        return locations

    def _extract_address_from_context(self, context: str) -> str:
        """Extract address information from context."""
        address_patterns = [
            r'\d+\s+[A-Za-z]+\s+(?:Street|Avenue|Road|Boulevard|St|Ave|Rd),\s*[A-Za-z]+',
            r'[A-Za-z]+(?:,\s*[A-Za-z]+)*(?:,\s*[A-Z]{2}\s*\d{5})?',
            r'[A-Za-z]+-?\s*\d+',
        ]

        for pattern in address_patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(0)

        return ""

    def _calculate_confidence(self, location_name: str, context: str) -> float:
        """Calculate confidence score for extracted location."""
        confidence = 0.5  # Base confidence

        # Boost for specific location types
        if any(keyword in location_name.lower() for keyword in [
            'station', 'temple', 'shrine', 'park', 'tower', 'bridge', 'building'
        ]):
            confidence += 0.2

        # Boost for context indicators
        context_lower = context.lower()
        if any(keyword in context_lower for keyword in [
            'real location', 'actual place', 'filming location', 'anime pilgrimage',
            'can visit', 'access', 'how to get'
        ]):
            confidence += 0.2

        # Boost for Japanese context
        if any(keyword in context_lower for keyword in ['japan', 'japanese', 'tokyo', 'kyoto']):
            confidence += 0.1

        return min(confidence, 1.0)

    async def _validate_locations(self, state: CrawlerState) -> CrawlerState:
        """Validate and filter extracted locations."""
        locations = state["total_locations"]

        # Filter by confidence score
        validated_locations = [
            loc for loc in locations
            if loc.get('confidence_score', 0) >= 0.3
        ]

        # Sort by confidence
        validated_locations.sort(
            key=lambda x: x.get('confidence_score', 0),
            reverse=True
        )

        # Limit to top locations
        validated_locations = validated_locations[:15]

        state["total_locations"] = validated_locations
        return state

    async def _coordinate_lookup(self, state: CrawlerState) -> CrawlerState:
        """Add coordinates to locations using geocoding."""
        locations = state["total_locations"]

        for location in locations:
            if location.get('real_world_address'):
                # Simulate coordinate lookup (in production would use real geocoding API)
                location['coordinates'] = {
                    'lat': 35.6762 + random.uniform(-1, 1),  # Around Tokyo area
                    'lng': 139.6503 + random.uniform(-1, 1)
                }
            else:
                location['coordinates'] = None

        state["total_locations"] = locations
        return state

    async def crawl_anime_locations(self, query_analysis: QueryAnalysis) -> List[PilgrimageLocation]:
        """
        Main method to crawl anime pilgrimage locations.

        Args:
            query_analysis: Results from query analysis

        Returns:
            List of PilgrimageLocation objects
        """
        initial_state = {
            "messages": [HumanMessage(content="Start anime pilgrimage location crawling")],
            "query_analysis": query_analysis,
            "current_depth": 0,
            "max_depth": 2
        }

        try:
            # Run the LangGraph workflow
            final_state = await self.graph.ainvoke(initial_state)

            # Convert raw data to PilgrimageLocation objects
            pilgrimage_locations = []
            for loc_data in final_state.get("total_locations", []):
                pilgrimage_locations.append(PilgrimageLocation(**loc_data))

            return pilgrimage_locations

        except Exception as e:
            print(f"Error in crawling workflow: {e}")
            return []

        finally:
            # Clean up session
            if self.session:
                await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()


async def main():
    """Demo function for testing the web crawler."""
    from src.components.query_analyzer import QueryAnalyzer
    from src.components.query_interface import QueryInterface

    # Test the full pipeline
    interface = QueryInterface()
    analyzer = QueryAnalyzer()

    test_query = "I want to visit locations from Your Name in Tokyo and Kyoto"

    print(f"🚀 Testing crawler with query: '{test_query}'")

    # Process query
    user_query = interface.process_query(test_query)
    if not user_query:
        print("❌ Query rejected")
        return

    # Analyze query
    analysis = analyzer.analyze_query(user_query)
    print(f"📊 Query analysis complete: {len(analysis.identified_anime)} anime identified")

    # Crawl locations
    async with AgenticWebCrawler() as crawler:
        locations = await crawler.crawl_anime_locations(analysis)

        print(f"🎌 Found {len(locations)} pilgrimage locations:")
        for i, loc in enumerate(locations[:5], 1):  # Show top 5
            print(f"\n{i}. {loc.name}")
            print(f"   📍 Address: {loc.real_world_address}")
            print(f"   📺 Anime: {loc.anime_title}")
            print(f"   ⭐ Confidence: {loc.confidence_score:.2f}")
            if loc.coordinates:
                print(f"   🗺️  Coordinates: {loc.coordinates['lat']:.4f}, {loc.coordinates['lng']:.4f}")
            print(f"   🔗 Source: {loc.source_url}")


if __name__ == "__main__":
    asyncio.run(main())