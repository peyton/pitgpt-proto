from enum import Enum
from html.parser import HTMLParser
from typing import Protocol as TypingProtocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ValidationError

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
from pitgpt.core.workflows import WorkflowDefinition, build_workflow_query

PROTOCOL_FOLLOW_UP_STEPS = [
    "What are the exact two routines, products, or behaviors you want to compare?",
    "What single daily 0-10 outcome should decide which option worked better for you?",
    "Are any medications, symptoms, pregnancy, urgent issues, or clinician instructions involved?",
]
SOURCE_FETCH_TIMEOUT_S = 20.0


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
    workflow: WorkflowDefinition | None = None,
    model_warning: str | None = None,
) -> IngestionResult:
    _validate_query(query)
    query = query.strip()
    documents = await _resolve_documents(documents)
    _validate_documents(documents, max_document_chars, max_total_document_chars)
    prefiltered = prefilter_query(query, documents)
    if prefiltered is not None:
        return prefiltered

    workflow_query = build_workflow_query(query, workflow)
    user_parts = [f"User query: {workflow_query}"]
    for i, doc in enumerate(documents, 1):
        user_parts.append(f"\n--- Uploaded Document {i} ---\n{doc}")

    user_message = "\n".join(user_parts)
    raw = await client.complete(SAFETY_POLICY_PROMPT, user_message)

    decision = IngestionDecision(str(raw["decision"]))
    protocol_data = raw.get("protocol")
    protocol = None
    if protocol_data and isinstance(protocol_data, dict):
        try:
            protocol = Protocol.model_validate(protocol_data)
        except ValidationError:
            if decision in {
                IngestionDecision.GENERATE_PROTOCOL,
                IngestionDecision.GENERATE_PROTOCOL_WITH_RESTRICTIONS,
            }:
                return _manual_review_for_incomplete_protocol(
                    raw,
                    model_id or client.model,
                    "The model returned a protocol, but it was missing required details.",
                    "provider_protocol_invalid",
                    workflow=workflow,
                    model_warning=model_warning,
                )
            raise
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
                model_warning=model_warning,
                workflow_id=workflow.id if workflow else None,
                response_validation_status="blocked_generated_protocol_safety_text",
            )
    elif decision in {
        IngestionDecision.GENERATE_PROTOCOL,
        IngestionDecision.GENERATE_PROTOCOL_WITH_RESTRICTIONS,
    }:
        return _manual_review_for_incomplete_protocol(
            raw,
            model_id or client.model,
            "The model did not return a complete protocol.",
            "provider_protocol_missing",
            workflow=workflow,
            model_warning=model_warning,
        )

    return IngestionResult(
        decision=decision,
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
        model_warning=model_warning,
        workflow_id=workflow.id if workflow else None,
        response_validation_status="validated",
        source_summaries=_string_list(raw.get("source_summaries")),
        claimed_outcomes=_string_list(raw.get("claimed_outcomes")),
        sources=_model_list(raw.get("sources"), ResearchSource),
        extracted_claims=_model_list(raw.get("extracted_claims"), ExtractedClaim),
        suitability_scores=_model_list(raw.get("suitability_scores"), SuitabilityScore),
        next_steps=_string_list(raw.get("next_steps")),
    )


def _manual_review_for_incomplete_protocol(
    raw: dict[str, object],
    model: str,
    reason: str,
    status: str,
    workflow: WorkflowDefinition | None = None,
    model_warning: str | None = None,
) -> IngestionResult:
    next_steps = _string_list(raw.get("next_steps")) or PROTOCOL_FOLLOW_UP_STEPS
    return IngestionResult(
        decision=IngestionDecision.MANUAL_REVIEW_BEFORE_PROTOCOL,
        safety_tier=_enum_or_default(raw.get("safety_tier"), SafetyTier, SafetyTier.YELLOW),
        evidence_quality=_enum_or_default(
            raw.get("evidence_quality"), EvidenceQuality, EvidenceQuality.NOVEL
        ),
        evidence_conflict=bool(raw.get("evidence_conflict", False)),
        risk_level=_enum_or_default(raw.get("risk_level"), RiskLevel, RiskLevel.LOW),
        risk_rationale=str(raw.get("risk_rationale", "")),
        clinician_note=str(raw.get("clinician_note", "")),
        protocol=None,
        block_reason=reason,
        user_message=(
            "I need a little more detail before I can lock this protocol. "
            "Answer the follow-up questions and try again."
        ),
        policy_version=str(raw.get("policy_version", SAFETY_POLICY_VERSION)),
        model=model,
        model_warning=model_warning,
        workflow_id=workflow.id if workflow else None,
        response_validation_status=status,
        source_summaries=_string_list(raw.get("source_summaries")),
        claimed_outcomes=_string_list(raw.get("claimed_outcomes")),
        sources=_model_list(raw.get("sources"), ResearchSource),
        extracted_claims=_model_list(raw.get("extracted_claims"), ExtractedClaim),
        suitability_scores=_model_list(raw.get("suitability_scores"), SuitabilityScore),
        next_steps=next_steps,
    )


def _validate_inputs(
    query: str,
    documents: list[str],
    max_document_chars: int | None = None,
    max_total_document_chars: int | None = None,
) -> None:
    _validate_query(query)
    _validate_documents(documents, max_document_chars, max_total_document_chars)


def _validate_query(query: str) -> None:
    if not query.strip():
        raise IngestionInputError("Query is required.")


def _validate_documents(
    documents: list[str],
    max_document_chars: int | None = None,
    max_total_document_chars: int | None = None,
) -> None:
    settings = load_settings()
    per_doc_limit = (
        settings.max_document_chars if max_document_chars is None else max_document_chars
    )
    total_limit = (
        settings.max_total_document_chars
        if max_total_document_chars is None
        else max_total_document_chars
    )
    if per_doc_limit is not None and per_doc_limit <= 0:
        raise IngestionInputError("Per-document character limit must be greater than 0.")
    if total_limit is not None and total_limit <= 0:
        raise IngestionInputError("Total source character limit must be greater than 0.")
    total_chars = 0
    for i, doc in enumerate(documents, 1):
        doc_len = len(doc)
        total_chars += doc_len
        if per_doc_limit is not None and doc_len > per_doc_limit:
            raise IngestionInputError(
                f"Document {i} is too large ({doc_len:,} chars). "
                f"Limit each source to {per_doc_limit:,} chars."
            )
    if total_limit is not None and total_chars > total_limit:
        raise IngestionInputError(
            f"Sources are too large in total ({total_chars:,} chars). "
            f"Limit all sources to {total_limit:,} chars."
        )


async def _resolve_documents(documents: list[str]) -> list[str]:
    resolved: list[str] = []
    async with httpx.AsyncClient(timeout=SOURCE_FETCH_TIMEOUT_S, follow_redirects=True) as client:
        for doc in documents:
            source = doc.strip()
            if not _is_url_source(source):
                resolved.append(doc)
                continue
            resolved.append(await _fetch_url_source(client, source))
    return resolved


def _is_url_source(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and "\n" not in source


async def _fetch_url_source(client: httpx.AsyncClient, url: str) -> str:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise IngestionInputError(f"Could not fetch source URL {url}: {error}") from error

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" in content_type:
        text = _html_to_text(response.text)
    elif content_type.startswith("text/") or "json" in content_type or "xml" in content_type:
        text = response.text
    else:
        text = (
            f"Source URL: {url}\n"
            f"Content type: {content_type or 'unknown'}\n"
            "The linked resource was not directly text-readable. Upload a text PDF or paste "
            "the article text if the source content is needed."
        )
    return f"Source URL: {url}\n\n{text.strip()}"


def _html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.text()


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag in {"p", "br", "li", "section", "article", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in {"p", "li", "section", "article"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        return " ".join("".join(self._parts).split())


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _enum_or_default[EnumT: Enum](value: object, enum_type: type[EnumT], default: EnumT) -> EnumT:
    try:
        return enum_type(str(value))
    except ValueError:
        return default


def _model_list[ModelT: BaseModel](value: object, model_type: type[ModelT]) -> list[ModelT]:
    if not isinstance(value, list):
        return []
    result: list[ModelT] = []
    for item in value:
        if isinstance(item, dict):
            result.append(model_type.model_validate(item))
    return result
