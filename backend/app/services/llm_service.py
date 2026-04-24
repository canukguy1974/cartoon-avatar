"""Stream chat completions from OpenRouter (OpenAI-compatible API)."""

import os
import json
import logging
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are Sunny, a friendly and knowledgeable AI assistant for Tangerine Bank. "
    "You help customers with banking questions. "
    "CRITICAL: Respond in EXACTLY 1 short, conversational sentence. Keep it under 15 words. "
    "Be extremely brief and to the point to ensure fast voice playback. "
    "Never make up specific account numbers or balances."
)


def _get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. "
            "Add it to backend/.env or export it as an environment variable."
        )
    return key


def _get_model() -> str:
    return os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")


async def stream_chat_response(user_message: str) -> AsyncGenerator[str, None]:
    """Yield text token chunks as they stream from the LLM.

    Uses OpenRouter's OpenAI-compatible streaming API.
    """
    api_key = _get_api_key()
    model = _get_model()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8001",
        "X-Title": "Sunny Banking Assistant",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "max_tokens": 300,
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream(
            "POST",
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise RuntimeError(
                    f"OpenRouter returned {response.status_code}: {body.decode()}"
                )

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue

                data_str = line[6:]  # strip "data: " prefix
                if data_str.strip() == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, IndexError, KeyError) as exc:
                    logger.debug("Skipping unparseable SSE chunk: %s (%s)", data_str, exc)
                    continue
