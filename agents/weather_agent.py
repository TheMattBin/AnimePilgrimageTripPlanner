from typing import Dict, List, Optional
import requests
import json
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_community.llms import HuggingFaceEndpoint
from config import Config

class WeatherAgent:
    def __init__(self):
        self.llm = HuggingFaceEndpoint(
            repo_id=Config.HUGGINGFACE_MODEL_NAME,
            task="text-generation",
            max_length=1000,
            temperature=0.7,
        )
        self.api_key = Config.WEATHER_API_KEY

    @tool
    def get_current_weather(self, city: str, country: Optional[str] = None) -> Dict:
        """
        Get current weather for a city
        """
        try:
            if not self.api_key:
                return self._mock_weather_data(city, country)

            base_url = "http://api.openweathermap.org/data/2.5/weather"
            location = f"{city},{country}" if country else city

            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'
            }

            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                return self._mock_weather_data(city, country)

        except Exception as e:
            return self._mock_weather_data(city, country)

    @tool
    def get_forecast(self, city: str, country: Optional[str] = None, days: int = 7) -> Dict:
        """
        Get weather forecast for multiple days
        """
        try:
            if not self.api_key:
                return self._mock_forecast_data(city, country, days)

            base_url = "http://api.openweathermap.org/data/2.5/forecast"
            location = f"{city},{country}" if country else city

            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': days * 8  # 8 forecasts per day (3-hour intervals)
            }

            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                return self._mock_forecast_data(city, country, days)

        except Exception as e:
            return self._mock_forecast_data(city, country, days)

    def _mock_weather_data(self, city: str, country: Optional[str] = None) -> Dict:
        """
        Mock weather data for demonstration purposes
        """
        import random

        weather_conditions = [
            {"main": "Clear", "description": "clear sky", "icon": "01d"},
            {"main": "Clouds", "description": "few clouds", "icon": "02d"},
            {"main": "Clouds", "description": "scattered clouds", "icon": "03d"},
            {"main": "Rain", "description": "light rain", "icon": "10d"},
            {"main": "Sun", "description": "sunny", "icon": "01d"}
        ]

        condition = random.choice(weather_conditions)

        return {
            "name": city,
            "sys": {"country": country or "Unknown"},
            "main": {
                "temp": round(random.uniform(15, 35), 1),
                "feels_like": round(random.uniform(15, 35), 1),
                "humidity": random.randint(40, 90),
                "pressure": random.randint(1000, 1020)
            },
            "weather": [condition],
            "wind": {
                "speed": round(random.uniform(0, 15), 1),
                "deg": random.randint(0, 360)
            }
        }

    def _mock_forecast_data(self, city: str, country: Optional[str] = None, days: int = 7) -> Dict:
        """
        Mock forecast data for demonstration purposes
        """
        import random

        forecast_data = []
        for i in range(days * 8):
            weather_conditions = [
                {"main": "Clear", "description": "clear sky", "icon": "01d"},
                {"main": "Clouds", "description": "few clouds", "icon": "02d"},
                {"main": "Rain", "description": "light rain", "icon": "10d"}
            ]

            condition = random.choice(weather_conditions)

            forecast_data.append({
                "dt": datetime.now().timestamp() + i * 3 * 3600,
                "main": {
                    "temp": round(random.uniform(15, 35), 1),
                    "humidity": random.randint(40, 90)
                },
                "weather": [condition],
                "wind": {"speed": round(random.uniform(0, 15), 1)}
            })

        return {
            "city": {"name": city, "country": country or "Unknown"},
            "list": forecast_data
        }

    def process_weather_query(self, query: str) -> str:
        """
        Process weather-related queries using the LLM
        """
        messages = [
            HumanMessage(content=f"""
            You are a weather information assistant. Analyze the following query and extract weather search parameters:

            Query: {query}

            Please extract and return in JSON format:
            - cities: List of cities to check weather for
            - country: Country if specified (can be null)
            - date_type: "current" or "forecast"
            - days: Number of days for forecast (default 7)
            - specific_requirements: Any specific weather requirements mentioned
            """)
        ]

        response = self.llm.invoke(messages)

        try:
            import json
            import re

            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group())

                cities = params.get('cities', [])
                country = params.get('country')
                date_type = params.get('date_type', 'current')
                days = params.get('days', 7)

                if not cities:
                    return "Please specify which cities you'd like weather information for."

                result = f"🌤️ **Weather Information**\n\n"

                for city in cities:
                    if date_type == "current":
                        weather_data = self.get_current_weather(city, country)
                        result += self._format_current_weather(weather_data)
                    else:
                        forecast_data = self.get_forecast(city, country, days)
                        result += self._format_forecast(forecast_data, days)

                    result += "\n"

                return result
            else:
                return "I couldn't parse the weather query. Please specify the cities you want weather information for."

        except Exception as e:
            return f"Error processing weather query: {str(e)}"

    def _format_current_weather(self, weather_data: Dict) -> str:
        """
        Format current weather data for display
        """
        if not weather_data or 'main' not in weather_data:
            return "Weather data not available."

        city = weather_data.get('name', 'Unknown')
        country = weather_data.get('sys', {}).get('country', '')
        temp = weather_data['main'].get('temp', 'N/A')
        feels_like = weather_data['main'].get('feels_like', 'N/A')
        humidity = weather_data['main'].get('humidity', 'N/A')
        pressure = weather_data['main'].get('pressure', 'N/A')
        wind_speed = weather_data.get('wind', {}).get('speed', 'N/A')
        description = weather_data.get('weather', [{}])[0].get('description', 'N/A')

        result = f"**{city}, {country}**\n"
        result += f"Temperature: {temp}°C (feels like {feels_like}°C)\n"
        result += f"Condition: {description.capitalize()}\n"
        result += f"Humidity: {humidity}%\n"
        result += f"Pressure: {pressure} hPa\n"
        result += f"Wind Speed: {wind_speed} m/s\n"

        return result

    def _format_forecast(self, forecast_data: Dict, days: int) -> str:
        """
        Format forecast data for display
        """
        if not forecast_data or 'list' not in forecast_data:
            return "Forecast data not available."

        city = forecast_data.get('city', {}).get('name', 'Unknown')
        country = forecast_data.get('city', {}).get('country', '')

        result = f"**{days}-Day Forecast for {city}, {country}**\n"

        daily_forecasts = {}
        for item in forecast_data['list'][:days * 8]:
            date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
            if date not in daily_forecasts:
                daily_forecasts[date] = {
                    'temps': [],
                    'conditions': [],
                    'humidity': []
                }
            daily_forecasts[date]['temps'].append(item['main']['temp'])
            daily_forecasts[date]['conditions'].append(item['weather'][0]['description'])
            daily_forecasts[date]['humidity'].append(item['main']['humidity'])

        for date, data in list(daily_forecasts.items())[:days]:
            avg_temp = sum(data['temps']) / len(data['temps'])
            avg_humidity = sum(data['humidity']) / len(data['humidity'])
            most_common_condition = max(set(data['conditions']), key=data['conditions'].count)

            result += f"\n**{date}**\n"
            result += f"Avg Temperature: {avg_temp:.1f}°C\n"
            result += f"Condition: {most_common_condition.capitalize()}\n"
            result += f"Avg Humidity: {avg_humidity:.0f}%\n"

        return result

    def get_best_travel_days(self, cities: List[str], country: Optional[str] = None,
                           preferred_temp_range: tuple = (20, 28)) -> Dict:
        """
        Analyze weather forecasts to recommend best travel days
        """
        best_days = {}

        for city in cities:
            forecast_data = self.get_forecast(city, country, 10)

            if 'list' in forecast_data:
                daily_scores = {}
                for item in forecast_data['list'][:10 * 8]:
                    date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
                    temp = item['main']['temp']
                    condition = item['weather'][0]['main']

                    if date not in daily_scores:
                        daily_scores[date] = {'temps': [], 'good_conditions': 0, 'total_conditions': 0}

                    daily_scores[date]['temps'].append(temp)

                    if condition in ['Clear', 'Clouds']:
                        daily_scores[date]['good_conditions'] += 1
                    daily_scores[date]['total_conditions'] += 1

                for date, scores in daily_scores.items():
                    avg_temp = sum(scores['temps']) / len(scores['temps'])
                    condition_ratio = scores['good_conditions'] / scores['total_conditions']

                    if preferred_temp_range[0] <= avg_temp <= preferred_temp_range[1]:
                        score = (condition_ratio * 0.7) + (0.3 if avg_temp < 25 else 0.2)
                    else:
                        score = condition_ratio * 0.5

                    best_days[f"{city}_{date}"] = score

        return dict(sorted(best_days.items(), key=lambda x: x[1], reverse=True))