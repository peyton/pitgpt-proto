from pitgpt.core.models import Condition, ScheduleAssignment


def generate_seed() -> int:
    import secrets

    return secrets.randbelow(2_147_483_647)


def generate_schedule(
    duration_weeks: int,
    block_length_days: int,
    seed: int,
) -> list[ScheduleAssignment]:
    total_days = duration_weeks * 7
    if duration_weeks <= 0:
        raise ValueError("duration_weeks must be positive")
    if block_length_days <= 0:
        raise ValueError("block_length_days must be positive")

    period_count = (total_days + block_length_days - 1) // block_length_days
    rng = _mulberry32(seed)
    schedule: list[ScheduleAssignment] = []

    for pair_index in range((period_count + 1) // 2):
        first_period = pair_index * 2
        a_first = rng() < 0.5
        conditions = (Condition.A, Condition.B) if a_first else (Condition.B, Condition.A)

        for offset, condition in enumerate(conditions):
            period_index = first_period + offset
            if period_index >= period_count:
                break
            start_day = period_index * block_length_days + 1
            end_day = min(total_days, start_day + block_length_days - 1)
            schedule.append(
                ScheduleAssignment(
                    period_index=period_index,
                    pair_index=pair_index,
                    condition=condition,
                    start_day=start_day,
                    end_day=end_day,
                )
            )

    return schedule


def _mulberry32(seed: int):
    state = seed & 0xFFFFFFFF

    def next_value() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        value = state
        value = _imul(value ^ (value >> 15), 1 | value)
        value = (value + _imul(value ^ (value >> 7), 61 | value)) ^ value
        return ((value ^ (value >> 14)) & 0xFFFFFFFF) / 4294967296

    return next_value


def _imul(a: int, b: int) -> int:
    return ((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF)) & 0xFFFFFFFF
