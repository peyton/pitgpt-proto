"""Test the ingestion pipeline with mocked LLM responses."""

import json
from unittest.mock import patch

import httpx
import pytest
import respx

from pitgpt.core.ingestion import IngestionInputError, ingest
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
    async def test_generated_protocol_missing_required_fields_asks_follow_up(self, client):
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

        result = await ingest("test", [], client)

        assert result.decision == IngestionDecision.MANUAL_REVIEW_BEFORE_PROTOCOL
        assert result.protocol is None
        assert result.response_validation_status == "provider_protocol_invalid"
        assert result.next_steps
        assert "two routines" in result.next_steps[0]

    @respx.mock
    @pytest.mark.asyncio
    async def test_generated_protocol_missing_protocol_asks_follow_up(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "generate_protocol",
                        "safety_tier": "GREEN",
                        "evidence_quality": "novel",
                        "protocol": None,
                        "user_message": "Ready.",
                    }
                ),
            )
        )

        result = await ingest("test", [], client)

        assert result.decision == IngestionDecision.MANUAL_REVIEW_BEFORE_PROTOCOL
        assert result.protocol is None
        assert result.block_reason == "The model did not return a complete protocol."
        assert result.response_validation_status == "provider_protocol_missing"
        assert result.next_steps

    @respx.mock
    @pytest.mark.asyncio
    async def test_large_document_allowed_by_default(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "block",
                        "safety_tier": "RED",
                        "evidence_quality": "weak",
                        "protocol": None,
                        "block_reason": "Unsafe.",
                        "user_message": "No.",
                    }
                ),
            )
        )

        result = await ingest("test", ["x" * 120_001], client)

        assert result.decision == IngestionDecision.BLOCK

    @patch.dict(
        "os.environ",
        {"PITGPT_MAX_DOCUMENT_CHARS": "3", "PITGPT_MAX_TOTAL_DOCUMENT_CHARS": "10"},
    )
    @pytest.mark.asyncio
    async def test_document_limits_can_come_from_settings(self, client):
        with pytest.raises(IngestionInputError, match="Document 1 is too large"):
            await ingest("test", ["xxxx"], client)

    @patch.dict(
        "os.environ",
        {"PITGPT_MAX_DOCUMENT_CHARS": "3", "PITGPT_MAX_TOTAL_DOCUMENT_CHARS": "10"},
    )
    @respx.mock
    @pytest.mark.asyncio
    async def test_document_limit_override_allows_trusted_local_input(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "block",
                        "safety_tier": "RED",
                        "evidence_quality": "weak",
                        "protocol": None,
                        "block_reason": "Unsafe.",
                        "user_message": "No.",
                    }
                ),
            )
        )

        result = await ingest("test", ["xxxx"], client, max_document_chars=10)

        assert result.decision == IngestionDecision.BLOCK

    @pytest.mark.asyncio
    async def test_non_positive_document_limit_override_is_rejected(self, client):
        with pytest.raises(IngestionInputError, match="Per-document character limit"):
            await ingest("test", ["x"], client, max_document_chars=0)

    @respx.mock
    @pytest.mark.asyncio
    async def test_query_is_trimmed_before_provider_prompt(self, client):
        route = respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "block",
                        "safety_tier": "RED",
                        "evidence_quality": "weak",
                        "protocol": None,
                        "block_reason": "Unsafe.",
                        "source_summaries": [" useful ", ""],
                        "user_message": "No.",
                    }
                ),
            )
        )

        result = await ingest("  test  ", [], client)

        request = json.loads(route.calls[0].request.content)
        assert request["messages"][1]["content"] == "User query: test"
        assert result.source_summaries == ["useful"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_url_source_is_fetched_before_provider_prompt(self, client):
        respx.get("https://example.com/article").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><body><h1>Trial evidence</h1><script>bad()</script><p>Comfort improved.</p></body></html>",
            )
        )
        route = respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "block",
                        "safety_tier": "RED",
                        "evidence_quality": "weak",
                        "protocol": None,
                        "block_reason": "Unsafe.",
                        "user_message": "No.",
                    }
                ),
            )
        )

        await ingest("test", ["https://example.com/article"], client)

        request = json.loads(route.calls[0].request.content)
        user_prompt = request["messages"][1]["content"]
        assert "Source URL: https://example.com/article" in user_prompt
        assert "Trial evidence" in user_prompt
        assert "Comfort improved." in user_prompt
        assert "bad()" not in user_prompt

    @respx.mock
    @pytest.mark.asyncio
    async def test_document_limit_applies_to_fetched_url_content(self, client):
        route = respx.get("https://example.com/article").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text=f"<html><body><p>{'x' * 80}</p></body></html>",
            )
        )

        with pytest.raises(IngestionInputError, match="Document 1 is too large"):
            await ingest(
                "test",
                ["https://example.com/article"],
                client,
                max_document_chars=60,
            )

        assert route.called

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


class TestLLMClientOperations:
    @respx.mock
    @pytest.mark.asyncio
    async def test_referer_and_title_headers_are_absent_by_default(self, client):
        route = respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "block",
                        "safety_tier": "RED",
                        "evidence_quality": "weak",
                        "protocol": None,
                        "block_reason": "Unsafe.",
                        "user_message": "No.",
                    }
                ),
            )
        )

        await client.complete("system", "user")

        headers = route.calls[0].request.headers
        assert "HTTP-Referer" not in headers
        assert "X-Title" not in headers

    @patch.dict(
        "os.environ",
        {
            "PITGPT_LLM_REFERER": "https://pitgpt.local",
            "PITGPT_LLM_TITLE": "PitGPT Tests",
        },
    )
    @respx.mock
    @pytest.mark.asyncio
    async def test_referer_and_title_headers_are_configurable(self, client):
        route = respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "block",
                        "safety_tier": "RED",
                        "evidence_quality": "weak",
                        "protocol": None,
                        "block_reason": "Unsafe.",
                        "user_message": "No.",
                    }
                ),
            )
        )

        await client.complete("system", "user")

        headers = route.calls[0].request.headers
        assert headers["HTTP-Referer"] == "https://pitgpt.local"
        assert headers["X-Title"] == "PitGPT Tests"

    @respx.mock
    @pytest.mark.asyncio
    async def test_opt_in_cache_reuses_successful_response(self, tmp_path, client):
        route = respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "block",
                        "safety_tier": "RED",
                        "evidence_quality": "weak",
                        "protocol": None,
                        "block_reason": "Unsafe.",
                        "user_message": "No.",
                    }
                ),
            )
        )

        with patch.dict(
            "os.environ",
            {"PITGPT_LLM_CACHE": "1", "PITGPT_LLM_CACHE_DIR": str(tmp_path)},
        ):
            first = await client.complete("system", "user")
            second = await client.complete("system", "user")

        assert first == second
        assert route.call_count == 1
        assert list(tmp_path.glob("*.json"))


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


class TestDeterministicSafetyGates:
    @respx.mock
    @pytest.mark.asyncio
    async def test_red_prefilter_blocks_before_llm(self, client):
        route = respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(500, json={"detail": "should not be called"})
        )

        result = await ingest("Can I stop my prescription medication for a week?", [], client)

        assert result.decision == IngestionDecision.BLOCK
        assert result.safety_tier == SafetyTier.RED
        assert result.response_validation_status.startswith("prefiltered:")
        assert route.call_count == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_generated_protocol_safety_text_is_blocked(self, client):
        respx.post("https://test.api/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json=_mock_llm_response(
                    {
                        "decision": "generate_protocol",
                        "safety_tier": "GREEN",
                        "evidence_quality": "weak",
                        "protocol": {
                            "template": "Custom A/B",
                            "duration_weeks": 2,
                            "block_length_days": 7,
                            "cadence": "daily",
                            "washout": "None",
                            "primary_outcome_question": "How did the dose affect symptoms?",
                            "screening": "",
                            "warnings": "",
                            "condition_a_label": "Ozempic dose A",
                            "condition_b_label": "Ozempic dose B",
                        },
                        "block_reason": None,
                        "user_message": "Ready.",
                    }
                ),
            )
        )

        result = await ingest("Compare two morning routines", [], client)

        assert result.decision == IngestionDecision.BLOCK
        assert result.safety_tier == SafetyTier.RED
        assert result.response_validation_status == "blocked_generated_protocol_safety_text"
