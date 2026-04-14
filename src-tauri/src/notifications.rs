use serde::{Deserialize, Serialize};

use crate::models::Condition;
use crate::schedule::generate_schedule_result;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReminderPlan {
    pub day_index: u32,
    pub offset_days: u32,
    pub time: String,
    pub condition: Condition,
}

pub fn plan_trial_reminders_result(
    duration_weeks: u32,
    block_length_days: u32,
    seed: u32,
    reminder_time: &str,
    enabled: bool,
) -> Result<Vec<ReminderPlan>, String> {
    if !enabled {
        return Ok(Vec::new());
    }
    validate_reminder_time(reminder_time)?;
    let assignments = generate_schedule_result(duration_weeks, block_length_days, seed)?;
    let mut reminders = Vec::new();

    for assignment in assignments {
        for day_index in assignment.start_day..=assignment.end_day {
            reminders.push(ReminderPlan {
                day_index,
                offset_days: day_index.saturating_sub(1),
                time: reminder_time.to_string(),
                condition: assignment.condition,
            });
        }
    }

    Ok(reminders)
}

fn validate_reminder_time(value: &str) -> Result<(), String> {
    let Some((hour, minute)) = value.split_once(':') else {
        return Err("reminder_time must use HH:MM format".to_string());
    };
    let hour: u32 = hour
        .parse()
        .map_err(|_| "reminder_time hour must be numeric".to_string())?;
    let minute: u32 = minute
        .parse()
        .map_err(|_| "reminder_time minute must be numeric".to_string())?;
    if hour > 23 || minute > 59 {
        return Err("reminder_time must be a valid 24-hour clock time".to_string());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disabled_reminders_do_not_schedule_anything() {
        let reminders = plan_trial_reminders_result(6, 7, 123, "09:00", false).unwrap();
        assert!(reminders.is_empty());
    }

    #[test]
    fn plans_one_reminder_per_trial_day() {
        let reminders = plan_trial_reminders_result(2, 7, 123, "21:30", true).unwrap();
        assert_eq!(reminders.len(), 14);
        assert_eq!(reminders[0].day_index, 1);
        assert_eq!(reminders[0].offset_days, 0);
        assert_eq!(reminders[0].time, "21:30");
        assert_eq!(reminders.last().unwrap().day_index, 14);
    }

    #[test]
    fn rejects_invalid_clock_time() {
        let err = plan_trial_reminders_result(2, 7, 123, "25:00", true).unwrap_err();
        assert!(err.contains("valid 24-hour"));
    }
}
