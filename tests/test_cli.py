"""Test CLI commands."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from pitgpt.cli.main import app

runner = CliRunner()


class TestAnalyzeCLI:
    def test_help_shows_documented_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ingest" in result.stdout
        assert "analyze" in result.stdout
        assert "benchmark" in result.stdout
        assert "demo" in result.stdout
        assert "trial" in result.stdout
        assert "checkin" in result.stdout
        assert "ingest-cmd" not in result.stdout
        assert "analyze-cmd" not in result.stdout

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
                "analyze",
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
                "analyze",
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
                "ingest",
                "--query",
                "Test",
            ],
        )
        assert result.exit_code == 1


class TestProgressiveDisclosureCLI:
    def test_demo_analyze_json_output(self):
        result = runner.invoke(app, ["demo", "analyze", "--format", "json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["quality_grade"] in {"A", "B", "C", "D"}

    def test_trial_randomize_uses_block_length_days(self, tmp_path):
        proto = tmp_path / "protocol.json"
        proto.write_text(json.dumps({"duration_weeks": 6, "block_length_days": 14}))

        result = runner.invoke(
            app,
            ["trial", "randomize", "--protocol", str(proto), "--seed", "123", "--format", "json"],
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["assignments"]) == 3
        assert data["assignments"][0]["start_day"] == 1
        assert data["assignments"][-1]["end_day"] == 42

    def test_checkin_add_guards_duplicate_day(self, tmp_path):
        obs = tmp_path / "observations.csv"
        base_args = [
            "checkin",
            "add",
            "--observations",
            str(obs),
            "--day",
            "1",
            "--date",
            "2026-01-01",
            "--condition",
            "A",
            "--score",
            "7",
        ]

        first = runner.invoke(app, base_args)
        second = runner.invoke(app, base_args)

        assert first.exit_code == 0
        assert second.exit_code == 1

    def test_validate_reports_warnings_as_json(self, tmp_path):
        proto = tmp_path / "protocol.json"
        proto.write_text(json.dumps({"planned_days": 7, "block_length_days": 7}))
        obs = tmp_path / "observations.csv"
        obs.write_text(
            "\n".join(
                [
                    "day_index,date,condition,primary_score,irritation,adherence,note,is_backfill,backfill_days",
                    "1,2026-01-01,A,7,no,yes,,no,",
                    "3,2026-01-03,B,6,no,yes,,no,",
                ]
            )
        )

        result = runner.invoke(
            app,
            [
                "validate",
                "--protocol",
                str(proto),
                "--observations",
                str(obs),
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        assert "Missing day_index" in " ".join(json.loads(result.stdout)["warnings"])
