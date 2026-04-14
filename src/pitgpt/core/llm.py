import asyncio
import json
import logging
from typing import Any

import httpx

from pitgpt.core.settings import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_TIMEOUT_S

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = DEFAULT_LLM_BASE_URL
MAX_RETRIES = 3
BACKOFF_BASE = 2.0


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout_s: float = DEFAULT_LLM_TIMEOUT_S,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    async def complete(self, system: str, user: str) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pitgpt.dev",
            "X-Title": "PitGPT Prototype",
        }
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            for attempt in range(MAX_RETRIES):
                try:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = _extract_message_content(data)
                    parsed = json.loads(content)
                    if not isinstance(parsed, dict):
                        raise LLMError("LLM response JSON must be an object")
                    return parsed
                except (
                    httpx.HTTPStatusError,
                    httpx.RequestError,
                    json.JSONDecodeError,
                    LLMError,
                ) as e:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        wait = BACKOFF_BASE ** (attempt + 1)
                        logger.warning(
                            "LLM request failed (attempt %d/%d): %s. Retrying in %.1fs",
                            attempt + 1,
                            MAX_RETRIES,
                            e,
                            wait,
                        )
                        await asyncio.sleep(wait)

        raise LLMError(f"LLM request failed after {MAX_RETRIES} attempts: {last_error}")


def _extract_message_content(data: Any) -> str:
    if not isinstance(data, dict):
        raise LLMError("LLM response was not a JSON object")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMError("LLM response missing choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise LLMError("LLM response choice was not an object")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise LLMError("LLM response choice missing message")
    content = message.get("content")
    if not isinstance(content, str) or content == "":
        raise LLMError("LLM response message missing content")
    return content
