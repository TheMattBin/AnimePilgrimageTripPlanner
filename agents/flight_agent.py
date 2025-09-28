from typing import Dict, List, Optional
import requests
import json
from datetime import datetime, timedelta
from core.config import Config

class FlightAgent:
    def __init__(self):
        self.api_key = Config.FLIGHT_API_KEY
    def search_flights(self, origin: str, destination: str, departure_date: str,
                      return_date: Optional[str] = None, passengers: int = 1) -> Dict:
        """
        Search for flights between origin and destination
        """
        try:
            if not self.api_key:
                return self._mock_flight_search(origin, destination, departure_date, return_date, passengers)

            url = f"https://api.aviationstack.com/v1/flights"
            params = {
                'access_key': self.api_key,
                'dep_iata': origin[:3].upper(),
                'arr_iata': destination[:3].upper(),
                'flight_date': departure_date,
                'limit': 10
            }

            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                return self._mock_flight_search(origin, destination, departure_date, return_date, passengers)

        except Exception as e:
            return self._mock_flight_search(origin, destination, departure_date, return_date, passengers)

    def _mock_flight_search(self, origin: str, destination: str, departure_date: str,
                           return_date: Optional[str] = None, passengers: int = 1) -> Dict:
        """
        Mock flight search for demonstration purposes
        """
        return {
            "data": [
                {
                    "flight": {
                        "iata": f"{origin[:3].upper()}{destination[:3].upper()}001",
                        "departure": {
                            "iata": origin[:3].upper(),
                            "airport": f"{origin} International Airport",
                            "scheduled": f"{departure_date}T08:00:00+00:00"
                        },
                        "arrival": {
                            "iata": destination[:3].upper(),
                            "airport": f"{destination} International Airport",
                            "scheduled": f"{departure_date}T12:00:00+00:00"
                        },
                        "price": 350 + (passengers - 1) * 280
                    }
                },
                {
                    "flight": {
                        "iata": f"{origin[:3].upper()}{destination[:3].upper()}002",
                        "departure": {
                            "iata": origin[:3].upper(),
                            "airport": f"{origin} International Airport",
                            "scheduled": f"{departure_date}T14:00:00+00:00"
                        },
                        "arrival": {
                            "iata": destination[:3].upper(),
                            "airport": f"{destination} International Airport",
                            "scheduled": f"{departure_date}T18:00:00+00:00"
                        },
                        "price": 420 + (passengers - 1) * 350
                    }
                }
            ]
        }

    def process_flight_query(self, query: str) -> str:
        """
        Process flight-related queries using the LLM
        """
        messages = [
            HumanMessage(content=f"""
            You are a flight search assistant. Analyze the following query and extract flight search parameters:

            Query: {query}

            Please extract and return in JSON format:
            - origin: Origin city/airport
            - destination: Destination city/airport
            - departure_date: Departure date (YYYY-MM-DD format)
            - return_date: Return date if mentioned (YYYY-MM-DD format)
            - passengers: Number of passengers (default to 1)
            - additional_requirements: Any special requirements mentioned
            """)
        ]

        response = self.llm.invoke(messages)

        try:
            import json
            import re

            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group())

                flights = self.search_flights(
                    origin=params.get('origin', ''),
                    destination=params.get('destination', ''),
                    departure_date=params.get('departure_date', ''),
                    return_date=params.get('return_date'),
                    passengers=params.get('passengers', 1)
                )

                return self._format_flight_results(flights)
            else:
                return "I couldn't parse the flight search parameters. Please provide more specific information about origin, destination, and dates."

        except Exception as e:
            return f"Error processing flight query: {str(e)}"

    def _format_flight_results(self, flight_data: Dict) -> str:
        """
        Format flight search results for display
        """
        if not flight_data or 'data' not in flight_data:
            return "No flights found for your search criteria."

        result = "[FLIGHTS] Available Flights\n\n"

        for i, flight in enumerate(flight_data['data'][:5], 1):
            flight_info = flight.get('flight', {})

            result += f"Flight {i}: {flight_info.get('iata', 'N/A')}\n"
            result += f"From: {flight_info.get('departure', {}).get('airport', 'N/A')}\n"
            result += f"To: {flight_info.get('arrival', {}).get('airport', 'N/A')}\n"
            result += f"Departure: {flight_info.get('departure', {}).get('scheduled', 'N/A')}\n"
            result += f"Arrival: {flight_info.get('arrival', {}).get('scheduled', 'N/A')}\n"
            result += f"Price: ${flight_info.get('price', 'N/A')}\n\n"

        return result