"""
Response Generator Component
Convert itinerary and travel data into a user-friendly response using HuggingFace LLM.
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from dotenv import load_dotenv

from src.components.trip_planner import TravelPlan, DailyItinerary
from src.components.query_analyzer import QueryAnalysis
from src.agents.web_crawler import PilgrimageLocation

# Load environment variables
load_dotenv()


class GeneratedResponse(BaseModel):
    """Data model for the generated response."""

    response_type: str = Field(..., description="Type of response (itinerary, clarification, error)")
    title: str = Field(..., description="Response title")
    introduction: str = Field(..., description="Introduction text")
    main_content: str = Field(..., description="Main response content")
    summary: str = Field(..., description="Brief summary of the plan")
    recommendations: List[str] = Field(default_factory=list, description="Additional recommendations")
    disambiguation_needed: bool = Field(default=False, description="Whether user clarification is needed")
    disambiguation_questions: List[str] = Field(default_factory=list, description="Questions for user")
    confidence: float = Field(default=0.0, description="Confidence in the response")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ResponseGenerator:
    """
    Response Generator
    Core: HuggingFace LLM or LangGraph natural language generation pipeline.

    Function: Convert itinerary and travel data into a user-friendly response.
    Output: Detailed textual travel plan with routes, site descriptions, timing, and activities.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("HUGGINGFACE_MODEL_NAME", "google/gemma-3-4b-it")
        self.tokenizer = None
        self.model = None
        self.generator = None

        # Response templates
        self.templates = {
            'itinerary': self._load_itinerary_template(),
            'clarification': self._load_clarification_template(),
            'error': self._load_error_template()
        }

    def _load_itinerary_template(self) -> str:
        """Template for itinerary responses."""
        return """# {title}

## Introduction
{introduction}

## Travel Plan Overview
{overview}

## Detailed Itinerary
{daily_itineraries}

## Practical Information
{practical_info}

## Summary
{summary}

## Additional Recommendations
{recommendations}

---

*This plan was generated based on your anime pilgrimage preferences. Travel times and costs are estimates and may vary.*
"""

    def _load_clarification_template(self) -> str:
        """Template for clarification responses."""
        return """# I Need Some Clarification

{introduction}

## Questions to Help Me Plan Better
{questions}

## Examples of What I Can Help With
{examples}

Once you provide more details, I'll be able to create a perfect anime pilgrimage itinerary for you!
"""

    def _load_error_template(self) -> str:
        """Template for error responses."""
        return """# I Couldn't Generate a Plan

{introduction}

## What I Need
{requirements}

## Tips for Better Results
{tips}

Please try again with a more specific request!
"""

    def _initialize_model(self):
        """Initialize the HuggingFace model and tokenizer."""
        if self.generator is None:
            try:
                print(f"Loading response generator model: {self.model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token

                # Check for CUDA availability
                device = "cuda" if torch.cuda.is_available() else "cpu"
                dtype = torch.bfloat16 if device == "cuda" else torch.float32

                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    dtype=dtype,
                    device_map="auto" if device == "cuda" else None
                )
                self.generator = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    max_length=1024,
                    temperature=0.8,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                print(f"Response generator model loaded successfully on {device}")
            except Exception as e:
                print(f"Warning: Could not load response model {self.model_name}: {e}")
                print("Falling back to template-based generation")
                self.generator = None

    def _generate_llm_enhancement(self, prompt: str) -> str:
        """
        Generate enhanced text using LLM (if available).

        Args:
            prompt: Prompt for text generation

        Returns:
            Generated text
        """
        if self.generator is None:
            return ""

        try:
            result = self.generator(
                prompt,
                max_length=300,
                num_return_sequences=1,
                temperature=0.7,
                pad_token_id=self.tokenizer.eos_token_id
            )
            return result[0]['generated_text'].strip()
        except Exception as e:
            print(f"LLM enhancement failed: {e}")
            return ""

    def _format_introduction(self, query_analysis: QueryAnalysis, travel_plan: TravelPlan) -> str:
        """Format the introduction section."""
        anime_titles = [anime.anime_title for anime in query_analysis.identified_anime]

        intro = f"I've created a fantastic {travel_plan.duration_days}-day anime pilgrimage itinerary for you! "
        intro += f"This plan focuses on visiting real-world locations from "

        if len(anime_titles) == 1:
            intro += f"**{anime_titles[0]}**"
        else:
            intro += f"{' and '.join(anime_titles[:-1])} and {anime_titles[-1]}"

        intro += f" in and around {travel_plan.destination}. "

        # Add travel style context
        if query_analysis.trip_preferences.get('travel_style'):
            style = query_analysis.trip_preferences['travel_style']
            intro += f"Perfect for a {style} travel experience, "

        intro += "this itinerary includes detailed directions, timing suggestions, and practical tips to make your anime pilgrimage unforgettable!"

        return intro

    def _format_overview(self, travel_plan: TravelPlan, locations: List[PilgrimageLocation]) -> str:
        """Format the overview section."""
        overview = f"**🎯 Trip Highlights:**\n"
        overview += f"- **Duration:** {travel_plan.duration_days} days\n"
        overview += f"- **Locations to Visit:** {travel_plan.total_locations} anime pilgrimage spots\n"
        overview += f"- **Primary Anime:** {travel_plan.trip_title}\n"
        overview += f"- **Transportation:** {travel_plan.transportation_mode.replace('_', ' ').title()}\n"

        if travel_plan.total_estimated_cost.get('total'):
            overview += f"- **Estimated Cost:** ¥{travel_plan.total_estimated_cost['total']:,.0f}\n"

        overview += f"\n**📍 Featured Locations:**\n"
        for location in locations[:5]:  # Top 5 locations
            overview += f"- **{location.name}** - From {location.anime_title}\n"

        return overview

    def _format_daily_itineraries(self, daily_itineraries: List[DailyItinerary]) -> str:
        """Format the daily itineraries section."""
        if not daily_itineraries:
            return "No daily itineraries available."

        content = ""
        for day in daily_itineraries:
            content += f"\n### Day {day.day}\n\n"

            if day.locations:
                # Format locations and activities
                for i, (location, activity) in enumerate(zip(day.locations, day.activities), 1):
                    content += f"**{i}. {location}**\n"
                    content += f"   - Activity: {activity}\n"
                    if i < len(day.travel_times):
                        travel_time = day.travel_times[i-1]
                        content += f"   - Travel time to next location: {travel_time} minutes\n"

                # Add day statistics
                total_hours = (day.total_visit_time + day.total_travel_time) / 60
                content += f"\n**Day Summary:**\n"
                content += f"- Total visit time: {day.total_visit_time} minutes ({day.total_visit_time/60:.1f} hours)\n"
                content += f"- Total travel time: {day.total_travel_time} minutes ({day.total_travel_time/60:.1f} hours)\n"
                content += f"- Total day duration: ~{total_hours:.1f} hours\n"

                if day.estimated_cost.get('total'):
                    content += f"- Estimated daily cost: ¥{day.estimated_cost['total']:,.0f}\n"

                # Add notes
                if day.notes:
                    content += f"\n**Special Notes:**\n"
                    for note in day.notes:
                        content += f"- {note}\n"
            else:
                content += "Free day for rest and exploration.\n"

            content += "\n---\n"

        return content

    def _format_practical_info(self, travel_plan: TravelPlan, query_analysis: QueryAnalysis) -> str:
        """Format the practical information section."""
        info = "**🏨 Accommodation Suggestions:**\n"
        for suggestion in travel_plan.accommodation_suggestions:
            info += f"- {suggestion}\n"

        info += f"\n**🚆 Transportation:**\n"
        info += f"- Primary mode: {travel_plan.transportation_mode.replace('_', ' ').title()}\n"
        info += f"- Consider purchasing a JR Pass if traveling between cities\n"
        info += f"- Download local transit apps for real-time information\n"

        info += f"\n**💰 Budget Breakdown:**\n"
        for category, cost in travel_plan.total_estimated_cost.items():
            if category != 'total':
                info += f"- {category.title()}: ¥{cost:,.0f}\n"
        info += f"- **Total Estimated Cost: ¥{travel_plan.total_estimated_cost.get('total', 0):,.0f}**\n"

        info += f"\n**🆘 Emergency Contacts:**\n"
        for service, number in travel_plan.emergency_contacts.items():
            info += f"- {service.title()}: {number}\n"

        return info

    def _format_summary(self, travel_plan: TravelPlan, query_analysis: QueryAnalysis) -> str:
        """Format the summary section."""
        anime_count = len(query_analysis.identified_anime)
        location_count = travel_plan.total_locations

        summary = f"This {travel_plan.duration_days}-day anime pilgrimage covers {location_count} "
        summary += f"real-world locations from {anime_count} "

        if anime_count == 1:
            summary += f"anime ({query_analysis.identified_anime[0].anime_title})"
        else:
            summary += f"different anime series"

        summary += f" in the {travel_plan.destination} area. "

        # Add travel style context
        style = query_analysis.trip_preferences.get('travel_style', 'standard')
        if style == 'budget':
            summary += "The itinerary is designed for budget-conscious travelers "
        elif style == 'luxury':
            summary += "The itinerary features premium experiences and "
        else:
            summary += "The itinerary offers a balanced experience with "

        summary += f"estimated total costs of ¥{travel_plan.total_estimated_cost.get('total', 0):,.0f}. "
        summary += "Each day includes efficient routing, timing suggestions, and practical tips for the best pilgrimage experience!"

        return summary

    def _format_recommendations(self, travel_plan: TravelPlan) -> List[str]:
        """Format additional recommendations."""
        recommendations = travel_plan.general_tips.copy()

        # Add some standard recommendations
        additional_recommendations = [
            "Check weather forecasts and pack accordingly for the season",
            "Bring a portable charger for your phone for navigation and photos",
            "Consider purchasing a pocket WiFi or SIM card for constant connectivity",
            "Many locations have small souvenir shops perfect for anime merchandise",
            "Try local cuisine near pilgrimage locations for a complete cultural experience"
        ]

        recommendations.extend(additional_recommendations)
        return recommendations[:8]  # Limit to 8 recommendations

    def _generate_clarification_response(self, query_analysis: QueryAnalysis) -> GeneratedResponse:
        """Generate a response asking for user clarification."""
        if not query_analysis.disambiguation_questions:
            # Generic clarification
            questions = [
                "Which specific anime are you most interested in?",
                "How many days would you like your trip to be?",
                "What's your preferred travel style (budget, standard, or luxury)?",
                "Are there any specific locations you definitely want to visit?"
            ]
        else:
            questions = query_analysis.disambiguation_questions

        content = {
            'introduction': "I'd love to help you plan the perfect anime pilgrimage, but I need a bit more information to create the best itinerary for you.",
            'questions': '\n'.join([f"• {q}" for q in questions]),
            'examples': '''• "I want to visit locations from Your Name in Tokyo for 3 days"
• "Plan a budget trip to Attack on Titan locations in Oita"
• "I'd like to see Studio Ghibli pilgrimage sites over a weekend"'''
        }

        response_text = self.templates['clarification'].format(**content)

        return GeneratedResponse(
            response_type="clarification",
            title="Need More Information",
            introduction=content['introduction'],
            main_content=response_text,
            summary="Please provide more details about your anime pilgrimage preferences.",
            disambiguation_needed=True,
            disambiguation_questions=questions,
            confidence=0.3,
            metadata={'requires_clarification': True}
        )

    def _generate_error_response(self, error_message: str) -> GeneratedResponse:
        """Generate an error response."""
        content = {
            'introduction': f"I apologize, but I encountered an issue while generating your travel plan: {error_message}",
            'requirements': '''• A clear mention of anime titles
• Desired locations or cities
• Trip duration (if you have a preference)
• Any specific requirements or preferences''',
            'tips': '''• Be specific about which anime you're interested in
• Mention the cities or regions you'd like to visit
• Include your preferred trip length if known
• Specify any budget or travel style preferences'''
        }

        response_text = self.templates['error'].format(**content)

        return GeneratedResponse(
            response_type="error",
            title="Unable to Generate Plan",
            introduction=content['introduction'],
            main_content=response_text,
            summary="Please check your request and try again with more specific details.",
            confidence=0.1,
            metadata={'error': error_message}
        )

    def generate_itinerary_response(
        self,
        travel_plan: TravelPlan,
        query_analysis: QueryAnalysis,
        locations: List[PilgrimageLocation]
    ) -> GeneratedResponse:
        """
        Generate a complete itinerary response.

        Args:
            travel_plan: Generated travel plan
            query_analysis: Query analysis results
            locations: List of pilgrimage locations

        Returns:
            GeneratedResponse object
        """
        if not travel_plan or not travel_plan.daily_itineraries:
            return self._generate_error_response("No valid itinerary could be generated")

        # Initialize model if needed
        if self.generator is None:
            self._initialize_model()

        # Format each section
        introduction = self._format_introduction(query_analysis, travel_plan)
        overview = self._format_overview(travel_plan, locations)
        daily_itineraries = self._format_daily_itineraries(travel_plan.daily_itineraries)
        practical_info = self._format_practical_info(travel_plan, query_analysis)
        summary = self._format_summary(travel_plan, query_analysis)
        recommendations = self._format_recommendations(travel_plan)

        # Try to enhance with LLM
        enhanced_intro = self._generate_llm_enhancement(
            f"Make this anime pilgrimage introduction more engaging and exciting: {introduction}"
        )
        if enhanced_intro:
            introduction = enhanced_intro

        # Format complete response
        template_data = {
            'title': travel_plan.trip_title,
            'introduction': introduction,
            'overview': overview,
            'daily_itineraries': daily_itineraries,
            'practical_info': practical_info,
            'summary': summary,
            'recommendations': '\n'.join([f"• {rec}" for rec in recommendations])
        }

        response_text = self.templates['itinerary'].format(**template_data)

        return GeneratedResponse(
            response_type="itinerary",
            title=travel_plan.trip_title,
            introduction=introduction,
            main_content=response_text,
            summary=summary,
            recommendations=recommendations,
            disambiguation_needed=False,
            confidence=query_analysis.analysis_confidence,
            metadata={
                'duration_days': travel_plan.duration_days,
                'total_locations': travel_plan.total_locations,
                'estimated_cost': travel_plan.total_estimated_cost.get('total', 0),
                'anime_count': len(query_analysis.identified_anime)
            }
        )

    def generate_response(
        self,
        travel_plan: Optional[TravelPlan],
        query_analysis: QueryAnalysis,
        locations: Optional[List[PilgrimageLocation]] = None,
        error: Optional[str] = None
    ) -> GeneratedResponse:
        """
        Generate appropriate response based on inputs.

        Args:
            travel_plan: Generated travel plan (if successful)
            query_analysis: Query analysis results
            locations: List of pilgrimage locations
            error: Error message (if generation failed)

        Returns:
            GeneratedResponse object
        """
        if error:
            return self._generate_error_response(error)

        if query_analysis.disambiguation_questions and not travel_plan:
            return self._generate_clarification_response(query_analysis)

        if not travel_plan:
            return self._generate_error_response("No travel plan was generated")

        # Generate markdown response
        markdown_content = self.generate_markdown_response(
            travel_plan,
            query_analysis,
            locations or []
        )

        return self.generate_itinerary_response(
            travel_plan,
            query_analysis,
            locations or []
        )

    def generate_markdown_response(
        self,
        travel_plan: TravelPlan,
        query_analysis: QueryAnalysis,
        locations: List[PilgrimageLocation]
    ) -> str:
        """
        Generate a comprehensive markdown travel plan.

        Args:
            travel_plan: Generated travel plan
            query_analysis: Query analysis results
            locations: List of pilgrimage locations

        Returns:
            Complete markdown formatted travel plan
        """
        # Get anime title for header
        anime_title = travel_plan.trip_title if travel_plan.trip_title else "Anime Pilgrimage"

        # Create markdown content
        markdown = f"""# {anime_title} - Anime Pilgrimage Travel Plan

## 📋 Trip Overview

- **🎯 Primary Anime:** {anime_title}
- **📅 Duration:** {travel_plan.duration_days} days
- **📍 Total Locations:** {travel_plan.total_locations} pilgrimage spots
- **🚊 Transportation:** {travel_plan.transportation_mode.replace('_', ' ').title()}
- **💰 Estimated Total Cost:** ¥{travel_plan.total_estimated_cost.get('total', 0):,.0f}

---

## 🗾 Featured Pilgrimage Locations

"""

        # Add featured locations
        for i, location in enumerate(locations[:8], 1):
            markdown += f"""### {i}. {location.name}

**📍 Address:** {location.address}

**🎬 Anime Scene:** {location.scene_description}

**🗺️ Coordinates:** {location.coordinates}

**⭐ Why Visit:** {location.description}

**🚌 Access:** {location.access_method}

---

"""

        # Add daily itineraries
        markdown += """## 📅 Detailed Itinerary

"""

        for day in travel_plan.daily_itineraries:
            markdown += f"""### Day {day.day}

**🕐 Estimated Duration:** {(day.total_visit_time + day.total_travel_time) / 60:.1f} hours
**💰 Daily Cost:** ¥{day.estimated_cost.get('total', 0):,.0f}

"""

            for i, (location, activity) in enumerate(zip(day.locations, day.activities), 1):
                markdown += f"""**{i}. {location}**
   - **Activity:** {activity}
"""

                if i < len(day.travel_times):
                    travel_time = day.travel_times[i-1]
                    markdown += f"   - **⏱️ Travel Time to Next:** {travel_time} minutes\n"

            if day.notes:
                markdown += "\n**📝 Special Notes:**\n"
                for note in day.notes:
                    markdown += f"- {note}\n"

            markdown += "\n---\n\n"

        # Add travel tips
        markdown += """## 💡 Travel Tips & Information

### 🎌 Best Time to Visit
- **Spring (March-May):** Cherry blossom season, pleasant weather
- **Autumn (September-November):** Fall foliage, comfortable temperatures
- **Avoid:** Golden Week (late April-early May) due to crowds

### 💼 Money Matters
- **Currency:** Japanese Yen (JPY)
- **Payment:** Cash is still widely accepted, IC cards (Suica/Pasmo) recommended for transport
- **Budget Tips:** Convenience stores for cheap meals, JR Pass for long-distance travel

### 📱 Useful Apps
- **Google Maps:** Navigation and transit info
- **Google Translate:** Camera translation for signs
- **Hyperdia:** Train schedules and routes
- **Tabelog:** Restaurant reviews

### 🏨 Accommodation Suggestions
- **Budget:** Capsule hotels, business hotels, hostels
- **Mid-range:** Business hotels, ryokans (traditional inns)
- **Luxury:** High-end hotels, themed accommodations

---

## 🎬 Anime Pilgrimage Etiquette

1. **📸 Photography:** Be respectful of private property and local residents
2. **🤫 Quiet Behavior:** Many locations are in residential areas
3. **🗑️ Leave No Trace:** Take your trash with you
4. **🙏 Support Local:** Purchase goods from local shops and cafes
5. **📍 Check Access:** Some locations may be private or require special permission

---

## 🆘 Emergency Information

- **Emergency Numbers:** 110 (Police), 119 (Fire/Ambulance)
- **Tourist Information:** Available at major train stations
- **English Support:** Limited outside major cities, learn basic Japanese phrases

---

*🎌 Generated by Anime Pilgrimage Trip Planner | Powered by AI Agentic System*
"""

        return markdown


def main():
    """Demo function for testing the response generator."""
    from src.components.trip_planner import TravelPlan, DailyItinerary
    from src.components.query_analyzer import QueryAnalysis, AnimeIdentification
    from src.components.query_interface import UserQuery
    from src.agents.web_crawler import PilgrimageLocation

    # Create sample data
    user_query = UserQuery(
        original_text="I want to visit Your Name locations in Tokyo",
        normalized_text="I want to visit Your Name locations in Tokyo",
        confidence=0.9
    )

    anime_info = AnimeIdentification(
        anime_title="Your Name",
        confidence=0.9,
        keywords=["romance", "drama", "supernatural"],
        context="visit locations from Your Name",
        disambiguation_needed=False
    )

    query_analysis = QueryAnalysis(
        original_query=user_query,
        identified_anime=[anime_info],
        locations_mentioned=["Tokyo"],
        trip_preferences={"duration_preference": "2 days", "travel_style": "standard"},
        analysis_confidence=0.9
    )

    # Create sample travel plan
    daily_itinerary = DailyItinerary(
        day=1,
        locations=["Shinjuku Gyoen", "Suga Shrine"],
        activities=["Visit Shinjuku Gyoen from Your Name", "See Suga Shrine staircase"],
        travel_times=[25],
        total_visit_time=120,
        total_travel_time=25,
        estimated_cost={'total': 5000}
    )

    travel_plan = TravelPlan(
        trip_title="Your Name Pilgrimage Trip",
        destination="Tokyo",
        duration_days=2,
        total_locations=5,
        daily_itineraries=[daily_itinerary],
        total_estimated_cost={'total': 25000}
    )

    # Create sample locations
    locations = [
        PilgrimageLocation(
            name="Shinjuku Gyoen National Garden",
            anime_title="Your Name",
            real_world_address="11 Naitomachi, Shinjuku City, Tokyo",
            confidence_score=0.9
        )
    ]

    # Test response generator
    generator = ResponseGenerator()
    response = generator.generate_response(travel_plan, query_analysis, locations)

    print(f"📝 Generated Response:")
    print(f"Title: {response.title}")
    print(f"Type: {response.response_type}")
    print(f"Confidence: {response.confidence:.2f}")
    print(f"\n{response.main_content}")


if __name__ == "__main__":
    main()