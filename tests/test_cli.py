"""Test CLI commands."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from pitgpt.cli.main import app

runner = CliRunner()


class TestAnalyzeCLI:
    def test_analyze_json_output(self, tmp_path):
        proto = tmp_path / "protocol.json"
        proto.write_text(json.dumps({"planned_days": 14, "block_length_days": 7}))

        obs = tmp_path / "observations.csv"
        lines = [
            "day_index,date,condition,primary_score,irritation,adherence,note,is_backfill,backfill_days"
        ]
        for i in range(7):
            lines.append(f"{i + 1},2026-01-{i + 1:02d},A,7.0,no,yes,,no,")
        for i in range(7):
            lines.append(f"{i + 8},2026-01-{i + 8:02d},B,5.0,no,yes,,no,")
        obs.write_text("\n".join(lines))

        result = runner.invoke(
            app,
            [
                "analyze-cmd",
                "--protocol",
                str(proto),
                "--observations",
                str(obs),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["quality_grade"] == "A"

    def test_analyze_missing_file(self):
        result = runner.invoke(
            app,
            [
                "analyze-cmd",
                "--protocol",
                "/nonexistent/file.json",
                "--observations",
                "/nonexistent/obs.csv",
            ],
        )
        assert result.exit_code == 1


class TestIngestCLI:
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""})
    def test_ingest_no_api_key(self):
        result = runner.invoke(
            app,
            [
                "ingest-cmd",
                "--query",
                "Test",
            ],
        )
        assert result.exit_code == 1
