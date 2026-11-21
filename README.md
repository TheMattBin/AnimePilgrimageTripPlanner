# Anime Pilgrimage Trip Planner

An agentic system that turns natural-language anime pilgrimage requests into structured, geocoded, multi-day Japan travel itineraries using **LangGraph**, **OpenRouter free-tier LLMs/VLMs**, and **`uv`**.

## Highlights

- **`uv`-managed Python package** (`pyproject.toml` + `uv.lock`, no heavy local PyTorch/HuggingFace weights)
- **OpenRouter Free-Tier LLM & VLM Client** (`openrouter/free` with configurable `:free` fallbacks, structured Pydantic JSON extraction, retry/backoff, and VLM image-analysis support ready for screenshot lookup)
- **Iterative LangGraph Web Crawler** — plans English + Japanese (`聖地巡礼` / `ロケ地`) searches across all identified anime, extracts structured locations from cleaned articles (`trafilatura`), refines queries when coverage is sparse, and deduplicates candidates
- **Real Geocoding & Metadata** — OpenStreetMap Nominatim + Photon fallback with SQLite caching and Jikan (MyAnimeList) official Japanese title enrichment
- **Multi-City Route & Budget Optimizer** — separates regional clusters (e.g., Tokyo vs. Hida Takayama), preserves un-geocoded spots, runs nearest-neighbor + 2-opt TSP ordering, generates timed daily schedules, and computes tier-aware JPY budgets including lodging
- **API-Ready Models** — strongly typed Pydantic v2 models (`GeneratedResponse`, `TravelPlan`, `ScheduledStop`, `PilgrimageLocation`) ready to power a future TypeScript web UI

## Architecture

```
User Query
  ↓
[QueryInterface]               Unicode-safe validation & normalization
  ↓
[QueryAnalyzer]                OpenRouter structured LLM + Jikan EN/JP metadata
  ↓
[AgenticWebCrawler]            LangGraph iterative loop:
                               plan_queries → search_and_fetch → extract_locations
                               → merge_locations ──(refine if sparse)──↺
                                                 └→ geocode_locations (Nominatim/Photon + SQLite cache)
  ↓
[TripPlanner]                  Multi-city clustering, 2-opt TSP, timetable & JPY budget
  ↓
[ResponseGenerator]            Markdown guide + structured JSON payload
```

## Quick Start (with `uv`)

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Add your free API key from [OpenRouter](https://openrouter.ai/keys):
   ```env
   OPENROUTER_API_KEY=sk-or-v1-...
   OPENROUTER_LLM_MODEL=openrouter/free
   OPENROUTER_VLM_MODEL=openrouter/free
   ```
   *(Optional: add `TAVILY_API_KEY` for higher-precision web search; defaults to free DuckDuckGo search via `ddgs`.)*

3. **Run the CLI:**

   Interactive mode:
   ```bash
   uv run pilgrimage
   ```

   Single query with Markdown + JSON export:
   ```bash
   uv run pilgrimage \
     -q "Plan a 3-day budget Your Name pilgrimage in Tokyo and Hida Takayama" \
     -m outputs/your_name.md \
     -o outputs/your_name.json
   ```

## Project Structure

```
AnimePilgrimageTripPlanner/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── src/anime_pilgrimage/
│   ├── config.py                  # Pydantic Settings & logging setup
│   ├── models.py                  # Shared Pydantic v2 models (API/TS-UI ready)
│   ├── planner.py                 # High-level async AnimePilgrimagePlanner facade
│   ├── cli.py                     # Rich CLI entry point (`pilgrimage`)
│   ├── llm/
│   │   └── openrouter.py          # Shared OpenRouter LLM/VLM client with retries & fallbacks
│   ├── services/
│   │   ├── anime_metadata.py      # Jikan API lookup + SQLite cache
│   │   ├── geocoder.py            # Nominatim/Photon async geocoder + SQLite cache
│   │   └── search.py              # DDGS / Tavily search + concurrent trafilatura fetching
│   ├── components/
│   │   ├── query_interface.py     # Input validation & normalization
│   │   ├── query_analyzer.py      # LLM query parsing + rule-based fallback
│   │   ├── trip_planner.py        # Multi-city clustering, 2-opt TSP, budgets
│   │   └── response_generator.py  # Markdown & JSON itinerary rendering
│   └── agents/
│       └── web_crawler.py         # Iterative LangGraph discovery agent
└── tests/                         # Fast offline pytest suite
```

## Development & Testing

```bash
# Run unit & integration tests (offline, mocked external calls)
uv run pytest

# Lint with ruff
uv run ruff check src tests
```

## Disclaimer

Travel times, costs, and access details are estimates generated for planning purposes. Always verify opening hours, transit schedules, and local photography etiquette before visiting real-world pilgrimage sites.
