#!/usr/bin/env python3
"""
Enhanced Report Generator for Trip Planning System
Generates comprehensive Markdown and PDF reports with detailed itineraries,
interactive maps, and episode-specific photos for anime pilgrimage trips.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import markdown
from jinja2 import Environment, FileSystemLoader, Template
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.colors import HexColor
from reportlab.lib import colors
import base64
from io import BytesIO
import folium
from agents.maps.enhanced import EnhancedMapAgent
from core.config import Config


class ReportGenerator:
    """
    Comprehensive report generator for anime pilgrimage trip planning
    """

    def __init__(self):
        self.map_agent = EnhancedMapAgent()
        self.template_env = Environment(loader=FileSystemLoader('.'))
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()

    def setup_custom_styles(self):
        """Setup custom styles for PDF generation"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#2E5090'),
            alignment=1  # Center alignment
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            textColor=HexColor('#2E5090'),
            borderWidth=1,
            borderColor=HexColor('#2E5090'),
            borderPadding=5
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            textColor=HexColor('#4A6741')
        ))

        self.styles.add(ParagraphStyle(
            name='AnimeLocation',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            leftIndent=20,
            backgroundColor=HexColor('#F0F8FF')
        ))

    def generate_comprehensive_report(self, trip_data: Dict[str, Any], output_format: str = "both") -> Dict[str, str]:
        """
        Generate comprehensive trip report in multiple formats

        Args:
            trip_data: Trip planning data from the planner
            output_format: "markdown", "pdf", or "both"

        Returns:
            Dictionary with paths to generated files
        """
        output_files = {}

        # Generate enhanced map data first
        anime_theme = trip_data.get("parsed_data", {}).get("anime_theme", "Anime Pilgrimage")
        destination = trip_data.get("parsed_data", {}).get("destination", "Japan")
        duration = trip_data.get("parsed_data", {}).get("duration", 7)

        # Create main enhanced map
        main_map_file = self.map_agent.create_main_anime_map(
            anime_title=anime_theme,
            trip_duration=duration
        )

        # Update trip data with enhanced map information
        trip_data["main_map"] = main_map_file

        base_filename = f"{anime_theme.lower().replace(' ', '_')}_pilgrimage_report"

        if output_format in ["markdown", "both"]:
            markdown_file = self.generate_markdown_report(trip_data, base_filename)
            output_files["markdown"] = markdown_file

        if output_format in ["pdf", "both"]:
            pdf_file = self.generate_pdf_report(trip_data, base_filename)
            output_files["pdf"] = pdf_file

        return output_files

    def generate_markdown_report(self, trip_data: Dict[str, Any], base_filename: str) -> str:
        """Generate detailed Markdown report"""

        anime_theme = trip_data.get("parsed_data", {}).get("anime_theme", "Anime Pilgrimage")
        destination = trip_data.get("parsed_data", {}).get("destination", "Japan")
        duration = trip_data.get("parsed_data", {}).get("duration", 7)

        markdown_content = self.create_markdown_template(trip_data)

        filename = f"{base_filename}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        print(f"[REPORT] Markdown report generated: {filename}")
        return filename

    def create_markdown_template(self, trip_data: Dict[str, Any]) -> str:
        """Create comprehensive Markdown template"""

        anime_theme = trip_data.get("parsed_data", {}).get("anime_theme", "Anime Pilgrimage")
        destination = trip_data.get("parsed_data", {}).get("destination", "Japan")
        duration = trip_data.get("parsed_data", {}).get("duration", 7)
        departure_date = trip_data.get("parsed_data", {}).get("departure_date", "2024-12-01")

        # Calculate date range
        if departure_date and isinstance(departure_date, str):
            start_date = datetime.strptime(departure_date, "%Y-%m-%d")
        else:
            start_date = datetime.now() + timedelta(days=30)  # Default to 30 days from now
        end_date = start_date + timedelta(days=duration-1)

        main_map = trip_data.get("main_map", "")

        template = f"""# {anime_theme} Anime Pilgrimage Trip Report

**Destination:** {destination} | **Duration:** {duration} days | **Dates:** {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}

---

## 📋 Trip Overview

This comprehensive report details your {duration}-day anime pilgrimage journey to {destination} featuring locations from the beloved anime series **{anime_theme}**. The itinerary includes optimized routes, visit schedules, and episode-specific photo opportunities.

---

## 🎯 Trip Highlights

- **Total Locations:** Multiple anime pilgrimage sites
- **Estimated Travel Distance:** Available on interactive map
- **Best Visit Season:** Based on weather analysis
- **Special Focus:** {anime_theme} filming locations and scenes

---

## 📅 Detailed Itinerary

{self._generate_markdown_itinerary(trip_data)}

---

## 🗺️ Interactive Pilgrimage Map

![Main Route Map]({main_map})

**Open the HTML file above to explore:**
- Interactive anime pilgrimage locations
- Episode-specific scene details
- Photo opportunities and visit suggestions
- Optimized travel routes and schedules

---

## ✈️ Flight Information

{self._generate_markdown_flights(trip_data)}

---

## 🌤️ Weather Information

{self._generate_markdown_weather(trip_data)}

---

## 📸 Episode Guide and Photo Opportunities

{self._generate_markdown_episode_guide(trip_data)}

---

## 📊 Route Statistics

{self._generate_markdown_statistics()}

---

## 💡 Travel Tips and Recommendations

{self._generate_markdown_recommendations(trip_data)}

---

## 📞 Emergency Information

### Important Contacts
- **Tourist Information Hotline:** +81-3-3201-3331 (Japan)
- **Emergency Services:** 110 (Police), 119 (Ambulance/Fire)
- **Translation Services:** Google Translate, DeepL

### Transportation
- **JR Pass:** Recommended for extensive train travel
- **IC Cards:** Suica/Pasmo for convenient local transport
- **Rental Car:** Recommended for remote locations

### Accommodation
- Book accommodations in advance, especially during peak seasons
- Consider staying near major railway stations for convenience
- Look for anime-themed hotels or guesthouses for enhanced experience

---

*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return template

    def _generate_markdown_itinerary(self, trip_data: Dict[str, Any]) -> str:
        """Generate detailed itinerary section"""
        itinerary = trip_data.get("itinerary", {})
        daily_plans = itinerary.get("daily_plans", [])

        if not daily_plans:
            return "Detailed itinerary not available."

        content = ""
        for i, day_plan in enumerate(daily_plans, 1):
            content += f"\n### Day {i}: {day_plan.get('date', 'TBD')}\n\n"

            # Morning activities
            if "morning" in day_plan:
                content += "**Morning Activities:**\n"
                for activity in day_plan["morning"]:
                    content += f"- {activity.get('activity', 'TBD')} ({activity.get('duration', 'TBD')})\n"
                content += "\n"

            # Afternoon activities
            if "afternoon" in day_plan:
                content += "**Afternoon Activities:**\n"
                for activity in day_plan["afternoon"]:
                    content += f"- {activity.get('activity', 'TBD')} ({activity.get('duration', 'TBD')})\n"
                content += "\n"

            # Evening activities
            if "evening" in day_plan:
                content += "**Evening Activities:**\n"
                for activity in day_plan["evening"]:
                    content += f"- {activity.get('activity', 'TBD')} ({activity.get('duration', 'TBD')})\n"
                content += "\n"

            # Anime pilgrimage locations
            if "anime_pilgrimage" in day_plan:
                content += "**🎬 Anime Pilgrimage Sites:**\n"
                for site in day_plan["anime_pilgrimage"]:
                    content += f"- **{site.get('location', 'TBD')}**\n"
                    content += f"  - Scene: {site.get('description', 'TBD')}\n"
                    content += f"  - Episode: {site.get('episode', 'TBD')}\n"
                    if site.get('visit_time'):
                        content += f"  - Best Visit Time: {site.get('visit_time')}\n"
                    if site.get('photo_tip'):
                        content += f"  - Photo Tip: {site.get('photo_tip')}\n"
                content += "\n"

        return content

    def _generate_markdown_flights(self, trip_data: Dict[str, Any]) -> str:
        """Generate flight information section"""
        flight_info = trip_data.get("flight_info", {})

        if isinstance(flight_info, dict) and "data" in flight_info:
            content = "\n"
            for i, flight in enumerate(flight_info["data"][:3], 1):
                flight_data = flight.get("flight", {})
                content += f"### Flight Option {i}\n\n"
                content += f"**Flight Number:** {flight_data.get('iata', 'TBD')}\n"
                content += f"**Departure:** {flight_data.get('departure', {}).get('airport', 'TBD')}\n"
                content += f"**Arrival:** {flight_data.get('arrival', {}).get('airport', 'TBD')}\n"
                content += f"**Price:** ${flight_data.get('price', 'TBD')}\n\n"
            return content
        else:
            return "Flight information not available."

    def _generate_markdown_weather(self, trip_data: Dict[str, Any]) -> str:
        """Generate weather information section"""
        weather_info = trip_data.get("weather_info", {})

        if isinstance(weather_info, dict) and "current" in weather_info:
            current = weather_info["current"]
            content = f"""
### Current Weather Conditions
- **Temperature:** {current.get('temperature', 'TBD')}°C
- **Condition:** {current.get('condition', 'TBD')}
- **Humidity:** {current.get('humidity', 'TBD')}%
- **Wind Speed:** {current.get('wind_speed', 'TBD')} km/h

### Travel Recommendations
- {weather_info.get('best_travel_days', 'Check weather forecast for best travel days')}
"""
            return content
        else:
            return "Weather information not available."

    def _generate_markdown_episode_guide(self, trip_data: Dict[str, Any]) -> str:
        """Generate episode guide with photo opportunities"""
        anime_theme = trip_data.get("parsed_data", {}).get("anime_theme", "Anime Pilgrimage")

        episode_guides = {
            "Slam Dunk": {
                "key_episodes": [
                    {"episode": "Episode 1", "title": "The Birth of a Genius", "locations": ["Shohoku High School"], "photo_tip": "Capture the school gate entrance scene"},
                    {"episode": "Episode 26", "title": "Inter-High Tournament", "locations": ["Tokyo Metropolitan Gymnasium"], "photo_tip": "Action shots of basketball courts"},
                    {"episode": "Episode 101", "title": "Final Game", "locations": ["National Stadium"], "photo_tip": "Panoramic stadium shots"}
                ]
            },
            "Your Name": {
                "key_episodes": [
                    {"episode": "Movie Scene", "title": "Stairway Connection", "locations": ["Suga Shrine Steps"], "photo_tip": "Morning light photography of the stairs"},
                    {"episode": "Movie Scene", "title": "Comet Appearance", "locations": ["Lake Suwa"], "photo_tip": "Night photography with reflection"},
                    {"episode": "Movie Scene", "title": "Town Overlook", "locations": ["Mt. Hiei"], "photo_tip": "Panoramic city views"}
                ]
            }
        }

        guide = episode_guides.get(anime_theme, {"key_episodes": []})

        content = f"""
### Key {anime_theme} Episodes to Follow

The following episodes feature the locations you'll be visiting:

"""

        for episode in guide["key_episodes"]:
            content += f"""
#### {episode['title']}
- **Episode:** {episode['episode']}
- **Featured Locations:** {', '.join(episode['locations'])}
- **Photo Opportunity:** {episode['photo_tip']}

"""

        content += """
### Photography Tips for Anime Pilgrimage

1. **Time of Day**: Early morning or late afternoon for best lighting
2. **Seasonal Considerations**: Match your photos with the anime's seasonal setting
3. **Angle Matching**: Try to replicate camera angles from the anime
4. **Context Shots**: Include both close-up details and wider contextual shots
5. **People-Free**: Visit during off-peak hours for empty location shots

"""

        return content

    def _generate_markdown_statistics(self, route_summary: Dict[str, Any] = None) -> str:
        """Generate route statistics section"""

        return """
### Route Overview
- **Total Distance:** Available on interactive map
- **Estimated Travel Time:** Available on interactive map
- **Number of Locations:** Available on interactive map
- **Average Daily Distance:** Available on interactive map

### Interactive Features
The interactive map provides detailed statistics including:
- Optimized travel routes between locations
- Estimated travel times and distances
- Location-specific visit recommendations
- Episode and scene information
- Photo opportunity guidelines

"""

    def _generate_markdown_recommendations(self, trip_data: Dict[str, Any]) -> str:
        """Generate travel recommendations section"""

        recommendations = trip_data.get("recommendations", [])

        content = """
### General Travel Tips
"""

        for rec in recommendations:
            content += f"- {rec}\n"

        content += """

### Anime-Specific Recommendations
- **Learn Key Phrases**: Study Japanese phrases related to your favorite anime
- **Bring Merchandise**: Consider bringing related merchandise for photo opportunities
- **Seasonal Events**: Check for anime-related events or exhibitions during your visit
- **Local Guides**: Consider hiring local guides who know anime locations
- **Social Media**: Share your pilgrimage experience with anime communities

### Packing List
- Comfortable walking shoes for extensive location visits
- Camera equipment with extra batteries and memory cards
- Portable power bank for smartphone navigation
- Weather-appropriate clothing and accessories
- Anime merchandise for photo opportunities
- Journal for recording your pilgrimage experience

### Cultural Considerations
- Respect private property and local residents
- Follow photography rules at each location
- Be mindful of noise levels, especially in residential areas
- Support local businesses and anime merchandise shops
- Learn basic Japanese etiquette and customs

"""

        return content

    def generate_pdf_report(self, trip_data: Dict[str, Any], base_filename: str) -> str:
        """Generate professional PDF report"""

        filename = f"{base_filename}.pdf"

        # Create PDF document
        doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
        story = []

        # Title
        anime_theme = trip_data.get("parsed_data", {}).get("anime_theme", "Anime Pilgrimage")
        title = Paragraph(f"{anime_theme} Anime Pilgrimage Trip Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 20))

        # Trip Overview
        overview_text = self._create_pdf_overview(trip_data)
        story.append(Paragraph(overview_text, self.styles['Normal']))
        story.append(Spacer(1, 12))

        # Detailed Itinerary
        story.append(Paragraph("Daily Itinerary", self.styles['CustomHeading1']))
        itinerary_content = self._create_pdf_itinerary(trip_data)
        for paragraph in itinerary_content:
            story.append(Paragraph(paragraph, self.styles['Normal']))
            story.append(Spacer(1, 6))

        story.append(PageBreak())

        # Flight Information
        story.append(Paragraph("Flight Information", self.styles['CustomHeading1']))
        flight_content = self._create_pdf_flights(trip_data)
        if flight_content:
            story.append(Paragraph(flight_content, self.styles['Normal']))
        else:
            story.append(Paragraph("Flight information not available.", self.styles['Normal']))
        story.append(Spacer(1, 12))

        # Weather Information
        story.append(Paragraph("Weather Information", self.styles['CustomHeading1']))
        weather_content = self._create_pdf_weather(trip_data)
        story.append(Paragraph(weather_content, self.styles['Normal']))
        story.append(Spacer(1, 12))

        # Travel Tips
        story.append(Paragraph("Travel Tips & Recommendations", self.styles['CustomHeading1']))
        tips_content = self._create_pdf_tips(trip_data)
        story.append(Paragraph(tips_content, self.styles['Normal']))

        # Build PDF
        doc.build(story)

        print(f"[REPORT] PDF report generated: {filename}")
        return filename

    def _create_pdf_overview(self, trip_data: Dict[str, Any]) -> str:
        """Create PDF overview section"""
        anime_theme = trip_data.get("parsed_data", {}).get("anime_theme", "Anime Pilgrimage")
        destination = trip_data.get("parsed_data", {}).get("destination", "Japan")
        duration = trip_data.get("parsed_data", {}).get("duration", 7)
        departure_date = trip_data.get("parsed_data", {}).get("departure_date", "2024-12-01")

        start_date = datetime.strptime(departure_date, "%Y-%m-%d")
        end_date = start_date + timedelta(days=duration-1)

        route_summary = trip_data.get("route_summary", {})

        return f"""
<b>Trip Overview:</b><br/>
Destination: {destination}<br/>
Duration: {duration} days ({start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')})<br/>
Theme: {anime_theme} Anime Pilgrimage<br/>
Total Locations: {route_summary.get('total_locations', 'Multiple')}<br/>
Estimated Distance: {route_summary.get('total_distance_km', 'TBD')} km
"""

    def _create_pdf_itinerary(self, trip_data: Dict[str, Any]) -> List[str]:
        """Create PDF itinerary section"""
        itinerary = trip_data.get("itinerary", {})
        daily_plans = itinerary.get("daily_plans", [])

        content = []

        if not daily_plans:
            return ["Detailed itinerary not available."]

        for i, day_plan in enumerate(daily_plans, 1):
            content.append(f"<b>Day {i}:</b> {day_plan.get('date', 'TBD')}")
            content.append("")

            if "anime_pilgrimage" in day_plan:
                content.append("<b>Anime Pilgrimage Sites:</b>")
                for site in day_plan["anime_pilgrimage"]:
                    content.append(f"• {site.get('location', 'TBD')}")
                    content.append(f"  Scene: {site.get('description', 'TBD')}")
                    if site.get('episode'):
                        content.append(f"  Episode: {site.get('episode')}")
                content.append("")

        return content

    def _create_pdf_flights(self, trip_data: Dict[str, Any]) -> str:
        """Create PDF flight section"""
        flight_info = trip_data.get("flight_info", {})

        if isinstance(flight_info, dict) and "data" in flight_info:
            content = "<b>Available Flights:</b><br/><br/>"
            for i, flight in enumerate(flight_info["data"][:2], 1):
                flight_data = flight.get("flight", {})
                content += f"<b>Flight {i}:</b> {flight_data.get('iata', 'TBD')}<br/>"
                content += f"From: {flight_data.get('departure', {}).get('airport', 'TBD')}<br/>"
                content += f"To: {flight_data.get('arrival', {}).get('airport', 'TBD')}<br/>"
                content += f"Price: ${flight_data.get('price', 'TBD')}<br/><br/>"
            return content
        return ""

    def _create_pdf_weather(self, trip_data: Dict[str, Any]) -> str:
        """Create PDF weather section"""
        weather_info = trip_data.get("weather_info", {})

        if isinstance(weather_info, dict) and "current" in weather_info:
            current = weather_info["current"]
            return f"""
<b>Current Weather Conditions:</b><br/>
Temperature: {current.get('temperature', 'TBD')}°C<br/>
Condition: {current.get('condition', 'TBD')}<br/>
Humidity: {current.get('humidity', 'TBD')}%<br/>
Best Travel Days: {weather_info.get('best_travel_days', 'Check forecast')}
"""
        return "Weather information not available."

    def _create_pdf_tips(self, trip_data: Dict[str, Any]) -> str:
        """Create PDF tips section"""
        recommendations = trip_data.get("recommendations", [])

        content = "<b>General Recommendations:</b><br/><br/>"
        for rec in recommendations:
            content += f"• {rec}<br/>"

        content += "<br/><b>Anime Pilgrimage Tips:</b><br/><br/>"
        content += "• Bring camera equipment for location photos<br/>"
        content += "• Learn basic Japanese phrases<br/>"
        content += "• Pack comfortable walking shoes<br/>"
        content += "• Consider JR Pass for train travel<br/>"
        content += "• Download offline maps and translation apps<br/>"

        return content


def main():
    """Test the enhanced report generator"""
    print("[TEST] Testing Enhanced Report Generator...")

    # Sample trip data
    sample_trip_data = {
        "query": "7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Slam Dunk",
        "parsed_data": {
            "origin": "Taiwan",
            "destination": "Japan",
            "duration": 7,
            "departure_date": "2024-12-01",
            "anime_theme": "Slam Dunk",
            "budget_level": "medium",
            "interests": ["anime", "culture", "sightseeing"]
        },
        "flight_info": {
            "data": [
                {
                    "flight": {
                        "iata": "TWJPN001",
                        "departure": {"airport": "Taiwan International Airport"},
                        "arrival": {"airport": "Tokyo International Airport"},
                        "price": 350
                    }
                }
            ]
        },
        "weather_info": {
            "current": {
                "temperature": 15,
                "condition": "Partly Cloudy",
                "humidity": 65,
                "wind_speed": 12
            },
            "best_travel_days": "December 1-7, 2024"
        },
        "itinerary": {
            "daily_plans": [
                {
                    "date": "2024-12-01",
                    "anime_pilgrimage": [
                        {
                            "location": "Shohoku High School (Kamakura High School)",
                            "description": "Hanamichi Sakuragi's school",
                            "episode": "Episode 1-101",
                            "coordinates": [35.3193, 139.5529]
                        }
                    ]
                }
            ]
        },
        "recommendations": [
            "Pack comfortable walking shoes for extensive sightseeing",
            "Consider getting a JR Pass for convenient train travel in Japan",
            "Download offline maps and translation apps before your trip"
        ]
    }

    try:
        generator = ReportGenerator()
        output_files = generator.generate_comprehensive_report(
            sample_trip_data,
            output_format="both"
        )

        print("[SUCCESS] Report generation completed!")
        print("[OUTPUT] Generated files:")
        for format_type, file_path in output_files.items():
            print(f"  - {format_type.upper()}: {file_path}")

        return output_files

    except Exception as e:
        print(f"[ERROR] Report generation failed: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    main()