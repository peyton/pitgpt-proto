import { describe, expect, it } from "vitest";
import {
  createExperimentConversation,
  enrichIngestionResultWithSources,
  messageFromIngestionResult,
  statusFromIngestionResult,
  titleFromQuery,
} from "./experiments";
import type { IngestionResult } from "./types";

const readyResult: IngestionResult = {
  decision: "generate_protocol",
  safety_tier: "GREEN",
  evidence_quality: "novel",
  evidence_conflict: false,
  protocol: {
    template: "Custom A/B",
    duration_weeks: 2,
    block_length_days: 7,
    cadence: "daily",
    washout: "None",
    primary_outcome_question: "Score",
    screening: "",
    warnings: "",
  },
  block_reason: null,
  user_message: "Ready to lock.",
};

describe("experiment helpers", () => {
  it("creates a conversation with the first user message", () => {
    const conversation = createExperimentConversation({
      query: " Compare two routines ",
      documents: ["source"],
      sourceNames: ["study.md"],
    });

    expect(conversation.status).toBe("draft");
    expect(conversation.title).toBe("Compare two routines");
    expect(conversation.messages).toHaveLength(1);
    expect(conversation.messages[0]).toMatchObject({
      role: "user",
      content: "Compare two routines",
    });
  });

  it("derives statuses and assistant messages from ingestion results", () => {
    const manual: IngestionResult = {
      ...readyResult,
      decision: "manual_review_before_protocol",
      protocol: null,
      block_reason: "Needs detail.",
      next_steps: ["Which two routines?"],
      user_message: "Answer one follow-up.",
    };

    expect(statusFromIngestionResult(readyResult)).toBe("ready_to_lock");
    expect(statusFromIngestionResult(manual)).toBe("needs_review");
    expect(messageFromIngestionResult(manual).questions).toEqual(["Which two routines?"]);
  });

  it("adds source metadata when the provider response has none", () => {
    const enriched = enrichIngestionResultWithSources(readyResult, ["study.md"]);

    expect(enriched.sources?.[0]).toMatchObject({
      source_id: "source-1",
      title: "study.md",
      rationale: "Attached by the user before protocol generation.",
    });
  });

  it("keeps sidebar titles short", () => {
    expect(titleFromQuery("x".repeat(60))).toHaveLength(42);
    expect(titleFromQuery("")).toBe("Untitled experiment");
  });
});
