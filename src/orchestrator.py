from langgraph.graph import StateGraph, END, START
from typing import Dict, Any, Optional, Annotated
import asyncio
from .agents.core_types import WorkflowState, AgentState
from .agents.anime_identifier_agent import AnimeIdentifierAgent
from .agents.web_crawler_agent import WebCrawlerAgent
from .agents.trip_planner_agent import TripPlannerAgent
from .agents.report_generator import ReportGenerator

class AnimePilgrimageOrchestrator:
    def __init__(self):
        self.anime_identifier = AnimeIdentifierAgent()
        self.web_crawler = WebCrawlerAgent()
        self.trip_planner = TripPlannerAgent()
        self.report_generator = ReportGenerator()

        # Create the workflow graph
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        """
        Create the LangGraph workflow for anime pilgrimage planning
        """
        workflow = StateGraph(WorkflowState)

        # Add nodes for each agent
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("identify_anime", self._identify_anime)
        workflow.add_node("find_locations", self._find_locations)
        workflow.add_node("plan_trip", self._plan_trip)
        workflow.add_node("generate_report", self._generate_report)

        # Set the entry point
        workflow.add_edge(START, "analyze_query")

        # Add edges
        workflow.add_edge("analyze_query", "identify_anime")
        workflow.add_edge("identify_anime", "find_locations")
        workflow.add_edge("find_locations", "plan_trip")
        workflow.add_edge("plan_trip", "generate_report")
        workflow.add_edge("generate_report", END)

        # Compile the workflow
        return workflow.compile()

    async def _analyze_query(self, state: WorkflowState) -> WorkflowState:
        """
        Analyze the user query to determine intent
        """
        state.current_state = AgentState.ANALYZING_QUERY
        state.add_message("orchestrator", "system", state.user_query, "query_received")

        # Basic validation
        if not state.user_query or len(state.user_query.strip()) < 3:
            state.errors.append("Query too short. Please provide more details about the anime you're interested in.")
            return state

        return state

    async def _identify_anime(self, state: WorkflowState) -> WorkflowState:
        """
        Identify the anime from the user query
        """
        state.current_state = AgentState.IDENTIFYING_ANIME

        try:
            anime_info = await self.anime_identifier.identify_anime(state.user_query, state)
            state.current_state = AgentState.FINDING_LOCATIONS
        except Exception as e:
            state.errors.append(f"Failed to identify anime: {str(e)}")
            # Use fallback anime info
            from .agents.core_types import AnimeInfo
            state.anime_info = AnimeInfo(
                title="Unknown Anime",
                alternative_titles=[],
                genres=[],
                description="Could not identify specific anime from query"
            )

        return state

    async def _find_locations(self, state: WorkflowState) -> WorkflowState:
        """
        Find pilgrimage locations for the identified anime
        """
        state.current_state = AgentState.CRAWLING_DATA

        try:
            if state.anime_info:
                locations = await self.web_crawler.search_anime_locations(
                    state.anime_info.title, state
                )
                state.current_state = AgentState.PLANNING_TRIP
            else:
                state.errors.append("No anime information available for location search")
                state.locations = []
        except Exception as e:
            state.errors.append(f"Failed to find locations: {str(e)}")
            state.locations = []

        return state

    async def _plan_trip(self, state: WorkflowState) -> WorkflowState:
        """
        Create the trip plan based on found locations
        """
        state.current_state = AgentState.PLANNING_TRIP

        try:
            if state.locations and state.anime_info:
                trip_plan = await self.trip_planner.create_trip_plan(
                    state.anime_info.title, state.locations, state
                )
                state.current_state = AgentState.GENERATING_REPORT
            else:
                state.errors.append("No locations available for trip planning")
                state.trip_plan = None
        except Exception as e:
            state.errors.append(f"Failed to plan trip: {str(e)}")
            state.trip_plan = None

        return state

    async def _generate_report(self, state: WorkflowState) -> WorkflowState:
        """
        Generate the final markdown report
        """
        state.current_state = AgentState.GENERATING_REPORT

        try:
            if state.trip_plan:
                report = await self.report_generator.generate_markdown_report(
                    state.trip_plan, state
                )
                state.current_state = AgentState.COMPLETED
            else:
                state.errors.append("No trip plan available for report generation")
                report = self._generate_error_report(state)

        except Exception as e:
            state.errors.append(f"Failed to generate report: {str(e)}")
            report = self._generate_error_report(state)

        return state

    def _generate_error_report(self, state: WorkflowState) -> str:
        """
        Generate a report when errors occur
        """
        report = ["# Anime Pilgrimage Trip Plan - Error Report\n"]
        report.append(f"**Query:** {state.user_query}")
        report.append(f"**Status:** Failed to generate complete plan\n")
        report.append("## Errors Encountered:\n")

        for error in state.errors:
            report.append(f"- {error}")

        report.append("\n## Suggestions:")
        report.append("- Try providing more specific anime titles")
        report.append("- Check if the anime has real-world locations")
        report.append("- Try different phrasing of your query")
        report.append("- Consider that not all anime have pilgrimage locations")

        return "\n".join(report)

    async def plan_trip(self, user_query: str) -> Dict[str, Any]:
        """
        Main method to plan an anime pilgrimage trip
        """
        # Initialize state
        state = WorkflowState()
        state.user_query = user_query

        try:
            # Run the workflow
            result = await self.workflow.ainvoke(state)

            # Extract the final report
            final_report = None
            if result.trip_plan:
                final_report = await self.report_generator.generate_markdown_report(
                    result.trip_plan, result
                )
            else:
                final_report = self._generate_error_report(result)

            return {
                "success": len(result.errors) == 0,
                "report": final_report,
                "anime_info": result.anime_info,
                "locations": result.locations,
                "trip_plan": result.trip_plan,
                "errors": result.errors
            }

        except Exception as e:
            return {
                "success": False,
                "report": f"# Error\n\nFailed to process your request: {str(e)}",
                "anime_info": None,
                "locations": [],
                "trip_plan": None,
                "errors": [str(e)]
            }

    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the orchestrator
        """
        return {
            "status": "ready",
            "agents": {
                "anime_identifier": "available",
                "web_crawler": "available",
                "trip_planner": "available",
                "report_generator": "available"
            }
        }