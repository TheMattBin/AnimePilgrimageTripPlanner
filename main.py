#!/usr/bin/env python3
"""
Main Anime Pilgrimage Trip Planner
Natural language interface for comprehensive trip planning
"""

import sys
import os
import argparse
from typing import Optional
from datetime import datetime
import textwrap

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.planner import SimpleTripPlanner
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.colors import black, blue, gray, lightblue
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class AnimePilgragePlanner:
    """Main interface for anime pilgrimage trip planning"""

    def __init__(self):
        self.planner = SimpleTripPlanner()

    def plan_trip(self, query: str, verbose: bool = False) -> dict:
        """
        Plan a trip based on natural language query

        Args:
            query: Natural language trip description
            verbose: Whether to show detailed process information

        Returns:
            Complete trip planning result
        """
        if verbose:
            print(f"Planning trip: {query}")
            print("=" * 60)

        try:
            result = self.planner.plan_trip(query)

            if verbose:
                print("[SUCCESS] Trip planning completed successfully!")
                print(f"Itinerary: {len(result.get('itinerary', {}).get('daily_plans', []))} days")
                print(f"Anime map: {'Created' if result.get('anime_map') else 'Not created'}")
                print(f"Flights: {'Available' if result.get('flight_info') else 'Not searched'}")
                print(f"Weather: {'Available' if result.get('weather_info') else 'Not checked'}")
                print(f"Recommendations: {len(result.get('recommendations', []))} tips")

            return result

        except Exception as e:
            print(f"Error planning trip: {e}")
            return {"error": str(e)}

    def format_results(self, result: dict) -> str:
        """Format trip results for user-friendly display"""
        if "error" in result:
            return f"Error: {result['error']}"

        output = self.planner.format_response_for_display(result)
        return output

    def generate_pdf_report(self, result: dict, filename: str = None) -> str:
        """
        Generate a detailed PDF trip plan

        Args:
            result: Trip planning result dictionary
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to generated PDF file
        """
        if "error" in result:
            raise ValueError(f"Cannot generate PDF from error result: {result['error']}")

        if filename is None:
            anime_theme = result.get('parsed_data', {}).get('anime_theme', 'anime_trip')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"anime_pilgrimage_{anime_theme}_{timestamp}.pdf"

        # Ensure filename has .pdf extension
        if not filename.endswith('.pdf'):
            filename += '.pdf'

        # Create PDF document
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=blue,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            textColor=black
        )

        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            textColor=black
        )

        normal_style = styles['Normal']
        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=10
        )

        # Title
        query = result.get('query', 'Anime Pilgrimage Trip')
        anime_theme = result.get('parsed_data', {}).get('anime_theme', 'Anime Pilgrimage')

        story.append(Paragraph("Anime Pilgrimage Trip Plan", title_style))
        story.append(Spacer(1, 20))

        # Trip Overview
        story.append(Paragraph("Trip Overview", heading_style))

        overview_data = [
            ['Destination', result.get('parsed_data', {}).get('destination', 'Japan')],
            ['Duration', f"{result.get('parsed_data', {}).get('duration', 7)} days"],
            ['Anime Theme', anime_theme],
            ['Budget Level', result.get('parsed_data', {}).get('budget_level', 'Medium')],
            ['Trip Date', result.get('parsed_data', {}).get('departure_date', 'Flexible')]
        ]

        overview_table = Table(overview_data, colWidths=[2*inch, 4*inch])
        overview_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), lightblue),
            ('TEXTCOLOR', (0, 0), (0, -1), black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), gray),
            ('GRID', (0, 0), (-1, -1), 1, black)
        ]))
        story.append(overview_table)
        story.append(Spacer(1, 20))

        # Flight Information
        if result.get('flight_info') and isinstance(result['flight_info'], dict):
            story.append(Paragraph("Flight Information", heading_style))

            flight_data = result['flight_info']
            if 'data' in flight_data and isinstance(flight_data['data'], list):
                flights = flight_data['data']
                for i, flight in enumerate(flights[:3], 1):  # Show max 3 flights
                    story.append(Paragraph(f"Flight Option {i}", subheading_style))

                    flight_info = [
                        ['Flight Number', flight.get('flight_number', 'N/A')],
                        ['Route', f"{flight.get('origin', 'N/A')} → {flight.get('destination', 'N/A')}"],
                        ['Departure', flight.get('departure_time', 'N/A')],
                        ['Arrival', flight.get('arrival_time', 'N/A')],
                        ['Price', flight.get('price', 'N/A')]
                    ]

                    flight_table = Table(flight_info, colWidths=[1.5*inch, 4.5*inch])
                    flight_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), lightblue),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 1, black)
                    ]))
                    story.append(flight_table)
                    story.append(Spacer(1, 10))
            story.append(Spacer(1, 20))

        # Weather Information
        if result.get('weather_info') and isinstance(result['weather_info'], dict):
            story.append(Paragraph("Weather Information", heading_style))

            weather_data = result['weather_info']
            if 'current' in weather_data:
                current = weather_data['current']
                weather_info = [
                    ['Location', current.get('location', 'Japan')],
                    ['Temperature', current.get('temperature', 'N/A')],
                    ['Condition', current.get('condition', 'N/A')],
                    ['Humidity', current.get('humidity', 'N/A')],
                    ['Wind Speed', current.get('wind_speed', 'N/A')]
                ]

                weather_table = Table(weather_info, colWidths=[1.5*inch, 4.5*inch])
                weather_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), lightblue),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, black)
                ]))
                story.append(weather_table)
            story.append(Spacer(1, 20))

        # Detailed Itinerary
        if result.get('itinerary') and isinstance(result['itinerary'], dict):
            story.append(Paragraph("Detailed Itinerary", heading_style))

            itinerary = result['itinerary']

            # Check if itinerary has an error
            if 'error' in itinerary:
                story.append(Paragraph("Note: Detailed itinerary generation encountered an error. Basic schedule shown below.", normal_style))
                # Generate a basic itinerary from parsed data
                parsed_data = result.get('parsed_data', {})
                duration = parsed_data.get('duration', 7)
                destination = parsed_data.get('destination', 'Japan')

                for day in range(1, duration + 1):
                    story.append(Paragraph(f"Day {day}: Exploring {destination}", subheading_style))

                    basic_activities = [
                        ['Morning (9:00-12:00)', 'Explore local cuisine and culture', '$30-50'],
                        ['Afternoon (13:00-17:00)', 'Visit landmarks and attractions', '$40-70'],
                        ['Evening (18:00-21:00)', 'Dinner and relaxation', '$25-45']
                    ]

                    activity_table = Table(basic_activities, colWidths=[1.5*inch, 2.5*inch, 1.5*inch])
                    activity_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), lightblue),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 1, black)
                    ]))
                    story.append(activity_table)
                    story.append(Spacer(1, 15))

            else:
                # Use the actual itinerary data
                daily_plans = itinerary.get('daily_plans', [])

                for i, day_plan in enumerate(daily_plans, 1):
                    story.append(Paragraph(f"Day {i}", subheading_style))

                    # Activities for the day
                    activities = []
                    if 'regular_activities' in day_plan:
                        activities.extend(day_plan['regular_activities'])
                    if 'anime_pilgrimage' in day_plan:
                        activities.extend(day_plan['anime_pilgrimage'])

                    if activities:
                        activity_data = [['Time', 'Activity', 'Estimated Cost']]
                        for activity in activities:
                            time_str = activity.get('time', 'N/A')
                            name = activity.get('name', 'N/A')
                            cost = activity.get('cost', 'N/A')
                            activity_data.append([time_str, name, cost])

                        activity_table = Table(activity_data, colWidths=[1*inch, 3*inch, 2*inch])
                        activity_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), lightblue),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 1, black)
                        ]))
                        story.append(activity_table)

                    story.append(Spacer(1, 15))

        # Anime Pilgrimage Locations
        anime_locations = []

        # Try to get anime locations from different sources
        if result.get('anime_locations'):
            anime_locations = result['anime_locations']
        elif result.get('parsed_data', {}).get('anime_theme'):
            # Extract from the search results in the planner
            anime_theme = result['parsed_data']['anime_theme']
            story.append(Paragraph(f"Anime Pilgrimage Locations for {anime_theme}", heading_style))
            story.append(Paragraph("Real anime pilgrimage locations were searched and found. Visit the interactive map for detailed location information.", normal_style))
            story.append(Spacer(1, 10))

        if anime_locations:
            story.append(Paragraph("Anime Pilgrimage Locations", heading_style))

            for i, location in enumerate(anime_locations[:10], 1):  # Show max 10 locations
                story.append(Paragraph(f"{i}. {location.get('name', 'Unknown Location')}", subheading_style))

                location_info = [
                    ['Address', location.get('real_location', 'N/A')],
                    ['City', location.get('city', 'N/A')],
                    ['Description', location.get('description', 'No description available')],
                    ['Scene', location.get('scene_description', 'N/A')],
                    ['Coordinates', f"{location.get('coordinates', ['N/A', 'N/A'])[0]}, {location.get('coordinates', ['N/A', 'N/A'])[1]}"]
                ]

                location_table = Table(location_info, colWidths=[1*inch, 5*inch])
                location_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), lightblue),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, black)
                ]))
                story.append(location_table)
                story.append(Spacer(1, 10))

        # Recommendations
        if result.get('recommendations'):
            story.append(Paragraph("Travel Recommendations", heading_style))

            recommendations = result['recommendations']
            for i, rec in enumerate(recommendations, 1):
                rec_text = f"{i}. {rec}"
                story.append(Paragraph(rec_text, normal_style))

            story.append(Spacer(1, 20))

        # Footer
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Anime Pilgrimage Trip Planner"
        story.append(Paragraph(footer_text, small_style))

        # Build PDF
        doc.build(story)

        print(f"PDF report generated: {filename}")
        return filename


def main():
    """Main command line interface"""
    parser = argparse.ArgumentParser(
        description="Anime Pilgrimage Trip Planner - Plan your anime-themed trips with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "plan a 7-day trip in coming dec to have anime Pilgrimage for Rascal Does Not Dream of Santa Claus"
  python main.py "7-days trip plan from Taiwan to Japan for Bunny Girl Senpai pilgrimage" --output pdf
  python main.py "I want to visit Demon Slayer filming locations in Japan for 5 days" --both
  python main.py "Your Name pilgrimage" --output pdf --pdf-filename "my_trip.pdf"
  python main.py --interactive
        """
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Natural language trip description"
    )

    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive mode"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed planning process"
    )

    parser.add_argument(
        "--output", "-o",
        choices=["console", "json", "pdf"],
        default="console",
        help="Output format (default: console; pdf generates detailed trip report)"
    )

    parser.add_argument(
        "--pdf-filename", "-f",
        type=str,
        help="Custom PDF filename (only used with --output pdf)"
    )

    parser.add_argument(
        "--both", "-b",
        action="store_true",
        help="Show console output AND generate PDF"
    )

    args = parser.parse_args()

    # Initialize planner
    trip_planner = AnimePilgragePlanner()

    if args.interactive:
        # Interactive mode
        print("Welcome to Anime Pilgrimage Trip Planner!")
        print("Type your trip description or 'quit' to exit")
        print("-" * 50)

        while True:
            try:
                query = input("\nDescribe your trip: ").strip()

                if query.lower() in ['quit', 'exit', 'q']:
                    print("Happy travels!")
                    break

                if not query:
                    print("Please enter a trip description")
                    continue

                result = trip_planner.plan_trip(query, args.verbose)

                if args.output == "json":
                    import json
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                elif args.output == "pdf" or args.both:
                    # Generate PDF
                    try:
                        pdf_filename = args.pdf_filename if args.pdf_filename else None
                        pdf_path = trip_planner.generate_pdf_report(result, pdf_filename)
                        print(f"PDF generated successfully: {pdf_path}")
                    except Exception as e:
                        print(f"Error generating PDF: {e}")
                        print("Falling back to console output...")
                        args.output = "console"
                        args.both = False

                if args.output == "console" or args.both:
                    formatted_output = trip_planner.format_results(result)
                    # Handle character encoding for Windows console
                    try:
                        print(formatted_output)
                    except UnicodeEncodeError:
                        # Fallback: replace problematic characters
                        safe_output = formatted_output.encode('ascii', 'ignore').decode('ascii')
                        print(safe_output)
                        print("\nSome characters could not be displayed due to encoding limitations")

            except KeyboardInterrupt:
                print("\nHappy travels!")
                break
            except Exception as e:
                print(f"Error: {e}")

    elif args.query:
        # Single query mode
        result = trip_planner.plan_trip(args.query, args.verbose)

        if args.output == "json":
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.output == "pdf" or args.both:
            # Generate PDF
            try:
                pdf_filename = args.pdf_filename if args.pdf_filename else None
                pdf_path = trip_planner.generate_pdf_report(result, pdf_filename)
                print(f"PDF generated successfully: {pdf_path}")
            except Exception as e:
                print(f"Error generating PDF: {e}")
                print("Falling back to console output...")
                args.output = "console"
                args.both = False

        if args.output == "console" or args.both:
            formatted_output = trip_planner.format_results(result)
            # Handle character encoding for Windows console
            try:
                print(formatted_output)
            except UnicodeEncodeError:
                # Fallback: replace problematic characters
                safe_output = formatted_output.encode('ascii', 'ignore').decode('ascii')
                print(safe_output)
                print("\nSome characters could not be displayed due to encoding limitations")

    else:
        # No arguments, show help
        parser.print_help()
        print("\nExample usage:")
        print('python main.py "plan a 7-day trip in coming dec to have anime Pilgrimage for Rascal Does Not Dream of Santa Claus"')


if __name__ == "__main__":
    main()