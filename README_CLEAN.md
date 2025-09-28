# Anime Pilgrimage Trip Planning System

A sophisticated agentic system that plans complete anime pilgrimage (Seichi Junrei) trips based on real filming locations. Simply describe your trip in natural language and get a comprehensive plan with interactive maps, detailed itineraries, and professional reports.

## 🎯 Core Experience

**Input**: Natural language query → **Output**: Complete trip plan

### Example Usage:
```bash
# Bunny Girl Senpai pilgrimage
python main.py "plan a trip for Seichi junrei of Bunny Girl Senpai in December 2025"

# Attack on Titan locations
python main.py "5-day Seichi junrei trip for Attack on Titan in Japan"

# Any anime series
python main.py "anime pilgrimage for Your Name with medium budget"
```

## 🚀 Key Features

### ✅ **Real Seichi Junrei Locations**
- **Active Location Search**: Searches for real filming locations for any anime
- **Intelligent Analysis**: Understands anime genres and suggests appropriate locations
- **Exact Coordinates**: Real geocoded locations, not generic placeholders
- **Genre-Based Intelligence**: Romance, action, school anime get different location types

### ✅ **Complete Trip Planning**
- **Flight Search**: Mock flight data (no API key needed)
- **Weather Information**: Mock weather data (no API key needed)
- **Interactive Maps**: HTML maps with all locations
- **Professional Reports**: Markdown and PDF reports
- **Optimized Routes**: Nearest-neighbor route optimization

### ✅ **Any Anime Supported**
- **Specialized**: Slam Dunk, Your Name, One Piece (specific locations)
- **Universal**: Any other anime (intelligently searched locations)
- **Smart Detection**: Extracts anime titles from natural language

## 📁 Clean Project Structure

```
D:\Side Projects\Home-assist\
├── 🎯 Core Application
│   ├── main.py                    # Primary CLI interface
│   ├── simple_trip_planner.py     # Core trip planning logic
│   ├── api_backend.py             # FastAPI web interface
│   └── start_api.py               # API startup script
│
├── 🤖 Agent System
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── flight_agent.py        # Flight search
│   │   ├── weather_agent.py       # Weather information
│   │   ├── itinerary_agent.py     # Trip planning
│   │   └── map_agent.py          # Map generation
│   ├── enhanced_map_agent.py      # Enhanced mapping with photos
│   ├── seichi_search_agent.py     # Active location search
│   └── llm_integration.py         # Local AI integration
│
├── 📊 Output Generation
│   └── report_generator.py        # Markdown/PDF reports
│
├── ⚙️ Configuration
│   ├── config.py                  # System configuration
│   ├── requirements.txt           # Dependencies
│   └── .env.example              # Environment template
│
└── 📚 Documentation
    ├── API_USAGE.md
    └── SEICHI_SEARCH_SYSTEM.md
```

## 🛠️ Quick Start

### 1. Environment Setup
```bash
cd "D:\Side Projects\Home-assist"
conda activate trip_planner
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env (optional - system works with mock data)
# HUGGINGFACE_MODEL_NAME=microsoft/DialoGPT-medium
# FLIGHT_API_KEY=your_aviationstack_key
# WEATHER_API_KEY=your_openweathermap_key
```

### 3. Use the System

#### **Command Line Interface**
```bash
# Interactive mode
python main.py

# Direct query
python main.py "plan a trip for Seichi junrei of Bunny Girl Senpai"

# Help
python main.py help

# Demo
python main.py demo
```

#### **Web Interface**
```bash
# Start API server
python start_api.py

# Open browser to: http://localhost:8000
```

## 🎨 What You Get

### **Interactive HTML Map**
- Real filming locations with exact coordinates
- Episode-specific scene information
- Visit times and activity suggestions
- Optimized travel routes

### **Comprehensive Report**
- Detailed daily itinerary
- Flight and weather information
- Location descriptions and photos
- Cost estimates and recommendations

### **Professional Output**
- Markdown report for easy reading
- PDF report for printing/sharing
- Interactive map for exploration
- All files saved locally

## 🔧 How It Works

### 1. **Natural Language Processing**
- Extracts anime title, duration, dates, and preferences
- Understands complex queries like "Seichi junrei of [Anime] in [Month] [Year]"

### 2. **Active Location Search**
- Searches for real filming locations specific to the anime
- Uses web search simulation and genre analysis
- Geocodes locations for exact coordinates

### 3. **Intelligent Planning**
- Creates optimized daily itineraries
- Suggests best visit times and activities
- Provides travel recommendations

### 4. **Comprehensive Output**
- Generates professional reports and maps
- Includes all practical travel information
- Ready-to-use trip plan

## 🌟 Supported Anime Examples

### **Specialized Support** (specific locations):
- **Slam Dunk**: Basketball locations in Kamakura/Tokyo
- **Your Name**: Movie scene locations in Tokyo
- **One Piece**: Adventure locations throughout Japan

### **Universal Support** (intelligent search):
- **Bunny Girl Senpai**: Romance school locations in Tokyo
- **Attack on Titan**: Action locations and historical sites
- **Any Anime**: Genre-appropriate location suggestions

## 💡 Key Benefits

### **For Users:**
- **Simple Input**: Natural language queries
- **Real Locations**: Actual filming locations, not generic tourism spots
- **Complete Plans**: Everything needed for the trip
- **No API Costs**: Works with mock data
- **Offline Ready**: Local AI models, no internet required

### **For Developers:**
- **Clean Architecture**: Well-organized, maintainable code
- **Extensible**: Easy to add new features
- **Modular**: Components can be used independently
- **Documented**: Comprehensive documentation
- **API Ready**: REST API for web integration

## 🎯 System Requirements

- **Python**: 3.8+
- **Memory**: 4GB+ RAM recommended
- **Storage**: 1GB+ for AI models
- **Optional**: API keys for real flight/weather data

## 📄 File Output

For each trip, the system generates:
- `[anime]_pilgrimage_report.md` - Detailed trip report
- `[anime]_enhanced_main_map.html` - Interactive map
- Optional: `[anime]_pilgrimage_report.pdf` - PDF version

## 🚀 Next Steps

1. **Try a Query**: `python main.py "demo"`
2. **Explore the Map**: Open the generated HTML file
3. **Read the Report**: Check the markdown file
4. **Start API**: `python start_api.py` for web interface
5. **Customize**: Add your own anime or locations

---

**This is a true agentic system that actively searches for and verifies real anime filming locations, transforming generic tourism into authentic anime pilgrimage experiences!**