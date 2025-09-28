#!/usr/bin/env python3
"""
Enhanced Anime Title Parser
Specialized parser for extracting exact anime titles from user queries
Optimized for API calls to anitabi.cn and other anime databases
"""

import re
from typing import List, Tuple, Optional, Dict, Any
from difflib import SequenceMatcher
import json


class AnimeTitleParser:
    """
    Specialized parser for extracting anime titles from natural language queries
    Uses multiple strategies to identify exact anime titles for API calls
    """

    def __init__(self):
        # Common anime title patterns
        self.anime_patterns = [
            r'(?:seichi\s+junrei|anime\s+pilgrimage|pilgrimage)\s+(?:of|for|to)\s+([A-Z][a-zA-Z0-9\s\':\-]+?)(?=\s+(?:in|during|for|plan|$|trip|travel))',
            r'(?:plan|trip|travel)\s+(?:for|to)?\s*([A-Z][a-zA-Z0-9\s\':\-]+?)\s*(?:seichi|pilgrimage|anime)',
            r'([A-Z][a-zA-Z0-9\s\':\-]+?)\s*(?:seichi|junrei|pilgrimage)',
            r'([A-Z][a-zA-Z0-9\s\':\-]+?)\s*(?:anime|series|show|manga)',
            r'want\s+(?:to|a)\s+([A-Z][a-zA-Z0-9\s\':\-]+?)\s+(?:seichi|pilgrimage|trip)',
            r'for\s+([A-Z][a-zA-Z0-9\s\':\-]+?)\s*(?:trip|travel|pilgrimage)',
        ]

        # Noise words to filter out
        self.noise_words = {
            'trip', 'travel', 'plan', 'planning', 'days', 'day', 'week', 'month',
            'from', 'to', 'in', 'during', 'for', 'and', 'or', 'with', 'without',
            'seichi', 'junrei', 'pilgrimage', 'anime', 'series', 'show', 'manga',
            'taiwan', 'japan', 'tokyo', 'osaka', 'kyoto', 'want', 'would', 'like',
            'budget', 'medium', 'luxury', 'cheap', 'expensive', 'hotel', 'flight',
            'weather', 'map', 'guide', 'tour', 'visit', 'see', 'enjoy', 'experience'
        }

        # Common anime title suffixes/prefixes to clean
        self.title_suffixes = [
            r'\s+(?:series|show|manga|anime|the\s+movie|movie|film)$',
            r'\s+(?:seichi|junrei|pilgrimage|trip|travel|plan)$',
            r'\s+(?:days?|weeks?|months?|year|decade)$',
            r'\s+\d{4}$'  # Remove years
        ]

        # Known anime variations mapping
        self.anime_variations = {
            'bunny girl senpai': 'Bunny Girl Senpai',
            'rascal does not dream of bunny girl senpai': 'Bunny Girl Senpai',
            'seishun buta yarou': 'Bunny Girl Senpai',
            'your name': 'Your Name',
            'kimi no na wa': 'Your Name',
            'weathering with you': 'Weathering with You',
            'tenki no ko': 'Weathering with You',
            'silent voice': 'A Silent Voice',
            'koe no katachi': 'A Silent Voice',
            'demon slayer': 'Demon Slayer',
            'kimetsu no yaiba': 'Demon Slayer',
            'attack on titan': 'Attack on Titan',
            'shingeki no kyojin': 'Attack on Titan',
            'my hero academia': 'My Hero Academia',
            'boku no hero academia': 'My Hero Academia',
            'one piece': 'One Piece',
            'naruto': 'Naruto',
            'dragon ball z': 'Dragon Ball Z',
            'sailor moon': 'Sailor Moon',
            'death note': 'Death Note',
            'fullmetal alchemist': 'Fullmetal Alchemist',
            'steins gate': 'Steins;Gate',
            're zero': 'Re:Zero',
            'slam dunk': 'Slam Dunk'
        }

    def extract_anime_title(self, query: str) -> Tuple[str, float]:
        """
        Extract the most likely anime title from a user query
        Returns (title, confidence_score)
        """
        query = query.strip()
        best_match = ""
        best_confidence = 0.0

        # Strategy 1: Pattern-based extraction
        pattern_matches = self._extract_with_patterns(query)
        for match, confidence in pattern_matches:
            if confidence > best_confidence:
                best_match = match
                best_confidence = confidence

        # Strategy 2: Keyword-based extraction
        if not best_match:
            keyword_matches = self._extract_with_keywords(query)
            for match, confidence in keyword_matches:
                if confidence > best_confidence:
                    best_match = match
                    best_confidence = confidence

        # Strategy 3: Variation matching
        if not best_match:
            variation_matches = self._extract_with_variations(query)
            for match, confidence in variation_matches:
                if confidence > best_confidence:
                    best_match = match
                    best_confidence = confidence

        # Clean and validate the extracted title
        if best_match:
            cleaned_title = self._clean_title(best_match)
            if self._is_valid_anime_title(cleaned_title):
                return cleaned_title, best_confidence

        return "", 0.0

    def _extract_with_patterns(self, query: str) -> List[Tuple[str, float]]:
        """Extract using regex patterns"""
        matches = []

        for pattern in self.anime_patterns:
            for match in re.finditer(pattern, query, re.IGNORECASE):
                title = match.group(1).strip()
                confidence = self._calculate_confidence(title, query)
                if confidence > 0.3:  # Minimum confidence threshold
                    matches.append((title, confidence))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    def _extract_with_keywords(self, query: str) -> List[Tuple[str, float]]:
        """Extract by identifying potential anime titles among keywords"""
        matches = []
        words = query.split()

        # Look for sequences of capitalized words that could be anime titles
        for i in range(len(words)):
            for j in range(i + 1, min(i + 8, len(words) + 1)):  # Max 8 words for title
                candidate = " ".join(words[i:j])

                # Check if candidate starts with capital letter and has reasonable length
                if (candidate and candidate[0].isupper() and
                    2 <= len(candidate.split()) <= 6 and  # 2-6 words typical for anime titles
                    self._has_anime_like_characteristics(candidate)):

                    confidence = self._calculate_confidence(candidate, query)
                    if confidence > 0.2:
                        matches.append((candidate, confidence))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    def _extract_with_variations(self, query: str) -> List[Tuple[str, float]]:
        """Extract by matching known anime variations"""
        matches = []
        query_lower = query.lower()

        for variation, standard_title in self.anime_variations.items():
            if variation in query_lower:
                # Find the position to extract context
                pos = query_lower.find(variation)
                start = max(0, pos - 10)
                end = min(len(query), pos + len(variation) + 10)
                context = query[start:end]

                confidence = self._calculate_confidence(standard_title, context)
                matches.append((standard_title, confidence + 0.3))  # Boost for known variations

        return sorted(matches, key=lambda x: x[1], reverse=True)

    def _has_anime_like_characteristics(self, text: str) -> bool:
        """Check if text has characteristics of an anime title"""
        # Check for non-noise words
        words = text.lower().split()
        non_noise = [w for w in words if w not in self.noise_words]

        if not non_noise:
            return False

        # Check for anime-like patterns
        has_capitals = any(w[0].isupper() for w in text.split() if w)
        has_numbers = any(c.isdigit() for c in text)
        has_colon = ':' in text
        has_japanese = any(ord(c) > 127 for c in text)  # Simple Japanese character detection

        return has_capitals or has_numbers or has_colon or has_japanese

    def _calculate_confidence(self, title: str, context: str) -> float:
        """Calculate confidence score for extracted title"""
        if not title:
            return 0.0

        confidence = 0.0

        # Length bonus (optimal length is 2-4 words)
        word_count = len(title.split())
        if 2 <= word_count <= 4:
            confidence += 0.3
        elif 1 <= word_count <= 6:
            confidence += 0.2

        # Capitalization bonus
        if title.istitle() or all(w[0].isupper() for w in title.split() if w):
            confidence += 0.2

        # Position bonus (titles near pilgrimage keywords are more likely)
        context_lower = context.lower()
        if any(keyword in context_lower for keyword in ['seichi', 'pilgrimage', 'anime']):
            confidence += 0.2

        # Noise penalty
        title_lower = title.lower()
        noise_count = sum(1 for word in title_lower.split() if word in self.noise_words)
        noise_ratio = noise_count / len(title.split()) if title.split() else 0
        confidence -= noise_ratio * 0.3

        # Known anime bonus
        if any(variation in title_lower for variation in self.anime_variations.keys()):
            confidence += 0.3

        return max(0.0, min(1.0, confidence))

    def _clean_title(self, title: str) -> str:
        """Clean extracted title"""
        # Remove common suffixes
        for suffix in self.title_suffixes:
            title = re.sub(suffix, '', title, flags=re.IGNORECASE)

        # Clean up whitespace and punctuation
        title = ' '.join(title.split())
        title = title.strip(' :;,-.')

        # Apply known variations
        title_lower = title.lower()
        for variation, standard_title in self.anime_variations.items():
            if variation == title_lower:
                return standard_title

        return title

    def _is_valid_anime_title(self, title: str) -> bool:
        """Validate if the extracted title is likely to be an anime title"""
        if not title or len(title) < 2:
            return False

        # Check minimum content
        words = title.split()
        if len(words) < 1 or len(words) > 8:
            return False

        # Check if it's not just noise words
        title_lower = title.lower()
        content_words = [w for w in title_lower.split() if w not in self.noise_words]
        if not content_words:
            return False

        # Check for at least one meaningful word
        return len(content_words) > 0

    def get_multiple_candidates(self, query: str, max_candidates: int = 5) -> List[Tuple[str, float]]:
        """
        Get multiple candidate anime titles with confidence scores
        Useful for disambiguation when API returns multiple results
        """
        all_candidates = []

        # Get candidates from all methods
        pattern_matches = self._extract_with_patterns(query)
        keyword_matches = self._extract_with_keywords(query)
        variation_matches = self._extract_with_variations(query)

        all_candidates.extend(pattern_matches)
        all_candidates.extend(keyword_matches)
        all_candidates.extend(variation_matches)

        # Deduplicate and sort by confidence
        seen = set()
        unique_candidates = []
        for title, confidence in all_candidates:
            cleaned = self._clean_title(title)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                unique_candidates.append((cleaned, confidence))

        return sorted(unique_candidates, key=lambda x: x[1], reverse=True)[:max_candidates]

    def test_extraction(self, query: str) -> Dict[str, Any]:
        """Test the title extraction with detailed analysis"""
        result = {
            "query": query,
            "best_match": "",
            "confidence": 0.0,
            "all_candidates": [],
            "analysis": {}
        }

        # Extract best match
        best_match, confidence = self.extract_anime_title(query)
        result["best_match"] = best_match
        result["confidence"] = confidence

        # Get all candidates
        candidates = self.get_multiple_candidates(query)
        result["all_candidates"] = candidates

        # Detailed analysis
        result["analysis"] = {
            "pattern_matches": self._extract_with_patterns(query),
            "keyword_matches": self._extract_with_keywords(query),
            "variation_matches": self._extract_with_variations(query),
            "title_validation": self._is_valid_anime_title(best_match) if best_match else False
        }

        return result


def main():
    """Test the Anime Title Parser"""
    parser = AnimeTitleParser()

    # Test queries
    test_queries = [
        "7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Bunny Girl Senpai",
        "I want to plan a trip for anime pilgrimage of Your Name",
        "Plan a seichi junrei for Demon Slayer in Mid-Dec 2025",
        "Want to visit Slam Dunk filming locations in Japan",
        "Travel to Japan for Attack on Titan pilgrimage",
        "Looking for Weathering with You anime locations"
    ]

    print("[TEST] Anime Title Parser Test")
    print("=" * 50)

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = parser.test_extraction(query)

        print(f"Best Match: '{result['best_match']}' (confidence: {result['confidence']:.2f})")
        print(f"Candidates: {len(result['all_candidates'])}")
        for i, (title, conf) in enumerate(result['all_candidates'][:3], 1):
            print(f"  {i}. {title} ({conf:.2f})")


if __name__ == "__main__":
    main()