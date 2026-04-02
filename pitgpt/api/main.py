import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pitgpt.core.analysis import analyze
from pitgpt.core.ingestion import ingest
from pitgpt.core.llm import LLMClient, LLMError
from pitgpt.core.models import IngestionResult, Observation, ResultCard

app = FastAPI(title="PitGPT", version="0.1.0")


class IngestRequest(BaseModel):
    query: str
    documents: list[str] = []
    model: str = "anthropic/claude-sonnet-4"


class AnalyzeRequest(BaseModel):
    protocol: dict
    observations: list[Observation]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestionResult)
async def ingest_endpoint(req: IngestRequest):
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set")
    client = LLMClient(model=req.model, api_key=api_key)
    try:
        return await ingest(req.query, req.documents, client)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/analyze", response_model=ResultCard)
async def analyze_endpoint(req: AnalyzeRequest):
    return analyze(req.protocol, req.observations)
