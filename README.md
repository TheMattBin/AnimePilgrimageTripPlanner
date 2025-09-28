# Multi-Agent Trip Planning System

A comprehensive AI-powered trip planning system specializing in Anime Pilgrimage (聖地巡礼) travel using LangGraph and local Hugging Face models.

## Features

✈️ **Flight Search Agent**
- Real-time flight search and booking assistance
- Mock data support for demonstration
- Price comparison and scheduling

🌤️ **Weather Agent**
- Current weather conditions
- 10-day weather forecasts
- Best travel day recommendations based on weather preferences

🗺️ **Itinerary Planning Agent**
- Customizable travel plans
- Anime pilgrimage location integration
- Budget-based recommendations
- Activity suggestions based on interests

🎌 **Anime Pilgrimage Support**
- Slam Dunk locations (Kamakura, Tokyo)
- Your Name locations (Shinjuku, Tokyo)
- One Piece locations (Tokyo Tower, Odaiba)
- Interactive mapping with coordinates

🗺️ **Map Integration**
- Interactive travel maps using Folium
- Route optimization
- Distance calculations
- Location visualization

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Home-assist
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Create a `.env` file with the following:

```env
HUGGINGFACE_MODEL_NAME="microsoft/DialoGPT-medium"
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
FLIGHT_API_KEY=your_flight_api_key_here
WEATHER_API_KEY=your_weather_api_key_here
OPENSTREETMAP_USER_AGENT=trip_planner_app
NOMINATIM_EMAIL=your_email@example.com
```

## Usage

### Interactive Mode

Run the main application:
```bash
python main.py
```

### Command Line Mode

Plan a specific trip:
```bash
python main.py "7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Slam Dunk"
```

### Example Queries

- `"7-days trip plan from Taiwan to Japan and wanna enjoy Seichi junrei of Slam Dunk"`
- `"Plan a 5-day trip to Tokyo focusing on Your Name locations"`
- `"10-day Japan trip with One Piece pilgrimage, medium budget"`
- `"3-day Kyoto trip with cultural sites and traditional food experience"`

## System Architecture

### Multi-Agent System

The system uses LangGraph to coordinate multiple specialized agents:

1. **Query Parser Agent**: Analyzes user queries and extracts parameters
2. **Flight Search Agent**: Handles flight searches and booking information
3. **Weather Agent**: Provides weather forecasts and recommendations
4. **Itinerary Agent**: Creates detailed travel plans with anime pilgrimage integration
5. **Map Agent**: Creates interactive maps and route optimization

### Local Model Support

The system uses local Hugging Face models for privacy and offline capability:
- Microsoft DialoGPT (default)
- TinyLlama (lightweight option)
- Custom model support

### Supported Anime Pilgrimage

#### Slam Dunk
- **Kamakura High School** (Shohoku High School)
- **Tokyo Metropolitan Gymnasium** (Inter-high tournament)
- **Enoshima Electric Railway**

#### Your Name (君の名は。)
- **Shinjuku Gyoen** (Meeting park)
- **Suga Shrine Steps** (Iconic staircase)
- **Shinjuku Station** (Train station)

#### One Piece
- **Tokyo Tower** (Marianne inspiration)
- **Odaiba** (Statue of Liberty)

## Output Example

The system provides comprehensive trip plans including:

- ✈️ Flight options and prices
- 🌤️ Weather forecasts and best travel days
- 🗺️ Detailed daily itineraries with anime locations
- 🗺️ Interactive HTML maps
- 📊 Travel statistics (distances, times)
- 💡 Personalized recommendations

## Map Features (100% Free!)

- **Interactive HTML maps** with location markers using OpenStreetMap
- **Multiple tile layers** (OpenStreetMap, Stamen Terrain, CartoDB)
- **Color-coded categories** (anime, food, hotels, transport)
- **Route optimization** between pilgrimage sites
- **Distance calculations** and travel time estimates
- **Nearby places search** using Overpass API
- **Export capabilities** for offline use

## Free Map APIs Used

1. **OpenStreetMap Nominatim** - Free geocoding (address to coordinates)
2. **OpenStreetMap Overpass API** - Free nearby places search
3. **Folium** - Free interactive map library
4. **Geopy** - Free geocoding library

No Google Maps API required! All mapping features work completely free.

## Customization

### Adding New Anime Locations

Edit `agents/itinerary_agent.py` to add new pilgrimage locations:

```python
self.seichi_junrei_locations["New Anime"] = {
    "Region": {
        "Location Name": {
            "real_location": "Real place name",
            "address": "Full address",
            "description": "Description of the location",
            "coordinates": [latitude, longitude],
            "activities": ["Activity 1", "Activity 2"]
        }
    }
}
```

### Adding New Agents

Create new agent classes in the `agents/` directory and integrate them into the LangGraph workflow in `trip_planner_graph.py`.

## Requirements

- Python 3.8+
- PyTorch (for local model inference)
- Internet connection (for API calls and map tiles)
- Sufficient RAM for model loading (2GB+ recommended)

## License

This project is for educational and personal use. Please ensure compliance with terms of service for any external APIs used.

## Contributing

Feel free to submit issues and enhancement requests!

## Support

For issues and questions, please check the documentation or create an issue in the repository.