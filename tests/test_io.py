import pytest

from pitgpt.core.io import parse_observations_csv


def test_strict_observation_csv_rejects_unknown_columns() -> None:
    csv = "day_index,date,condition,primary_score,unexpected\n1,2026-01-01,A,7,x\n"

    with pytest.raises(ValueError, match="unknown column"):
        parse_observations_csv(csv, strict=True)


def test_strict_observation_csv_rejects_duplicate_days_and_dates() -> None:
    csv = "\n".join(
        [
            "day_index,date,condition,primary_score",
            "1,2026-01-01,A,7",
            "1,2026-01-01,B,6",
        ]
    )

    with pytest.raises(ValueError, match="duplicate day_index"):
        parse_observations_csv(csv, strict=True)


def test_observation_csv_parses_methodology_metadata() -> None:
    csv = "\n".join(
        [
            "observation_id,day_index,date,condition,assigned_condition,actual_condition,primary_score,deviation_codes,confounders",
            'obs-1,1,2026-01-01,A,A,B,7,"[""swapped_condition""]","{""sleep"":""poor""}"',
        ]
    )

    observations = parse_observations_csv(csv, strict=True)

    assert observations[0].observation_id == "obs-1"
    assert observations[0].assigned_condition == "A"
    assert observations[0].actual_condition == "B"
    assert observations[0].deviation_codes == ["swapped_condition"]
    assert observations[0].confounders == {"sleep": "poor"}


def test_observation_csv_rejects_non_numeric_secondary_scores() -> None:
    csv = "\n".join(
        [
            "day_index,date,condition,primary_score,secondary_scores",
            '1,2026-01-01,A,7,"{""sleep"":""bad""}"',
        ]
    )

    with pytest.raises(ValueError, match="secondary_scores.sleep must be numeric"):
        parse_observations_csv(csv, strict=True)


def test_observation_csv_trims_context_metadata() -> None:
    csv = "\n".join(
        [
            "day_index,date,condition,primary_score,deviation_codes,confounders",
            '1,2026-01-01,A,7,"["" late "", "" ""]","{"" sleep "":"" poor "", "" "": ""skip""}"',
        ]
    )

    observations = parse_observations_csv(csv, strict=True)

    assert observations[0].deviation_codes == ["late"]
    assert observations[0].confounders == {"sleep": "poor"}
