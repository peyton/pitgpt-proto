from pydantic import BaseModel

from pitgpt.core.llm import LLMClient
from pitgpt.core.models import (
    EvidenceQuality,
    ExtractedClaim,
    IngestionDecision,
    IngestionResult,
    Protocol,
    ResearchSource,
    RiskLevel,
    SafetyTier,
    SuitabilityScore,
)
from pitgpt.core.policy import SAFETY_POLICY_PROMPT, SAFETY_POLICY_VERSION

MAX_DOCUMENT_CHARS = 12_000
MAX_TOTAL_DOCUMENT_CHARS = 40_000


class IngestionInputError(ValueError):
    pass


async def ingest(
    query: str,
    documents: list[str],
    client: LLMClient,
    model_id: str | None = None,
) -> IngestionResult:
    _validate_inputs(query, documents)
    user_parts = [f"User query: {query}"]
    for i, doc in enumerate(documents, 1):
        user_parts.append(f"\n--- Uploaded Document {i} ---\n{doc}")

    user_message = "\n".join(user_parts)
    raw = await client.complete(SAFETY_POLICY_PROMPT, user_message)

    protocol_data = raw.get("protocol")
    protocol = None
    if protocol_data and isinstance(protocol_data, dict):
        protocol = Protocol.model_validate(protocol_data)

    return IngestionResult(
        decision=IngestionDecision(raw["decision"]),
        safety_tier=SafetyTier(raw["safety_tier"]),
        evidence_quality=EvidenceQuality(raw["evidence_quality"]),
        evidence_conflict=raw.get("evidence_conflict", False),
        risk_level=RiskLevel(raw.get("risk_level", RiskLevel.LOW.value)),
        risk_rationale=str(raw.get("risk_rationale", "")),
        clinician_note=str(raw.get("clinician_note", "")),
        protocol=protocol,
        block_reason=raw.get("block_reason"),
        user_message=raw.get("user_message", ""),
        policy_version=raw.get("policy_version", SAFETY_POLICY_VERSION),
        model=model_id or client.model,
        response_validation_status="validated",
        source_summaries=_string_list(raw.get("source_summaries")),
        claimed_outcomes=_string_list(raw.get("claimed_outcomes")),
        sources=_model_list(raw.get("sources"), ResearchSource),
        extracted_claims=_model_list(raw.get("extracted_claims"), ExtractedClaim),
        suitability_scores=_model_list(raw.get("suitability_scores"), SuitabilityScore),
        next_steps=_string_list(raw.get("next_steps")),
    )


def _validate_inputs(query: str, documents: list[str]) -> None:
    if not query.strip():
        raise IngestionInputError("Query is required.")
    total_chars = 0
    for i, doc in enumerate(documents, 1):
        doc_len = len(doc)
        total_chars += doc_len
        if doc_len > MAX_DOCUMENT_CHARS:
            raise IngestionInputError(
                f"Document {i} is too large ({doc_len:,} chars). "
                f"Limit each source to {MAX_DOCUMENT_CHARS:,} chars."
            )
    if total_chars > MAX_TOTAL_DOCUMENT_CHARS:
        raise IngestionInputError(
            f"Sources are too large in total ({total_chars:,} chars). "
            f"Limit all sources to {MAX_TOTAL_DOCUMENT_CHARS:,} chars."
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _model_list[ModelT: BaseModel](value: object, model_type: type[ModelT]) -> list[ModelT]:
    if not isinstance(value, list):
        return []
    result: list[ModelT] = []
    for item in value:
        if isinstance(item, dict):
            result.append(model_type.model_validate(item))
    return result
