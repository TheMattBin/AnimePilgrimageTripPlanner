#!/usr/bin/env python3
"""
Simple startup script for the FastAPI backend
"""

import uvicorn
from api_backend import app

if __name__ == "__main__":
    print("=" * 60)
    print("Anime Pilgrimage Trip Planning API")
    print("=" * 60)
    print("Starting server...")
    print("Web Interface: http://localhost:8000")
    print("API Health: http://localhost:8000/health")
    print("API Info: http://localhost:8000/api-info")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )