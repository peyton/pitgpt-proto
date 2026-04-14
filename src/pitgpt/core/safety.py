import re
from dataclasses import dataclass

from pitgpt.core.models import (
    EvidenceQuality,
    IngestionDecision,
    IngestionResult,
    Protocol,
    RiskLevel,
    SafetyTier,
)
from pitgpt.core.policy import SAFETY_POLICY_VERSION


@dataclass(frozen=True)
class SafetyPrefilterMatch:
    tier: SafetyTier
    reason: str
    pattern: str


_RED_PATTERNS = {
    r"\b(bupropion|ssri|isotretinoin|ozempic|semaglutide|tacrolimus|steroid cream)\b": (
        "Prescription medication changes are outside PitGPT's trial scope."
    ),
    (
        r"\b(stop|stopping|discontinue|quit|pause)\b.*"
        r"\b(medication|medicine|antihistamine|ssri|prescription)\b"
    ): ("Medication stopping experiments are outside PitGPT's trial scope."),
    r"\b(nac|creatine|supplement|focus stack|microdose)\b": (
        "Supplement, ingestible, or dosing experiments require a different safety path."
    ),
    r"\b(diagnose|diagnosis|do i have|whether i have)\b": (
        "Diagnosis questions are outside PitGPT's trial scope."
    ),
    r"\b(urgent|emergency|crisis|severe pain|rapidly worsening|suicidal)\b": (
        "Urgent or rapidly worsening symptoms need immediate clinical support, "
        "not a personal trial."
    ),
    r"\b(microneedling|needle|invasive)\b": (
        "Invasive-device experiments are outside PitGPT's trial scope."
    ),
}

_UNSAFE_TEXT_PATTERNS = {
    r"\b(prescription|rx|dose|microdose|diagnose|cure|treats?|heals?)\b": (
        "Protocol text contains treatment, diagnosis, dosing, or cure language."
    ),
    r"\b(ozempic|semaglutide|bupropion|ssri|isotretinoin|tacrolimus)\b": (
        "Protocol text mentions a prescription medication."
    ),
    r"\b(nac|creatine|supplement stack)\b": (
        "Protocol text mentions a supplement or ingestible stack."
    ),
}


def prefilter_query(query: str, documents: list[str]) -> IngestionResult | None:
    text = " ".join([query, *documents]).lower()
    match = _match_patterns(text, _RED_PATTERNS)
    if match is None:
        return None
    return IngestionResult(
        decision=IngestionDecision.BLOCK,
        safety_tier=SafetyTier.RED,
        evidence_quality=EvidenceQuality.WEAK,
        risk_level=RiskLevel.HIGH,
        risk_rationale=match.reason,
        protocol=None,
        block_reason=match.reason,
        user_message=(
            "PitGPT cannot create a personal trial for this request. "
            "Use the app for reversible, low-risk routines or products."
        ),
        policy_version=SAFETY_POLICY_VERSION,
        response_validation_status=f"prefiltered:{match.pattern}",
    )


def validate_protocol_safety_text(protocol: Protocol) -> list[str]:
    fields = [
        protocol.condition_a_label,
        protocol.condition_b_label,
        protocol.condition_a_instructions,
        protocol.condition_b_instructions,
        protocol.primary_outcome_question,
        protocol.screening,
        protocol.warnings,
    ]
    text = " ".join(part for part in fields if part).lower()
    matches: list[str] = []
    for pattern, reason in _UNSAFE_TEXT_PATTERNS.items():
        if re.search(pattern, text):
            matches.append(reason)
    return matches


def _match_patterns(
    text: str,
    patterns: dict[str, str],
) -> SafetyPrefilterMatch | None:
    for pattern, reason in patterns.items():
        if re.search(pattern, text):
            return SafetyPrefilterMatch(SafetyTier.RED, reason, pattern)
    return None
