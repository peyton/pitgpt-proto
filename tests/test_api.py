"""Test the FastAPI endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pitgpt.api.main import app
from pitgpt.core.models import (
    EvidenceQuality,
    IngestionDecision,
    IngestionResult,
    Protocol,
    SafetyTier,
)


@pytest.fixture
def api_client():
    return TestClient(app)


class TestHealth:
    def test_health(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


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

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""})
    def test_ingest_no_api_key(self, api_client):
        resp = api_client.post("/ingest", json={"query": "Test"})
        assert resp.status_code == 500
