"""
User Query Interface Component
Accepts natural language queries from users about anime pilgrimage trips.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import re


class UserQuery(BaseModel):
    """Data model for user pilgrimage queries."""

    original_text: str = Field(..., description="Original user query text")
    normalized_text: str = Field(..., description="Cleaned and normalized query text")
    query_type: str = Field(default="pilgrimage", description="Type of query")
    confidence: float = Field(default=1.0, description="Confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional query metadata")


class QueryInterface:
    """
    User Query Interface
    Function: Accept natural language queries from users about anime pilgrimage trips.

    Example Input: "I want to visit locations from Your Name in Tokyo and Kyoto."
    """

    def __init__(self):
        self.query_patterns = [
            r"(?:i want to|i'd like to|i wanna).*(?:visit|see|go to|travel to)",
            r"(?:anime|manga|game).*(?:locations?|spots?|places?)",
            r"(?:pilgrimage|holy grail|sacred).*(?:sites?|locations?|places?)",
            r"(?:real life|actual|real world).*(?:locations?|spots?|places?)"
        ]

    def validate_query(self, text: str) -> bool:
        """
        Validate if the input is a valid pilgrimage query.

        Args:
            text: Raw user input text

        Returns:
            bool: True if valid pilgrimage query
        """
        if not text or len(text.strip()) < 5:
            return False

        text_lower = text.lower()

        # Check for anime-related patterns (more flexible)
        anime_patterns = [
            r'\b(anime|manga|series|movie|film)\b',
            r'\b(bunny girl|rascal|senpai|dream|seishun|buta)\b',  # Common anime terms
            r'\b(tokyo|japan|japanese|kyoto|osaka)\b',  # Location indicators
            r'\b(pilgrimage|location|spot|place|visit|trip)\b'
        ]

        # Check for trip-related patterns
        trip_patterns = [
            r'(?:plan|want|like|create).{0,20}(?:trip|visit|travel)',
            r'(?:days?|week|weekend).{0,20}(?:trip|tour)',
            r'\d+\s+days?.{0,20}(?:trip|tour)'
        ]

        # More flexible validation
        return (
            any(re.search(pattern, text_lower) for pattern in self.query_patterns) or
            any(re.search(pattern, text_lower) for pattern in anime_patterns) or
            any(re.search(pattern, text_lower) for pattern in trip_patterns)
        )

    def normalize_text(self, text: str) -> str:
        """
        Clean and normalize user input text.

        Args:
            text: Raw user input text

        Returns:
            str: Normalized text
        """
        # Basic cleaning
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'[^\w\s\-\.,!?]', '', text)  # Remove special chars except basic punctuation

        return text

    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract basic metadata from the query.

        Args:
            text: Normalized query text

        Returns:
            Dict with extracted metadata
        """
        metadata = {
            'word_count': len(text.split()),
            'char_count': len(text),
            'has_locations': bool(re.search(r'(?:tokyo|kyoto|osaka|japan|japanese)', text.lower())),
            'has_anime_terms': bool(re.search(r'(?:anime|manga|game)', text.lower())),
            'time_mentions': re.findall(r'\b(?:days?|week|month|year)s?\b', text.lower()),
        }

        return metadata

    def process_query(self, raw_text: str) -> Optional[UserQuery]:
        """
        Process raw user input into a structured UserQuery object.

        Args:
            raw_text: Raw user input text

        Returns:
            UserQuery object if valid, None otherwise
        """
        if not self.validate_query(raw_text):
            return None

        normalized_text = self.normalize_text(raw_text)
        metadata = self.extract_metadata(normalized_text)

        # Calculate confidence based on pattern matches
        confidence = 0.5  # Base confidence
        text_lower = normalized_text.lower()

        # Boost confidence for strong indicators
        if any(term in text_lower for term in ['anime', 'manga', 'game']):
            confidence += 0.2
        if any(term in text_lower for term in ['locations', 'spots', 'places']):
            confidence += 0.2
        if any(term in text_lower for term in ['visit', 'see', 'go to']):
            confidence += 0.1

        confidence = min(confidence, 1.0)

        return UserQuery(
            original_text=raw_text,
            normalized_text=normalized_text,
            query_type="pilgrimage",
            confidence=confidence,
            metadata=metadata
        )

    def format_query_for_analysis(self, query: UserQuery) -> str:
        """
        Format the query for the Query Analysis component.

        Args:
            query: Processed UserQuery object

        Returns:
            str: Formatted query text for analysis
        """
        return f"User Query: {query.normalized_text}\nMetadata: {query.metadata}"


def main():
    """Demo function for testing the Query Interface."""
    interface = QueryInterface()

    test_queries = [
        "I want to visit locations from Your Name in Tokyo and Kyoto.",
        "Show me anime pilgrimage spots in Japan",
        "I'd like to go to real life places from Attack on Titan",
        "What's the weather today?",  # Invalid query
        ""  # Empty query
    ]

    for query_text in test_queries:
        print(f"\nProcessing: '{query_text}'")
        result = interface.process_query(query_text)

        if result:
            print(f"✓ Valid query (confidence: {result.confidence:.2f})")
            print(f"  Normalized: '{result.normalized_text}'")
            print(f"  Metadata: {result.metadata}")
        else:
            print("✗ Invalid or rejected query")


if __name__ == "__main__":
    main()