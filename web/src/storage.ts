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
  const legacyId = puzzle.id.match(/^TSH-2026-(\d{2})$/)?.[1];
  const legacyKey = legacyId ? attemptKey(`TSH-${legacyId}`) : null;
  const attempt = readJson<AttemptStateV1>(attemptKey(puzzle.id)) ?? (legacyKey ? readJson<AttemptStateV1>(legacyKey) : null);
  if (!attempt) return null;
  if (attempt.schemaVersion !== 1 || attempt.dataVersion !== puzzle.dataVersion || attempt.sourceHash !== puzzle.sourceHash) {
    clearAttempt(puzzle.id);
    return null;
  }
  if (attempt.puzzleId !== puzzle.id) {
    const migrated = { ...attempt, puzzleId: puzzle.id };
    saveAttempt(migrated);
    if (legacyKey) localStorage.removeItem(legacyKey);
    return migrated;
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
  const completed = readJson<Record<string, CompletedPuzzleV1>>(COMPLETED_KEY) ?? {};
  let changed = false;
  for (let index = 1; index <= 20; index += 1) {
    const oldId = `TSH-${String(index).padStart(2, "0")}`;
    const newId = `TSH-2026-${String(index).padStart(2, "0")}`;
    if (!completed[oldId] || completed[newId]) continue;
    const old = completed[oldId];
    completed[newId] = { ...old, puzzleId: newId, latestReceipt: { ...old.latestReceipt, puzzleId: newId } };
    delete completed[oldId];
    changed = true;
  }
  if (changed) writeJson(COMPLETED_KEY, completed);
  return completed;
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
