from typing import Dict, List, Any
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.messages import HumanMessage, SystemMessage
from .core_types import AnimeInfo, WorkflowState

class AnimeIdentifierAgent:
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium"):
        self.llm = HuggingFaceEndpoint(
            repo_id=model_name,
            task="text-generation",
            max_new_tokens=512,
            temperature=0.7,
        )

    async def identify_anime(self, user_query: str, state: WorkflowState) -> AnimeInfo:
        """
        Identify anime from user's natural language query
        """
        system_prompt = """You are an anime expert. Analyze the user's query and identify which anime they are referring to.
        Return a JSON response with:
        - title: The main title of the anime
        - alternative_titles: List of alternative titles/English titles
        - genres: List of genres
        - year: Release year if known
        - description: Brief description of the anime

        If multiple animes could be referenced, choose the most likely one based on the context."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User query: {user_query}")
            ]

            response = await self.llm.ainvoke(messages)
            result = self._parse_response(response)

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
            state.errors.append(f"Anime identification failed: {str(e)}")
            raise

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