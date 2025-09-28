#!/usr/bin/env python3
"""
FastAPI Backend for Anime Pilgrimage Trip Planning System
Web API interface for the trip planning system
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
import json
from datetime import datetime
from simple_trip_planner import SimpleTripPlanner
from report_generator import ReportGenerator
from config import Config

# Initialize FastAPI app
app = FastAPI(
    title="Anime Pilgrimage Trip Planning API",
    description="API for planning anime pilgrimage trips with interactive maps and comprehensive reports",
    version="1.0.0"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
planner = SimpleTripPlanner()
report_generator = ReportGenerator()
config = Config()

# Pydantic models for request/response
class TripQuery(BaseModel):
    query: str
    output_format: Optional[str] = "both"  # "markdown", "pdf", "both"
    trip_duration: Optional[int] = 7
    start_date: Optional[str] = None

class TripResponse(BaseModel):
    success: bool
    message: str
    trip_data: Optional[Dict[str, Any]] = None
    report_files: Optional[Dict[str, str]] = None
    map_file: Optional[str] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    message: str
    model_loaded: bool
    map_generation_ready: bool

# Serve static files (generated maps and reports)
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Simple HTML interface for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Anime Pilgrimage Trip Planner</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            button { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background-color: #0056b3; }
            .result { margin-top: 20px; padding: 15px; border-radius: 4px; }
            .success { background-color: #d4edda; border: 1px solid #c3e6cb; }
            .error { background-color: #f8d7da; border: 1px solid #f5c6cb; }
            .loading { display: none; text-align: center; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>Anime Pilgrimage Trip Planner</h1>
        <div class="container">
            <form id="tripForm">
                <div class="form-group">
                    <label for="query">Trip Query:</label>
                    <textarea id="query" name="query" rows="4" placeholder="Describe your trip (e.g., '7-days trip from Taiwan to Japan for Slam Dunk pilgrimage')" required></textarea>
                </div>

                <div class="form-group">
                    <label for="duration">Trip Duration (days):</label>
                    <input type="number" id="duration" name="duration" value="7" min="1" max="30">
                </div>

                <div class="form-group">
                    <label for="start_date">Start Date (optional):</label>
                    <input type="date" id="start_date" name="start_date">
                </div>

                <div class="form-group">
                    <label for="output_format">Output Format:</label>
                    <select id="output_format" name="output_format">
                        <option value="both">Markdown + PDF</option>
                        <option value="markdown">Markdown Only</option>
                        <option value="pdf">PDF Only</option>
                    </select>
                </div>

                <button type="submit">Plan My Trip</button>
            </form>

            <div id="loading" class="loading">
                <p>Planning your trip... Please wait.</p>
            </div>

            <div id="result"></div>
        </div>

        <script>
            document.getElementById('tripForm').addEventListener('submit', async function(e) {
                e.preventDefault();

                const loading = document.getElementById('loading');
                const result = document.getElementById('result');

                loading.style.display = 'block';
                result.innerHTML = '';

                const formData = new FormData(this);
                const data = {
                    query: formData.get('query'),
                    trip_duration: parseInt(formData.get('duration')),
                    start_date: formData.get('start_date') || null,
                    output_format: formData.get('output_format')
                };

                try {
                    const response = await fetch('/plan-trip', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });

                    const responseData = await response.json();
                    loading.style.display = 'none';

                    if (responseData.success) {
                        let html = '<div class="result success">';
                        html += '<h3>Trip Planning Complete!</h3>';
                        html += '<p>' + responseData.message + '</p>';

                        if (responseData.report_files) {
                            html += '<h4>Generated Files:</h4>';
                            html += '<ul>';
                            for (const [format, filename] of Object.entries(responseData.report_files)) {
                                html += `<li><a href="/download/${filename}" target="_blank">${format.toUpperCase()} Report</a></li>`;
                            }
                            html += '</ul>';
                        }

                        if (responseData.map_file) {
                            html += `<h4>Interactive Map:</h4>`;
                            html += `<p><a href="/download/${responseData.map_file}" target="_blank">Open Interactive Map</a></p>`;
                        }

                        html += '</div>';
                    } else {
                        html = `<div class="result error"><h3>Error:</h3><p>${responseData.error}</p></div>`;
                    }

                    result.innerHTML = html;
                } catch (error) {
                    loading.style.display = 'none';
                    result.innerHTML = `<div class="result error"><h3>Error:</h3><p>${error.message}</p></div>`;
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check if AI model is loaded
        model_loaded = False
        try:
            llm = planner.llm_manager.get_model()
            model_loaded = llm is not None
        except:
            pass

        # Check if map generation works
        map_ready = False
        try:
            test_map = report_generator.map_agent.create_main_anime_map("Slam Dunk", 1)
            map_ready = test_map.endswith(".html")
        except:
            pass

        return HealthResponse(
            status="healthy",
            message="Trip Planning API is running",
            model_loaded=model_loaded,
            map_generation_ready=map_ready
        )
    except Exception as e:
        return HealthResponse(
            status="error",
            message=f"Health check failed: {str(e)}",
            model_loaded=False,
            map_generation_ready=False
        )

@app.post("/plan-trip", response_model=TripResponse)
async def plan_trip(trip_query: TripQuery):
    """Main trip planning endpoint"""
    try:
        print(f"[API] Processing trip query: {trip_query.query}")

        # Set default start date if not provided
        if not trip_query.start_date:
            trip_query.start_date = datetime.now().strftime("%Y-%m-%d")

        # Step 1: Plan the trip
        trip_result = planner.plan_trip(trip_query.query)

        if "error" in trip_result:
            return TripResponse(
                success=False,
                message="Trip planning failed",
                error=trip_result["error"]
            )

        # Step 2: Generate reports
        report_files = report_generator.generate_comprehensive_report(
            trip_result,
            output_format=trip_query.output_format
        )

        # Step 3: Get map file
        map_file = trip_result.get("main_map", "")

        # Step 4: Move files to static directory for web access
        moved_files = {}
        for format_type, file_path in report_files.items():
            if os.path.exists(file_path):
                new_path = f"static/{file_path}"
                os.rename(file_path, new_path)
                moved_files[format_type] = new_path

        moved_map_file = None
        if map_file and os.path.exists(map_file):
            moved_map_file = f"static/{map_file}"
            os.rename(map_file, moved_map_file)

        return TripResponse(
            success=True,
            message="Trip planned successfully!",
            trip_data=trip_result,
            report_files=moved_files,
            map_file=moved_map_file
        )

    except Exception as e:
        print(f"[API ERROR] {str(e)}")
        return TripResponse(
            success=False,
            message="Trip planning failed",
            error=str(e)
        )

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated files"""
    file_path = f"static/{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/api-info")
async def api_info():
    """API information and documentation"""
    return {
        "title": "Anime Pilgrimage Trip Planning API",
        "version": "1.0.0",
        "endpoints": {
            "/": "HTML interface",
            "/health": "Health check",
            "/plan-trip": "Plan a trip (POST)",
            "/download/{filename}": "Download generated files",
            "/api-info": "This information"
        },
        "supported_anime": ["Any anime series - specialized locations for Slam Dunk, Your Name, One Piece; generic locations for others"],
        "features": [
            "Flight search (mock data)",
            "Weather information (mock data)",
            "Interactive map generation",
            "Markdown and PDF reports",
            "Route optimization"
        ],
        "api_requirements": {
            "flight_api": "Optional - uses mock data",
            "weather_api": "Optional - uses mock data",
            "ai_models": "Local HuggingFace models"
        }
    }

if __name__ == "__main__":
    import uvicorn

    print("[API] Starting Anime Pilgrimage Trip Planning API...")
    print("[API] Health check: http://localhost:8000/health")
    print("[API] Web interface: http://localhost:8000/")
    print("[API] API documentation: http://localhost:8000/api-info")

    uvicorn.run(
        "api_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )