from typing import Protocol as TypingProtocol

from pydantic import BaseModel

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
from pitgpt.core.safety import prefilter_query, validate_protocol_safety_text
from pitgpt.core.settings import load_settings

MAX_DOCUMENT_CHARS = 12_000
MAX_TOTAL_DOCUMENT_CHARS = 40_000


class IngestionInputError(ValueError):
    pass


class CompletionClient(TypingProtocol):
    model: str

    async def complete(self, system: str, user: str) -> dict[str, object]: ...


async def ingest(
    query: str,
    documents: list[str],
    client: CompletionClient,
    model_id: str | None = None,
    max_document_chars: int | None = None,
    max_total_document_chars: int | None = None,
) -> IngestionResult:
    _validate_inputs(query, documents, max_document_chars, max_total_document_chars)
    prefiltered = prefilter_query(query, documents)
    if prefiltered is not None:
        return prefiltered

    user_parts = [f"User query: {query}"]
    for i, doc in enumerate(documents, 1):
        user_parts.append(f"\n--- Uploaded Document {i} ---\n{doc}")

    user_message = "\n".join(user_parts)
    raw = await client.complete(SAFETY_POLICY_PROMPT, user_message)

    protocol_data = raw.get("protocol")
    protocol = None
    if protocol_data and isinstance(protocol_data, dict):
        protocol = Protocol.model_validate(protocol_data)
        unsafe_reasons = validate_protocol_safety_text(protocol)
        if unsafe_reasons:
            reason = " ".join(dict.fromkeys(unsafe_reasons))
            return IngestionResult(
                decision=IngestionDecision.BLOCK,
                safety_tier=SafetyTier.RED,
                evidence_quality=EvidenceQuality(str(raw.get("evidence_quality", "weak"))),
                evidence_conflict=bool(raw.get("evidence_conflict", False)),
                risk_level=RiskLevel.HIGH,
                risk_rationale=reason,
                protocol=None,
                block_reason=reason,
                user_message=(
                    "The generated protocol crossed PitGPT's safety boundary, so it was blocked "
                    "before lock."
                ),
                policy_version=str(raw.get("policy_version", SAFETY_POLICY_VERSION)),
                model=model_id or client.model,
                response_validation_status="blocked_generated_protocol_safety_text",
            )

    return IngestionResult(
        decision=IngestionDecision(str(raw["decision"])),
        safety_tier=SafetyTier(str(raw["safety_tier"])),
        evidence_quality=EvidenceQuality(str(raw["evidence_quality"])),
        evidence_conflict=bool(raw.get("evidence_conflict", False)),
        risk_level=RiskLevel(str(raw.get("risk_level", RiskLevel.LOW.value))),
        risk_rationale=str(raw.get("risk_rationale", "")),
        clinician_note=str(raw.get("clinician_note", "")),
        protocol=protocol,
        block_reason=_optional_string(raw.get("block_reason")),
        user_message=str(raw.get("user_message", "")),
        policy_version=str(raw.get("policy_version", SAFETY_POLICY_VERSION)),
        model=model_id or client.model,
        response_validation_status="validated",
        source_summaries=_string_list(raw.get("source_summaries")),
        claimed_outcomes=_string_list(raw.get("claimed_outcomes")),
        sources=_model_list(raw.get("sources"), ResearchSource),
        extracted_claims=_model_list(raw.get("extracted_claims"), ExtractedClaim),
        suitability_scores=_model_list(raw.get("suitability_scores"), SuitabilityScore),
        next_steps=_string_list(raw.get("next_steps")),
    )


def _validate_inputs(
    query: str,
    documents: list[str],
    max_document_chars: int | None = None,
    max_total_document_chars: int | None = None,
) -> None:
    if not query.strip():
        raise IngestionInputError("Query is required.")
    settings = load_settings()
    per_doc_limit = max_document_chars or settings.max_document_chars
    total_limit = max_total_document_chars or settings.max_total_document_chars
    total_chars = 0
    for i, doc in enumerate(documents, 1):
        doc_len = len(doc)
        total_chars += doc_len
        if doc_len > per_doc_limit:
            raise IngestionInputError(
                f"Document {i} is too large ({doc_len:,} chars). "
                f"Limit each source to {per_doc_limit:,} chars."
            )
    if total_chars > total_limit:
        raise IngestionInputError(
            f"Sources are too large in total ({total_chars:,} chars). "
            f"Limit all sources to {total_limit:,} chars."
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _model_list[ModelT: BaseModel](value: object, model_type: type[ModelT]) -> list[ModelT]:
    if not isinstance(value, list):
        return []
    result: list[ModelT] = []
    for item in value:
        if isinstance(item, dict):
            result.append(model_type.model_validate(item))
    return result
