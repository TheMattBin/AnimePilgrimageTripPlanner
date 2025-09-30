"""
Anime Pilgrimage Trip Planner - Main Application
Integrates all components to create a complete agentic travel planning system.
"""

import asyncio
import sys
import os
from typing import Optional
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from src.components.query_interface import QueryInterface, UserQuery
from src.components.query_analyzer import QueryAnalyzer, QueryAnalysis
from src.agents.web_crawler import AgenticWebCrawler, PilgrimageLocation
from src.components.trip_planner import TripPlanner, TravelPlan
from src.components.response_generator import ResponseGenerator, GeneratedResponse


class AnimePilgrimagePlanner:
    """
    Main application class that orchestrates the complete anime pilgrimage planning workflow.

    High-Level Architecture:
    User Query
        ↓
    [Query Interface]
        ↓
    [Query Analyzer (HF LLM)]
        ↓
    [Anime(s) Identified + Keywords]
        ↓
    [Agentic Web Crawler (LangGraph + Custom Python)]
        ↓
    [Location & Activity Data]
        ↓
    [Trip Planner & Route Optimizer]
        ↓
    [Response Generator (HF LLM)]
        ↓
    Travel Plan Response to User
    """

    def __init__(self):
        """Initialize all components."""
        print("Initializing Anime Pilgrimage Trip Planner...")

        # Initialize components
        self.query_interface = QueryInterface()
        self.query_analyzer = QueryAnalyzer()
        self.trip_planner = TripPlanner()
        self.response_generator = ResponseGenerator()

        print("All components initialized successfully")

    async def process_query(self, user_input: str) -> GeneratedResponse:
        """
        Process a user query through the complete pipeline.

        Args:
            user_input: Raw user query text

        Returns:
            Generated response with travel plan or clarification
        """
        print(f"\nProcessing query: '{user_input}'")

        try:
            # Step 1: User Query Interface
            print("Step 1: Processing user query...")
            user_query = self.query_interface.process_query(user_input)

            if not user_query:
                return self.response_generator._generate_error_response(
                    "Invalid query. Please provide a valid anime pilgrimage request."
                )

            print(f"Query processed (confidence: {user_query.confidence:.2f})")

            # Step 2: Query Analysis & Anime Identification
            print("Step 2: Analyzing query and identifying anime...")
            query_analysis = await self.query_analyzer.analyze_query(user_query)

            print(f"Analysis complete (confidence: {query_analysis.analysis_confidence:.2f})")
            print(f"Identified anime: {[anime.anime_title for anime in query_analysis.identified_anime]}")

            # Check if disambiguation is needed
            if query_analysis.disambiguation_questions:
                print("Disambiguation needed")
                return self.response_generator._generate_clarification_response(query_analysis)

            # Step 3: Agentic Web Crawler & Data Retriever
            print("Step 3: Crawling for pilgrimage locations...")

            async with AgenticWebCrawler() as crawler:
                locations = await crawler.crawl_anime_locations(query_analysis)

            print(f"Found {len(locations)} pilgrimage locations")

            if not locations:
                return self.response_generator._generate_error_response(
                    f"No pilgrimage locations found for {', '.join([anime.anime_title for anime in query_analysis.identified_anime])}. "
                    "Please try with different anime or more specific location requests."
                )

            # Step 4: Trip Planner & Route Generator
            print("Step 4: Generating travel itinerary...")
            travel_plan = self.trip_planner.generate_travel_plan(locations, query_analysis)

            print(f"Generated {travel_plan.duration_days}-day travel plan")
            print(f"Total locations: {travel_plan.total_locations}")
            print(f"Estimated cost: ¥{travel_plan.total_estimated_cost.get('total', 0):,.0f}")

            # Step 5: Response Generator
            print("Step 5: Generating user-friendly response...")
            response = self.response_generator.generate_response(
                travel_plan, query_analysis, locations
            )

            # Step 6: Generate Markdown Output
            print("Step 6: Generating markdown travel guide...")
            anime_title = travel_plan.trip_title.replace(" ", "_").replace("/", "_")
            markdown_filename = f"travel_plan_{anime_title}_{travel_plan.duration_days}days.md"

            markdown_content = self.response_generator.generate_markdown_response(
                travel_plan, query_analysis, locations
            )

            # Save markdown file
            try:
                with open(markdown_filename, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                print(f"✅ Markdown travel guide saved: {markdown_filename}")
            except Exception as e:
                print(f"⚠️  Could not save markdown file: {e}")

            print("Complete response generated")
            return response

        except Exception as e:
            print(f"Error in processing pipeline: {str(e)}")
            return self.response_generator._generate_error_response(
                f"An error occurred while processing your request: {str(e)}"
            )

    def print_response(self, response: GeneratedResponse):
        """
        Print the response in a formatted way.

        Args:
            response: Generated response object
        """
        print("\n" + "="*80)
        print(f"ANIME PILGRIMAGE: {response.title}")
        print("="*80)

        if response.disambiguation_needed:
            print("I need some clarification to create the perfect plan for you:")
            for question in response.disambiguation_questions:
                print(f"   - {question}")
        else:
            # Print response with Unicode handling
            try:
                print(response.main_content)
            except UnicodeEncodeError:
                # Fallback: replace problematic characters
                safe_content = response.main_content.encode('ascii', 'ignore').decode('ascii')
                print(safe_content)

        print(f"\nResponse Confidence: {response.confidence:.2f}")
        if response.metadata:
            print("Additional Info:")
            for key, value in response.metadata.items():
                print(f"   - {key.replace('_', ' ').title()}: {value}")

        print("="*80)

    async def interactive_mode(self):
        """Run the planner in interactive mode."""
        print("\nWelcome to Anime Pilgrimage Trip Planner!")
        print("I can help you create detailed itineraries to visit real-world anime locations.")
        print("\nExample queries you can try:")
        print("- 'I want to visit locations from Your Name in Tokyo and Kyoto'")
        print("- 'Plan a budget trip to Attack on Titan locations in Oita'")
        print("- 'Show me Studio Ghibli pilgrimage sites for a weekend'")
        print("\nType 'quit' or 'exit' to stop.")
        print("-" * 60)

        while True:
            try:
                user_input = input("\nYour anime pilgrimage request: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Thank you for using Anime Pilgrimage Trip Planner! Safe travels!")
                    break

                if not user_input:
                    print("Please enter a valid query.")
                    continue

                # Process the query
                response = await self.process_query(user_input)

                # Display the response
                self.print_response(response)

            except KeyboardInterrupt:
                print("\n\nGoodbye! Safe travels on your anime pilgrimage!")
                break
            except Exception as e:
                print(f"\nAn unexpected error occurred: {e}")
                print("Please try again with a different query.")


async def main():
    """Main function to run the application."""
    import argparse

    parser = argparse.ArgumentParser(description="Anime Pilgrimage Trip Planner")
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Direct query to process (non-interactive mode)"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode (default if no query provided)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Save response to file (JSON format)"
    )

    args = parser.parse_args()

    # Initialize the planner
    planner = AnimePilgrimagePlanner()

    if args.query:
        # Single query mode
        response = await planner.process_query(args.query)
        planner.print_response(response)

        # Save to file if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(response.dict(), f, indent=2, ensure_ascii=False)
            print(f"\n💾 Response saved to {args.output}")

    else:
        # Interactive mode (default)
        await planner.interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())