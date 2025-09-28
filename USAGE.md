# Anime Pilgrimage Trip Planner - Usage Guide

## 🎌 Quick Start

The main script allows you to plan anime pilgrimage trips using natural language queries.

### Basic Usage

```bash
# Plan a trip with natural language
python main.py "plan a 7-day trip in coming dec to have anime Pilgrimage for Rascal Does Not Dream of Santa Claus"

# Another example
python main.py "5-day trip to Japan for Demon Slayer pilgrimage"

# Your Name example
python main.py "7-day trip to Japan for Your Name anime pilgrimage"
```

### Interactive Mode

```bash
# Start interactive mode
python main.py --interactive

# or short form
python main.py -i
```

### Advanced Options

```bash
# Show detailed planning process
python main.py "your query" --verbose

# or short form
python main.py "your query" -v

# Get JSON output
python main.py "your query" --output json

# Generate PDF report
python main.py "your query" --output pdf

# Generate PDF with custom filename
python main.py "your query" --output pdf --pdf-filename "my_trip.pdf"

# Show console output AND generate PDF
python main.py "your query" --both
```

## 🎯 Examples

### Anime Title Recognition
The system can identify anime titles from natural language:

- ✅ "Bunny Girl Senpai pilgrimage"
- ✅ "Demon Slayer filming locations"
- ✅ "Your Name anime trip"
- ✅ "Attack on Titan seichi junrei"
- ✅ "Weathering with You locations"

### Trip Features
Each planned trip includes:

- **Flight Options** - Multiple flight choices with prices
- **Weather Information** - Current conditions and forecasts
- **Daily Itinerary** - Day-by-day activity plans
- **Anime Locations** - Real pilgrimage sites with coordinates
- **Maps** - Interactive HTML maps (when available)
- **Recommendations** - Personalized travel tips
- **PDF Reports** - Detailed, printable trip documents

## 📊 What Happens Behind the Scenes

1. **Query Analysis** - AI extracts anime title and trip parameters
2. **Location Search** - Searches multiple sources for anime pilgrimage sites
3. **Data Integration** - Combines web scraping and API data
4. **Trip Planning** - Creates comprehensive itinerary
5. **Output Generation** - Formats results for easy reading

## 🌐 Data Sources

- **animepilgrimage.com** - Web scraping for location data
- **anitabi.cn** - API integration with bangumi IDs
- **Wikidata** - SPARQL queries for filming locations
- **Fallback Data** - Simulated data when external sources fail

## 🔧 Requirements

- Python 3.8+
- Conda environment with `trip_planner` activated
- Dependencies from `requirements.txt`

## 🎪 Tips for Best Results

- Use specific anime titles when possible
- Mention "pilgrimage", "seichi junrei", or "filming locations" for better recognition
- Include trip duration and destination preferences
- The system works best with popular anime titles

## 🚀 Example Commands to Try

```bash
# Try these popular anime:
python main.py "3-day trip for Slam Dunk pilgrimage in Japan"
python main.py "week-long trip to visit Attack on Titan locations"
python main.py "plan a trip for Steins;Gate anime pilgrimage"
python main.py "10-day journey to Japan for Fullmetal Alchemist sites"

# PDF generation examples:
python main.py "5-day Your Name pilgrimage" --output pdf
python main.py "Demon Slayer trip" --both --pdf-filename "demon_slayer.pdf"
```