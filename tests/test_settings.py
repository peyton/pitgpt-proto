import pytest

from pitgpt.core.settings import load_settings


def test_settings_parse_explicit_false_cache_flag() -> None:
    settings = load_settings({"PITGPT_LLM_CACHE": "off"})

    assert settings.llm_cache_enabled is False


def test_settings_reject_invalid_boolean_values() -> None:
    with pytest.raises(ValueError, match="PITGPT_LLM_CACHE must be one of"):
        load_settings({"PITGPT_LLM_CACHE": "sometimes"})


def test_settings_reject_non_positive_numeric_limits() -> None:
    with pytest.raises(ValueError, match="PITGPT_MAX_DOCUMENT_CHARS must be greater than 0"):
        load_settings({"PITGPT_MAX_DOCUMENT_CHARS": "0"})


def test_source_limits_are_unset_by_default() -> None:
    settings = load_settings({})

    assert settings.max_document_chars is None
    assert settings.max_total_document_chars is None


def test_settings_reject_non_positive_timeouts() -> None:
    with pytest.raises(ValueError, match="PITGPT_LLM_TIMEOUT_S must be greater than 0"):
        load_settings({"PITGPT_LLM_TIMEOUT_S": "-1"})


def test_settings_reject_non_finite_timeouts() -> None:
    with pytest.raises(ValueError, match="PITGPT_LLM_TIMEOUT_S must be greater than 0"):
        load_settings({"PITGPT_LLM_TIMEOUT_S": "nan"})
