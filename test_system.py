#!/usr/bin/env python3
"""
Simple test script to verify the anime pilgrimage system works
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.anime_title_parser import AnimeTitleParser
from agents.api.anime_pilgrimage_api import AnimePilgrimageAPI

def test_anime_parsing():
    """Test anime title parsing"""
    print("=" * 50)
    print("[TEST] Testing Anime Title Parser")
    print("=" * 50)

    parser = AnimeTitleParser()

    test_queries = [
        "7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Bunny Girl Senpai",
        "I want to plan a trip for anime pilgrimage of Your Name",
        "Plan a seichi junrei for Demon Slayer in Mid-Dec 2025",
        "Want to visit Slam Dunk filming locations in Japan",
        "Travel to Japan for Attack on Titan pilgrimage",
        "Looking for Weathering with You anime locations"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = parser.test_extraction(query)

        print(f"Best Match: '{result['best_match']}' (confidence: {result['confidence']:.2f})")
        print(f"Candidates: {len(result['all_candidates'])}")
        for i, (title, conf) in enumerate(result['all_candidates'][:3], 1):
            print(f"  {i}. {title} ({conf:.2f})")

def test_api_integration():
    """Test API integration"""
    print("\n" + "=" * 50)
    print("[TEST] Testing API Integration")
    print("=" * 50)

    api = AnimePilgrimageAPI()

    # Test with a popular anime
    test_anime = "Your Name"
    print(f"\nTesting API calls for: {test_anime}")

    try:
        # Test animepilgrimage.com web scraping
        print("[API] Testing animepilgrimage.com web scraping...")
        locations = api.search_animepilgrimage(test_anime)
        print(f"Found {len(locations)} locations from animepilgrimage.com")

        # Test anitabi.cn API
        print("[API] Testing anitabi.cn API...")
        locations = api.search_anitabi(test_anime)
        print(f"Found {len(locations)} locations from anitabi.cn")

        # Test comprehensive search
        print("[API] Testing comprehensive search...")
        all_locations = api.search_all_sources(test_anime)
        print(f"Found {len(all_locations)} total locations from all sources")

        # Convert to dict format
        if all_locations:
            result_dict = api.to_dict_format(all_locations)
            print(f"Result dictionary created with {result_dict['total_locations']} locations")
            print(f"Sources: {result_dict['sources']}")

    except Exception as e:
        print(f"[ERROR] API test failed: {e}")

def main():
    """Main test function"""
    print("[START] Testing Anime Pilgrimage System")

    # Test anime title parsing
    test_anime_parsing()

    # Test API integration
    test_api_integration()

    print("\n" + "=" * 50)
    print("[COMPLETE] All tests completed")
    print("=" * 50)

if __name__ == "__main__":
    main()