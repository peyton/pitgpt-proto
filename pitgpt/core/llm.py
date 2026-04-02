import asyncio
import json
import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
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
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def complete(self, system: str, user: str) -> dict:
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
        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(MAX_RETRIES):
                try:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
                except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError) as e:
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
