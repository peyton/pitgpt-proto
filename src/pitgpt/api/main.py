import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pitgpt.core.analysis import analyze
from pitgpt.core.ingestion import ingest
from pitgpt.core.llm import LLMClient, LLMError
from pitgpt.core.models import AnalysisProtocol, IngestionResult, Observation, ResultCard
from pitgpt.core.settings import load_settings

app = FastAPI(title="PitGPT", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("PITGPT_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    query: str
    documents: list[str] = Field(default_factory=list)
    model: str | None = None


class AnalyzeRequest(BaseModel):
    protocol: AnalysisProtocol
    observations: list[Observation]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestionResult)
async def ingest_endpoint(req: IngestRequest):
    settings = load_settings()
    api_key = settings.openrouter_api_key
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set")
    client = LLMClient(
        model=req.model or settings.default_model,
        api_key=api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout_s=settings.llm_timeout_s,
    )
    try:
        return await ingest(req.query, req.documents, client)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/analyze", response_model=ResultCard)
async def analyze_endpoint(req: AnalyzeRequest):
    return analyze(req.protocol, req.observations)
