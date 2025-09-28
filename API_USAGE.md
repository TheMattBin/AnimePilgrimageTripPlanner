# Anime Pilgrimage Trip Planning API

## Overview
This FastAPI backend provides a web interface for the Anime Pilgrimage Trip Planning System. It allows users to plan trips through a web browser or API calls.

## Features
- **Web Interface**: User-friendly HTML form for trip planning
- **REST API**: Programmatic access to trip planning functionality
- **File Downloads**: Access to generated reports and interactive maps
- **Health Checks**: Monitor system status and component availability

## Quick Start

### 1. Start the API Server
```bash
cd "D:\Side Projects\Home-assist"
conda activate trip_planner
python start_api.py
```

### 2. Access the Web Interface
Open your browser and go to: http://localhost:8000

### 3. Use the API
The API provides several endpoints:

#### Web Interface
- `GET /` - HTML form interface
- `GET /health` - System health check
- `GET /api-info` - API documentation

#### API Endpoints
- `POST /plan-trip` - Plan a trip
- `GET /download/{filename}` - Download generated files

## API Usage Examples

### Plan a Trip (Python)
```python
import requests

url = "http://localhost:8000/plan-trip"
data = {
    "query": "7-days trip from Taiwan to Japan for Slam Dunk pilgrimage",
    "trip_duration": 7,
    "start_date": "2024-12-01",
    "output_format": "both"
}

response = requests.post(url, json=data)
result = response.json()

if result["success"]:
    print("Trip planned successfully!")
    print("Reports:", result["report_files"])
    print("Map:", result["map_file"])
else:
    print("Error:", result["error"])
```

### Plan a Trip (curl)
```bash
curl -X POST "http://localhost:8000/plan-trip" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "5-day trip to Tokyo for Your Name pilgrimage",
    "trip_duration": 5,
    "output_format": "both"
  }'
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Request Format

### POST /plan-trip
```json
{
  "query": "string - Trip description",
  "trip_duration": "integer - Number of days (optional, default: 7)",
  "start_date": "string - Start date YYYY-MM-DD (optional)",
  "output_format": "string - 'markdown', 'pdf', or 'both' (optional, default: 'both')"
}
```

## Response Format

### Success Response
```json
{
  "success": true,
  "message": "Trip planned successfully!",
  "trip_data": { ... },
  "report_files": {
    "markdown": "static/report.md",
    "pdf": "static/report.pdf"
  },
  "map_file": "static/map.html"
}
```

### Error Response
```json
{
  "success": false,
  "message": "Trip planning failed",
  "error": "Error message"
}
```

## Supported Anime Series
- Slam Dunk
- Your Name
- One Piece

## Generated Files
- **Markdown Report**: Detailed trip itinerary
- **PDF Report**: Professional formatted report
- **Interactive Map**: HTML map with all locations

## System Requirements
- Python 3.8+
- Conda environment `trip_planner`
- All requirements in `requirements.txt`

## API Features
- No API keys required (uses mock data)
- Local AI models (no external costs)
- Interactive maps with OpenStreetMap
- Comprehensive trip planning with route optimization
- Weather and flight information (mock data)

## Free API Options
If you want to use real APIs instead of mock data:

### Flight APIs
- **AviationStack**: 500 requests/month free
  - Register: https://aviationstack.com/
  - Set `FLIGHT_API_KEY` in `.env`

### Weather APIs
- **OpenWeatherMap**: 1000 requests/day free
  - Register: https://openweathermap.org/api
  - Set `WEATHER_API_KEY` in `.env`

## Deployment
The API can be deployed to any cloud platform that supports Python:
- AWS Lambda
- Google Cloud Functions
- Azure Functions
- DigitalOcean App Platform
- Heroku

## Security Notes
- CORS is enabled for development (allow all origins)
- File uploads are not supported (potential security risk)
- All generated files are served from `/static` directory
- Consider adding authentication for production use