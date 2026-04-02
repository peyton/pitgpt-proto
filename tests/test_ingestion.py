"""Test the ingestion pipeline with mocked LLM responses."""

import json

import httpx
import pytest
import respx

from pitgpt.core.ingestion import ingest
from pitgpt.core.llm import LLMClient, LLMError
from pitgpt.core.models import EvidenceQuality, IngestionDecision, SafetyTier


def _mock_llm_response(response_data: dict):
    return {"choices": [{"message": {"content": json.dumps(response_data)}}]}


@pytest.fixture
def client():
    return LLMClient(model="test/model", api_key="test-key", base_url="https://test.api")


class TestIngestionGreen:
    @respx.mock
    @pytest.mark.asyncio
    async def test_query_only_green(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "generate_protocol",
                        "safety_tier": "GREEN",
                        "evidence_quality": "novel",
                        "evidence_conflict": False,
                        "protocol": {
                            "template": "Skincare Product",
                            "duration_weeks": 6,
                            "block_length_days": 7,
                            "cadence": "daily",
                            "washout": "None",
                            "primary_outcome_question": "How comfortable is your skin? (0-10)",
                            "screening": "",
                            "warnings": "",
                        },
                        "block_reason": None,
                        "user_message": "Ready to run your skincare comparison.",
                    }
                ),
            )
        )
        result = await ingest("Is CeraVe better than Cetaphil?", [], client)
        assert result.decision == IngestionDecision.GENERATE_PROTOCOL
        assert result.safety_tier == SafetyTier.GREEN
        assert result.evidence_quality == EvidenceQuality.NOVEL
        assert result.protocol is not None
        assert result.protocol.template == "Skincare Product"
        assert result.protocol.duration_weeks == 6


class TestIngestionYellow:
    @respx.mock
    @pytest.mark.asyncio
    async def test_otc_active_yellow(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "generate_protocol_with_restrictions",
                        "safety_tier": "YELLOW",
                        "evidence_quality": "weak",
                        "evidence_conflict": False,
                        "protocol": {
                            "template": "Custom A/B",
                            "duration_weeks": 6,
                            "block_length_days": 7,
                            "cadence": "daily",
                            "washout": "None",
                            "primary_outcome_question": "How clear and comfortable is your skin? (0-10)",
                            "screening": "Exclude pregnancy, broken skin.",
                            "warnings": "Stop if irritation persists.",
                        },
                        "block_reason": None,
                        "user_message": "Allowed with restrictions.",
                    }
                ),
            )
        )
        result = await ingest("Compare 2.5% vs 5% benzoyl peroxide", ["OTC info..."], client)
        assert result.decision == IngestionDecision.GENERATE_PROTOCOL_WITH_RESTRICTIONS
        assert result.safety_tier == SafetyTier.YELLOW
        assert result.protocol.screening != ""


class TestIngestionRed:
    @respx.mock
    @pytest.mark.asyncio
    async def test_prescription_blocked(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "block",
                        "safety_tier": "RED",
                        "evidence_quality": "weak",
                        "evidence_conflict": False,
                        "protocol": None,
                        "block_reason": "Prescription medication not allowed.",
                        "user_message": "Cannot create this protocol.",
                    }
                ),
            )
        )
        result = await ingest("Test bupropion timing", ["Paper..."], client)
        assert result.decision == IngestionDecision.BLOCK
        assert result.safety_tier == SafetyTier.RED
        assert result.protocol is None
        assert result.block_reason is not None


class TestIngestionManualReview:
    @respx.mock
    @pytest.mark.asyncio
    async def test_unknown_active(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "manual_review_before_protocol",
                        "safety_tier": "YELLOW",
                        "evidence_quality": "weak",
                        "evidence_conflict": False,
                        "protocol": None,
                        "block_reason": "Unknown active needs review.",
                        "user_message": "This product needs safety review.",
                    }
                ),
            )
        )
        result = await ingest("Build a trial for spicule serum", ["Product page..."], client)
        assert result.decision == IngestionDecision.MANUAL_REVIEW_BEFORE_PROTOCOL


class TestLLMErrors:
    @respx.mock
    @pytest.mark.asyncio
    async def test_api_failure_retries(self, client):
        route = respx.post("https://test.api/chat/completions")
        route.side_effect = [
            httpx.Response(500, text="Server error"),
            httpx.Response(500, text="Server error"),
            httpx.Response(500, text="Server error"),
        ]
        with pytest.raises(LLMError):
            await ingest("test", [], client)

    @respx.mock
    @pytest.mark.asyncio
    async def test_invalid_json_retries(self, client):
        route = respx.post("https://test.api/chat/completions")
        route.side_effect = [
            httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]}),
            httpx.Response(200, json={"choices": [{"message": {"content": "still not json"}}]}),
            httpx.Response(200, json={"choices": [{"message": {"content": "nope"}}]}),
        ]
        with pytest.raises(LLMError):
            await ingest("test", [], client)
