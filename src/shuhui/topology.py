from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Iterable

from .errors import PuzzleFormatError, TopologyError
from .model import ClueKind, Puzzle, Variant


@dataclass(frozen=True, slots=True)
class Vertex:
    id: str
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Edge:
    id: str
    vertices: tuple[str, str]
    sector: int | None = None
    circle_center: tuple[float, float] | None = None
    circle_radius: float | None = None
    start_angle: float | None = None
    span_angle: float | None = None


@dataclass(frozen=True, slots=True)
class Cell:
    id: str
    edge_ids: tuple[str, ...]
    center: tuple[float, float]
    kind: str


@dataclass(slots=True)
class Topology:
    vertices: dict[str, Vertex] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)
    cells: dict[str, Cell] = field(default_factory=dict)
    incident_edges: dict[str, list[str]] = field(default_factory=dict)

    def finish(self) -> "Topology":
        self.incident_edges = {vertex_id: [] for vertex_id in self.vertices}
        for edge in self.edges.values():
            for vertex_id in edge.vertices:
                self.incident_edges[vertex_id].append(edge.id)
        for edge_ids in self.incident_edges.values():
            edge_ids.sort()
        return self


def _point_key(x: float, y: float) -> tuple[int, int]:
    return round(x * 1_000_000), round(y * 1_000_000)


def build_classic(rows: int, cols: int) -> Topology:
    if not isinstance(rows, int) or isinstance(rows, bool) or rows <= 0:
        raise TopologyError("经典棋盘 rows 必须是正整数")
    if not isinstance(cols, int) or isinstance(cols, bool) or cols <= 0:
        raise TopologyError("经典棋盘 cols 必须是正整数")
    topology = Topology()
    for r in range(rows + 1):
        for c in range(cols + 1):
            vertex_id = f"v:{r}:{c}"
            topology.vertices[vertex_id] = Vertex(vertex_id, float(c), float(r))
    for r in range(rows + 1):
        for c in range(cols):
            edge_id = f"h:{r}:{c}"
            topology.edges[edge_id] = Edge(edge_id, (f"v:{r}:{c}", f"v:{r}:{c + 1}"))
    for r in range(rows):
        for c in range(cols + 1):
            edge_id = f"v:{r}:{c}"
            topology.edges[edge_id] = Edge(edge_id, (f"v:{r}:{c}", f"v:{r + 1}:{c}"))
    for r in range(rows):
        for c in range(cols):
            cell_id = f"cell:{r}:{c}"
            topology.cells[cell_id] = Cell(
                cell_id,
                (f"h:{r}:{c}", f"v:{r}:{c + 1}", f"h:{r + 1}:{c}", f"v:{r}:{c}"),
                (c + 0.5, r + 0.5),
                "square",
            )
    return topology.finish()


def _circle_rows(row_lengths: list[int]) -> tuple[list[tuple[str, float, float]], dict[str, tuple[float, float]]]:
    if not isinstance(row_lengths, list) or not row_lengths:
        raise TopologyError("特色棋盘 row_lengths 必须是非空数组")
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in row_lengths):
        raise TopologyError("row_lengths 中每项必须是正整数")
    if any(abs(a - b) != 1 for a, b in zip(row_lengths, row_lengths[1:])):
        raise TopologyError("相邻两行圆数必须恰好相差 1")
    offsets = [0.0]
    for previous, current in zip(row_lengths, row_lengths[1:]):
        offsets.append(offsets[-1] + (0.5 if current < previous else -0.5))
    minimum = min(offsets)
    offsets = [value - minimum for value in offsets]
    rows: list[tuple[str, float, float]] = []
    centers: dict[str, tuple[float, float]] = {}
    for r, (length, offset) in enumerate(zip(row_lengths, offsets)):
        for c in range(length):
            circle_id = f"circle:{r}:{c}"
            center = (offset + c, r * math.sqrt(3) / 2)
            rows.append((circle_id, *center))
            centers[circle_id] = center
    return rows, centers


def build_circle_pack(row_lengths: list[int]) -> Topology:
    circles, centers = _circle_rows(row_lengths)
    topology = Topology()
    vertex_by_point: dict[tuple[int, int], str] = {}
    circle_vertices: dict[str, list[str]] = {}
    radius = 0.5

    for circle_id, cx, cy in circles:
        vertex_ids: list[str] = []
        for direction in range(6):
            angle = direction * math.pi / 3
            x, y = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
            key = _point_key(x, y)
            vertex_id = vertex_by_point.get(key)
            if vertex_id is None:
                vertex_id = f"p:{key[0]}:{key[1]}"
                vertex_by_point[key] = vertex_id
                topology.vertices[vertex_id] = Vertex(vertex_id, x, y)
            vertex_ids.append(vertex_id)
        circle_vertices[circle_id] = vertex_ids
        edge_ids: list[str] = []
        _, r_text, c_text = circle_id.split(":")
        for sector in range(6):
            edge_id = f"arc:{r_text}:{c_text}:{sector}"
            start = vertex_ids[sector]
            end = vertex_ids[(sector + 1) % 6]
            topology.edges[edge_id] = Edge(
                edge_id,
                (start, end),
                sector,
                (cx, cy),
                radius,
                sector * 60.0,
                60.0,
            )
            edge_ids.append(edge_id)
        topology.cells[circle_id] = Cell(circle_id, tuple(edge_ids), (cx, cy), "circle")

    circle_ids = sorted(centers)
    for triple in itertools.combinations(circle_ids, 3):
        points = [centers[circle_id] for circle_id in triple]
        distances = [math.dist(points[a], points[b]) for a, b in ((0, 1), (0, 2), (1, 2))]
        if not all(math.isclose(distance, 1.0, abs_tol=1e-8) for distance in distances):
            continue
        tangent_keys = {
            _point_key((points[a][0] + points[b][0]) / 2, (points[a][1] + points[b][1]) / 2)
            for a, b in ((0, 1), (0, 2), (1, 2))
        }
        tangent_vertices = {vertex_by_point[key] for key in tangent_keys}
        boundary: list[str] = []
        for circle_id in triple:
            for edge_id in topology.cells[circle_id].edge_ids:
                if set(topology.edges[edge_id].vertices).issubset(tangent_vertices):
                    boundary.append(edge_id)
        if len(boundary) != 3:
            raise TopologyError(f"无法构造圆隙三角形：{triple}")
        center = (sum(point[0] for point in points) / 3, sum(point[1] for point in points) / 3)
        cell_id = "tri:" + "+".join(triple)
        topology.cells[cell_id] = Cell(cell_id, tuple(sorted(boundary)), center, "triangle")
    return topology.finish()


def build_topology(puzzle: Puzzle) -> Topology:
    if puzzle.variant == Variant.CLASSIC:
        rows = puzzle.board.get("rows")
        cols = puzzle.board.get("cols")
        topology = build_classic(rows, cols)
    elif puzzle.variant == Variant.CIRCLE_PACK:
        topology = build_circle_pack(puzzle.board.get("row_lengths"))
    else:
        raise TopologyError(f"未知题型：{puzzle.variant}")
    validate_puzzle_against_topology(puzzle, topology)
    return topology


def validate_puzzle_against_topology(puzzle: Puzzle, topology: Topology) -> None:
    seen: set[str] = set()
    for clue in puzzle.clues:
        if clue.cell_id in seen:
            raise PuzzleFormatError(f"单元格 {clue.cell_id} 存在重复提示")
        seen.add(clue.cell_id)
        cell = topology.cells.get(clue.cell_id)
        if cell is None:
            raise PuzzleFormatError(f"提示引用未知单元格：{clue.cell_id}")
        if clue.kind == ClueKind.PI:
            if puzzle.variant != Variant.CIRCLE_PACK:
                raise PuzzleFormatError("π 提示仅适用于特色数回")
        elif clue.value is None or not 0 <= clue.value <= len(cell.edge_ids):
            raise PuzzleFormatError(f"单元格 {clue.cell_id} 的数字应在 0–{len(cell.edge_ids)}")
    for name, edge_ids in (
        ("target_solution_edges", puzzle.target_solution_edges),
        ("analysis.solution_edges", puzzle.analysis.solution_edges),
    ):
        if edge_ids is None:
            continue
        if len(edge_ids) != len(set(edge_ids)):
            raise PuzzleFormatError(f"{name} 含重复边")
        unknown = set(edge_ids) - topology.edges.keys()
        if unknown:
            raise PuzzleFormatError(f"{name} 引用未知边：{sorted(unknown)[0]}")


def selected_boundary_edges(topology: Topology, cell_ids: Iterable[str]) -> set[str]:
    result: set[str] = set()
    for cell_id in cell_ids:
        result.update(topology.cells[cell_id].edge_ids)
    return result
