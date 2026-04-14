from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from os import environ

DEFAULT_MODEL = "anthropic/claude-sonnet-4"
DEFAULT_LLM_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LLM_TIMEOUT_S = 120.0
DEFAULT_LLM_TEMPERATURE = 0.0
DEFAULT_LLM_MAX_TOKENS = 4096
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1"
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str = ""
    api_token: str = ""
    default_model: str = DEFAULT_MODEL
    llm_base_url: str = DEFAULT_LLM_BASE_URL
    llm_timeout_s: float = DEFAULT_LLM_TIMEOUT_S
    llm_temperature: float = DEFAULT_LLM_TEMPERATURE
    llm_max_tokens: int = DEFAULT_LLM_MAX_TOKENS
    llm_referer: str = ""
    llm_title: str = ""
    llm_cache_enabled: bool = False
    llm_cache_dir: str = ""
    max_document_chars: int | None = None
    max_total_document_chars: int | None = None
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    ollama_default_model: str = DEFAULT_OLLAMA_MODEL


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source = environ if env is None else env
    return Settings(
        openrouter_api_key=source.get("OPENROUTER_API_KEY", ""),
        api_token=source.get("PITGPT_API_TOKEN", ""),
        default_model=source.get("PITGPT_DEFAULT_MODEL", DEFAULT_MODEL),
        llm_base_url=source.get("PITGPT_LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
        llm_timeout_s=_positive_float_from_env(
            source, "PITGPT_LLM_TIMEOUT_S", DEFAULT_LLM_TIMEOUT_S
        ),
        llm_temperature=_float_from_env(source, "PITGPT_LLM_TEMPERATURE", DEFAULT_LLM_TEMPERATURE),
        llm_max_tokens=_positive_int_from_env(
            source, "PITGPT_LLM_MAX_TOKENS", DEFAULT_LLM_MAX_TOKENS
        ),
        llm_referer=source.get("PITGPT_LLM_REFERER", ""),
        llm_title=source.get("PITGPT_LLM_TITLE", ""),
        llm_cache_enabled=_bool_from_env(source, "PITGPT_LLM_CACHE", False),
        llm_cache_dir=source.get("PITGPT_LLM_CACHE_DIR", ""),
        max_document_chars=_optional_positive_int_from_env(source, "PITGPT_MAX_DOCUMENT_CHARS"),
        max_total_document_chars=_optional_positive_int_from_env(
            source, "PITGPT_MAX_TOTAL_DOCUMENT_CHARS"
        ),
        ollama_base_url=source.get("PITGPT_OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        ollama_default_model=source.get("PITGPT_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
    )


def _float_from_env(source: Mapping[str, str], key: str, default: float) -> float:
    value = source.get(key)
    if value is None or value == "":
        return default
    return float(value)


def _int_from_env(source: Mapping[str, str], key: str, default: int) -> int:
    value = source.get(key)
    if value is None or value == "":
        return default
    return int(value)


def _positive_float_from_env(source: Mapping[str, str], key: str, default: float) -> float:
    parsed = _float_from_env(source, key, default)
    if not isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{key} must be greater than 0.")
    return parsed


def _positive_int_from_env(source: Mapping[str, str], key: str, default: int) -> int:
    parsed = _int_from_env(source, key, default)
    if parsed <= 0:
        raise ValueError(f"{key} must be greater than 0.")
    return parsed


def _optional_positive_int_from_env(source: Mapping[str, str], key: str) -> int | None:
    value = source.get(key)
    if value is None or value == "":
        return None
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{key} must be greater than 0.")
    return parsed


def _bool_from_env(source: Mapping[str, str], key: str, default: bool) -> bool:
    value = source.get(key)
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    accepted = ", ".join(sorted(_TRUE_VALUES | _FALSE_VALUES))
    raise ValueError(f"{key} must be one of: {accepted}.")
