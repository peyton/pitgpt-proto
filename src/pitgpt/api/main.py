import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from pitgpt.core.analysis import analyze
from pitgpt.core.ingestion import IngestionInputError, ingest
from pitgpt.core.llm import LLMClient, LLMError
from pitgpt.core.models import (
    AnalysisProtocol,
    IngestionResult,
    Observation,
    ResultCard,
    ScheduleAssignment,
)
from pitgpt.core.schedule import generate_schedule
from pitgpt.core.settings import load_settings
from pitgpt.core.templates import templates_as_dicts

app = FastAPI(title="PitGPT", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("PITGPT_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    query: str = Field(examples=["Compare CeraVe and La Roche-Posay for evening skin comfort"])
    documents: list[str] = Field(default_factory=list)
    model: str | None = None


class AnalyzeRequest(BaseModel):
    protocol: AnalysisProtocol
    observations: list[Observation]


class ScheduleRequest(BaseModel):
    duration_weeks: int = Field(gt=0, examples=[6])
    block_length_days: int = Field(gt=0, examples=[7])
    seed: int = Field(ge=0, examples=[12345])


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/templates")
async def templates():
    return {"templates": templates_as_dicts()}


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
async def ingest_endpoint(req: IngestRequest):
    settings = load_settings()
    api_key = settings.openrouter_api_key
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY not set")
    client = LLMClient(
        model=req.model or settings.default_model,
        api_key=api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout_s=settings.llm_timeout_s,
    )
    try:
        return await ingest(req.query, req.documents, client, req.model or settings.default_model)
    except IngestionInputError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except (KeyError, ValidationError, ValueError) as e:
        raise HTTPException(
            status_code=502,
            detail=f"Provider response failed validation: {e}",
        ) from e
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/analyze", response_model=ResultCard)
async def analyze_endpoint(req: AnalyzeRequest):
    return analyze(req.protocol, req.observations)
