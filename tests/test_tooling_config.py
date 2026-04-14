import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hk_pkl_config_has_declared_pkl_cli() -> None:
    """Clean CI runners need pkl to load hk.pkl before any hook can run."""
    mise_config = ROOT / "mise.toml"
    hk_config = ROOT / "hk.pkl"

    tools = tomllib.loads(mise_config.read_text(encoding="utf-8"))["tools"]

    assert hk_config.exists()
    assert "pkl" in tools


def test_ci_check_job_exports_zizmor_token_name() -> None:
    """The hk zizmor built-in reads GITHUB_TOKEN when CI runs raw hook commands."""
    ci_workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "GITHUB_TOKEN: ${{ github.token }}" in ci_workflow
    assert "GH_TOKEN: ${{ github.token }}" not in ci_workflow
