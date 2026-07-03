import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PlayablePuzzleV1 } from "../src/types";
import { PuzzleBoard } from "../src/components/PuzzleBoard";

const puzzle: PlayablePuzzleV1 = {
  schemaVersion: 1,
  dataVersion: "test",
  sourceHash: "test",
  id: "TSH-00",
  difficulty: "beginner",
  difficultyLabel: "初级 Beginner",
  clues: [{ cellId: "cell", kind: "number", value: 1 }],
  topology: {
    bounds: { minX: 0, maxX: 1, minY: 0, maxY: 0 },
    vertices: [{ id: "v0", x: 0, y: 0 }, { id: "v1", x: 1, y: 0 }],
    edges: [{ id: "edge", vertices: ["v0", "v1"], sector: 0 }],
    cells: [{ id: "cell", edgeIds: ["edge"], center: [0.5, 0.25], kind: "circle" }],
    incidentEdges: { v0: ["edge"], v1: ["edge"] },
  },
};

describe("PuzzleBoard", () => {
  it("provides a wide interactive edge target and toggles it", () => {
    const onToggle = vi.fn();
    const { container } = render(<PuzzleBoard puzzle={puzzle} selected={new Set()} onToggle={onToggle} />);
    const hit = container.querySelector<SVGPathElement>('[data-edge-id="edge"]')!;
    fireEvent.pointerDown(hit, { pointerId: 1, clientX: 10, clientY: 10 });
    fireEvent.pointerUp(hit, { pointerId: 1, clientX: 10, clientY: 10 });
    expect(onToggle).toHaveBeenCalledWith("edge");
    expect(screen.getByRole("button", { name: "放大" })).toBeVisible();
  });
});
