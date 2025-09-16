"""
Advanced Multi-Agent Home Assistant System using LangGraph

This system implements a sophisticated multi-agent architecture with:
- State management and conversation history
- Conditional routing based on query analysis
- Tool integration for specialized agents
- Error handling and fallback mechanisms
- Support for multimodal inputs (text + images)
"""

import asyncio
import json
import base64
from typing import Dict, Any, Optional, List, TypedDict, Annotated, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import io
import requests
from PIL import Image

from langgraph.graph import Graph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from markdownify import markdownify

import torch
from transformers import AutoProcessor, AutoModelForCausalLM, LlavaNextProcessor, LlavaNextForConditionalGeneration

# === Type Definitions ===
class AgentType(Enum):
    MEDICAL = "medical"
    MATH = "math"
    PHYSICS = "physics"
    GENERAL = "general"
    WEATHER = "weather"
    WEB_SEARCH = "web_search"

class AgentState(TypedDict):
    """State for the agent system"""
    messages: Annotated[List, add_messages]
    query: Optional[str]
    images: Optional[List[Image.Image]]
    classification: Optional[Dict[str, Any]]
    agent_used: Optional[str]
    response: Optional[str]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]

# === Tools ===
@tool
def get_weather_api(location: str, date: str) -> str:
    """Get weather forecast for a given location and date (YYYY-MM-DD)."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD."

    try:
        geo_resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json", "limit": 1},
            headers={"User-Agent": "home-assistant-agent"}
        )
        geo_data = geo_resp.json()
        if not geo_data:
            return f"Could not find location: {location}"
        lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]

        weather_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
                "start_date": date,
                "end_date": date,
            }
        )
        weather_data = weather_resp.json()
        daily = weather_data.get("daily")
        if not daily:
            return f"Could not get weather forecast for {location} on {date}."

        max_temp = daily["temperature_2m_max"][0]
        min_temp = daily["temperature_2m_min"][0]
        precipitation = daily["precipitation_sum"][0]

        return (
            f"Weather forecast for {location} on {date}: "
            f"Max temp {max_temp}°C, Min temp {min_temp}°C, "
            f"Precipitation {precipitation}mm."
        )
    except Exception as e:
        return f"Error getting weather data: {str(e)}"

@tool
def visit_webpage(url: str) -> str:
    """Visits a webpage at the given URL and returns its content as markdown."""
    try:
        response = requests.get(url)
        response.raise_for_status()

        markdown_content = markdownify(response.text).strip()
        markdown_content = "\n\n".join(
            line for line in markdown_content.split("\n") if line.strip()
        )

        return markdown_content
    except Exception as e:
        return f"Error fetching webpage: {str(e)}"

@tool
def web_search(query: str) -> str:
    """Search the web for information using DuckDuckGo."""
    try:
        search = DuckDuckGoSearchRun()
        results = search.run(query)
        return results
    except Exception as e:
        return f"Error performing web search: {str(e)}"

# === Agent Definitions ===
class QueryClassifier:
    """Classifies user queries to determine the appropriate agent"""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.llm = ChatOpenAI(model=model_name, temperature=0.1)
        self.parser = JsonOutputParser()

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query classifier that determines which agent should handle user queries.

Available agents:
- MEDICAL: Health, medicine, symptoms, treatments, anatomy, diseases, medical images
- MATH: Mathematical problems, calculations, equations, statistics, mathematical diagrams
- PHYSICS: Physics concepts, mechanics, thermodynamics, electromagnetism, physics diagrams
- WEATHER: Weather forecasts, climate information, atmospheric conditions
- WEB_SEARCH: General knowledge, current events, research, web-based information
- GENERAL: General conversation, small talk, queries that don't fit other categories

Analyze the user's query and respond with JSON:
{{
    "agent_type": "medical|math|physics|weather|web_search|general",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of the classification decision",
    "requires_tools": true/false
}}"""),
            ("human", "Query: {query}")
        ])

        self.chain = self.prompt | self.llm | self.parser

    async def classify(self, query: str) -> Dict[str, Any]:
        """Classify the query and return routing decision"""
        try:
            result = await self.chain.ainvoke({"query": query})
            return result
        except Exception as e:
            # Fallback classification
            query_lower = query.lower()
            if any(word in query_lower for word in ['weather', 'forecast', 'temperature']):
                return {"agent_type": "weather", "confidence": 0.8, "reasoning": "Weather keywords detected", "requires_tools": True}
            elif any(word in query_lower for word in ['medical', 'health', 'symptom', 'doctor']):
                return {"agent_type": "medical", "confidence": 0.8, "reasoning": "Medical keywords detected", "requires_tools": False}
            elif any(word in query_lower for word in ['math', 'calculate', 'equation', 'solve']):
                return {"agent_type": "math", "confidence": 0.8, "reasoning": "Math keywords detected", "requires_tools": False}
            elif any(word in query_lower for word in ['physics', 'force', 'energy', 'motion']):
                return {"agent_type": "physics", "confidence": 0.8, "reasoning": "Physics keywords detected", "requires_tools": False}
            elif any(word in query_lower for word in ['search', 'find', 'lookup', 'research']):
                return {"agent_type": "web_search", "confidence": 0.8, "reasoning": "Search keywords detected", "requires_tools": True}
            else:
                return {"agent_type": "general", "confidence": 0.6, "reasoning": "Fallback to general agent", "requires_tools": False}

class SpecializedAgent:
    """Base class for specialized agents"""

    def __init__(self, agent_type: AgentType, model_name: str = "gpt-3.5-turbo", tools: List = None):
        self.agent_type = agent_type
        self.llm = ChatOpenAI(model=model_name, temperature=0.7)
        self.tools = tools or []

        # System prompts for different agent types
        self.system_prompts = {
            AgentType.MEDICAL: """You are a medical AI assistant with expertise in healthcare, medicine, anatomy, diseases, and treatments.
            Provide accurate medical information while always recommending consulting healthcare professionals for serious concerns.
            Be thorough but accessible in your explanations.""",

            AgentType.MATH: """You are a mathematics expert capable of solving problems across all areas of mathematics.
            Show your work step-by-step and provide clear explanations for your reasoning.
            Use appropriate mathematical notation and explain your approach.""",

            AgentType.PHYSICS: """You are a physics expert with deep knowledge across all physics domains.
            Explain concepts clearly with examples and provide relevant equations when appropriate.
            Focus on fundamental principles and their applications.""",

            AgentType.WEATHER: """You are a weather and climate information specialist.
            Provide accurate weather forecasts and climate information.
            Include relevant details like temperature ranges, precipitation, and weather conditions.""",

            AgentType.WEB_SEARCH: """You are a research assistant specializing in finding and synthesizing information from web searches.
            Provide comprehensive, well-structured information from your search results.
            Always cite your sources and verify information accuracy.""",

            AgentType.GENERAL: """You are a helpful AI assistant capable of handling a wide variety of questions and tasks.
            Be conversational, informative, and adaptable to the user's needs.
            Provide thoughtful, accurate responses."""
        }

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompts[agent_type]),
            ("human", "{query}")
        ])

        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm

    async def process(self, query: str, context: Optional[Dict] = None) -> str:
        """Process the query with the specialized agent"""
        try:
            messages = self.prompt.format_messages(query=query)

            if context:
                context_msg = f"Context: {json.dumps(context, indent=2)}"
                messages.insert(-1, ("system", context_msg))

            if self.tools:
                response = await self.llm_with_tools.ainvoke(messages)

                # Check if the agent wants to use tools
                if response.tool_calls:
                    tool_results = []
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]

                        # Find and execute the tool
                        for tool in self.tools:
                            if tool.name == tool_name:
                                result = tool.invoke(tool_args)
                                tool_results.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                                break

                    # Continue the conversation with tool results
                    messages.extend([response] + tool_results)
                    final_response = await self.llm_with_tools.ainvoke(messages)
                    return final_response.content
                else:
                    return response.content
            else:
                response = await self.llm_with_tools.ainvoke(messages)
                return response.content

        except Exception as e:
            return f"Error processing query: {str(e)}"

# === LangGraph Nodes ===
async def classify_query_node(state: AgentState) -> Dict[str, Any]:
    """Node that classifies the user query"""
    query = state.get("query", "")

    if not query:
        return {"error": "No query provided", "classification": {"agent_type": "general", "confidence": 0.0}}

    classifier = QueryClassifier()
    classification = await classifier.classify(query)

    return {
        "classification": classification,
        "metadata": {"classification_time": datetime.now().isoformat()}
    }

async def route_query_node(state: AgentState) -> str:
    """Node that routes to the appropriate specialized agent"""
    classification = state.get("classification", {})
    agent_type = classification.get("agent_type", "general")

    # Return the next node name based on classification
    return f"agent_{agent_type}"

async def medical_agent_node(state: AgentState) -> Dict[str, Any]:
    """Medical specialist agent node"""
    query = state.get("query", "")
    agent = SpecializedAgent(AgentType.MEDICAL)

    response = await agent.process(query, state.get("classification"))

    return {
        "response": response,
        "agent_used": "medical",
        "metadata": {"agent_type": "medical", "timestamp": datetime.now().isoformat()}
    }

async def math_agent_node(state: AgentState) -> Dict[str, Any]:
    """Math specialist agent node"""
    query = state.get("query", "")
    agent = SpecializedAgent(AgentType.MATH)

    response = await agent.process(query, state.get("classification"))

    return {
        "response": response,
        "agent_used": "math",
        "metadata": {"agent_type": "math", "timestamp": datetime.now().isoformat()}
    }

async def physics_agent_node(state: AgentState) -> Dict[str, Any]:
    """Physics specialist agent node"""
    query = state.get("query", "")
    agent = SpecializedAgent(AgentType.PHYSICS)

    response = await agent.process(query, state.get("classification"))

    return {
        "response": response,
        "agent_used": "physics",
        "metadata": {"agent_type": "physics", "timestamp": datetime.now().isoformat()}
    }

async def weather_agent_node(state: AgentState) -> Dict[str, Any]:
    """Weather specialist agent node"""
    query = state.get("query", "")
    agent = SpecializedAgent(AgentType.WEATHER, tools=[get_weather_api])

    response = await agent.process(query, state.get("classification"))

    return {
        "response": response,
        "agent_used": "weather",
        "metadata": {"agent_type": "weather", "timestamp": datetime.now().isoformat()}
    }

async def web_search_agent_node(state: AgentState) -> Dict[str, Any]:
    """Web search specialist agent node"""
    query = state.get("query", "")
    agent = SpecializedAgent(AgentType.WEB_SEARCH, tools=[web_search, visit_webpage])

    response = await agent.process(query, state.get("classification"))

    return {
        "response": response,
        "agent_used": "web_search",
        "metadata": {"agent_type": "web_search", "timestamp": datetime.now().isoformat()}
    }

async def general_agent_node(state: AgentState) -> Dict[str, Any]:
    """General agent node"""
    query = state.get("query", "")
    agent = SpecializedAgent(AgentType.GENERAL)

    response = await agent.process(query, state.get("classification"))

    return {
        "response": response,
        "agent_used": "general",
        "metadata": {"agent_type": "general", "timestamp": datetime.now().isoformat()}
    }

async def format_response_node(state: AgentState) -> Dict[str, Any]:
    """Format the final response"""
    response = state.get("response", "No response generated")
    agent_used = state.get("agent_used", "unknown")
    classification = state.get("classification", {})

    formatted_response = {
        "query": state.get("query", ""),
        "response": response,
        "agent_used": agent_used,
        "confidence": classification.get("confidence", 0.0),
        "reasoning": classification.get("reasoning", ""),
        "timestamp": datetime.now().isoformat()
    }

    return {
        "messages": [AIMessage(content=json.dumps(formatted_response, indent=2))],
        "response": response
    }

# === Build the LangGraph ===
def build_agent_graph():
    """Build the agent system graph"""
    workflow = Graph()

    # Add nodes
    workflow.add_node("classify", classify_query_node)
    workflow.add_node("route", route_query_node)
    workflow.add_node("agent_medical", medical_agent_node)
    workflow.add_node("agent_math", math_agent_node)
    workflow.add_node("agent_physics", physics_agent_node)
    workflow.add_node("agent_weather", weather_agent_node)
    workflow.add_node("agent_web_search", web_search_agent_node)
    workflow.add_node("agent_general", general_agent_node)
    workflow.add_node("format_response", format_response_node)

    # Add edges
    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", "route")

    # Conditional routing from route node
    workflow.add_conditional_edges(
        "route",
        lambda x: x.get("classification", {}).get("agent_type", "general"),
        {
            "medical": "agent_medical",
            "math": "agent_math",
            "physics": "agent_physics",
            "weather": "agent_weather",
            "web_search": "agent_web_search",
            "general": "agent_general"
        }
    )

    # All agent nodes lead to format response
    for agent_node in ["agent_medical", "agent_math", "agent_physics", "agent_weather", "agent_web_search", "agent_general"]:
        workflow.add_edge(agent_node, "format_response")

    workflow.add_edge("format_response", END)

    return workflow.compile()

# === Main Agent System ===
class HomeAssistantSystem:
    """Main home assistant system using LangGraph"""

    def __init__(self):
        self.graph = build_agent_graph()
        self.conversation_history = []

    async def process_query(self, query: str, images: Optional[List[Union[str, Image.Image]]] = None) -> Dict[str, Any]:
        """Process a user query through the agent system"""

        # Process images if provided
        processed_images = []
        if images:
            for img in images:
                if isinstance(img, str):
                    if img.startswith(('http://', 'https://')):
                        response = requests.get(img)
                        processed_images.append(Image.open(io.BytesIO(response.content)))
                    else:
                        processed_images.append(Image.open(img))
                elif isinstance(img, Image.Image):
                    processed_images.append(img)

        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "images": processed_images if processed_images else None,
            "classification": None,
            "agent_used": None,
            "response": None,
            "error": None,
            "metadata": {"query_time": datetime.now().isoformat()}
        }

        try:
            # Process through the graph
            result = await self.graph.ainvoke(initial_state)

            # Parse the response
            response_content = result.get("messages", [])[-1].content
            try:
                response_data = json.loads(response_content)
            except json.JSONDecodeError:
                response_data = {
                    "query": query,
                    "response": response_content,
                    "agent_used": result.get("agent_used", "unknown"),
                    "confidence": 0.0,
                    "reasoning": "Error parsing response",
                    "timestamp": datetime.now().isoformat()
                }

            # Store in conversation history
            self.conversation_history.append(response_data)

            return response_data

        except Exception as e:
            error_response = {
                "query": query,
                "response": f"Error processing query: {str(e)}",
                "agent_used": "error",
                "confidence": 0.0,
                "reasoning": "System error occurred",
                "timestamp": datetime.now().isoformat()
            }

            self.conversation_history.append(error_response)
            return error_response

# === Example Usage ===
async def main():
    """Example usage of the LangGraph-based home assistant system"""
    print("🚀 Initializing LangGraph Home Assistant System...")

    system = HomeAssistantSystem()

    print("\n🤖 Home Assistant System Ready!\n" + "="*60)

    # Test queries
    test_queries = [
        "What are the symptoms of pneumonia?",
        "Solve for x: 3x^2 + 2x - 1 = 0",
        "What's the weather forecast for London tomorrow?",
        "Explain quantum entanglement",
        "Search for the latest news about artificial intelligence"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {query}")

        result = await system.process_query(query)

        print(f"🎯 Agent: {result['agent_used']} (confidence: {result['confidence']:.2f})")
        print(f"💭 Reasoning: {result['reasoning']}")
        print(f"💬 Response: {result['response'][:200]}{'...' if len(result['response']) > 200 else ''}")
        print("-" * 60)

if __name__ == "__main__":
    # Run the system
    asyncio.run(main())