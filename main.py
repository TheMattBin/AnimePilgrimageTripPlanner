#!/usr/bin/env python3
"""
Multi-Agent Trip Planning System
Specializing in Anime Pilgrimage (Seichi Junrei) Travel
"""

import asyncio
import sys
from typing import Dict, Any
from trip_planner_graph import TripPlannerGraph
from config import Config
from datetime import datetime, timedelta

class TripPlanningApp:
    """
    Main application for the multi-agent trip planning system
    """

    def __init__(self):
        self.planner = TripPlannerGraph()
        self.config = Config()

    def display_welcome(self):
        """Display welcome message and instructions"""
        print("🌸 **Welcome to the Multi-Agent Trip Planning System!** 🌸")
        print("=" * 60)
        print("Specializing in Anime Pilgrimage (聖地巡礼) Travel")
        print("=" * 60)
        print("\nFeatures:")
        print("✈️  Flight search and booking assistance")
        print("🌤️  Weather forecasting for multiple destinations")
        print("🗺️  Detailed itinerary planning")
        print("🎌  Anime pilgrimage location mapping")
        print("💰  Budget planning and cost estimation")
        print("\nExample queries:")
        print('- "7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Slam Dunk"')
        print('- "Plan a 5-day trip to Tokyo focusing on Your Name locations"')
        print('- "10-day Japan trip with One Piece pilgrimage, medium budget"')
        print("\nType 'exit' to quit or 'help' for more information.")
        print("=" * 60)

    def display_help(self):
        """Display help information"""
        print("\n📖 **Help - Trip Planning System**")
        print("-" * 40)
        print("Supported Features:")
        print("• Flight search between any cities")
        print("• Weather forecasting for up to 10 days")
        print("• Custom itinerary planning")
        print("• Anime pilgrimage mapping (Slam Dunk, Your Name, One Piece)")
        print("• Interactive map creation")
        print("• Travel statistics and recommendations")
        print("\nQuery Format:")
        print("Include these elements in your query:")
        print("• Origin and destination")
        print("• Trip duration")
        print("• Specific interests or anime themes")
        print("• Budget level (optional)")
        print("• Special requirements (optional)")
        print("\nSupported Anime:")
        print("• Slam Dunk")
        print("• Your Name (君の名は。)")
        print("• One Piece")
        print("-" * 40)

    def plan_taiwan_to_japan_slam_dunk_trip(self) -> Dict[str, Any]:
        """
        Example: Plan a 7-day Taiwan to Japan trip with Slam Dunk pilgrimage
        """
        query = "7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Slam Dunk"

        print(f"\n🚀 **Planning your trip...**")
        print(f"Query: {query}")
        print("Please wait while our agents work on your request...")
        print("-" * 50)

        try:
            result = self.planner.plan_trip(query)

            if "error" in result:
                print(f"❌ Error: {result['error']}")
                return result

            formatted_response = self.planner.format_response_for_display(result)
            print(formatted_response)

            return result

        except Exception as e:
            print(f"❌ Error during trip planning: {str(e)}")
            return {"error": str(e)}

    def plan_custom_trip(self, query: str) -> Dict[str, Any]:
        """
        Plan a custom trip based on user query
        """
        print(f"\n🚀 **Planning your custom trip...**")
        print(f"Query: {query}")
        print("Please wait while our agents work on your request...")
        print("-" * 50)

        try:
            result = self.planner.plan_trip(query)

            if "error" in result:
                print(f"❌ Error: {result['error']}")
                return result

            formatted_response = self.planner.format_response_for_display(result)
            print(formatted_response)

            return result

        except Exception as e:
            print(f"❌ Error during trip planning: {str(e)}")
            return {"error": str(e)}

    def display_system_info(self):
        """Display system information"""
        print("\n🔧 **System Information**")
        print("-" * 30)
        print(f"Current Model: {self.planner.llm_manager.current_model}")
        print("Available Models:")
        for model_name, model_info in self.planner.llm_manager.list_available_models().items():
            status = "✅ Loaded" if model_info["loaded"] else "❌ Failed"
            print(f"  • {model_name}: {model_info['description']} - {status}")

        if self.planner.llm_manager.current_model:
            test_result = self.planner.llm_manager.test_model()
            print(f"\nModel Test: {test_result}")

        print("-" * 30)

    def run_interactive(self):
        """Run the application in interactive mode"""
        self.display_welcome()

        while True:
            try:
                print("\n" + "=" * 60)
                user_input = input("🌟 What would you like to plan? (or type 'exit' to quit): ").strip()

                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("👋 Thank you for using the Trip Planning System! Have a great trip!")
                    break

                elif user_input.lower() in ['help', 'h']:
                    self.display_help()

                elif user_input.lower() in ['info', 'system', 'status']:
                    self.display_system_info()

                elif user_input.lower() in ['example', 'demo', 'slam dunk']:
                    print("\n🎯 Running example: Taiwan to Japan Slam Dunk Pilgrimage")
                    self.plan_taiwan_to_japan_slam_dunk_trip()

                elif user_input:
                    self.plan_custom_trip(user_input)

                else:
                    print("⚠️  Please enter a valid query or type 'help' for assistance.")

            except KeyboardInterrupt:
                print("\n\n👋 Thank you for using the Trip Planning System! Have a great trip!")
                break

            except Exception as e:
                print(f"❌ An unexpected error occurred: {str(e)}")
                continue

    def run_single_query(self, query: str) -> Dict[str, Any]:
        """Run a single query and return results"""
        try:
            return self.plan_custom_trip(query)
        except Exception as e:
            return {"error": str(e)}

def main():
    """Main entry point"""
    try:
        Config.validate_config()

        app = TripPlanningApp()

        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
            if query:
                print(f"🚀 Planning trip for query: {query}")
                result = app.run_single_query(query)
                return result

        app.run_interactive()

    except ValueError as e:
        print(f"❌ Configuration Error: {str(e)}")
        print("Please check your .env file and ensure all required configurations are set.")
        return {"error": str(e)}

    except Exception as e:
        print(f"❌ Application Error: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    main()