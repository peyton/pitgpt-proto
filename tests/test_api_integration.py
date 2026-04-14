"""HTTP-boundary integration tests for the FastAPI app."""

import json
from unittest.mock import patch

import httpx
import respx
from fastapi.testclient import TestClient

from pitgpt.api.main import app


def _mock_llm_response(response_data: dict):
    return {"choices": [{"message": {"content": json.dumps(response_data)}}]}


def _green_ingestion_payload():
    return {
        "decision": "generate_protocol",
        "safety_tier": "GREEN",
        "evidence_quality": "moderate",
        "evidence_conflict": False,
        "protocol": {
            "template": "Skincare Product",
            "duration_weeks": 6,
            "block_length_days": 7,
            "cadence": "daily",
            "washout": "None",
            "primary_outcome_question": "Skin satisfaction (0-10)",
            "screening": "",
            "warnings": "",
        },
        "block_reason": None,
        "user_message": "Ready to compare two everyday products.",
    }


class TestIngestIntegration:
    @respx.mock
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    def test_ingest_uses_llm_client_and_passes_documents(self):
        route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_mock_llm_response(_green_ingestion_payload()))
        )

        client = TestClient(app)
        resp = client.post(
            "/ingest",
            json={
                "query": "Compare CeraVe and La Roche-Posay",
                "documents": ["Source text about cosmetic comfort outcomes."],
                "model": "test/model",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["decision"] == "generate_protocol"
        assert route.called

        llm_payload = json.loads(route.calls[0].request.content)
        assert llm_payload["model"] == "test/model"
        user_message = llm_payload["messages"][1]["content"]
        assert "User query: Compare CeraVe and La Roche-Posay" in user_message
        assert "--- Uploaded Document 1 ---" in user_message
        assert "Source text about cosmetic comfort outcomes." in user_message

    @respx.mock
    @patch.dict(
        "os.environ",
        {"PITGPT_OLLAMA_BASE_URL": "http://ollama.test", "PITGPT_OLLAMA_MODEL": "llama3.1"},
    )
    def test_ingest_can_use_ollama_provider(self):
        route = respx.post("http://ollama.test/api/chat").mock(
            return_value=httpx.Response(
                200,
                json={"message": {"content": json.dumps(_green_ingestion_payload())}},
            )
        )

        client = TestClient(app)
        resp = client.post(
            "/ingest",
            json={
                "query": "Compare CeraVe and La Roche-Posay",
                "documents": [],
                "model": "llama3.1:latest",
                "provider": "ollama",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["model"] == "llama3.1:latest"
        assert route.called

        payload = json.loads(route.calls[0].request.content)
        assert payload["model"] == "llama3.1:latest"
        assert payload["format"] == "json"


class TestAnalyzeIntegration:
    def test_analyze_reports_integrity_fields_through_http_boundary(self):
        client = TestClient(app)
        protocol = {"planned_days": 14, "block_length_days": 7}
        observations = [
            {
                "day_index": day,
                "date": f"2026-01-{day:02d}",
                "condition": "A",
                "primary_score": 7.0,
                "irritation": "no",
                "adherence": "yes",
                "note": "",
                "is_backfill": "no",
                "backfill_days": None,
            }
            for day in range(1, 7)
        ] + [
            {
                "day_index": day,
                "date": f"2026-01-{day:02d}",
                "condition": "B",
                "primary_score": 5.0,
                "irritation": "no",
                "adherence": "yes",
                "note": "",
                "is_backfill": "no",
                "backfill_days": None,
            }
            for day in range(7, 12)
        ]
        observations.append(
            {
                "day_index": 12,
                "date": "2026-01-12",
                "condition": "B",
                "primary_score": 4.0,
                "irritation": "no",
                "adherence": "yes",
                "note": "Late entry",
                "is_backfill": "yes",
                "backfill_days": 3,
            }
        )

        resp = client.post("/analyze", json={"protocol": protocol, "observations": observations})

        assert resp.status_code == 200
        data = resp.json()
        assert data["quality_grade"] == "C"
        assert data["early_stop"] is True
        assert data["late_backfill_excluded"] == 1
        assert "Early termination" in data["caveats"]
        assert "late-backfill day(s) excluded" in data["caveats"]

    def test_invalid_payload_returns_validation_error(self):
        client = TestClient(app)
        resp = client.post("/analyze", json={"observations": []})

        assert resp.status_code == 422
