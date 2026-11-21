"""FastAPI backend exposing text & VLM screenshot pilgrimage planning endpoints."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from anime_pilgrimage import __version__
from anime_pilgrimage.components.scene_analyzer import (
    MAX_IMAGE_BYTES,
    ImageValidationError,
    validate_and_encode_image_bytes,
)
from anime_pilgrimage.config import Settings, _find_project_root, configure_logging, get_settings
from anime_pilgrimage.llm.openrouter import OpenRouterError
from anime_pilgrimage.models import GeneratedResponse, SceneAnalysis
from anime_pilgrimage.planner import AnimePilgrimagePlanner

logger = logging.getLogger(__name__)

_UPLOAD_PATHS = frozenset({"/api/scene/analyze", "/api/plan/from-image"})
# Image limit plus headroom for multipart boundaries and the small text form fields
MAX_UPLOAD_REQUEST_BYTES = MAX_IMAGE_BYTES + 1024 * 1024
_TOO_LARGE_DETAIL = f"Image exceeds the maximum allowed size of {MAX_IMAGE_BYTES // (1024 * 1024)} MB."


async def _read_upload(image: UploadFile) -> bytes:
    """Read at most MAX_IMAGE_BYTES + 1 so oversized uploads are never buffered in memory."""
    data = await image.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=_TOO_LARGE_DETAIL)
    return data


class PlanRequest(BaseModel):
    """JSON body for text pilgrimage planning."""

    query: str = Field(..., min_length=3, max_length=1000, description="Natural-language trip query")


class HealthResponse(BaseModel):
    """Backend status and active provider metadata."""

    status: str = "ok"
    version: str
    openrouter_configured: bool
    llm_model: str
    vlm_model: str
    search_provider: str


def create_app(
    *,
    settings: Settings | None = None,
    planner: AnimePilgrimagePlanner | None = None,
) -> FastAPI:
    """Create a configured FastAPI application instance."""
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(resolved_settings.log_level)
        if planner is not None:
            app.state.planner = planner
            app.state.owns_planner = False
        else:
            app.state.planner = AnimePilgrimagePlanner(settings=resolved_settings)
            app.state.owns_planner = True
        try:
            yield
        finally:
            if app.state.owns_planner:
                await app.state.planner.aclose()

    app = FastAPI(
        title="Anime Pilgrimage Trip Planner API",
        version=__version__,
        description="LangGraph + OpenRouter LLM/VLM anime pilgrimage planning service.",
        lifespan=lifespan,
    )

    # Reject oversized uploads from Content-Length before the multipart parser spools the
    # body. Registered before CORS so CORS stays outermost and the 413 keeps CORS headers.
    @app.middleware("http")
    async def limit_upload_size(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method == "POST" and request.url.path in _UPLOAD_PATHS:
            declared = request.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > MAX_UPLOAD_REQUEST_BYTES:
                return JSONResponse(status_code=413, content={"detail": _TOO_LARGE_DETAIL})
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _get_planner(request: Request) -> AnimePilgrimagePlanner:
        return request.app.state.planner

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=__version__,
            openrouter_configured=resolved_settings.has_openrouter_key,
            llm_model=resolved_settings.openrouter_llm_model,
            vlm_model=resolved_settings.openrouter_vlm_model,
            search_provider="tavily" if resolved_settings.tavily_api_key.strip() else "ddgs",
        )

    @app.post("/api/plan", response_model=GeneratedResponse)
    async def create_plan(body: PlanRequest, request: Request) -> GeneratedResponse:
        active_planner = _get_planner(request)
        return await active_planner.process_query(body.query)

    @app.post("/api/scene/analyze", response_model=SceneAnalysis)
    async def analyze_scene(
        request: Request,
        image: Annotated[UploadFile, File(description="Anime screenshot or pilgrimage photo")],
        hint: Annotated[str, Form(description="Optional hint or context")] = "",
    ) -> SceneAnalysis:
        active_planner = _get_planner(request)
        image_bytes = await _read_upload(image)
        try:
            return await active_planner.analyze_scene(
                image_bytes,
                content_type=image.content_type,
                filename=image.filename,
                hint=hint,
            )
        except ImageValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except OpenRouterError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/plan/from-image", response_model=GeneratedResponse)
    async def plan_from_image(
        request: Request,
        image: Annotated[UploadFile, File(description="Anime screenshot or pilgrimage photo")],
        prompt: Annotated[
            str, Form(description="Optional trip preferences (e.g., '2 days budget')")
        ] = "",
    ) -> GeneratedResponse:
        active_planner = _get_planner(request)
        image_bytes = await _read_upload(image)
        try:
            # Validate image early so client receives clean HTTP 400 on bad uploads
            validate_and_encode_image_bytes(
                image_bytes, content_type=image.content_type, filename=image.filename
            )
        except ImageValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if not active_planner.llm_client.is_configured:
            raise HTTPException(
                status_code=503,
                detail="OpenRouter API key is required for VLM screenshot planning. Set OPENROUTER_API_KEY in .env.",
            )

        return await active_planner.process_image_query(
            image_bytes,
            prompt=prompt,
            content_type=image.content_type,
            filename=image.filename,
        )

    # Serve built TypeScript frontend automatically when frontend/dist exists
    frontend_dist: Path = _find_project_root() / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


app = create_app()


def run_server() -> None:
    """CLI entrypoint (`uv run pilgrimage-api`) to launch the FastAPI server."""
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Run the Anime Pilgrimage Planner API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    uvicorn.run(
        "anime_pilgrimage.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
