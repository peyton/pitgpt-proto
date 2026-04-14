from dataclasses import dataclass

from pitgpt.core.models import Protocol
from pitgpt.core.shared import load_shared_json


@dataclass(frozen=True)
class TrialTemplate:
    id: str
    name: str
    description: str
    condition_a_placeholder: str
    condition_b_placeholder: str
    protocol: Protocol


def _load_templates() -> tuple[TrialTemplate, ...]:
    rows = load_shared_json("trial_templates.json")
    return tuple(
        TrialTemplate(
            id=str(row["id"]),
            name=str(row["name"]),
            description=str(row["description"]),
            condition_a_placeholder=str(row["condition_a_placeholder"]),
            condition_b_placeholder=str(row["condition_b_placeholder"]),
            protocol=Protocol.model_validate(row["protocol"]),
        )
        for row in rows
    )


TRIAL_TEMPLATES: tuple[TrialTemplate, ...] = _load_templates()


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
