import type { CompletedTrial, Observation, ResultCard, Trial } from "./types";

export function exportAppointmentBrief(completed: CompletedTrial): string {
  const { trial, result } = completed;
  const lines = [
    `# PitGPT Appointment Brief`,
    "",
    `## Question`,
    `${trial.conditionALabel} vs. ${trial.conditionBLabel}`,
    "",
    `## Protocol`,
    `- Template: ${trial.protocol.template ?? "Custom A/B"}`,
    `- Primary outcome: ${trial.protocol.primary_outcome_question}`,
    `- Duration: ${trial.protocol.duration_weeks} weeks`,
    `- Block length: ${trial.protocol.block_length_days} days`,
    `- Cadence: ${trial.protocol.cadence}`,
    `- Washout: ${trial.protocol.washout || "None"}`,
    `- Protocol hash: ${trial.protocolHash ?? "not recorded"}`,
    `- Analysis plan hash: ${trial.analysisPlanHash ?? "not recorded"}`,
    "",
    `## Result`,
    result.summary || resultHeadline(result, trial),
    "",
    `- Quality grade: ${result.quality_grade}`,
    `- Verdict: ${result.verdict}`,
    `- Mean A: ${value(result.mean_a)}`,
    `- Mean B: ${value(result.mean_b)}`,
    `- Difference: ${signedValue(result.difference)}`,
    `- 95% CI: ${value(result.ci_lower)} to ${value(result.ci_upper)}`,
    `- Adherence: ${Math.round(result.adherence_rate * 100)}%`,
    `- Days logged: ${Math.round(result.days_logged_pct * 100)}%`,
    "",
    `## What Changed Since The Trial Started`,
    ...timeline(trial.observations),
    "",
    `## Adverse Events Or Discomfort`,
    ...adverseEvents(trial),
    "",
    `## Research And Claims Used`,
    ...sourceContext(trial),
    "",
    `## Uncertainty`,
    result.caveats || "No additional caveats recorded.",
    "",
    `## Questions To Bring`,
    ...doctorQuestions(trial, result).map((question) => `- ${question}`),
    "",
    `Generated from the user's local PitGPT data. It is a memory aid for a conversation, not a diagnosis or care plan.`,
    "",
  ];
  return `${lines.join("\n")}`;
}

export function doctorQuestions(trial: Trial, result: ResultCard): string[] {
  const questions = [
    "Does this pattern change anything you would want me to monitor or track differently?",
  ];
  if (touchesConditionOrSymptoms(trial)) {
    questions.push("Are there any reasons I should not repeat or extend this low-risk routine test?");
  }
  if ((trial.adverseEvents ?? []).length > 0 || trial.observations.some((obs) => obs.irritation === "yes")) {
    questions.push("Do these discomfort events suggest I should stop, avoid, or modify this routine?");
  }
  if (result.verdict === "inconclusive") {
    questions.push("Would a longer or better-controlled test be useful, or is this enough to stop testing?");
  }
  return questions;
}

function timeline(observations: Observation[]): string[] {
  const noted = observations
    .filter((obs) => obs.note.trim() || obs.adherence !== "yes" || obs.irritation === "yes")
    .sort((a, b) => a.day_index - b.day_index)
    .slice(0, 12);
  if (noted.length === 0) return ["- No notable notes, missed adherence, or discomfort recorded."];
  return noted.map((obs) => {
    const parts = [`day ${obs.day_index}`, obs.date, `Condition ${obs.condition}`];
    if (obs.primary_score != null) parts.push(`score ${obs.primary_score}`);
    if (obs.adherence !== "yes") parts.push(`adherence ${obs.adherence}`);
    if (obs.adherence_reason) parts.push(`reason: ${obs.adherence_reason}`);
    if (obs.irritation === "yes") parts.push("discomfort logged");
    if (obs.note.trim()) parts.push(`note: ${obs.note.trim()}`);
    return `- ${parts.join(" · ")}`;
  });
}

function adverseEvents(trial: Trial): string[] {
  const events = trial.adverseEvents ?? [];
  if (events.length > 0) {
    return events.map(
      (event) =>
        `- ${event.date} · day ${event.day_index} · Condition ${event.condition} · ${event.severity}: ${event.description}`,
    );
  }
  const observations = trial.observations.filter((obs) => obs.irritation === "yes");
  if (observations.length === 0) return ["- None recorded."];
  return observations.map(
    (obs) =>
      `- ${obs.date} · day ${obs.day_index} · Condition ${obs.condition}: ${obs.adverse_event_description ?? "Discomfort logged."}`,
  );
}

function sourceContext(trial: Trial): string[] {
  const sources = trial.ingestion.sources ?? [];
  const claims = trial.ingestion.extracted_claims ?? [];
  const lines: string[] = [];
  if (sources.length === 0 && (trial.ingestion.source_summaries?.length ?? 0) === 0) {
    lines.push("- No source metadata recorded.");
  }
  for (const source of sources) {
    lines.push(
      `- ${source.title || source.source_id || "Source"} (${source.evidence_quality ?? "unrated"}): ${source.summary || source.rationale || "No summary recorded."}`,
    );
  }
  for (const summary of trial.ingestion.source_summaries ?? []) {
    lines.push(`- ${summary}`);
  }
  if (claims.length > 0) {
    lines.push("");
    lines.push("Claims extracted:");
    for (const claim of claims) {
      lines.push(
        `- ${claim.intervention || "Routine"} vs. ${claim.comparator || "comparison"}: ${claim.outcome || "outcome not specified"}`,
      );
    }
  }
  return lines;
}

function touchesConditionOrSymptoms(trial: Trial): boolean {
  return Boolean(
    trial.ingestion.risk_level && trial.ingestion.risk_level !== "low" ||
      trial.ingestion.clinician_note ||
      trial.protocol.clinician_note,
  );
}

function resultHeadline(result: ResultCard, trial: Trial): string {
  if (result.verdict === "favors_a") return `${trial.conditionALabel} scored higher in this trial.`;
  if (result.verdict === "favors_b") return `${trial.conditionBLabel} scored higher in this trial.`;
  if (result.verdict === "inconclusive") return "This trial did not clearly favor either condition.";
  return "There was not enough usable data for a reliable result.";
}

function value(input: number | null): string {
  return input == null ? "not available" : input.toFixed(2);
}

function signedValue(input: number | null): string {
  if (input == null) return "not available";
  return `${input > 0 ? "+" : ""}${input.toFixed(2)}`;
}
