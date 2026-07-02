from __future__ import annotations

import html
import math
from pathlib import Path

from .model import ClueKind, Puzzle
from .topology import Edge, Topology, build_topology


def _bounds(topology: Topology) -> tuple[float, float, float, float]:
    xs = [vertex.x for vertex in topology.vertices.values()]
    ys = [vertex.y for vertex in topology.vertices.values()]
    return min(xs), min(ys), max(xs), max(ys)


def _svg_edge_path(edge: Edge, topology: Topology, tx, ty, scale: float) -> str:
    a = topology.vertices[edge.vertices[0]]
    b = topology.vertices[edge.vertices[1]]
    if edge.circle_center is None:
        return f"M {tx(a.x):.2f} {ty(a.y):.2f} L {tx(b.x):.2f} {ty(b.y):.2f}"
    radius = (edge.circle_radius or 0.5) * scale
    return f"M {tx(a.x):.2f} {ty(a.y):.2f} A {radius:.2f} {radius:.2f} 0 0 1 {tx(b.x):.2f} {ty(b.y):.2f}"


def render_svg(
    puzzle: Puzzle,
    *,
    solution_edges: list[str] | None = None,
    width: int = 1000,
    margin: int = 55,
    title: str | None = None,
) -> str:
    topology = build_topology(puzzle)
    min_x, min_y, max_x, max_y = _bounds(topology)
    content_width = max(1e-6, max_x - min_x)
    content_height = max(1e-6, max_y - min_y)
    scale = (width - 2 * margin) / content_width
    board_height = content_height * scale
    title_height = 70 if title else 0
    height = math.ceil(board_height + 2 * margin + title_height)
    tx = lambda x: margin + (x - min_x) * scale
    ty = lambda y: margin + title_height + (y - min_y) * scale
    selected = set(solution_edges or [])
    clues = puzzle.clue_map()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
    ]
    if title:
        parts.append(f'<text x="{width / 2}" y="45" text-anchor="middle" font-size="28" font-family="sans-serif">{html.escape(title)}</text>')
    for edge in topology.edges.values():
        path = _svg_edge_path(edge, topology, tx, ty, scale)
        parts.append(f'<path d="{path}" fill="none" stroke="#b8bec7" stroke-width="2"/>')
    for edge_id in sorted(selected):
        edge = topology.edges[edge_id]
        path = _svg_edge_path(edge, topology, tx, ty, scale)
        parts.append(f'<path d="{path}" fill="none" stroke="#1859a9" stroke-width="7" stroke-linecap="round"/>')
    font_size = max(14, min(30, scale * 0.26))
    for cell_id, clue in clues.items():
        cell = topology.cells[cell_id]
        text = "π" if clue.kind == ClueKind.PI else str(clue.value)
        parts.append(
            f'<text x="{tx(cell.center[0]):.2f}" y="{ty(cell.center[1]) + font_size * 0.35:.2f}" '
            f'text-anchor="middle" font-size="{font_size:.1f}" font-weight="600" font-family="sans-serif">{text}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def export_svg(
    puzzle: Puzzle,
    path: str | Path,
    *,
    solution_edges: list[str] | None = None,
    title: str | None = None,
) -> None:
    Path(path).write_text(render_svg(puzzle, solution_edges=solution_edges, title=title), encoding="utf-8")

