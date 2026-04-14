import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pitgpt.benchmarks.scoring import score_analysis, score_ingestion
from pitgpt.core.analysis import analyze
from pitgpt.core.ingestion import ingest
from pitgpt.core.io import load_analysis_protocol, parse_observations_csv_file, read_text_file
from pitgpt.core.llm import LLMClient
from pitgpt.core.settings import load_settings

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
CASES_FILE = BENCHMARKS_DIR / "cases.jsonl"
RUNS_DIR = BENCHMARKS_DIR / "runs"


def _load_cases(track: str, case_filter: list[str] | None) -> list[dict]:
    cases = []
    with open(CASES_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if track != "all" and case.get("stage") != track:
                continue
            if case_filter and case["case_id"] not in case_filter:
                continue
            cases.append(case)
    return cases


def _load_documents(doc_string: str) -> list[str]:
    if not doc_string:
        return []
    docs = []
    for part in doc_string.split("|"):
        part = part.strip()
        if not part:
            continue
        path = BENCHMARKS_DIR / part
        if path.exists():
            docs.append(read_text_file(path))
        else:
            txt_path = Path(str(path) + ".txt")
            if txt_path.exists():
                docs.append(read_text_file(txt_path))
    return docs


def _load_expected(case: dict[str, Any]) -> dict[str, Any]:
    output_file = case.get("expected_output_file", "")
    if not output_file:
        return {}
    path = BENCHMARKS_DIR / output_file
    if not path.exists():
        return {}
    loaded = json.loads(read_text_file(path))
    if not isinstance(loaded, dict):
        return {}
    return loaded


async def _run_ingestion_case(case: dict, client: LLMClient) -> dict:
    query = case.get("query", "")
    documents = _load_documents(case.get("documents", ""))
    expected = _load_expected(case)

    start = time.monotonic()
    try:
        result = await ingest(query, documents, client)
        elapsed = time.monotonic() - start
        scores = score_ingestion(result, expected)
        return {
            "case_id": case["case_id"],
            "track": "ingestion",
            "score": scores["overall"],
            "scores": scores,
            "result": result.model_dump(),
            "expected": expected,
            "elapsed_s": round(elapsed, 2),
            "error": None,
            "details": _ingestion_details(scores),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        return {
            "case_id": case["case_id"],
            "track": "ingestion",
            "score": 0.0,
            "scores": {},
            "result": None,
            "expected": expected,
            "elapsed_s": round(elapsed, 2),
            "error": str(e),
            "details": f"Error: {e}",
        }


def _run_analysis_case(case: dict) -> dict:
    expected = _load_expected(case)
    docs = case.get("documents", "")
    parts = [p.strip() for p in docs.split("|") if p.strip()]

    protocol_path = None
    observations_path = None
    for part in parts:
        p = BENCHMARKS_DIR / part
        if "protocol" in part and p.exists():
            protocol_path = p
        elif "observations" in part and p.exists():
            observations_path = p

    if not protocol_path or not observations_path:
        return {
            "case_id": case["case_id"],
            "track": "analysis",
            "score": 0.0,
            "scores": {},
            "result": None,
            "expected": expected,
            "elapsed_s": 0,
            "error": "Missing protocol or observations file",
            "details": "Missing files",
        }

    protocol = load_analysis_protocol(protocol_path)
    observations = parse_observations_csv_file(observations_path)

    start = time.monotonic()
    result = analyze(protocol, observations)
    elapsed = time.monotonic() - start

    scores = score_analysis(result, expected)
    return {
        "case_id": case["case_id"],
        "track": "analysis",
        "score": scores["overall"],
        "scores": scores,
        "result": result.model_dump(),
        "expected": expected,
        "elapsed_s": round(elapsed, 4),
        "error": None,
        "details": _analysis_details(scores),
    }


def _ingestion_details(scores: dict) -> str:
    parts = []
    for key in ["decision_match", "safety_tier_match", "evidence_quality_match", "template_match"]:
        val = scores.get(key, 0)
        mark = "pass" if val >= 1.0 else "FAIL"
        parts.append(f"{key}={mark}")
    return " | ".join(parts)


def _analysis_details(scores: dict) -> str:
    parts = []
    for key in ["grade_match", "difference_accuracy", "ci_accuracy", "early_stop_match"]:
        val = scores.get(key, 0)
        if key in ("grade_match", "early_stop_match"):
            mark = "pass" if val >= 1.0 else "FAIL"
            parts.append(f"{key}={mark}")
        else:
            parts.append(f"{key}={val:.2f}")
    return " | ".join(parts)


async def run_benchmark(
    model: str,
    track: str = "all",
    case_filter: list[str] | None = None,
) -> dict:
    cases = _load_cases(track, case_filter)
    settings = load_settings()
    api_key = settings.openrouter_api_key
    client = (
        LLMClient(
            model=model,
            api_key=api_key,
            base_url=settings.llm_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout_s=settings.llm_timeout_s,
        )
        if api_key
        else None
    )

    results = []
    for case in cases:
        if case["stage"] == "ingestion":
            if not client:
                results.append(
                    {
                        "case_id": case["case_id"],
                        "track": "ingestion",
                        "score": 0.0,
                        "scores": {},
                        "result": None,
                        "error": "OPENROUTER_API_KEY not set",
                        "details": "Skipped: no API key",
                    }
                )
                continue
            r = await _run_ingestion_case(case, client)
        else:
            r = _run_analysis_case(case)
        results.append(r)

    total = len(results)
    pass_count = sum(1 for r in results if r["score"] >= 0.8)
    mean_score = sum(r["score"] for r in results) / total if total > 0 else 0.0

    run_result = {
        "model": model,
        "track": track,
        "timestamp": datetime.now(UTC).isoformat(),
        "cases": results,
        "summary": {
            "total": total,
            "pass_count": pass_count,
            "mean_score": round(mean_score, 4),
        },
    }

    _save_run(run_result, model)
    return run_result


def _save_run(result: dict, model: str):
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    slug = model.replace("/", "_").replace(" ", "_")
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = RUNS_DIR / f"{ts}_{slug}.json"
    path.write_text(json.dumps(result, indent=2, default=str))
