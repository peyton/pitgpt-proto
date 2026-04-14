from pitgpt.core.policy import SAFETY_POLICY_PROMPT
from pitgpt.core.templates import TRIAL_TEMPLATES, templates_as_dicts


def test_shared_templates_load_expected_template_ids() -> None:
    ids = {template.id for template in TRIAL_TEMPLATES}

    assert ids == {
        "skincare",
        "morning-routine",
        "sleep-routine",
        "haircare",
        "evening-routine",
        "custom-ab",
    }


def test_templates_endpoint_shape_uses_shared_data() -> None:
    templates = templates_as_dicts()

    assert templates[0]["condition_a_placeholder"]
    assert templates[0]["protocol"]["duration_weeks"] > 0


def test_safety_policy_loads_from_shared_prompt() -> None:
    assert "GREEN" in SAFETY_POLICY_PROMPT
    assert "YELLOW" in SAFETY_POLICY_PROMPT
    assert "RED" in SAFETY_POLICY_PROMPT
    assert "2026-04-14-risk-stratified" in SAFETY_POLICY_PROMPT
