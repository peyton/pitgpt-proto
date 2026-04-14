"""Test the FastAPI endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pitgpt.api.main import _parse_cors_origins, _request_id_from_header, app
from pitgpt.core.llm import LLMError
from pitgpt.core.models import (
    EvidenceQuality,
    IngestionDecision,
    IngestionResult,
    Protocol,
    SafetyTier,
)


@pytest.fixture
def api_client(monkeypatch):
    monkeypatch.delenv("PITGPT_API_TOKEN", raising=False)
    return TestClient(app)


class TestHealth:
    def test_health(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestReadEndpoints:
    def test_templates(self, api_client):
        resp = api_client.get("/templates")

        assert resp.status_code == 200
        assert len(resp.json()["templates"]) >= 1

    def test_providers(self, api_client):
        resp = api_client.get("/providers")

        assert resp.status_code == 200
        kinds = {item["kind"] for item in resp.json()}
        assert {
            "openrouter",
            "ollama",
            "claude_cli",
            "codex_cli",
            "chatgpt_cli",
            "ios_on_device",
        }.issubset(kinds)

    def test_schedule(self, api_client):
        resp = api_client.post(
            "/schedule",
            json={"duration_weeks": 6, "block_length_days": 14, "seed": 123},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["start_day"] == 1
        assert data[-1]["end_day"] == 42

    def test_analyze_example(self, api_client):
        resp = api_client.get("/analyze/example")

        assert resp.status_code == 200
        assert resp.json()["quality_grade"] in {"A", "B", "C", "D"}


class TestAnalyzeEndpoint:
    def test_simple_analysis(self, api_client):
        protocol = {"planned_days": 14, "block_length_days": 7}
        observations = [
            {
                "day_index": i + 1,
                "date": f"2026-01-{i + 1:02d}",
                "condition": "A",
                "primary_score": 7.0,
                "adherence": "yes",
                "is_backfill": "no",
            }
            for i in range(7)
        ] + [
            {
                "day_index": i + 8,
                "date": f"2026-01-{i + 8:02d}",
                "condition": "B",
                "primary_score": 5.0,
                "adherence": "yes",
                "is_backfill": "no",
            }
            for i in range(7)
        ]
        resp = api_client.post(
            "/analyze", json={"protocol": protocol, "observations": observations}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["quality_grade"] == "A"
        assert data["difference"] > 0

    def test_empty_observations(self, api_client):
        resp = api_client.post(
            "/analyze", json={"protocol": {"planned_days": 14}, "observations": []}
        )
        assert resp.status_code == 200
        assert resp.json()["quality_grade"] == "D"

    def test_invalid_protocol_rejected(self, api_client):
        resp = api_client.post(
            "/analyze", json={"protocol": {"planned_days": 0}, "observations": []}
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["message"] == "Request validation failed"
        assert "request_id" in resp.json()

    def test_invalid_observation_rejected(self, api_client):
        resp = api_client.post(
            "/analyze",
            json={
                "protocol": {"planned_days": 14},
                "observations": [
                    {
                        "day_index": 1,
                        "date": "2026-01-01",
                        "condition": "C",
                        "primary_score": 11,
                    }
                ],
            },
        )
        assert resp.status_code == 422
        assert resp.headers["X-Request-ID"]


class TestValidateEndpoint:
    def test_validate_reports_warnings(self, api_client):
        resp = api_client.post(
            "/validate",
            json={
                "protocol": {"planned_days": 7, "block_length_days": 7},
                "observations": [
                    {
                        "day_index": 1,
                        "date": "2026-01-01",
                        "condition": "A",
                        "primary_score": 7,
                    },
                    {
                        "day_index": 3,
                        "date": "2026-01-03",
                        "condition": "B",
                        "primary_score": 6,
                    },
                ],
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert "Missing day_index" in " ".join(data["warnings"])


class TestOptionalAuth:
    @patch.dict("os.environ", {"PITGPT_API_TOKEN": "secret"})
    def test_private_endpoint_requires_bearer_token(self):
        client = TestClient(app)

        unauthorized = client.get("/templates")
        authorized = client.get("/templates", headers={"Authorization": "Bearer secret"})

        assert unauthorized.status_code == 401
        assert unauthorized.json()["error"]["message"] == "Unauthorized"
        assert authorized.status_code == 200

    @patch.dict("os.environ", {"PITGPT_API_TOKEN": "secret"})
    def test_public_paths_remain_public(self):
        client = TestClient(app)

        assert client.get("/health").status_code == 200
        assert client.get("/openapi.json").status_code == 200

    def test_request_id_header_is_trimmed(self, api_client):
        resp = api_client.get("/health", headers={"X-Request-ID": " release-check "})

        assert resp.headers["X-Request-ID"] == "release-check"


class TestIngestEndpoint:
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    @patch("pitgpt.api.main.ingest")
    def test_ingest_success(self, mock_ingest, api_client):
        mock_ingest.return_value = IngestionResult(
            decision=IngestionDecision.GENERATE_PROTOCOL,
            safety_tier=SafetyTier.GREEN,
            evidence_quality=EvidenceQuality.NOVEL,
            protocol=Protocol(
                duration_weeks=6,
                block_length_days=7,
                cadence="daily",
                washout="None",
                primary_outcome_question="Test?",
            ),
            user_message="Ready.",
        )
        resp = api_client.post("/ingest", json={"query": "Test CeraVe vs Cetaphil"})
        assert resp.status_code == 200
        assert resp.json()["decision"] == "generate_protocol"

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    @patch("pitgpt.api.main.ingest")
    def test_ingest_defaults_to_openrouter_provider(self, mock_ingest, api_client):
        mock_ingest.return_value = IngestionResult(
            decision=IngestionDecision.GENERATE_PROTOCOL,
            safety_tier=SafetyTier.GREEN,
            evidence_quality=EvidenceQuality.NOVEL,
            protocol=Protocol(
                duration_weeks=6,
                block_length_days=7,
                cadence="daily",
                washout="None",
                primary_outcome_question="Test?",
            ),
            user_message="Ready.",
        )

        resp = api_client.post("/ingest", json={"query": "Test CeraVe vs Cetaphil"})

        assert resp.status_code == 200
        assert mock_ingest.call_args.args[3] == "anthropic/claude-sonnet-4"

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""})
    def test_ingest_no_api_key(self, api_client):
        resp = api_client.post("/ingest", json={"query": "Test"})
        assert resp.status_code == 503
        assert resp.json()["error"]["message"] == "OPENROUTER_API_KEY not set"
        assert "X-Request-ID" in resp.headers

    def test_unsupported_provider_rejected(self, api_client):
        resp = api_client.post(
            "/ingest",
            json={"query": "Test", "provider": "ios_on_device"},
        )

        assert resp.status_code == 400
        assert "not supported" in resp.json()["detail"]

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    @patch("pitgpt.api.main.ingest", side_effect=LLMError("malformed provider response"))
    def test_ingest_llm_error(self, mock_ingest, api_client):
        resp = api_client.post("/ingest", json={"query": "Test"})
        assert resp.status_code == 502
        assert "malformed provider response" in resp.json()["detail"]

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"})
    @patch("pitgpt.api.main.ingest", side_effect=ValueError("generated protocol required"))
    def test_ingest_validation_error(self, mock_ingest, api_client):
        resp = api_client.post("/ingest", json={"query": "Test"})
        assert resp.status_code == 502
        assert "Provider response failed validation" in resp.json()["detail"]


def test_cors_origins_are_trimmed_and_empty_values_are_ignored() -> None:
    assert _parse_cors_origins(" http://localhost:5173, https://pitgpt.test, ") == [
        "http://localhost:5173",
        "https://pitgpt.test",
    ]


def test_request_id_rejects_control_characters_and_long_values() -> None:
    generated = _request_id_from_header("bad\nvalue")
    too_long = _request_id_from_header("x" * 129)

    assert generated != "bad\nvalue"
    assert too_long != "x" * 129
