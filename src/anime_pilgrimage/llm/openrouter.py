"""Async OpenRouter client supporting free-tier LLMs, structured JSON, and VLMs."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import mimetypes
import re
from pathlib import Path
from typing import Any, TypeVar, overload

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    BadRequestError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from anime_pilgrimage.config import Settings, get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class OpenRouterError(RuntimeError):
    """Raised when an OpenRouter request fails after retries."""


def extract_json_payload(raw_text: str) -> Any:
    """Extract and parse a JSON object/array from raw LLM output.

    Handles markdown code fences and surrounding prose commonly returned by
    free-tier models when strict JSON mode is unavailable.
    """
    text = raw_text.strip()
    if not text:
        raise ValueError("Empty response from model")

    # 1. Direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract from fenced ```json ... ``` blocks
    for match in _CODE_FENCE_RE.finditer(text):
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # 3. Scan for outermost balanced JSON object or array
    for open_char, close_char in (("{", "}"), ("[", "]")):
        start = text.find(open_char)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == open_char:
                    depth += 1
                elif ch == close_char:
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : idx + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break

    raise ValueError(f"Could not extract valid JSON from model response: {text[:200]!r}")


def _encode_image_to_data_url(image_path: Path) -> str:
    """Read a local image file and encode it as a base64 data URI."""
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"
    raw_bytes = image_path.read_bytes()
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


class OpenRouterClient:
    """Shared async client for OpenRouter free-tier LLMs and VLMs."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._external_client = client is not None
        self._client: AsyncOpenAI | None = client

        if self._client is None and self.settings.has_openrouter_key:
            headers: dict[str, str] = {}
            if self.settings.openrouter_site_url:
                headers["HTTP-Referer"] = self.settings.openrouter_site_url
            if self.settings.openrouter_app_name:
                headers["X-Title"] = self.settings.openrouter_app_name

            self._client = AsyncOpenAI(
                api_key=self.settings.openrouter_api_key,
                base_url=self.settings.openrouter_base_url,
                default_headers=headers,
                timeout=self.settings.openrouter_timeout_seconds,
                max_retries=0,  # Handled explicitly below for fallback & backoff control
            )

    @property
    def is_configured(self) -> bool:
        """Whether an OpenRouter client is ready to handle requests."""
        return self._client is not None

    def _build_extra_body(self, primary_model: str) -> dict[str, Any] | None:
        fallbacks = [m for m in self.settings.fallback_models if m != primary_model]
        if not fallbacks:
            return None
        return {"models": [primary_model, *fallbacks]}

    async def _chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
    ) -> str:
        if self._client is None:
            raise OpenRouterError(
                "OpenRouter API key is not configured. Set OPENROUTER_API_KEY in .env."
            )

        extra_body = self._build_extra_body(model)
        use_json_format = json_mode
        last_error: Exception | None = None
        attempt = 0

        while attempt < self.settings.openrouter_max_retries:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if extra_body:
                kwargs["extra_body"] = extra_body
            if use_json_format:
                kwargs["response_format"] = {"type": "json_object"}

            try:
                response = await self._client.chat.completions.create(**kwargs)
                if not response.choices:
                    raise OpenRouterError("OpenRouter returned empty choices")
                content = response.choices[0].message.content or ""
                if not content.strip():
                    raise OpenRouterError("OpenRouter returned empty message content")
                return content.strip()

            except BadRequestError as exc:
                # Some free-tier models reject response_format=json_object; downgrade
                # without burning a transient retry attempt.
                if use_json_format:
                    logger.debug(
                        "Model %s rejected json_object response_format (%r); retrying plain text",
                        model,
                        exc,
                    )
                    use_json_format = False
                    continue
                raise OpenRouterError(f"OpenRouter bad request: {exc}") from exc

            except (RateLimitError, APIConnectionError, APITimeoutError) as exc:
                attempt += 1
                last_error = exc
                backoff = min(2.0 ** (attempt - 1), 8.0)
                logger.warning(
                    "OpenRouter transient error on attempt %d/%d (%s: %r). Retrying in %.1fs...",
                    attempt,
                    self.settings.openrouter_max_retries,
                    type(exc).__name__,
                    exc,
                    backoff,
                )
                if attempt < self.settings.openrouter_max_retries:
                    await asyncio.sleep(backoff)

            except APIStatusError as exc:
                attempt += 1
                last_error = exc
                if exc.status_code >= 500 or exc.status_code == 429:
                    backoff = min(2.0 ** (attempt - 1), 8.0)
                    logger.warning(
                        "OpenRouter HTTP %d on attempt %d/%d. Retrying in %.1fs...",
                        exc.status_code,
                        attempt,
                        self.settings.openrouter_max_retries,
                        backoff,
                    )
                    if attempt < self.settings.openrouter_max_retries:
                        await asyncio.sleep(backoff)
                    continue
                raise OpenRouterError(
                    f"OpenRouter HTTP {exc.status_code}: {exc.message}"
                ) from exc

        raise OpenRouterError(
            f"OpenRouter request failed after {self.settings.openrouter_max_retries} attempts: "
            f"{type(last_error).__name__ if last_error else 'UnknownError'}: {last_error!r}"
        ) from last_error

    async def generate_text(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a text completion using the configured OpenRouter LLM."""
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return await self._chat_completion(
            messages,
            model=model or self.settings.openrouter_llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=False,
        )

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        *,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> T:
        """Generate and validate a Pydantic-typed structured JSON response."""
        schema_json = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
        base_system = (system_prompt or "You are a precise structured data assistant.").strip()
        full_system = (
            f"{base_system}\n\n"
            "Return ONLY a valid JSON object strictly conforming to this JSON Schema "
            "(no markdown commentary, no extra keys outside the schema):\n"
            f"{schema_json}"
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": prompt},
        ]

        chosen_model = model or self.settings.openrouter_llm_model
        last_error: Exception | None = None

        for attempt in range(1, 3):
            raw_text = await self._chat_completion(
                messages,
                model=chosen_model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=True,
            )
            try:
                payload = extract_json_payload(raw_text)
                return response_model.model_validate(payload)
            except (ValueError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "Structured output validation failed (attempt %d/2): %s", attempt, exc
                )
                messages.append({"role": "assistant", "content": raw_text})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your previous output failed JSON schema validation: {exc}. "
                            "Reply with ONLY the corrected JSON object."
                        ),
                    }
                )

        raise OpenRouterError(
            f"Failed to produce valid {response_model.__name__}: {last_error}"
        ) from last_error

    @overload
    async def analyze_image(
        self,
        image_source: str | Path,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_model: None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str: ...

    @overload
    async def analyze_image(
        self,
        image_source: str | Path,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_model: type[T],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> T: ...

    async def analyze_image(
        self,
        image_source: str | Path,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_model: type[T] | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str | T:
        """Analyze an image URL or local file using an OpenRouter VLM."""
        if isinstance(image_source, Path) or not str(image_source).startswith(
            ("http://", "https://", "data:")
        ):
            image_url = _encode_image_to_data_url(Path(image_source))
        else:
            image_url = str(image_source)

        messages: list[dict[str, Any]] = []
        if response_model is not None:
            schema_json = json.dumps(response_model.model_json_schema(), ensure_ascii=False)
            sys_text = (system_prompt or "You are an expert anime pilgrimage visual analyst.").strip()
            messages.append(
                {
                    "role": "system",
                    "content": (
                        f"{sys_text}\n\n"
                        "Return ONLY a valid JSON object matching this schema:\n"
                        f"{schema_json}"
                    ),
                }
            )
        elif system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        )

        raw = await self._chat_completion(
            messages,
            model=model or self.settings.openrouter_vlm_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=response_model is not None,
        )
        if response_model is None:
            return raw

        payload = extract_json_payload(raw)
        return response_model.model_validate(payload)

    async def aclose(self) -> None:
        """Close the underlying HTTP client if owned by this instance."""
        if self._client is not None and not self._external_client:
            await self._client.close()

    async def __aenter__(self) -> OpenRouterClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()
