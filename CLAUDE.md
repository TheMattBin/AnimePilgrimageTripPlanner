# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a home assistant project using a multi-agent architecture with specialized agents for different domains. The system has evolved from smolagents to LangGraph for more advanced agent orchestration and state management.

## Architecture

### Primary System: LangGraph-based (langgraph_backend.py)
- Advanced stateful multi-agent system using LangGraph
- Sophisticated query routing with conditional edges
- Tool integration for specialized agents
- Error handling and fallback mechanisms
- Support for multimodal inputs (text + images)

### Legacy Systems
- **backend.py**: Original smolagents implementation (deprecated)
- **mcp_backend.py**: Multimodal system without LangGraph (deprecated)

## Key Dependencies

- **langgraph**: Agent orchestration framework
- **langchain**: LLM framework and tools
- **langchain-openai**: OpenAI API integration
- **langchain-community**: Community tools and integrations
- **transformers**: Hugging Face model library
- **Pillow**: Image processing
- **torch**: PyTorch for model inference
- **requests**: HTTP requests for APIs
- **markdownify**: HTML to markdown conversion

## Development Commands

### Running the LangGraph System
```bash
python langgraph_backend.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Environment Setup
Copy `.env.example` to `.env` and configure your OpenAI API key:
```bash
cp .env.example .env
```

## LangGraph Architecture

### Graph Structure
1. **START** → **classify** → **route** → **specialized_agents** → **format_response** → **END**
2. Conditional routing based on query classification
3. Each agent node can call tools if needed

### Agent Types
- **Medical**: Health, medicine, symptoms, treatments
- **Math**: Mathematical problems, calculations, equations
- **Physics**: Physics concepts, mechanics, thermodynamics
- **Weather**: Weather forecasts, climate information
- **Web Search**: Research, current events, web-based information
- **General**: General conversation and queries

### State Management
- **AgentState**: TypedDict containing messages, query, images, classification, response
- **Conversation History**: Maintained across multiple queries
- **Error Handling**: Fallback mechanisms for classification failures

### Tool Integration
- **get_weather_api**: Weather forecast from Open-Meteo
- **visit_webpage**: Web page content extraction
- **web_search**: DuckDuckGo search integration

## Code Structure

### langgraph_backend.py
- **QueryClassifier**: LLM-based query classification
- **SpecializedAgent**: Base class for domain-specific agents
- **LangGraph Nodes**: Individual processing nodes
- **HomeAssistantSystem**: Main orchestration class
- **Agent Definitions**: Medical, Math, Physics, Weather, Web Search, General

### Key Classes
- **AgentState**: State management for the graph
- **QueryClassifier**: Routes queries to appropriate agents
- **SpecializedAgent**: Handles domain-specific queries
- **HomeAssistantSystem**: Main system interface

## Configuration

### Environment Variables
- **OPENAI_API_KEY**: Required for OpenAI API access
- **DEFAULT_MODEL**: Default model for agents (gpt-3.5-turbo)
- **ROUTER_MODEL**: Model for query classification

### Model Configuration
- Uses OpenAI models by default
- Configurable for different model providers
- Tool binding for agents that require external APIs

## Key Patterns

1. **Graph-based Orchestration**: Uses LangGraph for complex workflows
2. **Conditional Routing**: Dynamic agent selection based on query content
3. **Tool Integration**: Agents can call external APIs and tools
4. **State Management**: Typed state with conversation history
5. **Error Handling**: Fallback classification and error recovery
6. **Modular Design**: Easy to add new agents and tools

## Development Notes

- The LangGraph implementation is the current primary system
- Legacy files (backend.py, mcp_backend.py) are maintained for reference
- New agents can be added by extending the SpecializedAgent class
- Tools are decorated with @tool and bound to appropriate agents
- The system supports both text and multimodal queries