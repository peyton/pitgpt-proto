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


def test_hk_ruff_steps_use_project_environment() -> None:
    """Clean CI runners need Ruff from the uv-managed project environment."""
    hk_config = (ROOT / "hk.pkl").read_text(encoding="utf-8")

    assert 'check_diff = "uv run --python 3.12 ruff format' in hk_config
    assert 'fix = "uv run --python 3.12 ruff format' in hk_config
    assert 'check = "uv run --python 3.12 ruff check' in hk_config
    assert 'fix = "uv run --python 3.12 ruff check' in hk_config


def test_macos_preview_release_is_scoped_to_native_app_changes() -> None:
    """Preview releases should only publish from master native app changes."""
    preview_workflow = (ROOT / ".github" / "workflows" / "macos-preview-release.yml").read_text(
        encoding="utf-8",
    )
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8",
    )

    assert "branches: [master]" in preview_workflow
    assert "PREVIEW_TAG: macos-preview" in preview_workflow
    assert '"src-tauri/**"' in preview_workflow
    assert '"web/**"' in preview_workflow
    assert '"shared/**"' in preview_workflow
    assert "contents: write" in preview_workflow
    assert "github.event.release.tag_name != 'macos-preview'" in release_workflow
