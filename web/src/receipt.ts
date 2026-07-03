import type { AttemptStateV1, CompletionReceiptV1, PlayablePuzzleV1 } from "./types";

export interface ReceiptIssueInput {
  puzzle: PlayablePuzzleV1;
  attempt: AttemptStateV1;
  selectedEdgeIds: string[];
  completedAt: number;
  elapsedMs: number;
}

export interface ReceiptIssuer {
  issue(input: ReceiptIssueInput): Promise<CompletionReceiptV1>;
}

const randomId = (): string =>
  globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;

export class LocalReceiptIssuer implements ReceiptIssuer {
  async issue(input: ReceiptIssueInput): Promise<CompletionReceiptV1> {
    const receiptId = randomId();
    return {
      schemaVersion: 1,
      eventId: "piday-2026",
      receiptId,
      shortCode: receiptId.replaceAll("-", "").slice(0, 8).toUpperCase(),
      puzzleId: input.puzzle.id,
      difficulty: input.puzzle.difficulty,
      difficultyLabel: input.puzzle.difficultyLabel,
      elapsedMs: input.elapsedMs,
      completedAt: input.completedAt,
      attemptId: input.attempt.attemptId,
      verification: "local",
    };
  }
}

export class RemoteReceiptIssuer implements ReceiptIssuer {
  constructor(private readonly endpoint: string) {}

  async issue(input: ReceiptIssueInput): Promise<CompletionReceiptV1> {
    const response = await fetch(`${this.endpoint.replace(/\/$/, "")}/api/v1/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        eventId: "piday-2026",
        puzzleId: input.puzzle.id,
        elapsedMs: input.elapsedMs,
        completedAt: input.completedAt,
        attemptId: input.attempt.attemptId,
        selectedEdgeIds: input.selectedEdgeIds,
      }),
    });
    if (!response.ok) throw new Error("服务端凭证签发失败");
    return (await response.json()) as CompletionReceiptV1;
  }
}
