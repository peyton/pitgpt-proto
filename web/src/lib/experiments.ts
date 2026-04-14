import type {
  ExperimentConversation,
  ExperimentMessage,
  ExperimentStatus,
  IngestionResult,
} from "./types";

interface CreateExperimentInput {
  query: string;
  documents?: string[];
  sourceNames?: string[];
  ingestionResult?: IngestionResult | null;
  status?: ExperimentStatus;
}

export type ExperimentMessageInput = Omit<ExperimentMessage, "id" | "createdAt"> &
  Partial<Pick<ExperimentMessage, "id" | "createdAt">>;

export function createExperimentConversation({
  query,
  documents = [],
  sourceNames = [],
  ingestionResult = null,
  status,
}: CreateExperimentInput): ExperimentConversation {
  const now = new Date().toISOString();
  const resolvedStatus = status ?? statusFromIngestionResult(ingestionResult) ?? "draft";
  const title = titleFromQuery(query);
  const messages: ExperimentMessage[] = [
    createExperimentMessage({
      role: "user",
      content: query.trim(),
      status: "done",
      createdAt: now,
    }),
  ];

  if (ingestionResult) {
    messages.push(messageFromIngestionResult(ingestionResult, now));
  }

  return {
    id: id("exp"),
    title,
    createdAt: now,
    updatedAt: now,
    status: resolvedStatus,
    unread: false,
    query: query.trim(),
    documents,
    sourceNames,
    ingestionResult,
    messages,
  };
}

export function createExperimentMessage(input: ExperimentMessageInput): ExperimentMessage {
  return {
    id: input.id ?? id("msg"),
    role: input.role,
    content: input.content,
    createdAt: input.createdAt ?? new Date().toISOString(),
    status: input.status ?? "done",
    questions: input.questions,
    ingestionResult: input.ingestionResult,
  };
}

export function messageFromIngestionResult(
  result: IngestionResult,
  createdAt = new Date().toISOString(),
): ExperimentMessage {
  if (result.decision === "block") {
    return createExperimentMessage({
      role: "assistant",
      content: result.user_message || result.block_reason || "This experiment is outside PitGPT's scope.",
      status: "done",
      createdAt,
      ingestionResult: result,
    });
  }
  if (result.decision === "manual_review_before_protocol") {
    return createExperimentMessage({
      role: "assistant",
      content: result.user_message || "I need a little more detail before I can lock a protocol.",
      status: "done",
      questions: result.next_steps ?? [],
      createdAt,
      ingestionResult: result,
    });
  }
  return createExperimentMessage({
    role: "assistant",
    content: result.user_message || "Protocol draft is ready for review.",
    status: "done",
    ingestionResult: result,
    createdAt,
  });
}

export function statusFromIngestionResult(result: IngestionResult | null | undefined): ExperimentStatus | null {
  if (!result) return null;
  if (result.decision === "block") return "blocked";
  if (result.decision === "manual_review_before_protocol") return "needs_review";
  return "ready_to_lock";
}

export function titleFromQuery(query: string): string {
  const normalized = query.trim().replace(/\s+/g, " ");
  if (!normalized) return "Untitled experiment";
  return normalized.length > 42 ? `${normalized.slice(0, 39).trim()}...` : normalized;
}

export function enrichIngestionResultWithSources(
  result: IngestionResult,
  sourceNames: string[],
): IngestionResult {
  if (sourceNames.length === 0 || (result.sources?.length ?? 0) > 0) return result;
  return {
    ...result,
    sources: sourceNames.map((name, index) => ({
      source_id: `source-${index + 1}`,
      source_type: "text",
      title: name,
      locator: name,
      evidence_quality: result.evidence_quality,
      summary: result.source_summaries?.[index] ?? "User-provided source.",
      rationale: "Attached by the user before protocol generation.",
    })),
  };
}

function id(prefix: string): string {
  return `${prefix}-${crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`}`;
}
