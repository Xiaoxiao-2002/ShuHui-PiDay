import { describe, expect, it } from "vitest";
import type { EdgeV1, PlayablePuzzleV1, VertexV1 } from "../src/types";
import { validateSolutionEdges } from "../src/validator";

function loopPuzzle(options?: { secondLoop?: boolean; clue?: number; pi?: boolean; duplicateSector?: boolean }): PlayablePuzzleV1 {
  const vertices: VertexV1[] = [];
  const edges: EdgeV1[] = [];
  const makeLoop = (prefix: string, offset: number) => {
    for (let i = 0; i < 6; i += 1) {
      vertices.push({ id: `${prefix}v${i}`, x: offset + Math.cos((i * Math.PI) / 3), y: Math.sin((i * Math.PI) / 3) });
      edges.push({
        id: `${prefix}e${i}`,
        vertices: [`${prefix}v${i}`, `${prefix}v${(i + 1) % 6}`],
        sector: options?.duplicateSector && i === 5 ? 4 : i,
      });
    }
  };
  makeLoop("a", 0);
  if (options?.secondLoop) makeLoop("b", 4);
  const incidentEdges = Object.fromEntries(vertices.map((vertex) => [vertex.id, edges.filter((edge) => edge.vertices.includes(vertex.id)).map((edge) => edge.id)]));
  return {
    schemaVersion: 1,
    dataVersion: "test-v1",
    sourceHash: "fixture",
    id: "TSH-00",
    difficulty: "beginner",
    difficultyLabel: "初级 Beginner",
    clues: [
      ...(options?.clue === undefined ? [] : [{ cellId: "cell:a", kind: "number" as const, value: options.clue }]),
      ...(options?.pi ? [{ cellId: "cell:a", kind: "pi" as const }, { cellId: "cell:shared", kind: "pi" as const }] : []),
    ],
    topology: {
      bounds: { minX: -1, maxX: 6, minY: -1, maxY: 1 },
      vertices,
      edges,
      cells: [
        { id: "cell:a", edgeIds: edges.filter((edge) => edge.id.startsWith("a")).map((edge) => edge.id), center: [0, 0], kind: "circle" },
        { id: "cell:shared", edgeIds: ["ae0", "ae1"], center: [0.5, 0], kind: "triangle" },
      ],
      incidentEdges,
    },
  };
}

describe("validateSolutionEdges", () => {
  it("accepts one non-empty connected loop", () => {
    expect(validateSolutionEdges(loopPuzzle(), ["ae0", "ae1", "ae2", "ae3", "ae4", "ae5"]).code).toBe("ok");
  });

  it.each([
    [[], "empty"],
    [["missing"], "unknown-edge"],
    [["ae0"], "degree"],
  ])("rejects %j as %s", (edges, code) => {
    expect(validateSolutionEdges(loopPuzzle(), edges).code).toBe(code);
  });

  it("rejects duplicate edge IDs", () => {
    expect(validateSolutionEdges(loopPuzzle(), ["ae0", "ae0"]).code).toBe("duplicate");
  });

  it("rejects multiple disjoint loops", () => {
    const selected = [...Array.from({ length: 6 }, (_, i) => `ae${i}`), ...Array.from({ length: 6 }, (_, i) => `be${i}`)];
    expect(validateSolutionEdges(loopPuzzle({ secondLoop: true }), selected).code).toBe("disconnected");
  });

  it("checks numeric clues", () => {
    const selected = Array.from({ length: 6 }, (_, i) => `ae${i}`);
    expect(validateSolutionEdges(loopPuzzle({ clue: 6 }), selected).valid).toBe(true);
    expect(validateSolutionEdges(loopPuzzle({ clue: 5 }), selected).code).toBe("number");
  });

  it("counts a physical edge adjacent to two pi cells only once", () => {
    const selected = Array.from({ length: 6 }, (_, i) => `ae${i}`);
    expect(validateSolutionEdges(loopPuzzle({ pi: true }), selected).valid).toBe(true);
  });

  it("requires exactly one selected arc in every pi direction", () => {
    const selected = Array.from({ length: 6 }, (_, i) => `ae${i}`);
    expect(validateSolutionEdges(loopPuzzle({ pi: true, duplicateSector: true }), selected).code).toBe("pi");
  });
});
