import json
from pathlib import Path

RUNS_DIR = Path(__file__).parent / "runs"


def generate_report() -> dict:
    if not RUNS_DIR.exists():
        return {"runs": [], "summary": "No benchmark runs found."}

    run_files = sorted(RUNS_DIR.glob("*.json"), reverse=True)
    if not run_files:
        return {"runs": [], "summary": "No benchmark runs found."}

    runs = []
    for rf in run_files:
        data = json.loads(rf.read_text())
        cases = data.get("cases", [])

        track_a = [c for c in cases if c.get("track") == "ingestion"]
        track_b = [c for c in cases if c.get("track") == "analysis"]

        track_a_score = sum(c["score"] for c in track_a) / len(track_a) if track_a else 0.0
        track_b_score = sum(c["score"] for c in track_b) / len(track_b) if track_b else 0.0
        overall = data.get("summary", {}).get("mean_score", 0.0)

        runs.append(
            {
                "model": data.get("model", "unknown"),
                "timestamp": data.get("timestamp", ""),
                "track_a_score": round(track_a_score, 4),
                "track_b_score": round(track_b_score, 4),
                "overall_score": round(overall, 4),
                "total_cases": len(cases),
                "pass_count": sum(1 for c in cases if c["score"] >= 0.8),
                "file": rf.name,
            }
        )

    return {"runs": runs}
