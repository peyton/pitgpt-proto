import asyncio
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx

from pitgpt.core.settings import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_TIMEOUT_S,
    DEFAULT_OLLAMA_BASE_URL,
    load_settings,
)

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
        settings = load_settings()
        cache_key = _cache_key(self.model, system, user, self.temperature, self.max_tokens)
        if settings.llm_cache_enabled:
            cached = _read_cache(settings.llm_cache_dir, cache_key)
            if cached is not None:
                return cached

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if settings.llm_referer:
            headers["HTTP-Referer"] = settings.llm_referer
        if settings.llm_title:
            headers["X-Title"] = settings.llm_title
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
                    parsed: object = json.loads(content)
                    if not isinstance(parsed, dict):
                        raise LLMError("LLM response JSON must be an object")
                    if settings.llm_cache_enabled:
                        _write_cache(settings.llm_cache_dir, cache_key, parsed)
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


class OllamaClient:
    def __init__(
        self,
        model: str,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        temperature: float = 0.0,
        timeout_s: float = DEFAULT_LLM_TIMEOUT_S,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout_s = timeout_s

    async def complete(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError) as e:
            raise LLMError(f"Ollama request failed: {e}") from e

        content = _extract_ollama_message_content(data)
        try:
            parsed: object = json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMError(f"Ollama response was not valid JSON: {e}") from e
        if not isinstance(parsed, dict):
            raise LLMError("Ollama response JSON must be an object")
        return parsed

    async def stream_json_text(self, system: str, user: str) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "stream": True,
            "format": "json",
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            async with (
                httpx.AsyncClient(timeout=self.timeout_s) as client,
                client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp,
            ):
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    content = _extract_ollama_message_content(data, allow_empty=True)
                    if content:
                        yield content
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError) as e:
            raise LLMError(f"Ollama streaming request failed: {e}") from e

    async def complete_streaming(self, system: str, user: str) -> dict[str, Any]:
        chunks: list[str] = []
        async for chunk in self.stream_json_text(system, user):
            chunks.append(chunk)
        try:
            parsed: object = json.loads("".join(chunks))
        except json.JSONDecodeError as e:
            raise LLMError(f"Ollama streaming response was not valid JSON: {e}") from e
        if not isinstance(parsed, dict):
            raise LLMError("Ollama streaming response JSON must be an object")
        return parsed


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


def _extract_ollama_message_content(data: Any, allow_empty: bool = False) -> str:
    if not isinstance(data, dict):
        raise LLMError("Ollama response was not a JSON object")
    message = data.get("message")
    if not isinstance(message, dict):
        raise LLMError("Ollama response missing message")
    content = message.get("content")
    if not isinstance(content, str) or (content == "" and not allow_empty):
        raise LLMError("Ollama response message missing content")
    return content


def _cache_key(
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "system": system,
            "user": user,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_dir(configured: str) -> Path:
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".pitgpt" / "cache"


def _read_cache(configured_dir: str, key: str) -> dict[str, Any] | None:
    path = _cache_dir(configured_dir) / f"{key}.json"
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _write_cache(configured_dir: str, key: str, value: dict[str, Any]) -> None:
    path = _cache_dir(configured_dir) / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)
