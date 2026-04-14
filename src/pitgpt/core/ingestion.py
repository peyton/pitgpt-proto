from pitgpt.core.llm import LLMClient
from pitgpt.core.models import (
    EvidenceQuality,
    IngestionDecision,
    IngestionResult,
    Protocol,
    SafetyTier,
)
from pitgpt.core.policy import SAFETY_POLICY_PROMPT


async def ingest(
    query: str,
    documents: list[str],
    client: LLMClient,
) -> IngestionResult:
    user_parts = [f"User query: {query}"]
    for i, doc in enumerate(documents, 1):
        user_parts.append(f"\n--- Uploaded Document {i} ---\n{doc}")

    user_message = "\n".join(user_parts)
    raw = await client.complete(SAFETY_POLICY_PROMPT, user_message)

    protocol_data = raw.get("protocol")
    protocol = None
    if protocol_data and isinstance(protocol_data, dict):
        protocol = Protocol(
            template=protocol_data.get("template"),
            duration_weeks=protocol_data.get("duration_weeks", 6),
            block_length_days=protocol_data.get("block_length_days", 7),
            cadence=protocol_data.get("cadence", "daily"),
            washout=protocol_data.get("washout", "None"),
            primary_outcome_question=protocol_data.get("primary_outcome_question", ""),
            screening=protocol_data.get("screening", ""),
            warnings=protocol_data.get("warnings", ""),
        )

    return IngestionResult(
        decision=IngestionDecision(raw["decision"]),
        safety_tier=SafetyTier(raw["safety_tier"]),
        evidence_quality=EvidenceQuality(raw["evidence_quality"]),
        evidence_conflict=raw.get("evidence_conflict", False),
        protocol=protocol,
        block_reason=raw.get("block_reason"),
        user_message=raw.get("user_message", ""),
    )
