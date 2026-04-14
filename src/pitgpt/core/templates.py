from dataclasses import dataclass

from pitgpt.core.models import Protocol


@dataclass(frozen=True)
class TrialTemplate:
    id: str
    name: str
    description: str
    condition_a_placeholder: str
    condition_b_placeholder: str
    protocol: Protocol


TRIAL_TEMPLATES: tuple[TrialTemplate, ...] = (
    TrialTemplate(
        id="skincare",
        name="Skincare A/B",
        description="Compare two cosmetic products over 6 weeks.",
        condition_a_placeholder="CeraVe Moisturizing Cream",
        condition_b_placeholder="La Roche-Posay Toleriane",
        protocol=Protocol(
            template="Skincare Product",
            duration_weeks=6,
            block_length_days=7,
            cadence="daily",
            washout="None",
            primary_outcome_question="Skin satisfaction (0-10)",
        ),
    ),
    TrialTemplate(
        id="morning-routine",
        name="Morning Routine",
        description="Compare two morning routines with daily ratings.",
        condition_a_placeholder="Current morning routine",
        condition_b_placeholder="New morning routine",
        protocol=Protocol(
            template="Morning Routine",
            duration_weeks=6,
            block_length_days=7,
            cadence="daily",
            washout="None",
            primary_outcome_question="Midday appearance (0-10)",
        ),
    ),
    TrialTemplate(
        id="sleep-routine",
        name="Sleep Routine",
        description="Compare two low-risk sleep habit routines.",
        condition_a_placeholder="Current sleep routine",
        condition_b_placeholder="New sleep routine",
        protocol=Protocol(
            template="Sleep Routine",
            duration_weeks=4,
            block_length_days=7,
            cadence="daily AM",
            washout="1-2 days",
            primary_outcome_question="Sleep quality (0-10)",
            warnings="Keep timing and environment as consistent as practical.",
        ),
    ),
    TrialTemplate(
        id="haircare",
        name="Haircare",
        description="Compare two haircare products over 6 weeks.",
        condition_a_placeholder="Current hair product",
        condition_b_placeholder="New hair product",
        protocol=Protocol(
            template="Haircare Product",
            duration_weeks=6,
            block_length_days=7,
            cadence="daily",
            washout="None",
            primary_outcome_question="Hair quality (0-10)",
        ),
    ),
    TrialTemplate(
        id="evening-routine",
        name="Evening Routine",
        description="Compare two evening routines with morning ratings.",
        condition_a_placeholder="Current evening routine",
        condition_b_placeholder="New evening routine",
        protocol=Protocol(
            template="Evening Routine",
            duration_weeks=6,
            block_length_days=7,
            cadence="daily",
            washout="None",
            primary_outcome_question="Morning skin feel (0-10)",
        ),
    ),
    TrialTemplate(
        id="custom-ab",
        name="Custom A/B",
        description="Compare everyday routines or products.",
        condition_a_placeholder="Condition A",
        condition_b_placeholder="Condition B",
        protocol=Protocol(
            template="Custom A/B",
            duration_weeks=6,
            block_length_days=7,
            cadence="daily",
            washout="None",
            primary_outcome_question="Personal outcome rating (0-10)",
            screening=(
                "Use this for low-risk routines, tracking, environmental changes, or products."
            ),
            warnings=(
                "Medication or supplement changes, urgent symptoms, invasive interventions, and "
                "diagnosis questions need a different path. Do not change medications or replace "
                "care."
            ),
        ),
    ),
)


def templates_as_dicts() -> list[dict]:
    return [
        {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "condition_a_placeholder": template.condition_a_placeholder,
            "condition_b_placeholder": template.condition_b_placeholder,
            "protocol": template.protocol.model_dump(mode="json"),
        }
        for template in TRIAL_TEMPLATES
    ]
