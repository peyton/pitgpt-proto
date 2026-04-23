import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from pitgpt.core.analysis import analyze
from pitgpt.core.ingestion import CompletionClient, IngestionInputError, ingest
from pitgpt.core.llm import LLMClient, LLMError, OllamaClient
from pitgpt.core.models import (
    AnalysisProtocol,
    IngestionResult,
    Observation,
    ResultCard,
    ScheduleAssignment,
    ValidationReport,
)
from pitgpt.core.providers import ProviderInfo, ProviderKind, list_providers
from pitgpt.core.schedule import generate_schedule
from pitgpt.core.settings import load_settings
from pitgpt.core.templates import templates_as_dicts
from pitgpt.core.validation import validate_trial
from pitgpt.core.workflows import (
    WorkflowDefinition,
    WorkflowDemoPayload,
    get_workflow,
    list_workflows,
    resolve_workflow_model,
    workflow_demo_payload,
)


def _parse_cors_origins(value: str | None) -> list[str]:
    raw = value if value is not None else "http://localhost:5173"
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost:5173"]


def _request_id_from_header(value: str | None) -> str:
    if value is None:
        return str(uuid4())
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 128 or any(char in cleaned for char in "\r\n"):
        return str(uuid4())
    return cleaned


app = FastAPI(title="PitGPT", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(os.environ.get("PITGPT_CORS_ORIGINS")),
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    query: str = Field(
        min_length=1,
        examples=["Compare CeraVe and La Roche-Posay for evening skin comfort"],
    )
    documents: list[str] = Field(default_factory=list)
    model: str | None = None
    provider: ProviderKind | None = None
    workflow_id: str | None = None


class AnalyzeRequest(BaseModel):
    protocol: AnalysisProtocol
    observations: list[Observation]


class ScheduleRequest(BaseModel):
    duration_weeks: int = Field(gt=0, examples=[6])
    block_length_days: int = Field(gt=0, examples=[7])
    seed: int = Field(ge=0, examples=[12345])


class IngestStreamEvent(BaseModel):
    type: str
    message: str
    result: IngestionResult | None = None


@dataclass(frozen=True)
class IngestionSelection:
    client: CompletionClient
    model_id: str
    provider: ProviderKind
    model_warning: str | None = None


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = _request_id_from_header(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    settings = load_settings()
    if settings.api_token and request.url.path not in _PUBLIC_PATHS:
        expected = f"Bearer {settings.api_token}"
        if request.headers.get("Authorization") != expected:
            return JSONResponse(
                status_code=401,
                headers={"X-Request-ID": request_id},
                content={
                    "detail": "Unauthorized",
                    "request_id": request_id,
                    "error": {"code": 401, "message": "Unauthorized"},
                },
            )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


_PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


@app.exception_handler(HTTPException)
async def structured_http_exception(request: Request, exc: HTTPException):
    response = await http_exception_handler(request, exc)
    request_id = getattr(request.state, "request_id", "")
    detail = exc.detail
    message = detail if isinstance(detail, str) else str(detail)
    return JSONResponse(
        status_code=response.status_code,
        headers={"X-Request-ID": request_id},
        content={
            "detail": message,
            "request_id": request_id,
            "error": {
                "code": response.status_code,
                "message": message,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def structured_request_validation_exception(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "")
    message = "Request validation failed"
    return JSONResponse(
        status_code=422,
        headers={"X-Request-ID": request_id},
        content={
            "detail": jsonable_encoder(exc.errors()),
            "request_id": request_id,
            "error": {
                "code": 422,
                "message": message,
            },
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/templates")
async def templates():
    return {"templates": templates_as_dicts()}


@app.get("/providers", response_model=list[ProviderInfo])
async def providers():
    return list_providers()


@app.get("/workflows", response_model=list[WorkflowDefinition])
async def workflows():
    return list_workflows()


@app.get("/workflows/{workflow_id}/demo", response_model=WorkflowDemoPayload)
async def workflow_demo(workflow_id: str):
    workflow = _resolve_workflow(workflow_id)
    assert workflow is not None
    return workflow_demo_payload(workflow)


@app.post("/schedule", response_model=list[ScheduleAssignment])
async def schedule_endpoint(req: ScheduleRequest):
    return generate_schedule(req.duration_weeks, req.block_length_days, req.seed)


@app.get("/analyze/example", response_model=ResultCard)
async def analyze_example_endpoint():
    from pathlib import Path

    from pitgpt.core.io import load_analysis_protocol, parse_observations_csv_file

    repo_root = Path(__file__).resolve().parents[3]
    protocol = load_analysis_protocol(repo_root / "examples" / "protocol.json")
    observations = parse_observations_csv_file(repo_root / "examples" / "observations.csv")
    return analyze(protocol, observations)


@app.post("/ingest", response_model=IngestionResult)
async def ingest_endpoint(req: IngestRequest, response: Response):
    workflow = _resolve_workflow(req.workflow_id)
    selection = _ingestion_client(req, workflow)
    if selection.model_warning:
        response.headers["X-Model-Warning"] = selection.model_warning
    try:
        return await ingest(
            req.query,
            req.documents,
            selection.client,
            selection.model_id,
            workflow=workflow,
            model_warning=selection.model_warning,
        )
    except IngestionInputError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except (KeyError, ValidationError, ValueError) as e:
        raise HTTPException(
            status_code=502,
            detail=f"Provider response failed validation: {e}",
        ) from e
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/experiments/ingest-stream")
async def ingest_stream_endpoint(req: IngestRequest):
    workflow = _resolve_workflow(req.workflow_id)
    selection = _ingestion_client(req, workflow)
    return StreamingResponse(
        _ingest_stream_events(req, selection, workflow),
        media_type="application/x-ndjson",
    )


def _ingestion_client(
    req: IngestRequest, workflow: WorkflowDefinition | None
) -> IngestionSelection:
    settings = load_settings()
    provider = req.provider or (
        workflow.recommended_provider if workflow else ProviderKind.OPENROUTER
    )
    warnings: list[str] = []
    if provider == ProviderKind.OPENROUTER and not settings.openrouter_api_key:
        if workflow and req.provider is None:
            provider = ProviderKind.OLLAMA
            warnings.append(
                "OPENROUTER_API_KEY was not set for this MedGemma workflow, "
                "so local Ollama fallback was used."
            )
        else:
            raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY not set")

    if provider == ProviderKind.OPENROUTER:
        model_id, warning = resolve_workflow_model(
            workflow=workflow,
            provider=provider,
            requested_model=req.model,
            fallback_model=settings.default_model,
            settings=settings,
            env=os.environ,
        )
        if warning:
            warnings.append(warning)
        client: CompletionClient = LLMClient(
            model=model_id,
            api_key=settings.openrouter_api_key,
            base_url=settings.llm_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout_s=settings.llm_timeout_s,
        )
    elif provider == ProviderKind.OLLAMA:
        model_id, warning = resolve_workflow_model(
            workflow=workflow,
            provider=provider,
            requested_model=req.model,
            fallback_model=settings.ollama_default_model,
            settings=settings,
            env=os.environ,
        )
        if warning:
            warnings.append(warning)
        client = OllamaClient(
            model=model_id,
            base_url=settings.ollama_base_url,
            temperature=settings.llm_temperature,
            timeout_s=settings.llm_timeout_s,
        )
    else:
        raise HTTPException(
            status_code=400, detail=f"Provider {provider.value} is not supported by API"
        )
    warning_text = " ".join(warnings).strip() or None
    return IngestionSelection(
        client=client,
        model_id=model_id,
        provider=provider,
        model_warning=warning_text,
    )


async def _ingest_stream_events(
    req: IngestRequest,
    selection: IngestionSelection,
    workflow: WorkflowDefinition | None,
) -> AsyncIterator[str]:
    if selection.model_warning:
        yield _stream_event("trace", selection.model_warning)
    yield _stream_event("trace", "Reading your experiment question.")
    if req.documents:
        yield _stream_event("trace", f"Reviewing {len(req.documents)} attached source(s).")
    yield _stream_event("trace", "Checking safety boundaries and trial fit.")
    yield _stream_event("trace", "Drafting follow-up questions or a protocol.")
    try:
        result = await ingest(
            req.query,
            req.documents,
            selection.client,
            selection.model_id,
            workflow=workflow,
            model_warning=selection.model_warning,
        )
    except IngestionInputError as e:
        yield _stream_event("error", str(e))
        return
    except (KeyError, ValidationError, ValueError) as e:
        yield _stream_event("error", f"Provider response failed validation: {e}")
        return
    except LLMError as e:
        yield _stream_event("error", str(e))
        return

    if result.decision == "manual_review_before_protocol":
        yield _stream_event("trace", "Follow-up questions are ready.")
    elif result.decision == "block":
        yield _stream_event("trace", "This request is outside the supported experiment scope.")
    else:
        yield _stream_event("trace", "Protocol draft is ready for review.")
    yield _stream_event("result", "Experiment setup complete.", result)


def _stream_event(
    event_type: str,
    message: str,
    result: IngestionResult | None = None,
) -> str:
    event = IngestStreamEvent(type=event_type, message=message, result=result)
    return f"{json.dumps(jsonable_encoder(event), separators=(',', ':'))}\n"


def _resolve_workflow(workflow_id: str | None) -> WorkflowDefinition | None:
    if workflow_id is None:
        return None
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} was not found")
    return workflow


@app.post("/analyze", response_model=ResultCard)
async def analyze_endpoint(req: AnalyzeRequest):
    return analyze(req.protocol, req.observations)


@app.post("/validate", response_model=ValidationReport)
async def validate_endpoint(req: AnalyzeRequest):
    return validate_trial(req.protocol, req.observations)
