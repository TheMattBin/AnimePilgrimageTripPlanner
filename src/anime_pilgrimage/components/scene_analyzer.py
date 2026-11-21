"""VLM-powered anime screenshot and pilgrimage photo analyzer via OpenRouter."""

from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path

from anime_pilgrimage.llm.openrouter import OpenRouterClient, OpenRouterError
from anime_pilgrimage.models import SceneAnalysis
from anime_pilgrimage.services.anime_metadata import AnimeMetadataService

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


class ImageValidationError(ValueError):
    """Raised when an uploaded image fails MIME type or size validation."""


def validate_and_encode_image_bytes(
    image_bytes: bytes, content_type: str | None = None, filename: str | None = None
) -> str:
    """Validate uploaded image bytes and encode them as a base64 data URI."""
    if not image_bytes:
        raise ImageValidationError("Uploaded image file is empty.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ImageValidationError(
            f"Image exceeds the maximum allowed size of {MAX_IMAGE_BYTES // (1024 * 1024)} MB."
        )

    mime = (content_type or "").split(";")[0].strip().lower()
    if not mime and filename:
        guessed, _ = mimetypes.guess_type(filename)
        mime = (guessed or "").lower()

    # Fallback sniff magic bytes for common formats when browser omits content-type
    if mime not in ALLOWED_IMAGE_MIME_TYPES:
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif image_bytes.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif image_bytes.startswith((b"GIF87a", b"GIF89a")):
            mime = "image/gif"
        elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            mime = "image/webp"

    if mime not in ALLOWED_IMAGE_MIME_TYPES:
        raise ImageValidationError(
            f"Unsupported image format {mime!r}. Allowed: JPEG, PNG, WEBP, GIF."
        )

    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


class SceneAnalyzer:
    """Uses an OpenRouter free-tier VLM to identify anime scenes and real-world landmarks."""

    def __init__(
        self,
        llm_client: OpenRouterClient | None = None,
        metadata_service: AnimeMetadataService | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.metadata_service = metadata_service

    async def analyze_image(
        self,
        image_source: bytes | Path | str,
        *,
        content_type: str | None = None,
        filename: str | None = None,
        hint: str = "",
    ) -> SceneAnalysis:
        """Identify anime, visual clues, real-world landmark guess, and framing tips from an image."""
        if self.llm_client is None or not self.llm_client.is_configured:
            raise OpenRouterError(
                "OpenRouter API key is required for VLM screenshot analysis. "
                "Set OPENROUTER_API_KEY in .env."
            )

        if isinstance(image_source, bytes):
            encoded_source: str | Path = validate_and_encode_image_bytes(
                image_source, content_type=content_type, filename=filename
            )
        elif isinstance(image_source, Path):
            if not image_source.is_file():
                raise ImageValidationError(f"Image file not found: {image_source}")
            encoded_source = validate_and_encode_image_bytes(
                image_source.read_bytes(), filename=image_source.name
            )
        elif str(image_source).startswith(("http://", "https://", "data:image/")):
            encoded_source = str(image_source)
        else:
            path = Path(image_source)
            if not path.is_file():
                raise ImageValidationError(f"Image file not found: {image_source}")
            encoded_source = validate_and_encode_image_bytes(
                path.read_bytes(), filename=path.name
            )

        system_prompt = (
            "You are an expert anime pilgrimage (聖地巡礼 / seichi junrei) visual researcher.\n"
            "Inspect the provided anime screenshot or real-world location photo carefully:\n"
            "1. Identify the anime title (canonical English + official Japanese title if recognizable).\n"
            "2. Read any Japanese signage, station boards, street markers, or distinctive architecture.\n"
            "3. Guess the real-world Japanese landmark (`landmark_guess` & `japanese_landmark`) and city/region.\n"
            "4. Give practical `camera_and_framing_tips` (vantage point, lens angle, best lighting/time of day).\n"
            "5. Produce 2-4 high-precision `suggested_search_queries` (mixing English and Japanese 聖地巡礼 terms).\n"
            "Be honest about uncertainty — lower `confidence` if the anime or landmark is not clearly recognizable."
        )
        hint_section = f"\nUser hint / trip context: {hint.strip()}" if hint.strip() else ""
        prompt = (
            "Analyze this anime screenshot or pilgrimage location photo and return structured "
            f"pilgrimage identification data.{hint_section}"
        )

        scene = await self.llm_client.analyze_image(
            encoded_source,
            prompt,
            system_prompt=system_prompt,
            response_model=SceneAnalysis,
            temperature=0.2,
            max_tokens=1500,
        )

        # Enrich with official Japanese title via Jikan if VLM left japanese_title empty
        if (
            scene.identified_anime
            and not scene.japanese_title
            and self.metadata_service is not None
        ):
            meta = await self.metadata_service.lookup(scene.identified_anime)
            if meta is not None and meta.match_score >= 0.85:
                scene = scene.model_copy(
                    update={
                        "identified_anime": meta.canonical_title or scene.identified_anime,
                        "japanese_title": meta.japanese_title or scene.japanese_title,
                    }
                )

        return scene

    @staticmethod
    def build_search_queries(scene: SceneAnalysis) -> list[str]:
        """Assemble prioritized web search queries from VLM scene output."""
        queries: list[str] = [q.strip() for q in scene.suggested_search_queries if q.strip()]
        anime = scene.identified_anime.strip()
        jp_anime = scene.japanese_title.strip()
        landmark = scene.landmark_guess.strip()
        jp_landmark = scene.japanese_landmark.strip()

        if anime and landmark:
            queries.append(f"{anime} {landmark} real life location Japan")
        if jp_anime and jp_landmark:
            queries.append(f"{jp_anime} {jp_landmark} 聖地巡礼")
        elif jp_anime and scene.city_or_region:
            queries.append(f"{jp_anime} {scene.city_or_region} 聖地巡礼 ロケ地")

        return list(dict.fromkeys(queries))[:4]
