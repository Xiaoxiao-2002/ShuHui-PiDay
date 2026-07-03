import type { PlayablePuzzleV1 } from "./types";

export interface TutorialProgressV1 {
  schemaVersion: 1;
  step: number;
  completed: boolean;
}

const KEY = "shuhui:piday:v1:tutorial";

export function loadTutorialProgress(): TutorialProgressV1 {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) ?? "null") as TutorialProgressV1 | null;
    if (saved?.schemaVersion === 1) {
      return { schemaVersion: 1, step: Math.max(0, Math.min(5, saved.step)), completed: Boolean(saved.completed) };
    }
  } catch {
    // Restricted or malformed storage should never block the tutorial.
  }
  return { schemaVersion: 1, step: 0, completed: false };
}

export function saveTutorialProgress(step: number, completed = false): TutorialProgressV1 {
  const progress = { schemaVersion: 1 as const, step: Math.max(0, Math.min(5, step)), completed };
  try {
    localStorage.setItem(KEY, JSON.stringify(progress));
  } catch {
    // Continue in memory when embedded browsers deny storage.
  }
  return progress;
}

export const tutorialPuzzle: PlayablePuzzleV1 = {
  schemaVersion: 1,
  dataVersion: "tutorial-v1",
  sourceHash: "tutorial-double-hex-v2",
  id: "教程练习",
  difficulty: "beginner",
  difficultyLabel: "互动教学",
  clues: [
    { cellId: "left", kind: "number", value: 5 },
    { cellId: "right", kind: "number", value: 5 },
  ],
  topology: {
    bounds: { minX: 0.134, maxX: 3.598, minY: 0, maxY: 2 },
    vertices: [
      { id: "shared-top", x: 1.866, y: 0.5 },
      { id: "shared-bottom", x: 1.866, y: 1.5 },
      { id: "a-bottom", x: 1, y: 2 },
      { id: "a-bottom-left", x: 0.134, y: 1.5 },
      { id: "a-top-left", x: 0.134, y: 0.5 },
      { id: "a-top", x: 1, y: 0 },
      { id: "b-top", x: 2.732, y: 0 },
      { id: "b-top-right", x: 3.598, y: 0.5 },
      { id: "b-bottom-right", x: 3.598, y: 1.5 },
      { id: "b-bottom", x: 2.732, y: 2 },
    ],
    edges: [
      { id: "shared", vertices: ["shared-top", "shared-bottom"], sector: 0 },
      { id: "a-lower-right", vertices: ["shared-bottom", "a-bottom"], sector: 1 },
      { id: "a-bottom-left", vertices: ["a-bottom", "a-bottom-left"], sector: 2 },
      { id: "a-left", vertices: ["a-bottom-left", "a-top-left"], sector: 3 },
      { id: "a-top-left", vertices: ["a-top-left", "a-top"], sector: 4 },
      { id: "a-upper-right", vertices: ["a-top", "shared-top"], sector: 5 },
      { id: "b-upper-left", vertices: ["shared-top", "b-top"], sector: 1 },
      { id: "b-top-right", vertices: ["b-top", "b-top-right"], sector: 2 },
      { id: "b-right", vertices: ["b-top-right", "b-bottom-right"], sector: 3 },
      { id: "b-bottom-right", vertices: ["b-bottom-right", "b-bottom"], sector: 4 },
      { id: "b-lower-left", vertices: ["b-bottom", "shared-bottom"], sector: 5 },
    ],
    cells: [
      { id: "left", edgeIds: ["shared", "a-lower-right", "a-bottom-left", "a-left", "a-top-left", "a-upper-right"], center: [1, 1], kind: "circle" },
      { id: "right", edgeIds: ["shared", "b-upper-left", "b-top-right", "b-right", "b-bottom-right", "b-lower-left"], center: [2.732, 1], kind: "circle" },
    ],
    incidentEdges: {
      "shared-top": ["shared", "a-upper-right", "b-upper-left"],
      "shared-bottom": ["shared", "a-lower-right", "b-lower-left"],
      "a-bottom": ["a-lower-right", "a-bottom-left"],
      "a-bottom-left": ["a-bottom-left", "a-left"],
      "a-top-left": ["a-left", "a-top-left"],
      "a-top": ["a-top-left", "a-upper-right"],
      "b-top": ["b-upper-left", "b-top-right"],
      "b-top-right": ["b-top-right", "b-right"],
      "b-bottom-right": ["b-right", "b-bottom-right"],
      "b-bottom": ["b-bottom-right", "b-lower-left"],
    },
  },
};
