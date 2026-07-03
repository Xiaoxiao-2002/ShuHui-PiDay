import type { PlayablePuzzleV1 } from "./types";

export type ValidationCode =
  | "ok"
  | "empty"
  | "duplicate"
  | "unknown-edge"
  | "degree"
  | "disconnected"
  | "number"
  | "pi";

export interface ValidationResult {
  valid: boolean;
  code: ValidationCode;
  message: string;
}

const fail = (code: Exclude<ValidationCode, "ok">, message: string): ValidationResult => ({
  valid: false,
  code,
  message,
});

export function validateSolutionEdges(
  puzzle: PlayablePuzzleV1,
  selectedInput: Iterable<string>,
): ValidationResult {
  const input = [...selectedInput];
  const selected = new Set(input);
  if (selected.size !== input.length) return fail("duplicate", "作答中存在重复圆弧。");
  if (!selected.size) return fail("empty", "还没有画出闭环。");

  const edgeMap = new Map(puzzle.topology.edges.map((edge) => [edge.id, edge]));
  const vertexMap = new Map(puzzle.topology.vertices.map((vertex) => [vertex.id, vertex]));
  const cellMap = new Map(puzzle.topology.cells.map((cell) => [cell.id, cell]));
  for (const edgeId of selected) {
    if (!edgeMap.has(edgeId)) return fail("unknown-edge", "作答中包含无效圆弧，请重新开始本题。");
  }

  const degrees = new Map([...vertexMap.keys()].map((id) => [id, 0]));
  for (const edgeId of selected) {
    for (const vertexId of edgeMap.get(edgeId)!.vertices) {
      degrees.set(vertexId, (degrees.get(vertexId) ?? 0) + 1);
    }
  }
  if ([...degrees.values()].some((value) => value !== 0 && value !== 2)) {
    return fail("degree", "当前曲线仍有端点或分叉。");
  }

  const firstEdge = edgeMap.get(selected.values().next().value as string)!;
  const stack = [firstEdge.vertices[0]];
  const visitedVertices = new Set(stack);
  const visitedEdges = new Set<string>();
  while (stack.length) {
    const vertexId = stack.pop()!;
    for (const edgeId of puzzle.topology.incidentEdges[vertexId] ?? []) {
      if (!selected.has(edgeId)) continue;
      visitedEdges.add(edgeId);
      for (const other of edgeMap.get(edgeId)!.vertices) {
        if (!visitedVertices.has(other)) {
          visitedVertices.add(other);
          stack.push(other);
        }
      }
    }
  }
  if (visitedEdges.size !== selected.size) return fail("disconnected", "曲线形成了多个互不相连的环。");

  for (const clue of puzzle.clues) {
    if (clue.kind !== "number") continue;
    const cell = cellMap.get(clue.cellId);
    const count = cell?.edgeIds.filter((edgeId) => selected.has(edgeId)).length ?? -1;
    if (count !== clue.value) return fail("number", "至少有一个数字提示尚未满足。");
  }

  const piCells = puzzle.clues.filter((clue) => clue.kind === "pi").map((clue) => clue.cellId);
  if (piCells.length) {
    const adjacent = new Set<string>();
    for (const cellId of piCells) {
      for (const edgeId of cellMap.get(cellId)?.edgeIds ?? []) adjacent.add(edgeId);
    }
    const counts = [0, 0, 0, 0, 0, 0];
    for (const edgeId of selected) {
      if (!adjacent.has(edgeId)) continue;
      const sector = edgeMap.get(edgeId)?.sector;
      if (sector === null || sector === undefined) return fail("pi", "π 提示涉及无方向圆弧。");
      counts[sector] += 1;
    }
    if (counts.some((count) => count !== 1)) return fail("pi", "π 提示要求的六种方向尚未各出现一次。");
  }
  return { valid: true, code: "ok", message: "恭喜，已经完成一条满足全部提示的单一闭环！" };
}
