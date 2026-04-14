import type { IngestionResult, Protocol } from "./types";

export interface TrialTemplate {
  id: string;
  icon: string;
  name: string;
  description: string;
  query: string;
  conditionAPlaceholder: string;
  conditionBPlaceholder: string;
  protocol: Protocol;
}

export const trialTemplates: TrialTemplate[] = [
  {
    id: "skincare",
    icon: "AB",
    name: "Skincare A/B",
    description: "Compare two cosmetic products over 6 weeks.",
    query: "Compare two skincare products",
    conditionAPlaceholder: "CeraVe Moisturizing Cream",
    conditionBPlaceholder: "La Roche-Posay Toleriane",
    protocol: {
      template: "Skincare Product",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Skin satisfaction (0-10)",
      screening: "",
      warnings: "",
    },
  },
  {
    id: "morning-routine",
    icon: "AM",
    name: "Morning Routine",
    description: "Compare two morning routines with daily ratings.",
    query: "Compare two morning routines",
    conditionAPlaceholder: "Current morning routine",
    conditionBPlaceholder: "New morning routine",
    protocol: {
      template: "Morning Routine",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Midday appearance (0-10)",
      screening: "",
      warnings: "",
    },
  },
  {
    id: "sleep-routine",
    icon: "SL",
    name: "Sleep Routine",
    description: "Compare two low-risk sleep habit routines.",
    query: "Compare two sleep routines",
    conditionAPlaceholder: "Current sleep routine",
    conditionBPlaceholder: "New sleep routine",
    protocol: {
      template: "Sleep Routine",
      duration_weeks: 4,
      block_length_days: 7,
      cadence: "daily AM",
      washout: "1-2 days",
      primary_outcome_question: "Sleep quality (0-10)",
      screening: "",
      warnings: "Keep timing and environment as consistent as practical.",
    },
  },
  {
    id: "haircare",
    icon: "HR",
    name: "Haircare",
    description: "Compare two haircare products over 6 weeks.",
    query: "Compare two haircare products",
    conditionAPlaceholder: "Current hair product",
    conditionBPlaceholder: "New hair product",
    protocol: {
      template: "Haircare Product",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Hair quality (0-10)",
      screening: "",
      warnings: "",
    },
  },
  {
    id: "evening-routine",
    icon: "PM",
    name: "Evening Routine",
    description: "Compare two evening routines with morning ratings.",
    query: "Compare two evening routines",
    conditionAPlaceholder: "Current evening routine",
    conditionBPlaceholder: "New evening routine",
    protocol: {
      template: "Evening Routine",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Morning skin feel (0-10)",
      screening: "",
      warnings: "",
    },
  },
  {
    id: "custom-ab",
    icon: "C",
    name: "Custom A/B",
    description: "Compare everyday routines or products.",
    query: "Custom A/B experiment",
    conditionAPlaceholder: "Condition A",
    conditionBPlaceholder: "Condition B",
    protocol: {
      template: "Custom A/B",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Personal outcome rating (0-10)",
      screening: "Use this only for everyday routines or products.",
      warnings:
        "This tool is for comparing everyday routines and products. Do not use it for medications, supplements, or medical-condition experiments.",
    },
  },
];

export function templateToIngestionResult(template: TrialTemplate): IngestionResult {
  return {
    decision: "generate_protocol",
    safety_tier: "GREEN",
    evidence_quality: "novel",
    evidence_conflict: false,
    protocol: template.protocol,
    block_reason: null,
    user_message:
      "Template protocol ready. Edit the condition labels, then lock the protocol before collecting data.",
  };
}
