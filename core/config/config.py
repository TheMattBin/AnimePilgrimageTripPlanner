import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    HUGGINGFACE_MODEL_NAME: str = os.getenv("HUGGINGFACE_MODEL_NAME", "microsoft/DialoGPT-medium")
    HUGGINGFACE_API_KEY: Optional[str] = os.getenv("HUGGINGFACE_API_KEY")
    FLIGHT_API_KEY: Optional[str] = os.getenv("FLIGHT_API_KEY")
    WEATHER_API_KEY: Optional[str] = os.getenv("WEATHER_API_KEY")
    OPENSTREETMAP_USER_AGENT: str = os.getenv("OPENSTREETMAP_USER_AGENT", "trip_planner_app")
    NOMINATIM_EMAIL: Optional[str] = os.getenv("NOMINATIM_EMAIL")

    @classmethod
    def validate_config(cls):
        required_keys = [
            "HUGGINGFACE_MODEL_NAME"
        ]

        for key in required_keys:
            if not getattr(cls, key):
                raise ValueError(f"Missing required configuration: {key}")