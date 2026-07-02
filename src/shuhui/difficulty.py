from __future__ import annotations

from dataclasses import dataclass

from .model import ClueKind, Puzzle
from .topology import build_topology


DIFFICULTY_TIERS = {
    "beginner": "初级 Beginner",
    "medium": "中级 Medium",
    "difficult": "高级 Difficult",
    "expert": "专家 Expert",
}


def difficulty_tier(level: int) -> str:
    """Map the internal five-point score band to the four public activity tiers."""
    if level <= 2:
        return "beginner"
    if level == 3:
        return "medium"
    if level == 4:
        return "difficult"
    return "expert"


def difficulty_display(tier: str) -> str:
    return DIFFICULTY_TIERS.get(tier, tier or "待定")


@dataclass(slots=True)
class DifficultyReport:
    label: str
    level: int
    logical_steps: int
    unresolved_edges: int
    total_edges: int
    score: float
    techniques: list[str]
    loop_edges: int = 0
    circle_transitions: int = 0
    coverage_ratio: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "level": self.level,
            "logical_steps": self.logical_steps,
            "unresolved_edges": self.unresolved_edges,
            "total_edges": self.total_edges,
            "score": round(self.score, 3),
            "techniques": self.techniques,
            "loop_edges": self.loop_edges,
            "circle_transitions": self.circle_transitions,
            "coverage_ratio": round(self.coverage_ratio, 3),
        }


def analyze_difficulty(puzzle: Puzzle) -> DifficultyReport:
    topology = build_topology(puzzle)
    state = {edge_id: -1 for edge_id in topology.edges}  # -1 未知，0 排除，1 选中
    steps = 0
    techniques: set[str] = set()

    def assign(edge_id: str, value: int, technique: str) -> bool:
        nonlocal steps
        if state[edge_id] == value:
            return False
        if state[edge_id] != -1:
            return False
        state[edge_id] = value
        steps += 1
        techniques.add(technique)
        return True

    changed = True
    while changed:
        changed = False
        for clue in puzzle.clues:
            if clue.kind != ClueKind.NUMBER:
                continue
            edge_ids = topology.cells[clue.cell_id].edge_ids
            selected = sum(state[edge_id] == 1 for edge_id in edge_ids)
            unknown = [edge_id for edge_id in edge_ids if state[edge_id] == -1]
            if selected == clue.value:
                for edge_id in unknown:
                    changed |= assign(edge_id, 0, "数字完成")
            elif selected + len(unknown) == clue.value:
                for edge_id in unknown:
                    changed |= assign(edge_id, 1, "数字填满")
        for edge_ids in topology.incident_edges.values():
            selected = sum(state[edge_id] == 1 for edge_id in edge_ids)
            unknown = [edge_id for edge_id in edge_ids if state[edge_id] == -1]
            if selected == 2:
                for edge_id in unknown:
                    changed |= assign(edge_id, 0, "顶点度数")
            elif selected == 1 and len(unknown) == 1:
                changed |= assign(unknown[0], 1, "顶点度数")
            elif selected == 0 and len(unknown) == 1:
                changed |= assign(unknown[0], 0, "顶点度数")
        pi_cells = [clue.cell_id for clue in puzzle.clues if clue.kind == ClueKind.PI]
        if pi_cells:
            pi_edges = {edge_id for cell_id in pi_cells for edge_id in topology.cells[cell_id].edge_ids}
            for sector in range(6):
                sector_edges = [edge_id for edge_id in pi_edges if topology.edges[edge_id].sector == sector]
                selected = sum(state[edge_id] == 1 for edge_id in sector_edges)
                unknown = [edge_id for edge_id in sector_edges if state[edge_id] == -1]
                if selected == 1:
                    for edge_id in unknown:
                        changed |= assign(edge_id, 0, "π 六方向")
                elif selected == 0 and len(unknown) == 1:
                    changed |= assign(unknown[0], 1, "π 六方向")

    unresolved = sum(value == -1 for value in state.values())
    ratio = unresolved / max(1, len(state))
    clue_density = len(puzzle.clues) / max(1, len(topology.cells))

    solution = set(puzzle.analysis.solution_edges or puzzle.target_solution_edges or [])
    loop_edges = len(solution)
    selected_vertices = {
        vertex_id
        for edge_id in solution
        if edge_id in topology.edges
        for vertex_id in topology.edges[edge_id].vertices
    }
    if selected_vertices:
        all_x = [vertex.x for vertex in topology.vertices.values()]
        all_y = [vertex.y for vertex in topology.vertices.values()]
        selected_x = [topology.vertices[vertex_id].x for vertex_id in selected_vertices]
        selected_y = [topology.vertices[vertex_id].y for vertex_id in selected_vertices]
        x_ratio = (max(selected_x) - min(selected_x)) / max(1e-9, max(all_x) - min(all_x))
        y_ratio = (max(selected_y) - min(selected_y)) / max(1e-9, max(all_y) - min(all_y))
        coverage_ratio = (max(0.0, x_ratio) * max(0.0, y_ratio)) ** 0.5
    else:
        coverage_ratio = 0.0

    def circle_owner(edge_id: str) -> str | None:
        parts = edge_id.split(":")
        return ":".join(parts[:3]) if len(parts) == 4 and parts[0] == "arc" else None

    circle_transitions = 0
    for incident in topology.incident_edges.values():
        selected_incident = [edge_id for edge_id in incident if edge_id in solution]
        if len(selected_incident) != 2:
            continue
        owners = [circle_owner(edge_id) for edge_id in selected_incident]
        if owners[0] is not None and owners[1] is not None and owners[0] != owners[1]:
            circle_transitions += 1

    length_scale = max(12.0, len(topology.edges) * 0.25)
    length_factor = min(1.0, loop_edges / length_scale)
    transition_factor = min(1.0, circle_transitions / 8.0)
    score = (
        35 * ratio
        + 25 * length_factor
        + 20 * min(1.0, coverage_ratio)
        + 15 * transition_factor
        + 5 * (1 - clue_density)
    )
    is_cell_perimeter = bool(solution) and any(solution == set(cell.edge_ids) for cell in topology.cells.values())
    if is_cell_perimeter or loop_edges <= 6:
        score = min(score, 25.0)
    elif circle_transitions < 2 and coverage_ratio < 0.25:
        score = min(score, 38.0)

    if puzzle.variant.value == "circle_pack":
        row_count = len(puzzle.board.get("row_lengths", []))
        board_width = max(puzzle.board.get("row_lengths", [0]))
    else:
        row_count = int(puzzle.board.get("rows", 0))
        board_width = int(puzzle.board.get("cols", 0))
    large_board = row_count >= 8 and board_width >= 8
    extreme = (
        large_board
        and score >= 80
        and loop_edges >= 80
        and circle_transitions >= 30
        and coverage_ratio >= 0.65
    )
    if extreme:
        level = 5
    elif large_board and score >= 60:
        level = 4
    elif score < 35:
        level = 1
    elif score < 65:
        level = 2
    else:
        level = 3
    # Levels 1 and 2 remain useful as an internal scoring distinction, but are
    # intentionally presented as one activity tier to players.
    label = difficulty_tier(level)
    return DifficultyReport(
        label,
        level,
        steps,
        unresolved,
        len(state),
        score,
        sorted(techniques),
        loop_edges,
        circle_transitions,
        coverage_ratio,
    )
