# Anime Pilgrimage Trip Planner

An agentic system that turns natural-language requests **or uploaded anime screenshots** into structured, geocoded, multi-day Japan travel itineraries with an interactive route map — powered by **LangGraph**, **OpenRouter free-tier LLMs/VLMs**, **`uv`**, **FastAPI**, and a **TypeScript + React + Leaflet UI**.

## Highlights

- **`uv`-managed Python package** (`pyproject.toml` + `uv.lock`, no local PyTorch/HuggingFace weights)
- **OpenRouter Free-Tier LLM & VLM Client** (`openrouter/free` with configurable `:free` fallbacks, structured Pydantic JSON extraction, retry/backoff, and multimodal screenshot analysis)
- **VLM Screenshot → Pilgrimage Itinerary** — upload an anime frame or photo to identify the anime, read Japanese signage, estimate the real-world landmark, get camera framing tips, and build a full itinerary
- **Iterative LangGraph Web Crawler** — plans English + Japanese (`聖地巡礼` / `ロケ地`) queries across all identified anime, decodes UTF-8 / `Shift_JIS` / `EUC-JP` blogs via `trafilatura`, filters off-target anime, verifies source URLs, and geocodes with cached OpenStreetMap Nominatim + Photon fallback
- **Realistic Japan Transit & Route Optimizer** — multi-city regional clustering, 2-opt TSP ordering, Shinkansen vs. hybrid Shinkansen + limited express vs. domestic flight timing, morning/evening transfer scheduling, and travel-style JPY budgets
- **FastAPI + TypeScript Web UI** — interactive Leaflet route map with day-colored numbered pins, scene popups, screenshot drag-and-drop, and Markdown/JSON export

## Quick Start

### 1. Backend Setup (`uv`)

```bash
uv sync
cp .env.example .env
# Add your free OpenRouter API key from https://openrouter.ai/keys
```

### 2. Run the CLI

```bash
# Interactive mode
uv run pilgrimage

# Single text query with Markdown + JSON export
uv run pilgrimage \
  -q "Plan a 3-day budget Your Name pilgrimage in Tokyo and Hida Takayama" \
  -m outputs/your_name.md \
  -o outputs/your_name.json

# VLM screenshot-to-itinerary mode
uv run pilgrimage --image screenshot.png -q "2 days budget trip"
```

### 3. Run the FastAPI Backend + TypeScript Web UI

In terminal 1 (API server on `http://127.0.0.1:8000`):
```bash
uv run pilgrimage-api --reload
```

In terminal 2 (TypeScript Vite dev server on `http://localhost:5173`, proxies `/api` to FastAPI):
```bash
cd frontend
pnpm install
pnpm dev
```

Or build the TypeScript UI once and let FastAPI serve both API and UI on `http://127.0.0.1:8000`:
```bash
cd frontend && pnpm build && cd ..
uv run pilgrimage-api
```

## Project Structure

```
AnimePilgrimageTripPlanner/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── src/anime_pilgrimage/
│   ├── config.py                  # Pydantic Settings & root-relative cache/env resolution
│   ├── models.py                  # Shared Pydantic v2 models (API + TS UI contract)
│   ├── planner.py                 # Async AnimePilgrimagePlanner facade (text + VLM image)
│   ├── api.py                     # FastAPI server (`pilgrimage-api`)
│   ├── cli.py                     # Rich CLI (`pilgrimage`)
│   ├── llm/
│   │   └── openrouter.py          # Shared OpenRouter LLM/VLM client
│   ├── services/
│   │   ├── anime_metadata.py      # Jikan API lookup + similarity validation + SQLite cache
│   │   ├── geocoder.py            # Nominatim/Photon async geocoder + SQLite cache
│   │   └── search.py              # DDGS / Tavily search + Shift_JIS-safe trafilatura extraction
│   ├── components/
│   │   ├── query_interface.py     # Unicode/JP-safe input validation & normalization
│   │   ├── query_analyzer.py      # OpenRouter structured parsing + rule fallback
│   │   ├── scene_analyzer.py      # OpenRouter VLM screenshot analyzer
│   │   ├── trip_planner.py        # Multi-city clustering, 2-opt TSP, Japan transit & budgets
│   │   └── response_generator.py  # Markdown & JSON itinerary rendering
│   └── agents/
│       └── web_crawler.py         # Iterative LangGraph discovery agent
├── frontend/                      # Vite + React + TypeScript + Leaflet interactive UI
└── tests/                         # Fast offline pytest suite
```

## Testing & Linting

```bash
# Python tests & lint
uv run pytest
uv run ruff check src tests

# TypeScript typecheck & production build
cd frontend && pnpm typecheck && pnpm build
```
