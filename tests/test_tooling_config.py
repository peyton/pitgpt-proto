import json
import os
import re
import subprocess
import tempfile
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


def test_repo_managed_cli_tools_are_pinned() -> None:
    """Local automation should not depend on global or moving latest CLIs."""
    tools = tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8"))["tools"]

    assert re.fullmatch(r"\d+\.\d+\.\d+", tools["just"])
    for name in ("actionlint", "zizmor", "act", "cocoapods"):
        assert tools[name] != "latest"
        assert re.fullmatch(r"\d+\.\d+\.\d+", tools[name])


def test_ios_workflows_use_mise_managed_cocoapods() -> None:
    """iOS CI should use the pinned mise CocoaPods tool instead of Homebrew."""
    ci_workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8",
    )

    assert "cocoapods" in tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8"))["tools"]
    assert "brew install cocoapods" not in ci_workflow
    assert "brew install cocoapods" not in release_workflow


def test_renovate_groups_tauri_dependency_updates() -> None:
    """Tauri npm and Cargo packages should update together to avoid version skew."""
    renovate_config = json.loads((ROOT / "renovate.json").read_text(encoding="utf-8"))
    tauri_rules = [
        rule
        for rule in renovate_config["packageRules"]
        if rule.get("groupName") == "tauri dependencies"
    ]

    assert tauri_rules
    assert "/^@tauri-apps\\//" in tauri_rules[0]["matchPackageNames"]
    assert "/^tauri(-.*)?$/" in tauri_rules[0]["matchPackageNames"]


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
    assert "scripts/publish-macos-preview.sh" in preview_workflow
    assert '"app/**"' in preview_workflow
    assert '"web/**"' in preview_workflow
    assert '"shared/**"' in preview_workflow
    assert "contents: write" in preview_workflow
    assert "github.event.release.tag_name != 'macos-preview'" in release_workflow


def test_ci_workflow_has_bounded_pinned_jobs() -> None:
    """CI should not drift on ubuntu-latest or run forever on stuck jobs."""
    ci_workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    dependabot_workflow = (ROOT / ".github" / "workflows" / "dependabot-auto-merge.yml").read_text(
        encoding="utf-8"
    )

    assert "concurrency:" in ci_workflow
    assert "cancel-in-progress: true" in ci_workflow
    assert "ubuntu-latest" not in ci_workflow
    assert "ubuntu-latest" not in dependabot_workflow
    assert ci_workflow.count("timeout-minutes:") >= 7
    assert "timeout-minutes: 10" in dependabot_workflow


def test_release_workflows_use_shared_apple_scripts() -> None:
    """Apple signing and artifact checks should live in testable repo scripts."""
    ci_workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    preview_workflow = (ROOT / ".github" / "workflows" / "macos-preview-release.yml").read_text(
        encoding="utf-8",
    )
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8",
    )
    combined = "\n".join([ci_workflow, preview_workflow, release_workflow])

    assert (
        "scripts/apple-release-preflight.sh macos-dmg --github-output-availability" in ci_workflow
    )
    assert combined.count("scripts/apple-release-preflight.sh macos-dmg --write-files") == 3
    assert "scripts/apple-release-preflight.sh ios-appstore --write-files" in release_workflow
    assert combined.count("scripts/collect-tauri-artifacts.sh macos-dmg") == 2
    assert "scripts/collect-tauri-artifacts.sh ios-ipa" in release_workflow
    assert 'APPLE_API_KEY_P8_B64" | base64 -d' not in combined
    assert "find app/target/release/bundle -type f -name '*.dmg'" not in combined


def test_ios_release_uses_app_store_connect_export_with_build_number() -> None:
    """Official iOS release artifacts should target App Store Connect, not simulator/TestFlight."""
    release_workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8",
    )

    assert "TAURI_BUILD_NUMBER: ${{ github.run_number }}" in release_workflow
    assert "--export-method app-store-connect" in release_workflow
    assert '--build-number "$TAURI_BUILD_NUMBER"' in release_workflow
    assert "--export-method release-testing" not in release_workflow


def test_apple_release_scripts_report_missing_secret_modes() -> None:
    """The preflight script supports optional CI skip mode and required release mode."""
    script = ROOT / "scripts" / "apple-release-preflight.sh"
    assert os.access(script, os.X_OK)

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_file = Path(tmp_dir) / "github-output.txt"
        env = {
            "GITHUB_OUTPUT": str(output_file),
            "HOME": tmp_dir,
            "PATH": os.environ["PATH"],
        }
        optional = subprocess.run(
            [str(script), "macos-dmg", "--github-output-availability"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        required = subprocess.run(
            [str(script), "ios-appstore"],
            cwd=ROOT,
            env={"HOME": tmp_dir, "PATH": os.environ["PATH"]},
            text=True,
            capture_output=True,
            check=False,
        )
        output_text = output_file.read_text(encoding="utf-8")

    assert optional.returncode == 0
    assert "available=false" in output_text
    assert "Skipping Apple release step" in optional.stdout
    assert required.returncode != 0
    assert "Missing Apple signing secret" in required.stdout


def test_ios_release_preflight_writes_private_files(tmp_path: Path) -> None:
    """Decoded iOS release files should not be left world-readable on runners."""
    script = ROOT / "scripts" / "apple-release-preflight.sh"
    profile_path = tmp_path / "PitGPT.mobileprovision"
    api_key_path = tmp_path / "AuthKey.p8"
    env = {
        "APPLE_API_ISSUER": "issuer",
        "APPLE_API_KEY": "key",
        "APPLE_API_KEY_P8_B64": "a2V5",
        "APPLE_CERTIFICATE": "cert",
        "APPLE_CERTIFICATE_PASSWORD": "password",
        "APPLE_DEVELOPMENT_TEAM": "team",
        "APPLE_SIGNING_IDENTITY": "identity",
        "IOS_PROVISIONING_PROFILE_B64": "cHJvZmlsZQ==",
        "APPLE_API_KEY_PATH": str(api_key_path),
        "IOS_PROVISIONING_PROFILE_PATH": str(profile_path),
        "HOME": str(tmp_path),
        "PATH": os.environ["PATH"],
    }

    result = subprocess.run(
        [str(script), "ios-appstore", "--write-files"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert api_key_path.read_text(encoding="utf-8") == "key"
    assert profile_path.read_text(encoding="utf-8") == "profile"
    assert oct(api_key_path.stat().st_mode & 0o777) == "0o600"
    assert oct(profile_path.stat().st_mode & 0o777) == "0o600"


def test_tauri_ios_npm_shim_rejects_non_repo_root(tmp_path: Path) -> None:
    """The iOS npm shim should fail clearly instead of creating stray files elsewhere."""
    script = ROOT / "scripts" / "tauri-ios-npm-shim.sh"

    result = subprocess.run(
        [str(script), str(tmp_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Could not find PitGPT repo root" in result.stderr
    assert not (tmp_path / "app" / "gen" / "apple" / "package.json").exists()


def test_artifact_collection_fails_when_expected_files_are_missing() -> None:
    """Release workflows should fail with a clear annotation when Tauri emits no artifact."""
    script = ROOT / "scripts" / "collect-tauri-artifacts.sh"
    assert os.access(script, os.X_OK)

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_file = Path(tmp_dir) / "artifacts.txt"
        result = subprocess.run(
            [str(script), "ios-ipa", str(output_file)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    assert result.returncode != 0
    assert "Missing iOS artifact" in result.stdout


def test_tauri_privacy_manifest_is_bundled() -> None:
    """Apple release bundles should include the checked-in privacy manifest."""
    tauri_config = json.loads((ROOT / "app" / "tauri.conf.json").read_text(encoding="utf-8"))
    privacy_manifest = json.loads(
        (ROOT / "app" / "PrivacyInfo.xcprivacy").read_text(encoding="utf-8"),
    )

    assert "PrivacyInfo.xcprivacy" in tauri_config["bundle"]["resources"]
    assert privacy_manifest["NSPrivacyTracking"] is False
    assert privacy_manifest["NSPrivacyCollectedDataTypes"] == []


def test_release_checklist_documents_required_secrets() -> None:
    """Release docs should list the same secret surface used by the preflight script."""
    checklist = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")

    for name in (
        "APPLE_API_ISSUER",
        "APPLE_API_KEY",
        "APPLE_API_KEY_P8_B64",
        "APPLE_CERTIFICATE",
        "APPLE_CERTIFICATE_PASSWORD",
        "APPLE_DEVELOPMENT_TEAM",
        "APPLE_SIGNING_IDENTITY",
        "APPLE_TEAM_ID",
        "IOS_PROVISIONING_PROFILE_B64",
    ):
        assert name in checklist
    assert "app-store-connect" in checklist
    assert "macos-preview" in checklist


def test_macos_preview_publish_script_requires_release_context() -> None:
    """The preview publish script should fail before gh calls when CI env is incomplete."""
    script = ROOT / "scripts" / "publish-macos-preview.sh"
    assert os.access(script, os.X_OK)

    result = subprocess.run(
        [str(script)],
        cwd=ROOT,
        env={"PATH": os.environ["PATH"]},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Missing preview release environment" in result.stdout
