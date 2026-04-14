use crate::models::{Assignment, Condition};

pub fn generate_schedule_result(
    duration_weeks: u32,
    block_length_days: u32,
    seed: u32,
) -> Result<Vec<Assignment>, String> {
    if duration_weeks == 0 {
        return Err("duration_weeks must be positive".to_string());
    }
    if block_length_days == 0 {
        return Err("block_length_days must be positive".to_string());
    }

    let total_days = duration_weeks * 7;
    let period_count = total_days.div_ceil(block_length_days);
    let mut rng = Mulberry32::new(seed);
    let mut schedule = Vec::new();

    for pair_index in 0..period_count.div_ceil(2) {
        let first_period = pair_index * 2;
        let a_first = rng.next() < 0.5;
        let conditions = if a_first {
            [Condition::A, Condition::B]
        } else {
            [Condition::B, Condition::A]
        };

        for (offset, condition) in conditions.into_iter().enumerate() {
            let period_index = first_period + offset as u32;
            if period_index >= period_count {
                break;
            }
            let start_day = period_index * block_length_days + 1;
            let end_day = total_days.min(start_day + block_length_days - 1);
            schedule.push(Assignment {
                period_index,
                pair_index,
                condition,
                start_day,
                end_day,
            });
        }
    }

    Ok(schedule)
}

struct Mulberry32 {
    state: u32,
}

impl Mulberry32 {
    fn new(seed: u32) -> Self {
        Self { state: seed }
    }

    fn next(&mut self) -> f64 {
        self.state = self.state.wrapping_add(0x6D2B79F5);
        let mut value = self.state;
        value = imul(value ^ (value >> 15), 1 | value);
        value = (value.wrapping_add(imul(value ^ (value >> 7), 61 | value))) ^ value;
        ((value ^ (value >> 14)) as f64) / 4_294_967_296.0
    }
}

fn imul(a: u32, b: u32) -> u32 {
    a.wrapping_mul(b)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn weekly_schedule_has_one_period_per_week() {
        let schedule = generate_schedule_result(6, 7, 123).unwrap();
        assert_eq!(schedule.len(), 6);
        assert_eq!(schedule[0].start_day, 1);
        assert_eq!(schedule.last().unwrap().end_day, 42);
    }

    #[test]
    fn fourteen_day_blocks_use_periods_not_week_count() {
        let schedule = generate_schedule_result(6, 14, 123).unwrap();
        let spans: Vec<_> = schedule
            .iter()
            .map(|item| (item.start_day, item.end_day))
            .collect();
        assert_eq!(spans, vec![(1, 14), (15, 28), (29, 42)]);
    }
}
