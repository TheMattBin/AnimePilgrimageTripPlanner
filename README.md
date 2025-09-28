# Anime Pilgrimage Trip Planning System

**Natural Language Query → Complete Trip Plan**

A sophisticated agentic system that plans complete anime pilgrimage (Seichi Junrei) trips by searching for real filming locations. Simply describe your trip in natural language and get interactive maps, detailed itineraries, and professional reports.

## 🚀 Quick Start

```bash
# Try it now
python main.py "plan a trip for Seichi junrei of Bunny Girl Senpai in December 2025"

# Web interface
python start_api.py  # Open http://localhost:8000

# Help
python main.py help
```

## ✨ What You Get

- **Real Filming Locations**: Searches for actual anime scene locations
- **Interactive Maps**: HTML maps with exact coordinates and routes
- **Complete Reports**: Markdown/PDF itineraries with all travel details
- **Any Anime**: Supports every anime series with intelligent location search
- **No API Costs**: Works with local AI models and mock data

## 🎯 Example Usage

```bash
# Bunny Girl Senpai pilgrimage
python main.py "Seichi junrei of Bunny Girl Senpai"

# Attack on Titan locations
python main.py "5-day Attack on Titan trip in Japan"

# Your Name romance tour
python main.py "romantic pilgrimage for Your Name anime"

# Any anime series
python main.py "anime pilgrimage for [Your Favorite Anime]"
```

## 📁 Clean Architecture

- **10 Core Python Files**: No duplicates or legacy code
- **Agent System**: Modular agents for flights, weather, maps, etc.
- **Local AI**: HuggingFace models run locally
- **Web Ready**: FastAPI backend included
- **Extensible**: Easy to add new features

## 🔧 System Requirements

- **Python**: 3.8+
- **Memory**: 4GB+ RAM recommended
- **Storage**: 1GB+ for AI models
- **Optional**: API keys for real flight/weather data

## 🌟 Key Features

- **Active Location Search**: Finds real filming locations for any anime
- **Intelligent Analysis**: Understands anime genres and themes
- **Route Optimization**: Efficient travel routes between locations
- **Professional Output**: Ready-to-use trip plans and maps
- **Universal Support**: Works with any anime series

## 📖 Documentation

- [API Usage Guide](API_USAGE.md) - Web API documentation
- [Seichi Search System](SEICHI_SEARCH_SYSTEM.md) - Technical details
- [Clean README](README_CLEAN.md) - Comprehensive guide

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

## 🚀 Setup Instructions

### 1. Environment Setup
```bash
cd "D:\Side Projects\Home-assist"
conda activate trip_planner
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
```bash
cp .env.example .env
# Edit .env - system works with mock data by default
```

### 3. Start Using

#### **Command Line**
```bash
# Interactive mode
python main.py

# Direct query
python main.py "plan a trip for Seichi junrei of Bunny Girl Senpai"

# Help
python main.py help
```

#### **Web Interface**
```bash
# Start API server
python start_api.py
# Open browser to: http://localhost:8000
```

## 🌟 Supported Anime

### **Specialized Support** (specific locations):
- **Slam Dunk**: Basketball locations in Kamakura/Tokyo
- **Your Name**: Movie scene locations in Tokyo
- **One Piece**: Adventure locations throughout Japan

### **Universal Support** (intelligent search):
- **Bunny Girl Senpai**: Romance school locations in Tokyo
- **Attack on Titan**: Action locations and historical sites
- **Any Anime**: Genre-appropriate location suggestions

---

**Transform your anime fandom into real pilgrimage experiences with authentic filming locations!** 🗺️✨