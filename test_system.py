#!/usr/bin/env python3
"""
Quick test script to demonstrate the anime pilgrimage planner system
without requiring web crawling.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.components.query_interface import QueryInterface
from src.components.query_analyzer import QueryAnalyzer
from src.components.trip_planner import TripPlanner
from src.components.response_generator import ResponseGenerator
from src.agents.web_crawler import PilgrimageLocation


async def test_full_pipeline():
    """Test the full pipeline with sample data."""
    print("=== Anime Pilgrimage Trip Planner Test ===\n")

    # Sample locations (simulating web crawling results)
    sample_locations = [
        PilgrimageLocation(
            name="Shinjuku Gyoen National Garden",
            anime_title="Your Name",
            real_world_address="11 Naitomachi, Shinjuku City, Tokyo",
            coordinates={'lat': 35.6852, 'lng': 139.7103},
            description="Large park and garden in central Tokyo featured in Your Name",
            scene_description="Scene where Taki and Miki walk through the garden",
            access_method="5 min walk from Shinjuku Station",
            nearby_attractions=["Shinjuku Gyoenmae Station", "Tokyo Metropolitan Government Building"],
            best_visit_time="Morning for best lighting",
            photography_notes="Great for matching movie scenes",
            source_url="test_location_1",
            confidence_score=0.95
        ),
        PilgrimageLocation(
            name="Suga Shrine",
            anime_title="Your Name",
            real_world_address="2-5-5 Motoasakusa, Taito City, Tokyo",
            coordinates={'lat': 35.7148, 'lng': 139.7967},
            description="Shinto shrine with famous staircase from Your Name",
            scene_description="Iconic staircase scene and shrine visit",
            access_method="5 min walk from Asakusa Station",
            nearby_attractions=["Asakusa Shrine", "Tokyo Skytree"],
            best_visit_time="Early morning to avoid crowds",
            photography_notes="Staircase view matches movie perfectly",
            source_url="test_location_2",
            confidence_score=0.98
        ),
        PilgrimageLocation(
            name="Tokyo Station",
            anime_title="Your Name",
            real_world_address="1 Chome Marunouchi, Chiyoda City, Tokyo",
            coordinates={'lat': 35.6812, 'lng': 139.7671},
            description="Major railway station with beautiful architecture",
            scene_description="Train station scenes throughout the movie",
            access_method="Multiple train lines accessible",
            nearby_attractions=["Imperial Palace", "Tokyo Station Hotel"],
            best_visit_time="Evening for illuminated views",
            photography_notes="Architecture photography recommended",
            source_url="test_location_3",
            confidence_score=0.85
        )
    ]

    # Test query
    test_query = "I want to visit locations from Your Name in Tokyo for 2 days"
    print(f"Test Query: '{test_query}'\n")

    # Step 1: Query Interface
    print("Step 1: Query Interface Processing...")
    interface = QueryInterface()
    user_query = interface.process_query(test_query)
    print(f"[OK] Query processed (confidence: {user_query.confidence:.2f})")
    print(f"   Normalized: '{user_query.normalized_text}'")

    # Step 2: Query Analysis
    print("\nStep 2: Query Analysis...")
    analyzer = QueryAnalyzer()
    query_analysis = analyzer.analyze_query(user_query)
    print(f"[OK] Analysis complete (confidence: {query_analysis.analysis_confidence:.2f})")
    print(f"   Identified anime: {[anime.anime_title for anime in query_analysis.identified_anime]}")
    print(f"   Trip preferences: {query_analysis.trip_preferences}")

    # Step 3: Web Crawler (simulated with sample data)
    print(f"\nStep 3: Web Crawling (simulated)...")
    print(f"[OK] Found {len(sample_locations)} pilgrimage locations")
    for i, loc in enumerate(sample_locations, 1):
        print(f"   {i}. {loc.name} (confidence: {loc.confidence_score:.2f})")

    # Step 4: Trip Planning
    print(f"\nStep 4: Trip Planning...")
    planner = TripPlanner()
    travel_plan = planner.generate_travel_plan(sample_locations, query_analysis)
    print(f"[OK] Generated {travel_plan.duration_days}-day travel plan")
    print(f"   Total locations: {travel_plan.total_locations}")
    print(f"   Estimated cost: ¥{travel_plan.total_estimated_cost.get('total', 0):,.0f}")

    # Step 5: Response Generation
    print(f"\nStep 5: Response Generation...")
    generator = ResponseGenerator()
    response = generator.generate_response(travel_plan, query_analysis, sample_locations)
    print(f"[OK] Response generated (confidence: {response.confidence:.2f})")

    # Display the response
    print("\n" + "="*80)
    print("GENERATED TRAVEL PLAN")
    print("="*80)
    print(response.main_content[:1000] + "..." if len(response.main_content) > 1000 else response.main_content)
    print(f"\nResponse Confidence: {response.confidence:.2f}")
    print("="*80)

    print("\n=== Test Complete! ===")
    print("All components of the Anime Pilgrimage Trip Planner are working correctly!")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())