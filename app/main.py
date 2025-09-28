#!/usr/bin/env python3
"""
Enhanced Trip Planning System - User Interface (ASCII version)
Specializing in Anime Pilgrimage (Seichi Junrei) Travel
Accepts simple text queries and outputs comprehensive trip plans
"""

import sys
import os
from typing import Dict, Any, Optional
from core.planner import SimpleTripPlanner
from outputs.reports import ReportGenerator
from core.config import Config
from datetime import datetime, timedelta


class TripPlanningApp:
    """
    Enhanced main application for the trip planning system
    """

    def __init__(self):
        self.planner = SimpleTripPlanner()
        self.report_generator = ReportGenerator()
        self.config = Config()

    def display_welcome(self):
        """Display welcome message and instructions"""
        print("*** Welcome to the Enhanced Anime Pilgrimage Trip Planner! ***")
        print("=" * 65)
        print("Specializing in Anime Pilgrimage (Seichi Junrei) Travel")
        print("=" * 65)
        print("\n[KEY FEATURES]:")
        print("- Flight search with mock data (no API key needed)")
        print("- Weather information with mock data (no API key needed)")
        print("- Detailed itinerary planning")
        print("- Interactive anime pilgrimage maps")
        print("- Comprehensive reports (Markdown & PDF)")
        print("- Episode-specific photo opportunities")
        print("=" * 65)
        print("\n[EXAMPLE QUERIES]:")
        print('- "7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Slam Dunk"')
        print('- "Plan a 5-day trip to Tokyo focusing on Your Name locations"')
        print('- "10-day Japan trip with One Piece pilgrimage, medium budget"')
        print('\n[COMMANDS]:')
        print('- Type your trip query in natural language')
        print('- Type "exit" to quit')
        print('- Type "help" for more information')
        print('- Type "demo" for example')
        print('- Type "api" for API information')
        print("=" * 65)

    def display_help(self):
        """Display help information"""
        print("\n[HELP] Trip Planning System Guide")
        print("-" * 45)
        print("\n[SUPPORTED FEATURES]:")
        print("- Flight search between any cities (mock data)")
        print("- Weather forecasting (mock data)")
        print("- Custom itinerary planning")
        print("- Anime pilgrimage mapping (Slam Dunk, Your Name, One Piece)")
        print("- Interactive map creation")
        print("- Travel statistics and recommendations")
        print("- Professional report generation")

        print("\n[QUERY FORMAT TIPS]:")
        print("Include these elements in your natural language query:")
        print("- Origin and destination locations")
        print("- Trip duration (e.g., '7 days', '5-day trip')")
        print("- Specific interests or anime themes")
        print("- Budget level (optional: budget/medium/luxury)")
        print("- Special requirements (optional)")

        print("\n[SUPPORTED ANIME SERIES]:")
        print("- Slam Dunk - Basketball locations in Japan")
        print("- Your Name - Movie scene locations")
        print("- One Piece - Various adventure locations")

        print("\n[GENERATED OUTPUTS]:")
        print("- Interactive HTML map with all locations")
        print("- Detailed Markdown report")
        print("- Professional PDF report")
        print("- Console output with trip summary")

        print("\n[API REQUIREMENTS]:")
        print("- NO API KEYS NEEDED - Uses mock data for flights and weather")
        print("- Free OpenStreetMap for mapping")
        print("- Local HuggingFace models for AI processing")
        print("-" * 45)

    def display_api_info(self):
        """Display information about APIs and alternatives"""
        print("\n[API] Information & Free Options")
        print("-" * 40)
        print("\n[FLIGHT APIs (Free Options Available)]:")
        print("- AviationStack (free tier: 500 requests/month)")
        print("  - Register: https://aviationstack.com/")
        print("  - Key: Set FLIGHT_API_KEY in .env file")
        print("- Mock Data: Currently used - works perfectly for testing")
        print("- Alternatives: Skyscanner API, Amadeus API (paid)")

        print("\n[WEATHER APIs (Free Options Available)]:")
        print("- OpenWeatherMap (free tier: 1000 requests/day)")
        print("  - Register: https://openweathermap.org/api")
        print("  - Key: Set WEATHER_API_KEY in .env file")
        print("- WeatherAPI (free tier: 1M requests/month)")
        print("  - Register: https://www.weatherapi.com/")
        print("- Mock Data: Currently used - provides realistic test data")

        print("\n[MAPPING APIs (Free)]:")
        print("- OpenStreetMap (completely free, no API key needed)")
        print("- Nominatim (free geocoding, no API key needed)")
        print("- Currently used: No costs or limitations")

        print("\n[AI MODELS (Local - No API Costs)]:")
        print("- HuggingFace models run locally on your machine")
        print("- No API calls or costs for AI processing")
        print("- Models: DialoGPT, TinyLlama (included in requirements)")

        print("\n[SAMPLE .env file]:")
        print("""
# Optional APIs - System works without these
FLIGHT_API_KEY=your_aviationstack_key_here
WEATHER_API_KEY=your_openweathermap_key_here

# Required for AI models
HUGGINGFACE_MODEL_NAME=microsoft/DialoGPT-medium
""")
        print("-" * 40)

    def process_user_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query and generate comprehensive trip plan
        """
        print(f"\n[PLANNING] Processing your trip request...")
        print(f"[QUERY]: {query}")
        print("Please wait while our AI agents work on your request...")
        print("-" * 60)

        try:
            # Step 1: Plan the trip using simple trip planner
            trip_result = self.planner.plan_trip(query)

            if "error" in trip_result:
                print(f"[ERROR] Trip planning failed: {trip_result['error']}")
                return trip_result

            # Step 2: Generate enhanced reports
            print("\n[REPORTS] Generating comprehensive reports...")
            report_files = self.report_generator.generate_comprehensive_report(
                trip_result,
                output_format="both"  # Generate both Markdown and PDF
            )

            # Step 3: Display formatted results
            print("\n" + "*** TRIP PLANNING COMPLETE! ***")
            print("=" * 30)

            # Display summary
            formatted_output = self.planner.format_response_for_display(trip_result)
            print(formatted_output)

            # Display generated files
            print("\n[GENERATED FILES]")
            print("-" * 30)
            for format_type, file_path in report_files.items():
                print(f"- {format_type.upper()}: {file_path}")

            # Display main map information
            main_map = trip_result.get("main_map", "")
            if main_map:
                print(f"- INTERACTIVE MAP: {main_map}")
                print("  Open this HTML file in your browser to explore the interactive map!")

            print("\n[SUCCESS] Your complete trip plan has been generated!")
            print("All files are saved in the current directory.")
            print("-" * 60)

            # Combine results
            result = {
                **trip_result,
                "report_files": report_files,
                "main_map": main_map
            }

            return result

        except Exception as e:
            print(f"[ERROR] Error during trip planning: {str(e)}")
            return {"error": str(e)}

    def run_demo(self):
        """Run a demonstration of the system"""
        print("\n[DEMO] Running Example: Taiwan to Japan Slam Dunk Pilgrimage")
        print("-" * 60)

        demo_query = "7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Slam Dunk"
        return self.process_user_query(demo_query)

    def run_interactive(self):
        """Run the application in interactive mode"""
        self.display_welcome()

        while True:
            try:
                print("\n" + "=" * 65)
                user_input = input("[PROMPT] What trip would you like to plan? ").strip()

                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n[GOODBYE] Thank you for using the Trip Planning System!")
                    print("Have a wonderful trip!")
                    break

                elif user_input.lower() in ['help', 'h']:
                    self.display_help()

                elif user_input.lower() in ['api', 'apis', 'keys']:
                    self.display_api_info()

                elif user_input.lower() in ['demo', 'example', 'slam dunk', 'test']:
                    print("\n[DEMO] Running demonstration...")
                    self.run_demo()

                elif user_input:
                    if len(user_input) < 10:
                        print("[WARNING] Please provide more details for your trip plan.")
                        print("Example: '7-days trip from Taiwan to Japan for Slam Dunk pilgrimage'")
                        continue

                    self.process_user_query(user_input)

                else:
                    print("[WARNING] Please enter a trip query or type 'help' for assistance.")

            except KeyboardInterrupt:
                print("\n\n[GOODBYE] Thank you for using the Trip Planning System!")
                print("Have a wonderful trip!")
                break

            except Exception as e:
                print(f"[ERROR] An unexpected error occurred: {str(e)}")
                print("Please try again or type 'help' for assistance.")
                continue

    def run_single_query(self, query: str) -> Dict[str, Any]:
        """Run a single query and return results"""
        try:
            return self.process_user_query(query)
        except Exception as e:
            return {"error": str(e)}

    def check_setup(self):
        """Check system setup and display status"""
        print("\n[SETUP] Checking system configuration...")
        print("-" * 40)

        try:
            Config.validate_config()
            print("Configuration: Valid")

            # Check if models are available
            try:
                llm = self.planner.llm_manager.get_model()
                if llm:
                    print("AI Model: Loaded successfully")
                else:
                    print("AI Model: Failed to load (will use fallback)")
            except Exception as e:
                print(f"AI Model: Issue detected - {str(e)}")

            # Check if enhanced map agent works
            try:
                test_map = self.report_generator.map_agent.create_main_anime_map("Slam Dunk", 1)
                if test_map.endswith(".html"):
                    print("Map Generation: Working")
                else:
                    print(f"Map Generation: {test_map}")
            except Exception as e:
                print(f"Map Generation: Issue detected - {str(e)}")

            print("\nSystem Status: READY FOR USE")
            print("Note: Flight and Weather APIs are optional - system uses mock data")

        except Exception as e:
            print(f"Configuration Error: {str(e)}")
            print("Please check your .env file and requirements")

        print("-" * 40)


def main():
    """Main entry point"""
    try:
        # Validate configuration
        Config.validate_config()

        app = TripPlanningApp()

        # Check if running with command line arguments
        if len(sys.argv) > 1:
            first_arg = sys.argv[1].lower()
            if first_arg in ['help', 'h']:
                app.display_help()
                return {"success": True}
            elif first_arg in ['api', 'apis', 'keys']:
                app.display_api_info()
                return {"success": True}
            elif first_arg in ['demo', 'example', 'slam dunk', 'test']:
                app.run_demo()
                return {"success": True}
            else:
                query = " ".join(sys.argv[1:])
                if query:
                    print(f"[COMMAND] Processing query: {query}")
                    result = app.run_single_query(query)
                    return result

        # Interactive mode
        app.check_setup()
        app.run_interactive()

    except ValueError as e:
        print(f"[ERROR] Configuration Error: {str(e)}")
        print("Please check your .env file and ensure all required configurations are set.")
        print("Required: HUGGINGFACE_MODEL_NAME")
        print("Optional: FLIGHT_API_KEY, WEATHER_API_KEY")
        return {"error": str(e)}

    except Exception as e:
        print(f"[ERROR] Application Error: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    main()