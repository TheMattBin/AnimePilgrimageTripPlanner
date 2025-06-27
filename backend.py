import re
import datetime
import requests
from requests.exceptions import RequestException

from markdownify import markdownify
from PIL import Image

import torch
from smolagents import tool
from smolagents import DuckDuckGoSearchTool, WebSearchTool
from smolagents import CodeAgent, TransformersModel, ToolCallingAgent
from datetime import datetime

@tool
def get_weather_api(location: str, date: str) -> str:
    """
    Get weather forecast for a given location and date (YYYY-MM-DD).

    Args:
    location: The location to check the weather.
    date: The date in (YYYY-MM-DD) to check the weather.

    Returns:
        The weather condition in the requested location.
    """
    # Validate date format
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD."

    # Geocode location (example using OpenStreetMap Nominatim)
    import requests
    geo_resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": location, "format": "json", "limit": 1},
        headers={"User-Agent": "smolagents-example"}
    )
    geo_data = geo_resp.json()
    if not geo_data:
        return f"Could not find location: {location}"
    lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]

    # Call Open-Meteo API for daily forecast
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

@tool
def visit_webpage(url: str) -> str:
    """Visits a webpage at the given URL and returns its content as a markdown string.

    Args:
        url: The URL of the webpage to visit.

    Returns:
        The content of the webpage converted to Markdown, or an error message if the request fails.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Convert the HTML content to Markdown
        markdown_content = markdownify(response.text).strip()

        # Remove multiple line breaks
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        return markdown_content

    except RequestException as e:
        return f"Error fetching the webpage: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

# === Configuration ===
MODELS = {
    "router": "unsloth/Qwen3-4B-bnb-4bit",
    # "medical": "google/medgemma-4b-it",
    "medical": "moondream/moondream-2b-2025-04-14-4bit",
    "general": "Qwen/Qwen3-0.6B"
}

# === Model Initialization ===
def create_smol_model(model_id):
    return TransformersModel(
        model_id=model_id,
        device_map="auto",
        trust_remote_code=True,
        # load_in_4bit=True,
    )

model = create_smol_model(MODELS["router"])


# Weather agent
weather_agent = ToolCallingAgent(tools=[get_weather_api], model=model, name="weather", description="Fetches weather data.")
web_agent = ToolCallingAgent(
    tools=[WebSearchTool(), visit_webpage],
    model=model,
    max_steps=10,
    name="web_search_agent",
    description="Runs web searches for you.",
)


manager_agent = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[weather_agent, web_agent],
    additional_authorized_imports=["time", "numpy", "pandas"],
)

# === Example Usage ===
if __name__ == "__main__":
    result = manager_agent.run("Plan a surf trip in Bali next week.")
    print(result)
