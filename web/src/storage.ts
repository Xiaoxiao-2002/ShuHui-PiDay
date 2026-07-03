import type { AttemptStateV1, CompletedPuzzleV1, CompletionReceiptV1, PlayablePuzzleV1 } from "./types";

const PREFIX = "shuhui:piday:v1";
const attemptKey = (id: string) => `${PREFIX}:attempt:${id}`;
const COMPLETED_KEY = `${PREFIX}:completed`;

function readJson<T>(key: string): T | null {
  try {
    const value = localStorage.getItem(key);
    return value ? (JSON.parse(value) as T) : null;
  } catch {
    return null;
  }
}

function writeJson(key: string, value: unknown): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function storageAvailable(): boolean {
  try {
    const key = `${PREFIX}:probe`;
    localStorage.setItem(key, "1");
    localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

export function loadAttempt(puzzle: PlayablePuzzleV1): AttemptStateV1 | null {
  const attempt = readJson<AttemptStateV1>(attemptKey(puzzle.id));
  if (!attempt) return null;
  if (attempt.schemaVersion !== 1 || attempt.dataVersion !== puzzle.dataVersion || attempt.sourceHash !== puzzle.sourceHash) {
    clearAttempt(puzzle.id);
    return null;
  }
  return attempt;
}

export function saveAttempt(attempt: AttemptStateV1): boolean {
  return writeJson(attemptKey(attempt.puzzleId), { ...attempt, updatedAt: Date.now() });
}

export function clearAttempt(puzzleId: string): void {
  try {
    localStorage.removeItem(attemptKey(puzzleId));
  } catch {
    // In privacy-restricted webviews, gameplay continues in memory.
  }
}

export function loadCompleted(): Record<string, CompletedPuzzleV1> {
  return readJson<Record<string, CompletedPuzzleV1>>(COMPLETED_KEY) ?? {};
}

export function saveCompletion(receipt: CompletionReceiptV1, dataVersion: string): Record<string, CompletedPuzzleV1> {
  const completed = loadCompleted();
  const previous = completed[receipt.puzzleId];
  completed[receipt.puzzleId] = {
    puzzleId: receipt.puzzleId,
    bestElapsedMs: previous ? Math.min(previous.bestElapsedMs, receipt.elapsedMs) : receipt.elapsedMs,
    latestReceipt: receipt,
    dataVersion,
  };
  writeJson(COMPLETED_KEY, completed);
  return completed;
}
