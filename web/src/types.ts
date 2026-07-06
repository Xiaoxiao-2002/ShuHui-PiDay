export type Difficulty = "beginner" | "medium" | "difficult" | "expert";

export interface PuzzleIndexItem {
  id: string;
  difficulty: Difficulty;
  difficultyLabel: string;
  sourceHash: string;
  file: string;
  publishedAt: string;
  updatedAt: string;
  revision: number;
  clueCount: number;
  cellCount: number;
}

export interface PuzzleIndexV1 {
  schemaVersion: 1;
  dataVersion: string;
  catalogVersion: string;
  puzzles: PuzzleIndexItem[];
}

export interface VertexV1 {
  id: string;
  x: number;
  y: number;
}

export interface EdgeV1 {
  id: string;
  vertices: [string, string];
  sector: number | null;
  circle?: {
    center: [number, number];
    radius: number;
    startAngle: number;
    spanAngle: number;
  };
}

export interface CellV1 {
  id: string;
  edgeIds: string[];
  center: [number, number];
  kind: "circle" | "triangle" | "square";
}

export interface ClueV1 {
  cellId: string;
  kind: "number" | "pi";
  value?: number;
}

export interface PlayablePuzzleV1 {
  schemaVersion: 1;
  dataVersion: string;
  sourceHash: string;
  id: string;
  difficulty: Difficulty;
  difficultyLabel: string;
  publishedAt?: string;
  updatedAt?: string;
  revision?: number;
  clues: ClueV1[];
  topology: {
    bounds: { minX: number; maxX: number; minY: number; maxY: number };
    vertices: VertexV1[];
    edges: EdgeV1[];
    cells: CellV1[];
    incidentEdges: Record<string, string[]>;
  };
}

export interface AttemptStateV1 {
  schemaVersion: 1;
  dataVersion: string;
  puzzleId: string;
  sourceHash: string;
  attemptId: string;
  selectedEdgeIds: string[];
  history: string[];
  startedAt: number;
  updatedAt: number;
}

export interface CompletionReceiptV1 {
  schemaVersion: 1;
  eventId: string;
  receiptId: string;
  shortCode: string;
  puzzleId: string;
  difficulty: Difficulty;
  difficultyLabel: string;
  elapsedMs: number;
  completedAt: number;
  attemptId: string;
  verification: "local" | "signed";
  token?: string;
}

export interface CompletedPuzzleV1 {
  puzzleId: string;
  bestElapsedMs: number;
  latestReceipt: CompletionReceiptV1;
  dataVersion: string;
}
