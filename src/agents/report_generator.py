from typing import Dict, Any
from datetime import datetime
from .core_types import TripPlan, WorkflowState

class ReportGenerator:
    def __init__(self):
        pass

    async def generate_markdown_report(self, trip_plan: TripPlan, state: WorkflowState) -> str:
        """
        Generate a comprehensive markdown report for the anime pilgrimage trip
        """
        try:
            report = self._build_report(trip_plan)

            state.add_message("report_generator", "orchestrator", report, "report_generated")

            return report

        except Exception as e:
            state.errors.append(f"Report generation failed: {str(e)}")
            raise

    def _build_report(self, trip_plan: TripPlan) -> str:
        """
        Build the complete markdown report
        """
        report = []

        # Header
        report.append("# Anime Pilgrimage Trip Plan\n")
        report.append(f"**Anime:** {trip_plan.anime_title}")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Estimated Duration:** {trip_plan.estimated_duration}")
        report.append(f"**Total Distance:** {trip_plan.total_distance} km" if trip_plan.total_distance else "")
        report.append("\n---\n")

        # Overview
        report.append("## Trip Overview\n")
        report.append(f"This pilgrimage plan will take you through {len(trip_plan.locations)} locations")
        report.append(f"inspired by scenes from *{trip_plan.anime_title}*.\n")

        # Budget Estimate
        if trip_plan.budget_estimate:
            report.append("## Budget Estimate\n")
            report.append("| Category | Estimated Cost (USD) |")
            report.append("|----------|---------------------|")
            for category, cost in trip_plan.budget_estimate.items():
                if category != "total":
                    report.append(f"| {category.title()} | ${cost:.2f} |")
            if "total" in trip_plan.budget_estimate:
                report.append(f"| **Total** | **${trip_plan.budget_estimate['total']:.2f}** |")
            report.append("")

        # Locations Summary
        report.append("## Pilgrimage Locations\n")
        for i, location in enumerate(trip_plan.locations, 1):
            report.append(f"### {i}. {location.name}")
            report.append(f"- **Address:** {location.address}")
            report.append(f"- **Coordinates:** {location.latitude:.4f}, {location.longitude:.4f}")
            report.append(f"- **Description:** {location.description}")
            if location.scene_description:
                report.append(f"- **Scene Reference:** {location.scene_description}")
            if location.accessibility_info:
                report.append(f"- **Accessibility:** {location.accessibility_info}")
            if location.nearby_attractions:
                report.append(f"- **Nearby Attractions:** {', '.join(location.nearby_attractions)}")
            report.append("")

        # Detailed Itinerary
        report.append("## Detailed Itinerary\n")
        for day in trip_plan.itinerary:
            report.append(f"### Day {day['day']} - {day['date']}")
            report.append(f"**Location:** {day['location']}")
            report.append(f"**Address:** {day['address']}\n")

            report.append("#### Activities:")
            for activity in day['activities']:
                report.append(f"- {activity}")
            report.append("")

            report.append(f"**Estimated Time:** {day['estimated_time']}\n")

            if day['travel_from_previous']:
                travel = day['travel_from_previous']
                report.append("#### Travel Information:")
                report.append(f"- **Method:** {travel['method']}")
                if 'distance' in travel:
                    report.append(f"- **Distance:** {travel['distance']}")
                if 'estimated_time' in travel:
                    report.append(f"- **Estimated Time:** {travel['estimated_time']}")
                report.append("")

            report.append("#### Meals:")
            for meal in day['meals']:
                report.append(f"- {meal}")
            report.append("")

            if day['accommodation_suggestion']:
                report.append(f"**Accommodation:** {day['accommodation_suggestion']}\n")

            report.append("---\n")

        # Travel Tips
        if trip_plan.travel_tips:
            report.append("## Travel Tips\n")
            for tip in trip_plan.travel_tips:
                report.append(f"- {tip}")
            report.append("")

        # Additional Information
        report.append("## Additional Information\n")
        report.append("### Important Notes:")
        report.append("- Always check the latest travel advisories and visa requirements")
        report.append("- Respect local customs and traditions when visiting pilgrimage sites")
        report.append("- Some locations may be on private property - always ask for permission")
        report.append("- Consider the best season to visit based on weather and local events")
        report.append("- Keep digital and physical copies of important documents")
        report.append("")

        report.append("### Recommended Apps:")
        report.append("- **Google Maps/Apple Maps:** For navigation")
        report.append("- **Google Translate:** For language assistance")
        report.append("- **Japan Travel by NAVITIME:** For local transportation")
        report.append("- **Hyperdia:** For train schedules and routes")
        report.append("- **Tabelog:** For restaurant reviews")
        report.append("")

        # Footer
        report.append("---\n")
        report.append("*This trip plan was generated by an AI-powered anime pilgrimage planning system.*")
        report.append("*Please verify all information and make necessary adjustments based on your preferences and current conditions.*\n")

        return "\n".join(report)