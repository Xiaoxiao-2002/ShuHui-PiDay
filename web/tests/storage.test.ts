import { describe, expect, it } from "vitest";
import type { AttemptStateV1, PlayablePuzzleV1 } from "../src/types";
import { loadAttempt, loadCompleted, saveAttempt, saveCompletion } from "../src/storage";

const puzzle = { id: "TSH-01", schemaVersion: 1, dataVersion: "v1", sourceHash: "hash-1" } as PlayablePuzzleV1;
const attempt: AttemptStateV1 = {
  schemaVersion: 1,
  dataVersion: "v1",
  puzzleId: "TSH-01",
  sourceHash: "hash-1",
  attemptId: "attempt-1",
  selectedEdgeIds: ["edge-1"],
  history: ["edge-1"],
  startedAt: 1000,
  updatedAt: 1000,
};

describe("attempt storage", () => {
  it("restores an attempt with the same data hash", () => {
    expect(saveAttempt(attempt)).toBe(true);
    expect(loadAttempt(puzzle)?.selectedEdgeIds).toEqual(["edge-1"]);
  });

  it("discards an attempt after puzzle data changes", () => {
    saveAttempt(attempt);
    expect(loadAttempt({ ...puzzle, sourceHash: "hash-2" })).toBeNull();
  });

  it("keeps the best completion time", () => {
    const receipt = {
      schemaVersion: 1 as const,
      eventId: "piday-2026",
      receiptId: "receipt-1",
      shortCode: "ABC12345",
      puzzleId: "TSH-01",
      difficulty: "beginner" as const,
      difficultyLabel: "初级 Beginner",
      elapsedMs: 9000,
      completedAt: 2000,
      attemptId: "attempt-1",
      verification: "local" as const,
    };
    saveCompletion(receipt, "v1");
    saveCompletion({ ...receipt, receiptId: "receipt-2", elapsedMs: 12_000 }, "v1");
    expect(loadCompleted()["TSH-01"].bestElapsedMs).toBe(9000);
  });
});
