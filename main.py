#!/usr/bin/env python3
"""
Anime Pilgrimage Trip Planner - Main Application
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.orchestrator_simple import AnimePilgrimageOrchestrator


async def main():
    """
    Main application entry point
    """
    parser = argparse.ArgumentParser(description="Anime Pilgrimage Trip Planner")
    parser.add_argument(
        "query",
        nargs="?",
        help="Natural language query about anime pilgrimage (e.g., 'I want to visit locations from Your Name')"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path for the markdown report (default: prints to console)"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode"
    )

    args = parser.parse_args()

    # Initialize the orchestrator
    orchestrator = AnimePilgrimageOrchestrator()

    if args.interactive:
        await interactive_mode(orchestrator)
    elif args.query:
        await process_query(orchestrator, args.query, args.output)
    else:
        print("Anime Pilgrimage Trip Planner")
        print("=" * 40)
        print("Usage: python main.py \"your query here\"")
        print("       python main.py --interactive")
        print("       python main.py \"query\" --output report.md")
        print("\nExample queries:")
        print("- \"I want to visit locations from Your Name movie\"")
        print("- \"Plan a trip for Spirited Away pilgrimage sites\"")
        print("- \"Show me locations from Attack on Titan in Japan\"")


async def interactive_mode(orchestrator):
    """
    Run the planner in interactive mode
    """
    print("Anime Pilgrimage Trip Planner - Interactive Mode")
    print("Type 'quit' or 'exit' to stop\n")

    while True:
        try:
            query = input("Enter your anime pilgrimage query: ").strip()

            if query.lower() in ['quit', 'exit', 'q']:
                break

            if not query:
                print("Please enter a valid query.")
                continue

            print("\nProcessing your request...")
            result = await orchestrator.plan_trip(query)

            if result['success']:
                print("\n" + "=" * 60)
                print("TRIP PLAN GENERATED SUCCESSFULLY")
                print("=" * 60 + "\n")
                print(result['report'])
            else:
                print("\n" + "=" * 60)
                print("ERRORS ENCOUNTERED")
                print("=" * 60 + "\n")
                print(result['report'])

            print("\n" + "-" * 60 + "\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


async def process_query(orchestrator, query, output_file=None):
    """
    Process a single query
    """
    print(f"Processing query: {query}")
    print("Please wait while we plan your anime pilgrimage trip...\n")

    try:
        result = await orchestrator.plan_trip(query)

        if result['success']:
            print("=" * 60)
            print("TRIP PLAN GENERATED SUCCESSFULLY")
            print("=" * 60 + "\n")

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result['report'])
                print(f"Report saved to: {output_file}")
            else:
                print(result['report'])
        else:
            print("=" * 60)
            print("ERRORS ENCOUNTERED")
            print("=" * 60 + "\n")
            print(result['report'])

            if result['errors']:
                print("\nDetailed errors:")
                for error in result['errors']:
                    print(f"- {error}")

    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())