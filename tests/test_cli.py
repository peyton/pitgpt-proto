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
        assert "brief" in result.stdout
        assert "power" in result.stdout
        assert "doctor" in result.stdout
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


class TestClaudeRankedCLI:
    def test_power_outputs_sample_size_json(self):
        result = runner.invoke(
            app,
            [
                "power",
                "--effect",
                "1",
                "--sigma",
                "1",
                "--power",
                "0.8",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["observations_per_condition"] > 0
        assert data["total_observations"] == data["observations_per_condition"] * 2

    def test_doctor_outputs_json(self):
        result = runner.invoke(app, ["doctor", "--format", "json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "checks" in data
        assert any(item["name"] == "Document limits" for item in data["checks"])

    def test_brief_outputs_summary_json(self, tmp_path):
        proto, obs = _write_small_trial(tmp_path)

        result = runner.invoke(
            app,
            [
                "brief",
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
        assert data["quality_grade"] in {"A", "B", "C", "D"}
        assert "summary" in data

    def test_trial_status_export_import_and_amend(self, tmp_path):
        proto, obs = _write_small_trial(tmp_path)

        status = runner.invoke(
            app,
            [
                "trial",
                "status",
                "--protocol",
                str(proto),
                "--observations",
                str(obs),
                "--format",
                "json",
            ],
        )
        assert status.exit_code == 0
        assert json.loads(status.stdout)["current_day"] == 4

        bundle = tmp_path / "bundle.json"
        exported = runner.invoke(
            app,
            [
                "trial",
                "export",
                "--protocol",
                str(proto),
                "--observations",
                str(obs),
                "--output",
                str(bundle),
            ],
        )
        assert exported.exit_code == 0
        assert bundle.exists()

        imported_dir = tmp_path / "imported"
        imported = runner.invoke(
            app,
            [
                "trial",
                "import",
                "--bundle",
                str(bundle),
                "--output-dir",
                str(imported_dir),
            ],
        )
        assert imported.exit_code == 0
        assert (imported_dir / "protocol.json").exists()
        assert (imported_dir / "observations.csv").exists()

        amended = runner.invoke(
            app,
            [
                "trial",
                "amend",
                "--protocol",
                str(proto),
                "--field",
                "minimum_meaningful_difference",
                "--value",
                "0.8",
                "--reason",
                "Set before analysis.",
            ],
        )
        assert amended.exit_code == 0
        amended_protocol = json.loads(proto.read_text())
        assert amended_protocol["minimum_meaningful_difference"] == "0.8"
        assert amended_protocol["amendments"][0]["reason"] == "Set before analysis."


def _write_small_trial(tmp_path):
    proto = tmp_path / "protocol.json"
    proto.write_text(
        json.dumps(
            {
                "planned_days": 4,
                "block_length_days": 2,
                "condition_a_label": "Morning",
                "condition_b_label": "Evening",
            }
        )
    )
    obs = tmp_path / "observations.csv"
    obs.write_text(
        "\n".join(
            [
                "day_index,date,condition,primary_score,irritation,adherence,note,is_backfill,backfill_days",
                "1,2026-01-01,A,8,no,yes,,no,",
                "2,2026-01-02,A,7,no,yes,,no,",
                "3,2026-01-03,B,5,no,yes,,no,",
                "4,2026-01-04,B,6,no,yes,,no,",
            ]
        )
    )
    return proto, obs
