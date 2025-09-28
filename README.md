# Anime Pilgrimage Trip Planner

A multi-agent AI system for planning anime pilgrimage trips using LangGraph and Hugging Face models.

## Features

- **Natural Language Processing**: Accepts natural language queries about anime pilgrimage
- **Anime Identification**: Identifies anime titles from user queries using pattern matching and AI
- **Location Discovery**: Crawls anime pilgrimage websites to find real-world locations
- **Trip Planning**: Creates comprehensive itineraries with optimized routes
- **Markdown Reports**: Generates detailed trip plans in markdown format
- **Multi-Agent Architecture**: Uses separate agents for each task

## Installation

1. Create and activate the conda environment:
```bash
conda create -n trip_planner python=3.11 -y
conda activate trip_planner
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

Run the planner with a natural language query:
```bash
python main.py "I want to visit locations from Your Name movie"
```

Save the report to a file:
```bash
python main.py "I want to visit Spirited Away locations" --output my_trip.md
```

Run in interactive mode:
```bash
python main.py --interactive
```

### Example Queries

- "I want to visit locations from Your Name movie"
- "Plan a trip for Spirited Away pilgrimage sites"
- "Show me locations from Attack on Titan in Japan"
- "Create an itinerary for Demon Slayer locations"

### Supported Anime

The system currently supports pattern matching for popular anime including:
- Your Name (Kimi no Na Wa)
- Spirited Away (Sen to Chihiro)
- Attack on Titan (Shingeki no Kyojin)
- Demon Slayer (Kimetsu no Yaiba)
- My Hero Academia (Boku no Hero Academia)
- One Piece
- Naruto
- Dragon Ball
- Pokemon
- Studio Ghibli films

## Architecture

The system uses a multi-agent architecture with the following components:

### Agents

1. **Anime Identifier Agent**: Identifies anime from natural language queries
2. **Web Crawler Agent**: Searches for pilgrimage locations on anime websites
3. **Trip Planner Agent**: Creates optimized itineraries and travel plans
4. **Report Generator**: Produces comprehensive markdown reports

### Workflow

1. **Query Analysis**: Validates and processes user input
2. **Anime Identification**: Determines which anime the user is referring to
3. **Location Discovery**: Finds real-world pilgrimage locations
4. **Trip Planning**: Creates optimized routes and itineraries
5. **Report Generation**: Produces the final markdown report

## Configuration

### Environment Variables

The system can be configured with the following environment variables:

- `HUGGINGFACE_API_KEY`: Your Hugging Face API key for enhanced AI capabilities
- `GOOGLE_MAPS_API_KEY`: For enhanced location services
- `WEATHER_API_KEY`: For weather integration in trip planning

### Customization

You can customize the system by modifying the agents in the `src/agents/` directory:

- `anime_identifier_agent.py`: Update anime patterns and AI models
- `web_crawler_agent.py`: Modify crawling strategies and data sources
- `trip_planner_agent.py`: Adjust trip planning algorithms and preferences
- `report_generator.py`: Customize report templates and content

## Output Format

The system generates comprehensive markdown reports including:

- Trip overview and summary
- Budget estimates
- Detailed location information
- Day-by-day itinerary
- Travel tips and recommendations
- Accessibility information
- Nearby attractions

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed in the conda environment
2. **Web Crawling Failures**: The target website may have changed structure or be unavailable
3. **API Key Issues**: Some features may require API keys for enhanced functionality
4. **Location Services**: Ensure geopy is properly configured for location services

### Error Handling

The system includes comprehensive error handling and will provide:
- Detailed error messages
- Suggestions for improving queries
- Fallback mechanisms when services are unavailable

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and research purposes. Please respect the terms of service of any external APIs or websites used.

## Acknowledgments

- LangGraph for the multi-agent framework
- Hugging Face for AI models
- animepilgrimage.com for pilgrimage location data
- Various open-source libraries for geolocation, web crawling, and report generation

## Future Enhancements

- Integration with more AI models
- Real-time weather and transportation data
- Interactive maps and visualizations
- Mobile application
- Community features for sharing pilgrimage experiences
- Integration with booking and reservation systems