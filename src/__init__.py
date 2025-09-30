"""
Anime Pilgrimage Trip Planner

An agentic system that plans anime pilgrimage trips by:
1. Accepting user queries about anime locations
2. Identifying referenced anime using HuggingFace LLM
3. Crawling relevant websites for real-life location data
4. Generating optimized multi-day travel plans
5. Providing user-friendly responses
"""

__version__ = "1.0.0"
__author__ = "Anime Pilgrimage Planner Team"
__description__ = "Agentic anime pilgrimage trip planning system"

from .main import AnimePilgrimagePlanner

__all__ = ["AnimePilgrimagePlanner"]