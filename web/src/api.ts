import type { PlayablePuzzleV1, PuzzleIndexV1 } from "./types";

const base = import.meta.env.BASE_URL;

export async function loadPuzzleIndex(): Promise<PuzzleIndexV1> {
  const response = await fetch(`${base}puzzles/index.json`);
  if (!response.ok) throw new Error("无法加载关卡列表");
  return (await response.json()) as PuzzleIndexV1;
}

export async function loadPuzzle(file: string): Promise<PlayablePuzzleV1> {
  const response = await fetch(`${base}puzzles/${file}`);
  if (!response.ok) throw new Error("无法加载题目数据");
  return (await response.json()) as PlayablePuzzleV1;
}
