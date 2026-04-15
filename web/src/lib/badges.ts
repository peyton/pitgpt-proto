import type { EvidenceQuality, SafetyTier } from "./types";

export const safetyBadgeClass: Record<string, string> = {
  GREEN: "badge badge-safe badge-dot",
  YELLOW: "badge badge-caution badge-dot",
  RED: "badge badge-danger badge-dot",
};

export const safetyLabel: Record<string, string> = {
  GREEN: "Green — Safe to Run",
  YELLOW: "Yellow — Restrictions Apply",
  RED: "Red — Blocked",
};

export const safetyLabelShort: Record<string, string> = {
  GREEN: "Green",
  YELLOW: "Yellow",
  RED: "Red",
};

export const evidenceClass: Record<string, string> = {
  strong: "badge badge-safe",
  moderate: "badge badge-info",
  weak: "badge badge-neutral",
  novel: "badge badge-pink",
};

export function getSafetyBadgeClass(tier: SafetyTier | string): string {
  return safetyBadgeClass[tier] ?? "badge badge-neutral";
}

export function getSafetyLabel(tier: SafetyTier | string, short = false): string {
  return (short ? safetyLabelShort : safetyLabel)[tier] ?? tier;
}

export function getEvidenceClass(quality: EvidenceQuality | string): string {
  return evidenceClass[quality] ?? "badge badge-neutral";
}
