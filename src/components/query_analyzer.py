"""
Query Analysis & Anime Identification Component
Uses HuggingFace LLM to extract anime titles and relevant keywords from user input.
"""

import os
import re
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from dotenv import load_dotenv

from src.components.query_interface import UserQuery

# Load environment variables
load_dotenv()


class AnimeIdentification(BaseModel):
    """Data model for identified anime information."""

    anime_title: str = Field(..., description="Identified anime title")
    confidence: float = Field(..., description="Confidence score (0-1)")
    keywords: List[str] = Field(default_factory=list, description="Relevant keywords")
    context: str = Field(default="", description="Context from user query")
    disambiguation_needed: bool = Field(default=False, description="Whether clarification is needed")


class QueryAnalysis(BaseModel):
    """Data model for complete query analysis results."""

    original_query: UserQuery
    identified_anime: List[AnimeIdentification] = Field(default_factory=list)
    extracted_keywords: List[str] = Field(default_factory=list)
    locations_mentioned: List[str] = Field(default_factory=list)
    trip_preferences: Dict[str, Any] = Field(default_factory=dict)
    disambiguation_questions: List[str] = Field(default_factory=list)
    analysis_confidence: float = Field(default=0.0, description="Overall confidence in analysis")


class QueryAnalyzer:
    """
    Query Analysis & Anime Identification
    Core: HuggingFace large language model (LLM) fine-tuned or prompt-engineered for anime domain recognition.

    Tasks:
    - Extract anime titles and relevant keywords from user input.
    - Disambiguate multiple or ambiguous anime references.
    - Output: Identified anime(s) and query context for crawling.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("HUGGINGFACE_MODEL_NAME", "google/gemma-3-4b-it")
        self.tokenizer = None
        self.model = None
        self.generator = None
        self.anime_database = self._load_anime_database()

    def _load_anime_database(self) -> Dict[str, Dict[str, Any]]:
        """
        Load or create a basic anime database for identification.
        This serves as fallback but the system now primarily uses agentic web analysis.
        """
        return {
            "your name": {
                "alternate_titles": ["Kimi no Na wa", "Your Name."],
                "locations": ["Tokyo", "Shinjuku", "Hida", "Takayama"],
                "keywords": ["romance", "drama", "supernatural", "body swapping"],
                "type": "movie"
            },
            "attack on titan": {
                "alternate_titles": ["Shingeki no Kyojin", "AOT"],
                "locations": ["Oita", "Hita", "Kumamoto"],
                "keywords": ["action", "dark fantasy", "post-apocalyptic", "titans"],
                "type": "series"
            },
            "spirited away": {
                "alternate_titles": ["Sen to Chihiro no Kamikakushi"],
                "locations": ["Tokyo", "Ghibli Museum", "Hakone"],
                "keywords": ["fantasy", "spirituality", "coming of age", "ghibli"],
                "type": "movie"
            }
        }

    def _initialize_model(self):
        """Initialize the HuggingFace model and tokenizer."""
        if self.generator is None:
            try:
                print(f"Loading model: {self.model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token

                # Check for CUDA availability
                device = "cuda" if torch.cuda.is_available() else "cpu"
                dtype = torch.bfloat16 if device == "cuda" else torch.float32

                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    dtype=dtype,
                    device_map="auto" if device == "cuda" else None
                )

                self.generator = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    # max_length=512,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                print(f"Model loaded successfully on {device}")
            except Exception as e:
                print(f"Warning: Could not load model {self.model_name}: {e}")
                print("Falling back to rule-based analysis")
                self.generator = None

    def _extract_anime_titles_rule_based(self, text: str) -> List[Tuple[str, float]]:
        """
        Rule-based anime title extraction as fallback.

        Args:
            text: Normalized query text

        Returns:
            List of (anime_title, confidence) tuples
        """
        text_lower = text.lower()
        found_anime = []

        # First, try database matches
        for anime_title, anime_info in self.anime_database.items():
            # Check main title
            if anime_title in text_lower:
                confidence = 0.9
                found_anime.append((anime_title, confidence))
                continue

            # Check alternate titles
            for alt_title in anime_info["alternate_titles"]:
                if alt_title.lower() in text_lower:
                    confidence = 0.8
                    found_anime.append((anime_title, confidence))
                    break

        # If no database matches, try to extract anime titles from text
        if not found_anime:
            # Look for patterns that might indicate anime titles - more specific patterns
            anime_patterns = [
                # Pattern for "anime pilgrimage of [title]" - more flexible for long titles
                r'anime\s+pilgrimage\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,8})(?:\s+(?:in|at|for|to|with)|$)',
                # Specific known anime patterns - include the new title
                r'([^,.!?]*?(?:bunny girl senpai|rascal does not dream|seishun buta|liz and the blue bird|hyouka|the fragrant flower blooms with dignity|beyond the boundary)[^,.!?]*?)(?:\s+(?:in|at|for|to|with)|$)',
                r'([^,.!?]*?(?:one piece|naruto|attack on titan|your name|spirited away)[^,.!?]*?)(?:\s+(?:in|at|for|to|with)|$)',
                # Pattern for "[title] anime" or "[title] series"
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,6})(?:\s+anime|manga|series)(?:\s+(?:in|at|for|to|with)|$)',
                # Pattern for single word anime titles (like Hyouka)
                r'\b([A-Z][a-z]+)\b(?![\s]*anime|[\s]*pilgrimage|[\s]*series)',
            ]

            for pattern in anime_patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    # Clean up the match - remove common trip words
                    title = match.strip()
                    # Remove trailing words that indicate location or time
                    title = re.sub(r'\s+(in|at|for|to|with|tokyo|japan|days?|trip|plan)\s*$', '', title, flags=re.IGNORECASE)
                    # Remove leading words that indicate action
                    title = re.sub(r'^(plan|trip|visit|anime|manga|series|of|for|day|days?|week|weeks?)\s+', '', title, flags=re.IGNORECASE)
                    # Remove common trip phrases
                    title = re.sub(r'\b(day\s+trip\s+to|trip\s+to|plan\s+to|visit\s+to|pilgrimage\s+of)\s+', '', title, flags=re.IGNORECASE)
                    # Filter out common non-anime phrases
                    if re.search(r'\b(day\s+trip|plan|trip|visit|japan|tokyo|for|to|in|at|with|pilgrimage)\b', title, re.IGNORECASE):
                        continue

                    title = title.strip().title()

                    # Skip if title is too generic or contains trip-related words
                    generic_words = ['pilgrimage', 'trip', 'plan', 'visit', 'japan', 'tokyo', 'day', 'days']
                    if any(word in title.lower() for word in generic_words):
                        continue

                    # Skip duplicates and substrings
                    is_duplicate = False
                    for existing_title, _ in found_anime:
                        if title.lower() == existing_title.lower() or title.lower() in existing_title.lower() or existing_title.lower() in title.lower():
                            is_duplicate = True
                            break

                    if not is_duplicate and len(title) > 3 and title not in [a[0] for a in found_anime]:
                        found_anime.append((title, 0.6))  # Lower confidence for extracted titles

        return found_anime

    def _extract_locations_rule_based(self, text: str) -> List[str]:
        """
        Extract location mentions from text.

        Args:
            text: Normalized query text

        Returns:
            List of location names
        """
        # Common Japanese locations
        location_patterns = [
            r'\b(tokyo|kyoto|osaka|nara|kobe|yokohama|nagoya)s?\b',
            r'\b(hokkaido|honshu|kyushu|shikoku)s?\b',
            r'\b(japan|japanese)\b',
            r'\b(shinjuku|shibuya|harajuku|akihabara|ginza)s?\b',
            r'\b(hida|takayama|oita|hita|kumamoto)s?\b'
        ]

        locations = set()
        text_lower = text.lower()

        for pattern in location_patterns:
            matches = re.findall(pattern, text_lower)
            locations.update(matches)

        return list(locations)

    def _extract_keywords_rule_based(self, text: str, identified_anime: List[str]) -> List[str]:
        """
        Extract relevant keywords from text and identified anime.

        Args:
            text: Normalized query text
            identified_anime: List of identified anime titles

        Returns:
            List of relevant keywords
        """
        text_lower = text.lower()
        keywords = set()

        # Extract trip-related keywords
        trip_patterns = [
            r'\b(days?|weeks?|month)s?\b',
            r'\b(visit|see|go to|explore|travel|trip|vacation)s?\b',
            r'\b(walk|hike|train|bus|car|flight)s?\b',
            r'\b(hotel|ryokan|hostel|accommodation)s?\b'
        ]

        for pattern in trip_patterns:
            matches = re.findall(pattern, text_lower)
            keywords.update(matches)

        # Add anime-specific keywords
        for anime_title in identified_anime:
            if anime_title in self.anime_database:
                keywords.update(self.anime_database[anime_title]["keywords"])

        return list(keywords)

    async def _agentic_anime_analysis(self, anime_title: str) -> Dict[str, Any]:
        """
        Agentic analysis of anime title using web search and information extraction.

        Args:
            anime_title: The anime title to analyze

        Returns:
            Dictionary with anime information
        """
        print(f"Performing agentic analysis for: '{anime_title}'")

        # Search queries to find information about the anime
        search_queries = [
            f"{anime_title} anime real locations",
            f"{anime_title} pilgrimage spots Japan",
            f"{anime_title} filming locations real places",
            f"visit {anime_title} locations Japan",
            f"{anime_title} anime tourism spots"
        ]

        anime_info = {
            "title": anime_title,
            "alternate_titles": [],
            "locations": [],
            "keywords": [],
            "type": "unknown",
            "confidence": 0.7,  # Base confidence for web analysis
            "real_world_info": []
        }

        # Create session for web requests
        connector = aiohttp.TCPConnector(limit=5)
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as session:

            for query in search_queries[:3]:  # Limit to 3 searches for efficiency
                try:
                    # Search for information
                    search_url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"

                    async with session.get(search_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            info = await self._extract_anime_info_from_search(content, anime_title)

                            # Merge information
                            if info["alternate_titles"]:
                                anime_info["alternate_titles"].extend(info["alternate_titles"])
                            if info["locations"]:
                                anime_info["locations"].extend(info["locations"])
                            if info["keywords"]:
                                anime_info["keywords"].extend(info["keywords"])
                            if info["type"] != "unknown":
                                anime_info["type"] = info["type"]
                            if info["real_world_info"]:
                                anime_info["real_world_info"].extend(info["real_world_info"])

                except Exception as e:
                    print(f"Search failed for '{query}': {e}")
                    continue

        # Remove duplicates and clean up
        anime_info["alternate_titles"] = list(set(anime_info["alternate_titles"]))
        anime_info["locations"] = list(set(anime_info["locations"]))
        anime_info["keywords"] = list(set(anime_info["keywords"]))

        # Boost confidence if we found meaningful information
        if anime_info["locations"] or anime_info["real_world_info"]:
            anime_info["confidence"] = min(0.9, anime_info["confidence"] + 0.2)

        print(f"Agentic analysis complete for '{anime_title}' (confidence: {anime_info['confidence']:.2f})")
        return anime_info

    async def _extract_anime_info_from_search(self, html_content: str, anime_title: str) -> Dict[str, Any]:
        """
        Extract anime information from search results HTML.

        Args:
            html_content: HTML content from search results
            anime_title: The anime title we're searching for

        Returns:
            Dictionary with extracted information
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        info = {
            "alternate_titles": [],
            "locations": [],
            "keywords": [],
            "type": "unknown",
            "real_world_info": []
        }

        # Extract text from search results
        text_content = soup.get_text().lower()

        # Look for location mentions
        location_patterns = [
            r'\b(tokyo|kyoto|osaka|nara|kobe|yokohama|nagoya|sapporo|fukuoka)\b',
            r'\b(shinjuku|shibuya|harajuku|akihabara|ginza|ikebukuro|roppongi)\b',
            r'\b(station|temple|shrine|park|tower|bridge|building|street)\b',
            r'\b(japan|japanese)\b'
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, text_content)
            info["locations"].extend(matches)

        # Look for anime type indicators
        if any(keyword in text_content for keyword in ['movie', 'film']):
            info["type"] = "movie"
        elif any(keyword in text_content for keyword in ['series', 'tv', 'episode']):
            info["type"] = "series"
        elif any(keyword in text_content for keyword in ['ova', 'ona']):
            info["type"] = "ova"

        # Look for genre/keywords
        genre_patterns = [
            r'\b(romance|drama|comedy|action|fantasy|sci-fi|supernatural|mystery|thriller)\b',
            r'\b(romantic|dramatic|funny|exciting|magical|psychological|suspenseful)\b',
            r'\b(love|friendship|adventure|school|coming of age|coming-of-age)\b'
        ]

        for pattern in genre_patterns:
            matches = re.findall(pattern, text_content)
            info["keywords"].extend(matches)

        # Look for real-world information mentions
        real_world_patterns = [
            r'real.*?location',
            r'actual.*?place',
            r'filming.*?location',
            r'inspired.*?by',
            r'based.*?on.*?real',
            r'visit.*?location',
            r'pilgrimage.*?site'
        ]

        for pattern in real_world_patterns:
            if re.search(pattern, text_content):
                info["real_world_info"].append("real_world_connection_found")
                break

        return info

    def _generate_llm_analysis(self, query_text: str) -> str:
        """
        Generate LLM-based analysis (if model is available).

        Args:
            query_text: The user query to analyze

        Returns:
            LLM-generated analysis text
        """
        if self.generator is None:
            return ""

        prompt = f"""You are an expert anime pilgrimage planner. Analyze this query and extract:

1. Anime titles mentioned (be thorough with long/complex titles)
2. Key locations referenced (cities, specific places)
3. Trip preferences (duration, travel style, budget)
4. Any special interests or requirements

Important: Look for anime titles even if they're complex like "Rascal Does Not Dream of Bunny Girl Senpai" or "Seishun Buta Yarō wa Bunny Girl Senpai no Yume o Minai".

Query: "{query_text}"

Please provide a detailed analysis:"""

        try:
            result = self.generator(prompt, max_length=512, num_return_sequences=1)
            return result[0]['generated_text']
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return ""

    def _check_disambiguation_needed(self, identified_anime: List[Tuple[str, float]]) -> List[str]:
        """
        Check if disambiguation questions are needed.

        Args:
            identified_anime: List of (anime_title, confidence) tuples

        Returns:
            List of disambiguation questions
        """
        questions = []

        # Low confidence anime need clarification
        for anime_title, confidence in identified_anime:
            if confidence < 0.7:
                questions.append(
                    f"Did you mean the anime '{anime_title.title()}'? Please confirm."
                )

        # Multiple anime need prioritization
        if len(identified_anime) > 1:
            titles = [title for title, _ in identified_anime]
            questions.append(
                f"I found multiple anime references: {', '.join(titles)}. "
                f"Which one are you most interested in?"
            )

        return questions

    async def analyze_query(self, user_query: UserQuery) -> QueryAnalysis:
        """
        Perform complete analysis of user query.

        Args:
            user_query: Processed UserQuery object

        Returns:
            Complete QueryAnalysis object
        """
        # Initialize model if needed
        if self.generator is None:
            self._initialize_model()

        text = user_query.normalized_text

        # Try LLM analysis first, fall back to rule-based
        llm_analysis = self._generate_llm_analysis(text)

        # Extract anime titles
        anime_with_confidence = self._extract_anime_titles_rule_based(text)

        # Extract locations
        locations = self._extract_locations_rule_based(text)

        # Extract keywords
        anime_titles = [title for title, _ in anime_with_confidence]
        keywords = self._extract_keywords_rule_based(text, anime_titles)

        # Create AnimeIdentification objects
        identified_anime = []
        updated_anime_with_confidence = []

        for title, confidence in anime_with_confidence:
            anime_info = self.anime_database.get(title, {})

            # If anime not in database, perform agentic analysis
            if not anime_info:
                print(f"Unknown anime '{title}' - performing agentic analysis...")
                anime_info = await self._agentic_anime_analysis(title)
                confidence = anime_info.get("confidence", confidence)

            # Update the confidence in our list
            updated_anime_with_confidence.append((title, confidence))

            identified_anime.append(
                AnimeIdentification(
                    anime_title=title,
                    confidence=confidence,
                    keywords=anime_info.get("keywords", []),
                    context=user_query.original_text,
                    disambiguation_needed=confidence < 0.7
                )
            )

        # Check for disambiguation needs using updated confidence scores
        disambiguation_questions = self._check_disambiguation_needed(updated_anime_with_confidence)

        # Extract trip preferences
        trip_preferences = {
            "duration_preference": self._extract_duration_preference(text),
            "travel_style": self._extract_travel_style(text),
            "group_size": self._extract_group_size(text)
        }

        # Calculate overall confidence
        overall_confidence = min(
            user_query.confidence,
            max([conf for _, conf in anime_with_confidence] + [0.3])
        )

        return QueryAnalysis(
            original_query=user_query,
            identified_anime=identified_anime,
            extracted_keywords=keywords,
            locations_mentioned=locations,
            trip_preferences=trip_preferences,
            disambiguation_questions=disambiguation_questions,
            analysis_confidence=overall_confidence
        )

    def _extract_duration_preference(self, text: str) -> Optional[str]:
        """Extract trip duration preference from text."""
        duration_patterns = [
            (r'\b(\d+)[-]?days?\b', 'days'),  # Match "5-day" and "5 days"
            (r'\b(\d+)\s+weeks?\b', 'weeks'),
            (r'\bweekend\b', 'weekend'),
            (r'\bday trip\b', 'day_trip')  # Check this last
        ]

        text_lower = text.lower()
        for pattern, duration_type in duration_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if duration_type in ['days', 'weeks']:
                    return f"{match.group(1)} {duration_type}"
                return duration_type

        return None

    def _extract_travel_style(self, text: str) -> str:
        """Extract travel style preference from text."""
        text_lower = text.lower()

        if any(word in text_lower for word in ['budget', 'cheap', 'affordable']):
            return 'budget'
        elif any(word in text_lower for word in ['luxury', 'comfortable', 'premium']):
            return 'luxury'
        elif any(word in text_lower for word in ['backpack', 'hostel', 'basic']):
            return 'backpacker'
        else:
            return 'standard'

    def _extract_group_size(self, text: str) -> str:
        """Extract group size preference from text."""
        text_lower = text.lower()

        if 'alone' in text_lower or 'solo' in text_lower:
            return 'solo'
        elif 'couple' in text_lower or 'partner' in text_lower:
            return 'couple'
        elif 'family' in text_lower or 'kids' in text_lower:
            return 'family'
        elif 'group' in text_lower or 'friends' in text_lower:
            return 'group'
        else:
            return 'unknown'


def main():
    """Demo function for testing the Query Analyzer."""
    from src.components.query_interface import QueryInterface

    interface = QueryInterface()
    analyzer = QueryAnalyzer()

    test_queries = [
        "I want to visit locations from Your Name in Tokyo and Kyoto for 3 days",
        "Show me Attack on Titan pilgrimage spots in Oita",
        "I'd like to see both Spirited Away and Your Name locations over a weekend",
        "Plan a budget trip to anime locations in Japan"
    ]

    for query_text in test_queries:
        print(f"\n{'='*60}")
        print(f"Analyzing: '{query_text}'")

        # Process query through interface
        user_query = interface.process_query(query_text)
        if not user_query:
            print("❌ Query rejected by interface")
            continue

        # Analyze query
        analysis = analyzer.analyze_query(user_query)

        print(f"✅ Analysis Complete (Confidence: {analysis.analysis_confidence:.2f})")
        print(f"📺 Identified Anime: {[a.anime_title for a in analysis.identified_anime]}")
        print(f"📍 Locations: {analysis.locations_mentioned}")
        print(f"🔑 Keywords: {analysis.extracted_keywords}")
        print(f"⚙️ Trip Preferences: {analysis.trip_preferences}")

        if analysis.disambiguation_questions:
            print(f"❓ Disambiguation Needed:")
            for question in analysis.disambiguation_questions:
                print(f"   • {question}")


if __name__ == "__main__":
    main()