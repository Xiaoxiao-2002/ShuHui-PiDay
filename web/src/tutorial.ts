import type { PlayablePuzzleV1 } from "./types";

export interface TutorialProgressV1 {
  schemaVersion: 1;
  step: number;
  completed: boolean;
}

export type TutorialTrack = "basic" | "pi" | "guided";

const LEGACY_KEY = "shuhui:piday:v1:tutorial";
const keyFor = (track: TutorialTrack) => `${LEGACY_KEY}:${track}`;
const lastStep: Record<TutorialTrack, number> = { basic: 4, pi: 2, guided: 2 };

export function loadTutorialProgress(track: TutorialTrack): TutorialProgressV1 {
  try {
    const saved = JSON.parse(localStorage.getItem(keyFor(track)) ?? "null") as TutorialProgressV1 | null;
    if (saved?.schemaVersion === 1) {
      return { schemaVersion: 1, step: Math.max(0, Math.min(lastStep[track], saved.step)), completed: Boolean(saved.completed) };
    }
    if (track === "basic") {
      const legacy = JSON.parse(localStorage.getItem(LEGACY_KEY) ?? "null") as TutorialProgressV1 | null;
      if (legacy?.schemaVersion === 1) {
        return { schemaVersion: 1, step: Math.max(0, Math.min(lastStep.basic, legacy.step)), completed: Boolean(legacy.completed) };
      }
    }
  } catch {
    // Restricted or malformed storage should never block the tutorial.
  }
  return { schemaVersion: 1, step: 0, completed: false };
}

export function saveTutorialProgress(track: TutorialTrack, step: number, completed = false): TutorialProgressV1 {
  const progress = { schemaVersion: 1 as const, step: Math.max(0, Math.min(lastStep[track], step)), completed };
  try {
    localStorage.setItem(keyFor(track), JSON.stringify(progress));
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

function buildPiGuidedPuzzle(): PlayablePuzzleV1 {
  const circleDefs = [
    { row: 0, col: 0, cx: 0, cy: 0 },
    { row: 0, col: 1, cx: 1, cy: 0 },
    { row: 1, col: 0, cx: 0.5, cy: Math.sqrt(3) / 2 },
  ];
  const vertices = new Map<string, { id: string; x: number; y: number }>();
  const edges: PlayablePuzzleV1["topology"]["edges"] = [];
  const cells: PlayablePuzzleV1["topology"]["cells"] = [];
  const incidentEdges: Record<string, string[]> = {};
  const vertexId = (x: number, y: number) => {
    const key = `p:${Math.round(x * 1_000_000)}:${Math.round(y * 1_000_000)}`;
    if (!vertices.has(key)) vertices.set(key, { id: key, x, y });
    return key;
  };

  for (const circle of circleDefs) {
    const ids = Array.from({ length: 6 }, (_, direction) => {
      const angle = (direction * Math.PI) / 3;
      return vertexId(circle.cx + 0.5 * Math.cos(angle), circle.cy + 0.5 * Math.sin(angle));
    });
    const edgeIds: string[] = [];
    for (let sector = 0; sector < 6; sector += 1) {
      const id = `arc:${circle.row}:${circle.col}:${sector}`;
      const ends: [string, string] = [ids[sector], ids[(sector + 1) % 6]];
      edges.push({ id, vertices: ends, sector, circle: { center: [circle.cx, circle.cy], radius: 0.5, startAngle: sector * 60, spanAngle: 60 } });
      for (const end of ends) (incidentEdges[end] ??= []).push(id);
      edgeIds.push(id);
    }
    cells.push({ id: `circle:${circle.row}:${circle.col}`, edgeIds, center: [circle.cx, circle.cy], kind: "circle" });
  }
  const triangleId = "tri:circle:0:0+circle:0:1+circle:1:0";
  cells.push({ id: triangleId, edgeIds: ["arc:0:0:0", "arc:0:1:2", "arc:1:0:4"], center: [0.5, Math.sqrt(3) / 6], kind: "triangle" });
  const allVertices = [...vertices.values()];
  return {
    schemaVersion: 1,
    dataVersion: "tutorial-v1",
    sourceHash: "tutorial-guided-pi-v1",
    id: "π 综合练习",
    difficulty: "beginner",
    difficultyLabel: "逐步引导",
    clues: [{ cellId: "circle:0:0", kind: "pi" }, { cellId: triangleId, kind: "pi" }],
    topology: {
      bounds: {
        minX: Math.min(...allVertices.map((item) => item.x)), maxX: Math.max(...allVertices.map((item) => item.x)),
        minY: Math.min(...allVertices.map((item) => item.y)), maxY: Math.max(...allVertices.map((item) => item.y)),
      },
      vertices: allVertices.sort((a, b) => a.id.localeCompare(b.id)), edges, cells,
      incidentEdges: Object.fromEntries(Object.entries(incidentEdges).sort(([a], [b]) => a.localeCompare(b))),
    },
  };
}

export const piGuidedPuzzle = buildPiGuidedPuzzle();
