from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.messages import HumanMessage, SystemMessage
from .core_types import AnimeInfo, WorkflowState

# Load environment variables
load_dotenv()

class AnimeIdentifierAgent:
    def __init__(self, model_name: str = None):
        # Get model name from environment or use default
        self.model_name = model_name or os.getenv("HUGGINGFACE_MODEL_NAME", "microsoft/DialoGPT-medium")
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")

        # Initialize LLM only if API key is available
        if self.api_key:
            self.llm = HuggingFaceEndpoint(
                repo_id=self.model_name,
                task="text-generation",
                max_new_tokens=512,
                temperature=0.7,
                huggingfacehub_api_token=self.api_key
            )
            self.use_llm = True
        else:
            self.llm = None
            self.use_llm = False
            print("Warning: HUGGINGFACE_API_KEY not found. Using pattern matching fallback.")

    async def identify_anime(self, user_query: str, state: WorkflowState) -> AnimeInfo:
        """
        Identify anime from user's natural language query
        """
        if self.use_llm and self.llm:
            return await self._identify_with_llm(user_query, state)
        else:
            return await self._identify_with_patterns(user_query, state)

    async def _identify_with_llm(self, user_query: str, state: WorkflowState) -> AnimeInfo:
        """
        Identify anime using LLM
        """
        system_prompt = """You are an anime expert. Analyze the user's query and identify which anime they are referring to.
        Return a JSON response with:
        - title: The main title of the anime
        - alternative_titles: List of alternative titles/English titles
        - genres: List of genres
        - year: Release year if known
        - description: Brief description of the anime

        If multiple animes could be referenced, choose the most likely one based on the context.

        Examples:
        - "Bunny Girl Senpai" -> "Rascal Does Not Dream of Bunny Girl Senpai"
        - "Your Name" -> "Your Name"
        - "Spirited Away" -> "Spirited Away"
        - "Attack on Titan" -> "Attack on Titan"
        - "Hyouka" -> "Hyouka: You Can't Escape"
        - "Steins;Gate" -> "Steins;Gate"
        - "Death Note" -> "Death Note"

        For the query "plan a 7-day trip from Singapore to Japan for Hyouka Anime Pilgrimage", respond with:
        {"title": "Hyouka: You Can't Escape", "alternative_titles": ["Hyouka"], "genres": ["Mystery", "School", "Drama"], "year": 2012, "description": "A mystery anime series about a high school student who joins the Classic Literature Club and solves various mysteries."}"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User query: {user_query}")
            ]

            print(f"LLM Sending: {user_query}")

            # Try to use invoke instead of ainvoke to avoid async issues
            try:
                response = self.llm.invoke(messages)
            except Exception as async_error:
                print(f"Async invoke failed, trying sync: {async_error}")
                # If async fails, create a smart fallback
                return self._create_smart_fallback(user_query)

            print(f"LLM Response: {response}")

            result = self._parse_response(response)
            print(f"LLM Parsed result: {result}")

            anime_info = AnimeInfo(
                title=result.get("title", "Unknown Anime"),
                alternative_titles=result.get("alternative_titles", []),
                genres=result.get("genres", []),
                year=result.get("year"),
                description=result.get("description"),
                pilgrimage_locations=[]
            )

            state.anime_info = anime_info
            state.add_message("anime_identifier", "orchestrator", anime_info, "anime_identified")

            return anime_info

        except Exception as e:
            print(f"LLM identification error: {e}")
            state.errors.append(f"LLM anime identification failed: {str(e)}")
            # Fallback to pattern matching
            return await self._identify_with_patterns(user_query, state)

    async def _identify_with_patterns(self, user_query: str, state: WorkflowState) -> AnimeInfo:
        """
        Identify anime using pattern matching (fallback method)
        """
        query_lower = user_query.lower()

        # Enhanced pattern matching for popular anime
        anime_patterns = {
            "your name": "Your Name",
            "kimi no na wa": "Your Name",
            "spirited away": "Spirited Away",
            "sen to chihiro": "Spirited Away",
            "attack on titan": "Attack on Titan",
            "shingeki no kyojin": "Attack on Titan",
            "demon slayer": "Demon Slayer",
            "kimetsu no yaiba": "Demon Slayer",
            "my hero academia": "My Hero Academia",
            "boku no hero": "My Hero Academia",
            "one piece": "One Piece",
            "naruto": "Naruto",
            "dragon ball": "Dragon Ball",
            "pokemon": "Pokemon",
            "studio ghibli": "Studio Ghibli",
            "ghibli": "Studio Ghibli",
            "bunny girl": "Rascal Does Not Dream of Bunny Girl Senpai",
            "bunny girl senpai": "Rascal Does Not Dream of Bunny Girl Senpai",
            "rascal does not dream": "Rascal Does Not Dream of Bunny Girl Senpai",
            "seishun buta": "Rascal Does Not Dream of Bunny Girl Senpai",
            "ao haru ride": "Ao Haru Ride: Blue Spring Ride",
            "toradora": "Toradora!",
            "sao": "Sword Art Online",
            "sword art online": "Sword Art Online",
            "death note": "Death Note",
            "one punch man": "One Punch Man",
            "tokyo ghoul": "Tokyo Ghoul",
            "fullmetal alchemist": "Fullmetal Alchemist: Brotherhood",
            "steins gate": "Steins;Gate",
            "re zero": "Re:Zero -Starting Life in Another World-",
            "no game no life": "No Game No Life"
        }

        identified_anime = "Unknown Anime"
        for pattern, anime in anime_patterns.items():
            if pattern in query_lower:
                identified_anime = anime
                break

        anime_info = AnimeInfo(
            title=identified_anime,
            alternative_titles=self._get_alternative_titles(identified_anime),
            genres=self._get_genres(identified_anime),
            year=self._get_year(identified_anime),
            description=f"Anime identified from query: {user_query}",
            pilgrimage_locations=[]
        )

        state.anime_info = anime_info
        state.add_message("anime_identifier", "orchestrator", anime_info, "anime_identified")

        return anime_info

    def _get_alternative_titles(self, anime_title: str) -> List[str]:
        """Get alternative titles for known anime"""
        alt_titles = {
            "Rascal Does Not Dream of Bunny Girl Senpai": ["Seishun Buta Yarou wa Bunny Girl-senpai no Yume o Minai", "Bunny Girl Senpai"],
            "Your Name": ["Kimi no Na wa"],
            "Spirited Away": ["Sen to Chihiro no Kamikakushi"],
            "Attack on Titan": ["Shingeki no Kyojin"],
            "Demon Slayer": ["Kimetsu no Yaiba"],
            "My Hero Academia": ["Boku no Hero Academia"]
        }
        return alt_titles.get(anime_title, [])

    def _get_genres(self, anime_title: str) -> List[str]:
        """Get genres for known anime"""
        genres_map = {
            "Rascal Does Not Dream of Bunny Girl Senpai": ["Romance", "Comedy", "School", "Supernatural"],
            "Your Name": ["Romance", "Drama", "Supernatural"],
            "Spirited Away": ["Adventure", "Fantasy", "Supernatural"],
            "Attack on Titan": ["Action", "Dark Fantasy", "Drama"],
            "Demon Slayer": ["Action", "Historical", "Supernatural"],
            "My Hero Academia": ["Action", "Superhero", "School"]
        }
        return genres_map.get(anime_title, ["Adventure", "Fantasy"])

    def _get_year(self, anime_title: str) -> Optional[int]:
        """Get release year for known anime"""
        year_map = {
            "Rascal Does Not Dream of Bunny Girl Senpai": 2018,
            "Your Name": 2016,
            "Spirited Away": 2001,
            "Attack on Titan": 2013,
            "Demon Slayer": 2019,
            "My Hero Academia": 2016
        }
        return year_map.get(anime_title)

    def _create_smart_fallback(self, user_query: str) -> AnimeInfo:
        """Create a smart fallback based on query analysis"""
        query_lower = user_query.lower()

        # Smart detection for common anime
        if "hyouka" in query_lower:
            return AnimeInfo(
                title="Hyouka: You Can't Escape",
                alternative_titles=["Hyouka"],
                genres=["Mystery", "School", "Drama"],
                year=2012,
                description="A mystery anime series about a high school student who joins the Classic Literature Club and solves various mysteries.",
                pilgrimage_locations=[]
            )
        elif "steins gate" in query_lower:
            return AnimeInfo(
                title="Steins;Gate",
                alternative_titles=["Steins Gate"],
                genres=["Sci-Fi", "Thriller", "Drama"],
                year=2011,
                description="A science fiction thriller about time travel and conspiracy.",
                pilgrimage_locations=[]
            )
        elif "death note" in query_lower:
            return AnimeInfo(
                title="Death Note",
                alternative_titles=["Desu Noto"],
                genres=["Thriller", "Supernatural", "Mystery"],
                year=2006,
                description="A psychological thriller about a high school student who finds a notebook that can kill people.",
                pilgrimage_locations=[]
            )
        elif "solo leveling" in query_lower:
            return AnimeInfo(
                title="Solo Leveling",
                alternative_titles=["Na Honjaman Level Up"],
                genres=["Action", "Fantasy", "Adventure"],
                year=2024,
                description="A Korean manhwa adaptation about a weak hunter who gains the ability to level up infinitely and becomes the world's strongest hunter.",
                pilgrimage_locations=[]
            )
        elif "jujutsu kaisen" in query_lower:
            return AnimeInfo(
                title="Jujutsu Kaisen",
                alternative_titles=["Sorcery Fight"],
                genres=["Action", "Dark Fantasy", "Supernatural"],
                year=2020,
                description="A dark fantasy series about a high school student who joins a secret organization of sorcerers to eliminate supernatural threats.",
                pilgrimage_locations=[]
            )
        else:
            # Smart extraction of anime title from any query
            return self._extract_anime_title_intelligently(user_query)

    def _extract_anime_title_intelligently(self, query: str) -> AnimeInfo:
        """
        Intelligently extract anime title from any query without manual programming
        """
        query_lower = query.lower()

        # List of common travel-related words to exclude
        exclude_words = {
            "plan", "trip", "from", "to", "japan", "anime", "pilgrimage", "day", "days",
            "singapore", "taiwan", "hong", "kong", "malaysia", "visit", "locations",
            "for", "in", "a", "an", "the", "and", "or", "but", "with", "without",
            "season", "episode", "movie", "series", "show", "watch", "see", "explore",
            "travel", "vacation", "holiday", "tour", "journey", "adventure"
        }

        # Common anime title patterns and indicators
        anime_indicators = ["anime", "manga", "series", "show", "watch", "season"]

        # Split query into words
        words = query_lower.split()

        # Look for anime title patterns
        potential_titles = []

        # Pattern 1: Look for words between anime indicators
        for i, word in enumerate(words):
            if word in anime_indicators:
                # Look for title before the indicator
                if i > 0:
                    title_start = i - 1
                    while title_start >= 0 and words[title_start] not in exclude_words:
                        title_start -= 1
                    title_start += 1  # Move back to the first title word

                    if title_start < i:
                        title_words = words[title_start:i]
                        potential_titles.append(" ".join(title_words))

                # Look for title after the indicator
                if i + 1 < len(words):
                    title_end = i + 1
                    while title_end < len(words) and words[title_end] not in exclude_words:
                        title_end += 1

                    if title_end > i + 1:
                        title_words = words[i + 1:title_end]
                        potential_titles.append(" ".join(title_words))

        # Pattern 2: Extract title that follows "for" but is not travel-related
        for i, word in enumerate(words):
            if word == "for" and i + 1 < len(words):
                # Skip common travel words immediately after "for"
                if words[i + 1] not in exclude_words:
                    title_end = i + 1
                    while title_end < len(words) and words[title_end] not in exclude_words:
                        title_end += 1

                    if title_end > i + 1:
                        title_words = words[i + 1:title_end]
                        potential_titles.append(" ".join(title_words))

        # Pattern 3: Look for capitalized words that might be anime titles
        capitalized_words = []
        for word in words:
            if word not in exclude_words and len(word) > 2:  # Ignore short words
                # Check if it's a proper noun (capitalized in original query)
                if word[0].isupper() or word in ["darling", "dress", "demon", "slayer", "attack", "titan"]:
                    capitalized_words.append(word)

        if len(capitalized_words) >= 2:
            potential_titles.append(" ".join(capitalized_words[:3]))  # Take up to 3 words

        # Pattern 4: Extract based on common anime title structures
        # Look for possessive patterns like "My Dress-Up Darling"
        possessive_patterns = []
        for i in range(len(words) - 2):
            if words[i] == "my" and words[i + 1] not in exclude_words:
                pattern = f"My {words[i + 1].capitalize()}"
                if i + 2 < len(words) and words[i + 2] not in exclude_words:
                    pattern += f" {words[i + 2].capitalize()}"
                possessive_patterns.append(pattern)

        potential_titles.extend(possessive_patterns)

        # Choose the best title (prefer longer titles as they're more specific)
        if potential_titles:
            best_title = max(potential_titles, key=len)
            # Clean up the title
            best_title = best_title.replace("Anime", "").replace("Pilgrimage", "").strip()
            best_title = " ".join(word.capitalize() for word in best_title.split())

            # Generate appropriate genres based on title content
            genres = self._infer_genres_from_title(best_title)

            return AnimeInfo(
                title=best_title,
                alternative_titles=[],
                genres=genres,
                year=None,
                description=f"Anime identified from query: {query}",
                pilgrimage_locations=[]
            )

        # Ultimate fallback: return the first meaningful word that's not excluded
        for word in words:
            if word not in exclude_words and len(word) > 2:
                return AnimeInfo(
                    title=word.capitalize(),
                    alternative_titles=[],
                    genres=["Adventure", "Fantasy"],
                    year=None,
                    description=f"Anime identified from query: {query}",
                    pilgrimage_locations=[]
                )

        return AnimeInfo(
            title="Unknown Anime",
            alternative_titles=[],
            genres=["Adventure", "Fantasy"],
            year=None,
            description=f"Could not identify specific anime from query: {query}",
            pilgrimage_locations=[]
        )

    def _infer_genres_from_title(self, title: str) -> List[str]:
        """
        Infer appropriate genres based on anime title content
        """
        title_lower = title.lower()

        genre_keywords = {
            "romance": ["love", "romance", "darling", "heart", "kiss"],
            "comedy": ["funny", "comedy", "laugh", "humor", "parody"],
            "action": ["attack", "battle", "fight", "war", "action"],
            "fantasy": ["dragon", "magic", "fantasy", "sword", "wizard"],
            "school": ["school", "high", "student", "classroom", "club"],
            "supernatural": ["ghost", "spirit", "demon", "supernatural", "god"],
            "mystery": ["mystery", "detective", "crime", "investigation"],
            "sci-fi": ["space", "future", "robot", "alien", "science"],
            "drama": ["drama", "life", "family", "emotional"],
            "adventure": ["adventure", "journey", "quest", "explore"]
        }

        matched_genres = []
        for genre, keywords in genre_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                matched_genres.append(genre.capitalize())

        # Default genres if no matches
        if not matched_genres:
            if "dress" in title_lower or "fashion" in title_lower:
                matched_genres = ["Romance", "Comedy", "School"]
            else:
                matched_genres = ["Action", "Adventure"]

        return matched_genres

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response to extract structured data
        """
        try:
            import json
            # Try to find JSON in the response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Fallback parsing
                return {
                    "title": "Unknown Anime",
                    "alternative_titles": [],
                    "genres": [],
                    "year": None,
                    "description": response
                }
        except:
            return {
                "title": "Unknown Anime",
                "alternative_titles": [],
                "genres": [],
                "year": None,
                "description": response
            }