"""Tests for OpenRouterClient JSON parsing, structured outputs, fallback, and VLM encoding."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import BadRequestError
from pydantic import BaseModel

from anime_pilgrimage.config import Settings
from anime_pilgrimage.llm.openrouter import OpenRouterClient, extract_json_payload


class _SampleSchema(BaseModel):
    title: str
    days: int


def _fake_completion(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_extract_json_payload_handles_fences_and_prose():
    assert extract_json_payload('{"title": "Your Name", "days": 3}') == {
        "title": "Your Name",
        "days": 3,
    }
    fenced = 'Sure! Here is the JSON:\n```json\n{"title": "Hyouka", "days": 2}\n```'
    assert extract_json_payload(fenced) == {"title": "Hyouka", "days": 2}

    wrapped = 'Result: {"title": "Suzume", "days": 5} -- enjoy!'
    assert extract_json_payload(wrapped) == {"title": "Suzume", "days": 5}


async def test_generate_structured_validates_and_sends_fallbacks():
    mock_openai = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(return_value=_fake_completion('{"title": "Your Name", "days": 3}'))
            )
        )
    )
    settings = Settings(
        openrouter_api_key="sk-or-test",
        openrouter_llm_model="openrouter/free",
        openrouter_fallback_models="meta-llama/llama-3.3-70b-instruct:free",
    )
    client = OpenRouterClient(settings=settings, client=mock_openai)  # type: ignore[arg-type]

    parsed = await client.generate_structured("Extract trip", _SampleSchema)
    assert parsed == _SampleSchema(title="Your Name", days=3)

    call_kwargs = mock_openai.chat.completions.create.await_args.kwargs
    assert call_kwargs["model"] == "openrouter/free"
    assert call_kwargs["extra_body"] == {
        "models": ["openrouter/free", "meta-llama/llama-3.3-70b-instruct:free"]
    }


async def test_json_mode_downgrade_does_not_burn_retry_budget():
    """With max_retries=1, downgrading from json_object to plain text must still succeed."""
    bad_req = BadRequestError(
        message="response_format json_object unsupported",
        response=httpx.Response(400, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")),
        body={"error": {"message": "unsupported"}},
    )
    create_mock = AsyncMock(
        side_effect=[bad_req, _fake_completion('```json\n{"title": "Hyouka", "days": 2}\n```')]
    )
    mock_openai = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock)))
    settings = Settings(
        openrouter_api_key="sk-or-test",
        openrouter_llm_model="openrouter/free",
        openrouter_max_retries=1,
    )
    client = OpenRouterClient(settings=settings, client=mock_openai)  # type: ignore[arg-type]

    parsed = await client.generate_structured("Extract trip", _SampleSchema)
    assert parsed == _SampleSchema(title="Hyouka", days=2)
    assert create_mock.await_count == 2
    assert "response_format" in create_mock.await_args_list[0].kwargs
    assert "response_format" not in create_mock.await_args_list[1].kwargs


async def test_analyze_image_encodes_local_file_as_data_uri(tmp_path: Path):
    img = tmp_path / "frame.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\nfakebytes")

    mock_openai = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=AsyncMock(return_value=_fake_completion('{"title": "Your Name", "days": 1}'))
            )
        )
    )
    settings = Settings(openrouter_api_key="sk-or-test", openrouter_vlm_model="openrouter/free")
    client = OpenRouterClient(settings=settings, client=mock_openai)  # type: ignore[arg-type]

    result = await client.analyze_image(img, "Identify this anime scene", response_model=_SampleSchema)
    assert result.title == "Your Name"

    sent_messages = mock_openai.chat.completions.create.await_args.kwargs["messages"]
    user_parts = sent_messages[-1]["content"]
    assert user_parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_unconfigured_client_raises_clear_error():
    settings = Settings(openrouter_api_key="")
    client = OpenRouterClient(settings=settings)
    assert client.is_configured is False
    with pytest.raises(Exception, match="OPENROUTER_API_KEY"):
        await client.generate_text("hello")
