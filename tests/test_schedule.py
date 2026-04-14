from pitgpt.core.models import Condition
from pitgpt.core.schedule import generate_schedule


def test_weekly_schedule_has_one_period_per_week() -> None:
    schedule = generate_schedule(duration_weeks=6, block_length_days=7, seed=123)

    assert len(schedule) == 6
    assert schedule[0].start_day == 1
    assert schedule[-1].end_day == 42
    for pair_index in range(3):
        pair = [item for item in schedule if item.pair_index == pair_index]
        assert {item.condition for item in pair} == {Condition.A, Condition.B}


def test_fourteen_day_blocks_use_periods_not_week_count() -> None:
    schedule = generate_schedule(duration_weeks=6, block_length_days=14, seed=123)

    assert len(schedule) == 3
    assert [(item.start_day, item.end_day) for item in schedule] == [
        (1, 14),
        (15, 28),
        (29, 42),
    ]


def test_odd_duration_keeps_final_partial_pair_period() -> None:
    schedule = generate_schedule(duration_weeks=5, block_length_days=14, seed=123)

    assert len(schedule) == 3
    assert schedule[-1].start_day == 29
    assert schedule[-1].end_day == 35


def test_short_trial_keeps_one_clipped_period() -> None:
    schedule = generate_schedule(duration_weeks=1, block_length_days=14, seed=123)

    assert len(schedule) == 1
    assert schedule[0].start_day == 1
    assert schedule[0].end_day == 7
