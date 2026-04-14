"""Test the ingestion pipeline with mocked LLM responses."""

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from pitgpt.core.ingestion import MAX_DOCUMENT_CHARS, IngestionInputError, ingest
from pitgpt.core.llm import LLMClient, LLMError
from pitgpt.core.models import EvidenceQuality, IngestionDecision, SafetyTier
from pitgpt.core.policy import SAFETY_POLICY_PROMPT, SAFETY_POLICY_VERSION


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
        assert result.policy_version == SAFETY_POLICY_VERSION
        assert result.model == "test/model"
        assert result.response_validation_status == "validated"


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

    @respx.mock
    @pytest.mark.asyncio
    async def test_low_risk_condition_adjacent_routine_allowed_with_restrictions(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "generate_protocol_with_restrictions",
                        "safety_tier": "YELLOW",
                        "evidence_quality": "weak",
                        "evidence_conflict": False,
                        "risk_level": "condition_adjacent_low",
                        "risk_rationale": "Low-risk sleep routine; no medication changes.",
                        "clinician_note": (
                            "Consider bringing this plan to your clinician if it affects symptoms."
                        ),
                        "protocol": {
                            "template": "Sleep Routine",
                            "duration_weeks": 4,
                            "block_length_days": 7,
                            "cadence": "daily AM",
                            "washout": "None",
                            "primary_outcome_question": "Morning restfulness (0-10)",
                            "screening": "Do not change medications or replace care.",
                            "warnings": "Stop if symptoms worsen.",
                            "outcome_anchor_low": "0 = worst morning restfulness you would log",
                            "outcome_anchor_mid": "5 = typical morning restfulness",
                            "outcome_anchor_high": "10 = best morning restfulness you would log",
                            "suggested_confounders": ["sleep duration", "travel"],
                            "clinician_note": (
                                "Consider bringing this plan to your clinician if it affects symptoms."
                            ),
                        },
                        "block_reason": None,
                        "sources": [
                            {
                                "source_id": "source-1",
                                "source_type": "text",
                                "title": "Uploaded note",
                                "evidence_quality": "weak",
                                "summary": "Routine timing note.",
                                "rationale": "User-provided note, not a controlled trial.",
                            }
                        ],
                        "extracted_claims": [
                            {
                                "intervention": "morning light",
                                "comparator": "usual routine",
                                "routine": "sleep",
                                "outcome": "morning restfulness",
                                "source_refs": ["source-1"],
                            }
                        ],
                        "suitability_scores": [
                            {
                                "dimension": "risk",
                                "score": 5,
                                "rationale": "Reversible routine.",
                            }
                        ],
                        "next_steps": ["Lock the protocol if the plan matches what you can do."],
                        "user_message": "This can be tested as a low-risk routine with restrictions.",
                    }
                ),
            )
        )

        result = await ingest(
            "Track a low-risk sleep routine for migraine patterns", ["Note"], client
        )

        assert result.decision == IngestionDecision.GENERATE_PROTOCOL_WITH_RESTRICTIONS
        assert result.safety_tier == SafetyTier.YELLOW
        assert result.risk_level == "condition_adjacent_low"
        assert result.clinician_note.startswith("Consider bringing")
        assert result.sources[0].source_id == "source-1"
        assert result.extracted_claims[0].outcome == "morning restfulness"
        assert result.suitability_scores[0].dimension == "risk"


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
    async def test_generated_protocol_missing_required_fields_rejected(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "generate_protocol",
                        "safety_tier": "GREEN",
                        "evidence_quality": "novel",
                        "protocol": {
                            "cadence": "daily",
                            "washout": "None",
                            "primary_outcome_question": "Comfort (0-10)",
                        },
                        "user_message": "Malformed.",
                    }
                ),
            )
        )
        with pytest.raises(ValidationError):
            await ingest("test", [], client)

    @pytest.mark.asyncio
    async def test_large_document_rejected_before_llm_call(self, client):
        with pytest.raises(IngestionInputError, match="too large"):
            await ingest("test", ["x" * (MAX_DOCUMENT_CHARS + 1)], client)

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

    @respx.mock
    @pytest.mark.asyncio
    async def test_malformed_provider_response_retries(self, client):
        route = respx.post("https://test.api/chat/completions")
        route.side_effect = [
            httpx.Response(200, json={"not_choices": []}),
            httpx.Response(200, json={"choices": []}),
            httpx.Response(200, json={"choices": [{"message": {}}]}),
        ]
        with pytest.raises(LLMError):
            await ingest("test", [], client)


class TestSafetyPolicy:
    def test_policy_versioned(self):
        assert SAFETY_POLICY_VERSION

    def test_policy_covers_prd_boundaries(self):
        prompt = SAFETY_POLICY_PROMPT
        assert "GREEN" in prompt
        assert "YELLOW" in prompt
        assert "RED" in prompt
        assert "prescription medication dose/timing/start/stop/switch change" in prompt
        assert "supplement or ingestible change" in prompt
        assert "condition-adjacent" in prompt
        assert "Acute, urgent, crisis" in prompt
        assert "skincare product comparisons" in prompt
