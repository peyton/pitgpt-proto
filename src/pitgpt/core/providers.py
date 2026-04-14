from enum import StrEnum
from shutil import which

import httpx
from pydantic import BaseModel, Field

from pitgpt.core.settings import load_settings


class ProviderKind(StrEnum):
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    CLAUDE_CLI = "claude_cli"
    CODEX_CLI = "codex_cli"
    CHATGPT_CLI = "chatgpt_cli"
    IOS_ON_DEVICE = "ios_on_device"


class ProviderStatus(StrEnum):
    AVAILABLE = "available"
    INSTALLED_UNAVAILABLE = "installed_unavailable"
    NOT_FOUND = "not_found"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    RESERVED = "reserved"


class ProviderInfo(BaseModel):
    kind: ProviderKind
    label: str
    status: ProviderStatus
    is_local: bool
    is_offline: bool
    models: list[str] = Field(default_factory=list)
    detail: str = ""


def list_providers() -> list[ProviderInfo]:
    settings = load_settings()
    return [
        ProviderInfo(
            kind=ProviderKind.OPENROUTER,
            label="OpenRouter",
            status=(
                ProviderStatus.AVAILABLE
                if settings.openrouter_api_key
                else ProviderStatus.INSTALLED_UNAVAILABLE
            ),
            is_local=False,
            is_offline=False,
            models=[settings.default_model],
            detail=(
                "OPENROUTER_API_KEY is set."
                if settings.openrouter_api_key
                else "OPENROUTER_API_KEY is not set."
            ),
        ),
        _ollama_provider(settings.ollama_base_url),
        _cli_provider(ProviderKind.CLAUDE_CLI, "Claude CLI", "claude"),
        _cli_provider(ProviderKind.CODEX_CLI, "Codex CLI", "codex"),
        _cli_provider(ProviderKind.CHATGPT_CLI, "ChatGPT CLI", "chatgpt"),
        ProviderInfo(
            kind=ProviderKind.IOS_ON_DEVICE,
            label="iOS On-Device Models",
            status=ProviderStatus.RESERVED,
            is_local=True,
            is_offline=True,
            detail="Reserved for a future on-device model runtime.",
        ),
    ]


def _ollama_provider(base_url: str) -> ProviderInfo:
    if which("ollama") is None:
        return ProviderInfo(
            kind=ProviderKind.OLLAMA,
            label="Ollama",
            status=ProviderStatus.NOT_FOUND,
            is_local=True,
            is_offline=True,
            detail="Ollama is not on PATH.",
        )

    try:
        with httpx.Client(timeout=1.0) as client:
            resp = client.get(f"{base_url.rstrip('/')}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as e:
        return ProviderInfo(
            kind=ProviderKind.OLLAMA,
            label="Ollama",
            status=ProviderStatus.INSTALLED_UNAVAILABLE,
            is_local=True,
            is_offline=True,
            detail=f"Ollama is installed but not reachable: {e}",
        )

    models = [
        str(item.get("name", ""))
        for item in data.get("models", [])
        if isinstance(item, dict) and item.get("name")
    ]
    return ProviderInfo(
        kind=ProviderKind.OLLAMA,
        label="Ollama",
        status=ProviderStatus.AVAILABLE if models else ProviderStatus.INSTALLED_UNAVAILABLE,
        is_local=True,
        is_offline=True,
        models=models,
        detail="Ollama is running." if models else "Ollama is running but no models were found.",
    )


def _cli_provider(kind: ProviderKind, label: str, binary: str) -> ProviderInfo:
    path = which(binary)
    return ProviderInfo(
        kind=kind,
        label=label,
        status=ProviderStatus.AVAILABLE if path else ProviderStatus.NOT_FOUND,
        is_local=True,
        is_offline=False,
        detail=f"Found at {path}." if path else f"{binary} is not on PATH.",
    )
