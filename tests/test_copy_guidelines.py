"""Copy and safety-policy checks for risk-stratified positioning."""

from pathlib import Path

from pitgpt.core.policy import SAFETY_POLICY_PROMPT

ROOT = Path(__file__).parent.parent


def test_policy_allows_low_risk_condition_adjacent_routines():
    assert "condition-adjacent" in SAFETY_POLICY_PROMPT
    assert "does not change medications or supplements" in SAFETY_POLICY_PROMPT
    assert "does not diagnose or decide care" not in SAFETY_POLICY_PROMPT


def test_user_facing_copy_avoids_blanket_disease_blocking():
    files = [
        ROOT / "web" / "src" / "pages" / "Home.tsx",
        ROOT / "web" / "src" / "lib" / "templates.ts",
        ROOT / "src" / "pitgpt" / "core" / "templates.py",
        ROOT / "README.md",
        ROOT / "docs" / "project-purpose.md",
    ]
    text = "\n".join(path.read_text() for path in files)
    collapsed = " ".join(text.split())

    assert "Not a fit: prescriptions, supplements, disease management" not in text
    assert "medical-condition experiments" not in text
    assert "do not change medications or replace care" in collapsed


def test_clinician_language_is_concise():
    clinician_sentence = (
        "Consider bringing this plan to your clinician if it affects a condition, "
        "medication, or symptoms."
    )
    assert clinician_sentence in SAFETY_POLICY_PROMPT
    assert len(clinician_sentence.split()) <= 15
