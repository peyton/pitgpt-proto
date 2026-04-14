import { invokeNative, isTauriRuntime } from "./runtime";
import type { Trial } from "./types";

const NOTIFIED_DAY_KEY = "pitgpt_native_reminder_last_day";

export type NativeReminderStatus = "unsupported" | "disabled" | "granted" | "denied" | "error";

export interface NativeReminderSync {
  status: NativeReminderStatus;
  scheduledCount: number;
  message: string;
}

export async function syncNativeReminderSchedule(
  trial: Trial | null,
  enabled: boolean,
  reminderTime: string,
): Promise<NativeReminderSync> {
  if (!isTauriRuntime()) {
    return { status: "unsupported", scheduledCount: 0, message: "Native reminders need the Tauri app." };
  }
  if (!enabled || !trial) {
    return { status: "disabled", scheduledCount: 0, message: "Native reminders are off." };
  }

  const permission = await ensureNotificationPermission();
  if (permission !== "granted") {
    return {
      status: "denied",
      scheduledCount: 0,
      message: "Notification permission was not granted.",
    };
  }

  try {
    const planned = await invokeNative<unknown[]>("plan_trial_reminders", {
      durationWeeks: trial.protocol.duration_weeks,
      blockLengthDays: trial.protocol.block_length_days,
      seed: trial.seed,
      reminderTime,
      enabled,
    });
    return {
      status: "granted",
      scheduledCount: planned.length,
      message: `Native reminder plan is ready for ${planned.length} trial days.`,
    };
  } catch (error) {
    return {
      status: "error",
      scheduledCount: 0,
      message: error instanceof Error ? error.message : "Could not prepare native reminders.",
    };
  }
}

export async function sendDueNativeReminder(
  trial: Trial,
  enabled: boolean,
  reminderTime: string,
): Promise<void> {
  if (!enabled || !isTauriRuntime()) return;
  const today = new Date().toISOString().slice(0, 10);
  const key = `${trial.id}:${today}`;
  if (localStorage.getItem(NOTIFIED_DAY_KEY) === key) return;
  if (new Date().toTimeString().slice(0, 5) < reminderTime) return;

  const permission = await ensureNotificationPermission();
  if (permission !== "granted") return;

  const { sendNotification } = await import("@tauri-apps/plugin-notification");
  sendNotification({
    title: "PitGPT check-in",
    body: "Log today's trial observation before the day gets noisy.",
  });
  localStorage.setItem(NOTIFIED_DAY_KEY, key);
}

async function ensureNotificationPermission(): Promise<"granted" | "denied"> {
  const { isPermissionGranted, requestPermission } = await import("@tauri-apps/plugin-notification");
  if (await isPermissionGranted()) return "granted";
  const permission = await requestPermission();
  return permission === "granted" ? "granted" : "denied";
}
