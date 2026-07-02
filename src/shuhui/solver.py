from __future__ import annotations

import time
import os
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from .errors import PuzzleFormatError, TopologyError
from .model import Analysis, AnalysisStatus, ClueKind, Puzzle
from .storage import puzzle_content_hash
from .topology import Topology, build_topology


@dataclass(slots=True)
class SolveResult:
    status: AnalysisStatus | None
    solutions: list[list[str]] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    message: str = ""
    branches: int = 0
    conflicts: int = 0

    @property
    def solution(self) -> list[str] | None:
        return self.solutions[0] if self.status == AnalysisStatus.UNIQUE and self.solutions else None


@dataclass(slots=True)
class _ModelBundle:
    model: cp_model.CpModel
    edge_vars: dict[str, cp_model.IntVar]


def _build_model(puzzle: Puzzle, topology: Topology) -> _ModelBundle:
    model = cp_model.CpModel()
    edge_vars = {edge_id: model.new_bool_var(f"edge[{edge_id}]") for edge_id in sorted(topology.edges)}
    # AddCircuit 用自环表示未使用顶点，并保证其余顶点只属于同一个有向环。
    # 相比 O(|V||E|) 的整数流模型，这里只增加每条边两个方向布尔量，传播也更强。
    vertex_ids = sorted(topology.vertices)
    vertex_index = {vertex_id: index for index, vertex_id in enumerate(vertex_ids)}
    circuit_arcs: list[tuple[int, int, cp_model.IntVar]] = []
    for vertex_id in vertex_ids:
        self_loop = model.new_bool_var(f"unused[{vertex_id}]")
        index = vertex_index[vertex_id]
        circuit_arcs.append((index, index, self_loop))
    for edge_id, edge in topology.edges.items():
        a, b = edge.vertices
        forward = model.new_bool_var(f"direction[{edge_id}:{a}->{b}]")
        backward = model.new_bool_var(f"direction[{edge_id}:{b}->{a}]")
        model.add(edge_vars[edge_id] == forward + backward)
        circuit_arcs.append((vertex_index[a], vertex_index[b], forward))
        circuit_arcs.append((vertex_index[b], vertex_index[a], backward))
    model.add_circuit(circuit_arcs)
    model.add(sum(edge_vars.values()) >= 3)

    for clue in puzzle.clues:
        cell = topology.cells[clue.cell_id]
        if clue.kind == ClueKind.NUMBER:
            model.add(sum(edge_vars[edge_id] for edge_id in cell.edge_ids) == clue.value)

    pi_cells = [clue.cell_id for clue in puzzle.clues if clue.kind == ClueKind.PI]
    if pi_cells:
        pi_edges = {edge_id for cell_id in pi_cells for edge_id in topology.cells[cell_id].edge_ids}
        by_sector: dict[int, list[cp_model.IntVar]] = {sector: [] for sector in range(6)}
        for edge_id in sorted(pi_edges):
            sector = topology.edges[edge_id].sector
            if sector is None:
                raise PuzzleFormatError("π 单元格包含无法分类方向的边")
            by_sector[sector].append(edge_vars[edge_id])
        for sector in range(6):
            model.add(sum(by_sector[sector]) == 1)
    return _ModelBundle(model, edge_vars)


def _solver_with_limit(seconds: float, seed: int, workers: int | None = None) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(0.001, seconds)
    solver.parameters.random_seed = seed
    solver.parameters.num_search_workers = max(1, workers or min(8, os.cpu_count() or 1))
    return solver


def _extract_solution(solver: cp_model.CpSolver, edge_vars: dict[str, cp_model.IntVar]) -> list[str]:
    return sorted(edge_id for edge_id, variable in edge_vars.items() if solver.value(variable))


def _forbid_solution(model: cp_model.CpModel, edge_vars: dict[str, cp_model.IntVar], solution: list[str]) -> None:
    selected = set(solution)
    differences = [1 - variable if edge_id in selected else variable for edge_id, variable in edge_vars.items()]
    model.add(sum(differences) >= 1)


def solve_puzzle(
    puzzle: Puzzle,
    *,
    time_limit: float = 10.0,
    max_solutions: int = 2,
    seed: int = 0,
    workers: int | None = None,
    update: bool = True,
) -> SolveResult:
    started = time.monotonic()
    try:
        topology = build_topology(puzzle)
        bundle = _build_model(puzzle, topology)
    except (PuzzleFormatError, TopologyError, KeyError, TypeError) as exc:
        result = SolveResult(AnalysisStatus.INVALID, elapsed_seconds=time.monotonic() - started, message=str(exc))
        if update:
            puzzle.analysis = Analysis(AnalysisStatus.INVALID, None, puzzle_content_hash(puzzle), result.elapsed_seconds, result.message)
        return result

    solutions: list[list[str]] = []
    proven_complete = False
    total_branches = 0
    total_conflicts = 0
    for attempt in range(max(1, max_solutions)):
        remaining = time_limit - (time.monotonic() - started)
        if remaining <= 0:
            break
        solver = _solver_with_limit(remaining, seed + attempt, workers)
        cp_status = solver.solve(bundle.model)
        total_branches += solver.num_branches
        total_conflicts += solver.num_conflicts
        if cp_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            solution = _extract_solution(solver, bundle.edge_vars)
            solutions.append(solution)
            _forbid_solution(bundle.model, bundle.edge_vars, solution)
            if len(solutions) >= max_solutions:
                break
        elif cp_status == cp_model.INFEASIBLE:
            proven_complete = True
            break
        else:
            break

    elapsed = time.monotonic() - started
    if not solutions and proven_complete:
        status = AnalysisStatus.UNSATISFIABLE
        message = "题目无解"
    elif len(solutions) >= 2:
        status = AnalysisStatus.MULTIPLE
        message = "题目存在多个解"
    elif len(solutions) == 1 and proven_complete:
        status = AnalysisStatus.UNIQUE
        message = "题目有唯一解"
    else:
        status = None
        message = "求解超时，尚不能判定唯一性"
    result = SolveResult(status, solutions, elapsed, message, total_branches, total_conflicts)
    if update:
        puzzle.analysis = Analysis(
            status,
            solutions[0] if status == AnalysisStatus.UNIQUE else None,
            puzzle_content_hash(puzzle),
            elapsed,
            message,
        )
    return result


def validate_solution_edges(
    puzzle: Puzzle,
    edge_ids: list[str] | set[str],
    *,
    check_clues: bool = True,
) -> tuple[bool, str]:
    try:
        topology = build_topology(puzzle)
    except (PuzzleFormatError, TopologyError, KeyError, TypeError) as exc:
        return False, str(exc)
    if len(edge_ids) != len(set(edge_ids)):
        return False, "作答中存在重复边"
    selected = set(edge_ids)
    unknown = selected - topology.edges.keys()
    if unknown:
        return False, f"作答引用未知边：{sorted(unknown)[0]}"
    if not selected:
        return False, "尚未画出曲线"
    degree: dict[str, int] = {vertex_id: 0 for vertex_id in topology.vertices}
    for edge_id in selected:
        for vertex_id in topology.edges[edge_id].vertices:
            degree[vertex_id] += 1
    if any(value not in (0, 2) for value in degree.values()):
        return False, "目标曲线存在端点或分叉"
    first_vertex = topology.edges[next(iter(selected))].vertices[0]
    visited_vertices = {first_vertex}
    stack = [first_vertex]
    visited_edges: set[str] = set()
    while stack:
        vertex_id = stack.pop()
        for edge_id in topology.incident_edges[vertex_id]:
            if edge_id not in selected:
                continue
            visited_edges.add(edge_id)
            for other in topology.edges[edge_id].vertices:
                if other not in visited_vertices:
                    visited_vertices.add(other)
                    stack.append(other)
    if visited_edges != selected:
        return False, "目标曲线包含多个互不相连的环"
    if check_clues:
        for clue in puzzle.clues:
            if clue.kind == ClueKind.NUMBER:
                count = len(selected.intersection(topology.cells[clue.cell_id].edge_ids))
                if count != clue.value:
                    return False, f"目标曲线不满足 {clue.cell_id} 的数字 {clue.value}"
        pi_cells = [clue.cell_id for clue in puzzle.clues if clue.kind == ClueKind.PI]
        if pi_cells:
            pi_edges = {edge_id for cell_id in pi_cells for edge_id in topology.cells[cell_id].edge_ids}
            counts = [0] * 6
            for edge_id in selected.intersection(pi_edges):
                sector = topology.edges[edge_id].sector
                if sector is None:
                    return False, "π 提示包含无方向边"
                counts[sector] += 1
            if counts != [1] * 6:
                return False, f"目标曲线不满足 π 六方向约束：{counts}"
    return True, "目标曲线是合法单一闭环"


def validate_target_solution(puzzle: Puzzle, *, check_clues: bool = True) -> tuple[bool, str]:
    if puzzle.target_solution_edges is None:
        return False, "尚未提供目标曲线"
    return validate_solution_edges(puzzle, puzzle.target_solution_edges, check_clues=check_clues)


def find_alternative_solution(
    puzzle: Puzzle,
    target_edges: list[str],
    *,
    time_limit: float,
    seed: int = 0,
    workers: int | None = None,
) -> tuple[list[str] | None, bool]:
    """返回替代解和是否已证明不存在替代解。"""
    topology = build_topology(puzzle)
    bundle = _build_model(puzzle, topology)
    _forbid_solution(bundle.model, bundle.edge_vars, target_edges)
    solver = _solver_with_limit(time_limit, seed, workers)
    status = solver.solve(bundle.model)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _extract_solution(solver, bundle.edge_vars), False
    return None, status == cp_model.INFEASIBLE
