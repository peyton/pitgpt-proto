from collections.abc import Mapping
from dataclasses import dataclass
from os import environ

DEFAULT_MODEL = "anthropic/claude-sonnet-4"
DEFAULT_LLM_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LLM_TIMEOUT_S = 120.0
DEFAULT_LLM_TEMPERATURE = 0.0
DEFAULT_LLM_MAX_TOKENS = 4096


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str = ""
    default_model: str = DEFAULT_MODEL
    llm_base_url: str = DEFAULT_LLM_BASE_URL
    llm_timeout_s: float = DEFAULT_LLM_TIMEOUT_S
    llm_temperature: float = DEFAULT_LLM_TEMPERATURE
    llm_max_tokens: int = DEFAULT_LLM_MAX_TOKENS


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source = environ if env is None else env
    return Settings(
        openrouter_api_key=source.get("OPENROUTER_API_KEY", ""),
        default_model=source.get("PITGPT_DEFAULT_MODEL", DEFAULT_MODEL),
        llm_base_url=source.get("PITGPT_LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
        llm_timeout_s=_float_from_env(source, "PITGPT_LLM_TIMEOUT_S", DEFAULT_LLM_TIMEOUT_S),
        llm_temperature=_float_from_env(source, "PITGPT_LLM_TEMPERATURE", DEFAULT_LLM_TEMPERATURE),
        llm_max_tokens=_int_from_env(source, "PITGPT_LLM_MAX_TOKENS", DEFAULT_LLM_MAX_TOKENS),
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
