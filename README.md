# 🎌 Anime Pilgrimage Trip Planner

An agentic system that creates detailed anime pilgrimage travel itineraries by identifying anime from user queries, crawling real-world location data, and generating optimized multi-day travel plans.

## 🌟 Features

- **🤖 Agentic Web Crawling**: Autonomous data collection using LangGraph workflows
- **🧠 AI-Powered Analysis**: HuggingFace LLM integration for anime identification and response generation
- **🗺️ Intelligent Route Planning**: Optimized travel routes with geographic clustering
- **📱 User-Friendly Interface**: Natural language input and comprehensive travel responses
- **⚡ Real-Time Processing**: Fast query processing with async web crawling

## 🏗️ System Architecture

```
User Query
    ↓
[Query Interface]
    ↓
[Query Analyzer (HF LLM)]
    ↓
[Anime(s) Identified + Keywords]
    ↓
[Agentic Web Crawler (LangGraph + Custom Python)]
    ↓
[Location & Activity Data]
    ↓
[Trip Planner & Route Optimizer]
    ↓
[Response Generator (HF LLM)]
    ↓
Travel Plan Response to User
```

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd AnimePilgrimageTripPlanner
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Download required models (first run only):**
   ```bash
   python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; AutoTokenizer.from_pretrained('microsoft/DialoGPT-medium')"
   ```

## 🔧 Configuration

Create a `.env` file with the following variables:

```env
HUGGINGFACE_MODEL_NAME="microsoft/DialoGPT-medium"
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
FLIGHT_API_KEY=your_flight_api_key_here
WEATHER_API_KEY=your_weather_api_key_here
OPENSTREETMAP_USER_AGENT=trip_planner_app
NOMINATIM_EMAIL=your_email@example.com
```

## 🚀 Usage

### Interactive Mode

Run the planner in interactive mode:

```bash
python src/main.py
```

### Single Query Mode

Process a single query:

```bash
python src/main.py -q "I want to visit locations from Your Name in Tokyo and Kyoto"
```

### Save Response to File

Save the generated plan to a JSON file:

```bash
python src/main.py -q "Plan a budget trip to Attack on Titan locations" -o my_trip_plan.json
```

## 💬 Example Queries

- "I want to visit locations from Your Name in Tokyo and Kyoto"
- "Show me anime pilgrimage spots in Japan for 3 days"
- "Plan a budget trip to Attack on Titan locations in Oita"
- "I'd like to see Studio Ghibli pilgrimage sites over a weekend"
- "Create a luxury tour of Naruto locations in Japan"

## 📁 Project Structure

```
AnimePilgrimageTripPlanner/
├── src/
│   ├── components/
│   │   ├── query_interface.py      # User input processing
│   │   ├── query_analyzer.py       # AI-powered anime identification
│   │   ├── trip_planner.py         # Route optimization and planning
│   │   └── response_generator.py   # AI response generation
│   ├── agents/
│   │   └── web_crawler.py          # Agentic web scraping
│   └── main.py                     # Main application
├── requirements.txt
├── .env.example
└── README.md
```

## 🤖 AI Components

### Query Analyzer
- Uses HuggingFace transformers for anime identification
- Rule-based fallback for robustness
- Confidence scoring and disambiguation

### Web Crawler
- LangGraph-based agentic workflows
- Intelligent site discovery and crawling
- Anti-bot measures and rate limiting
- Structured and unstructured data extraction

### Response Generator
- Template-based responses with LLM enhancement
- Personalized travel recommendations
- Cost estimates and practical information

## 🛠️ Development

### Adding New Anime

1. Edit `src/components/query_analyzer.py`
2. Add entries to the `_load_anime_database()` method:

```python
"anime_title": {
    "alternate_titles": ["Alternate Name 1", "Alternate Name 2"],
    "locations": ["Location1", "Location2"],
    "keywords": ["keyword1", "keyword2"],
    "type": "movie|series"
}
```

### Extending Web Sources

Add new pilgrimage websites to `src/agents/web_crawler.py`:

```python
self.pilgrimage_sites = [
    "https://your-anime-site.com",
    # ... existing sites
]
```

### Customizing Response Templates

Edit the template methods in `src/components/response_generator.py`:
- `_load_itinerary_template()`
- `_load_clarification_template()`
- `_load_error_template()`

## 🔍 Troubleshooting

### Model Loading Issues
- Ensure you have sufficient RAM (8GB+ recommended)
- Try a smaller model if encountering memory issues
- Check internet connection for first-time model downloads

### Web Scraping Issues
- Some sites may block scraping - the system includes retry logic
- Check network connectivity and DNS settings
- Consider using VPNs for region-restricted sites

### Memory Issues
- Reduce `max_depth` in the crawler
- Limit the number of locations processed
- Use smaller transformer models

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Search existing GitHub issues
3. Create a new issue with detailed information

## 🙏 Acknowledgments

- HuggingFace for providing transformer models
- LangGraph for agentic workflow frameworks
- The anime community for location data and inspiration

---

**⚠️ Disclaimer**: This is a demonstration system. Travel times, costs, and location information are estimates. Always verify details before planning actual travel.