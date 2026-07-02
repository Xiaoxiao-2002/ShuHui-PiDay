from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable

from ortools.sat.python import cp_model

from .difficulty import DifficultyReport, analyze_difficulty
from .errors import GenerationError
from .model import Analysis, AnalysisStatus, Clue, ClueKind, Puzzle, Variant
from .solver import find_alternative_solution, solve_puzzle, validate_target_solution
from .storage import puzzle_content_hash
from .topology import Topology, build_topology


@dataclass(slots=True)
class GenerationOptions:
    time_limit: float = 300.0
    seed: int = 0
    auto_pi: bool = True
    max_pi_candidates: int = 24
    target_difficulty: str | None = None
    require_pi: bool = False
    prefer_pi: bool = True
    workers: int | None = None
    greedy_fraction: float = 0.55
    stop_at_target: bool = False
    minimum_target_score: float | None = None
    enable_cegis: bool = True
    cancel_check: Callable[[], bool] | None = None
    progress: Callable[[str, float], None] | None = None


@dataclass(slots=True)
class GenerationResult:
    puzzle: Puzzle | None
    elapsed_seconds: float
    proven_minimal_numbers: bool
    numeric_clues: int | None = None
    pi_clues: int | None = None
    difficulty: DifficultyReport | None = None
    message: str = ""
    examined_pi_candidates: int = 0


def _cancelled(options: GenerationOptions) -> bool:
    return bool(options.cancel_check and options.cancel_check())


def _notify(options: GenerationOptions, message: str, fraction: float) -> None:
    if options.progress:
        options.progress(message, min(1.0, max(0.0, fraction)))


def _target_count(topology: Topology, target: set[str], cell_id: str) -> int:
    return len(target.intersection(topology.cells[cell_id].edge_ids))


def _valid_pi_groups(
    puzzle: Puzzle,
    topology: Topology,
    target: set[str],
    maximum: int,
    seed: int,
) -> list[frozenset[str]]:
    fixed = frozenset(clue.cell_id for clue in puzzle.clues if clue.kind == ClueKind.PI and clue.locked)
    forbidden = {clue.cell_id for clue in puzzle.clues if clue.kind == ClueKind.NUMBER and clue.locked}
    cell_selected = {
        cell_id: target.intersection(cell.edge_ids)
        for cell_id, cell in topology.cells.items()
        if cell_id not in forbidden
    }

    def compatible(union: set[str]) -> bool:
        sectors = [topology.edges[edge_id].sector for edge_id in union]
        return all(sector is not None for sector in sectors) and len(sectors) == len(set(sectors))

    initial_union = set().union(*(cell_selected[cell_id] for cell_id in fixed)) if fixed else set()
    if not compatible(initial_union):
        raise GenerationError("锁定的 π 提示在目标曲线上造成同方向圆弧重复")
    results: set[frozenset[str]] = set()
    if not fixed:
        results.add(frozenset())
    if len(initial_union) == 6:
        results.add(fixed)

    rng = random.Random(seed)
    candidates = [cell_id for cell_id, edges in cell_selected.items() if edges and cell_id not in fixed]
    rng.shuffle(candidates)

    def search(chosen: frozenset[str], union: set[str], depth: int) -> None:
        if len(results) >= maximum or depth > 6:
            return
        present = {topology.edges[edge_id].sector for edge_id in union}
        missing = next((sector for sector in range(6) if sector not in present), None)
        if missing is None:
            results.add(chosen)
            return
        additions = [
            cell_id
            for cell_id in candidates
            if cell_id not in chosen
            and any(topology.edges[edge_id].sector == missing for edge_id in cell_selected[cell_id])
        ]
        additions.sort(key=lambda cell_id: (len(cell_selected[cell_id] - union), cell_id))
        for cell_id in additions:
            new_union = union | cell_selected[cell_id]
            if new_union == union or not compatible(new_union):
                continue
            search(chosen | {cell_id}, new_union, depth + 1)
            if len(results) >= maximum:
                return

    search(fixed, initial_union, len(fixed))
    ordered = sorted(results, key=lambda group: (len(group), tuple(sorted(group))))
    return ordered[:maximum]


def _master_clue_selection(
    candidate_cells: list[str],
    locked_cells: set[str],
    distinguishing_sets: list[set[str]],
) -> tuple[set[str], bool]:
    model = cp_model.CpModel()
    variables = {cell_id: model.new_bool_var(f"clue[{cell_id}]") for cell_id in candidate_cells}
    for cell_id in locked_cells:
        model.add(variables[cell_id] == 1)
    for distinguishing in distinguishing_sets:
        usable = [variables[cell_id] for cell_id in distinguishing if cell_id in variables]
        if not usable:
            return set(), False
        model.add(sum(usable) >= 1)
    model.minimize(sum(variables.values()))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return set(), False
    return {cell_id for cell_id, variable in variables.items() if solver.value(variable)}, status == cp_model.OPTIMAL


def _make_candidate(
    source: Puzzle,
    topology: Topology,
    target: set[str],
    pi_cells: frozenset[str],
    selected_number_cells: set[str],
) -> Puzzle:
    locked_by_cell = {clue.cell_id: clue.locked for clue in source.clues}
    clues = [
        Clue(cell_id, ClueKind.NUMBER, _target_count(topology, target, cell_id), locked_by_cell.get(cell_id, False))
        for cell_id in sorted(selected_number_cells)
    ]
    clues.extend(Clue(cell_id, ClueKind.PI, None, locked_by_cell.get(cell_id, False)) for cell_id in sorted(pi_cells))
    return Puzzle(
        source.variant,
        dict(source.board),
        clues,
        sorted(target),
        Analysis(),
        dict(source.metadata),
        source.schema_version,
    )


def generate_puzzle(puzzle: Puzzle, options: GenerationOptions | None = None) -> GenerationResult:
    options = options or GenerationOptions()
    started = time.monotonic()
    valid, reason = validate_target_solution(puzzle, check_clues=True)
    if not valid:
        return GenerationResult(None, 0.0, False, message=reason)
    topology = build_topology(puzzle)
    target = set(puzzle.target_solution_edges or [])
    locked_numbers = {clue.cell_id for clue in puzzle.clues if clue.kind == ClueKind.NUMBER and clue.locked}
    fixed_pi = frozenset(clue.cell_id for clue in puzzle.clues if clue.kind == ClueKind.PI and clue.locked)

    if puzzle.variant == Variant.CIRCLE_PACK and options.auto_pi:
        try:
            requested_groups = options.max_pi_candidates + (1 if options.require_pi and not fixed_pi else 0)
            pi_groups = _valid_pi_groups(puzzle, topology, target, requested_groups, options.seed)
        except GenerationError as exc:
            return GenerationResult(None, time.monotonic() - started, False, message=str(exc))
    else:
        pi_groups = [fixed_pi]
    if options.require_pi:
        pi_groups = [group for group in pi_groups if group]
    elif options.prefer_pi:
        pi_groups.sort(key=lambda group: (not bool(group), len(group), tuple(sorted(group))))
    if not pi_groups:
        message = "目标曲线不存在合法的 π 组合" if options.require_pi else "没有可用的提示组合"
        return GenerationResult(None, time.monotonic() - started, False, message=message)

    best: Puzzle | None = None
    best_key: tuple[float, int, int] | None = None
    best_minimal = False
    examined = 0
    deadline = started + max(0.1, options.time_limit)
    rng = random.Random(options.seed)
    requested_level = (
        int(options.target_difficulty.rsplit("_", 1)[1])
        if options.target_difficulty and options.target_difficulty.startswith("level_")
        else None
    )

    def score_candidate(candidate: Puzzle, report: DifficultyReport, pi_cells: frozenset[str]) -> tuple[float, int, int]:
        number_count = sum(clue.kind == ClueKind.NUMBER for clue in candidate.clues)
        pi_count = len(pi_cells)
        if options.target_difficulty:
            target_score = {
                "easy": 25.0,
                "beginner": 45.0,
                "medium": 55.0,
                "hard": 82.0,
                "difficult": 82.0,
                "expert": 96.0,
                "level_1": 25.0,
                "level_2": 55.0,
                "level_3": 82.0,
                "level_4": 82.0,
                "level_5": 96.0,
            }[options.target_difficulty]
            return abs(report.score - target_score), number_count, pi_count
        pi_penalty = 0 if (pi_count or not options.prefer_pi or puzzle.variant != Variant.CIRCLE_PACK) else 1
        return float(number_count), pi_penalty, pi_count

    def mark_unique(candidate: Puzzle, message: str) -> None:
        candidate.analysis = Analysis(
            AnalysisStatus.UNIQUE,
            sorted(target),
            puzzle_content_hash(candidate),
            None,
            message,
        )

    for group_index, pi_cells in enumerate(pi_groups):
        if _cancelled(options) or time.monotonic() >= deadline:
            break
        examined += 1
        number_cells = sorted(set(topology.cells) - set(pi_cells))
        if not locked_numbers.issubset(number_cells):
            continue
        counterexamples: list[set[str]] = []
        selected_cells = set(locked_numbers)
        group_proven_minimal = False
        iterations = 0
        remaining_groups = max(1, len(pi_groups) - group_index)
        group_deadline = min(deadline, time.monotonic() + (deadline - time.monotonic()) / remaining_groups)

        # 先用所有兼容数字提示证明一个基线唯一题。这样即使后续最小化超时，
        # 也能返回一个确实唯一、可继续编辑的结果，而不是整轮生成失败。
        full_candidate = _make_candidate(puzzle, topology, target, pi_cells, set(number_cells))
        baseline_budget = min(10.0, max(0.25, (group_deadline - time.monotonic()) * 0.25))
        _notify(options, f"π 方案 {group_index + 1}/{len(pi_groups)}：验证全提示基线", (time.monotonic() - started) / options.time_limit)
        _, baseline_proven = find_alternative_solution(
            full_candidate,
            sorted(target),
            time_limit=baseline_budget,
            seed=rng.randrange(1_000_000_000),
            workers=options.workers,
        )
        if not baseline_proven:
            # 若所有数字仍允许替代解，任何数字子集都不可能唯一；若只是超时，
            # 继续本组也不会比验证最强题面更容易。
            continue
        baseline_result = solve_puzzle(
            full_candidate,
            time_limit=min(10.0, max(0.25, group_deadline - time.monotonic())),
            seed=options.seed,
            workers=options.workers,
        )
        if baseline_result.status != AnalysisStatus.UNIQUE:
            continue
        baseline_report = analyze_difficulty(full_candidate)
        baseline_key = score_candidate(full_candidate, baseline_report, pi_cells)
        if best_key is None or baseline_key < best_key:
            best, best_key = full_candidate, baseline_key
            best_minimal = False

        # 从已证明唯一的全提示题面向下删减。每次成功都会产生一个可立即返回的
        # 更好结果；失败时得到的替代解也可直接喂给后续 CEGIS 主问题。
        selected_cells = set(number_cells)
        counterexamples: list[set[str]] = []
        removable = [cell_id for cell_id in number_cells if cell_id not in locked_numbers]
        rng.shuffle(removable)
        greedy_fraction = min(0.98, max(0.05, options.greedy_fraction))
        greedy_deadline = time.monotonic() + max(0.0, (group_deadline - time.monotonic()) * greedy_fraction)
        target_reached = False
        for removal_index, cell_id in enumerate(removable, 1):
            if _cancelled(options) or time.monotonic() >= greedy_deadline:
                break
            trial_cells = selected_cells - {cell_id}
            trial = _make_candidate(puzzle, topology, target, pi_cells, trial_cells)
            alternative, proven_none = find_alternative_solution(
                trial,
                sorted(target),
                time_limit=min(5.0, max(0.05, greedy_deadline - time.monotonic())),
                seed=rng.randrange(1_000_000_000),
                workers=options.workers,
            )
            if proven_none:
                selected_cells = trial_cells
                mark_unique(trial, "贪心删提示后已证明唯一")
                report = analyze_difficulty(trial)
                key = score_candidate(trial, report, pi_cells)
                if best_key is None or key < best_key:
                    best, best_key = trial, key
                    best_minimal = False
                score_reached = options.minimum_target_score is None or report.score >= options.minimum_target_score
                if (
                    options.stop_at_target
                    and requested_level is not None
                    and report.level >= requested_level
                    and score_reached
                ):
                    target_reached = True
            elif alternative is not None:
                differing = {
                    candidate_cell
                    for candidate_cell in number_cells
                    if _target_count(topology, target, candidate_cell)
                    != _target_count(topology, set(alternative), candidate_cell)
                }
                if differing:
                    counterexamples.append(differing)
            _notify(
                options,
                f"π 方案 {group_index + 1}/{len(pi_groups)}：贪心删减 {removal_index}/{len(removable)}，保留 {len(selected_cells)} 个数字",
                (time.monotonic() - started) / options.time_limit,
            )
            if target_reached:
                _notify(options, f"已达到目标 {requested_level} 级，提前结束优化", (time.monotonic() - started) / options.time_limit)
                break

        if target_reached:
            break
        if not options.enable_cegis:
            break

        while time.monotonic() < group_deadline and not _cancelled(options):
            iterations += 1
            selected_cells, master_optimal = _master_clue_selection(number_cells, locked_numbers, counterexamples)
            candidate = _make_candidate(puzzle, topology, target, pi_cells, selected_cells)
            remaining = group_deadline - time.monotonic()
            alternative, proven_none = find_alternative_solution(
                candidate,
                sorted(target),
                time_limit=max(0.001, remaining),
                seed=rng.randrange(1_000_000_000),
                workers=options.workers,
            )
            if proven_none:
                solve_result = solve_puzzle(
                    candidate,
                    time_limit=max(0.1, min(10.0, deadline - time.monotonic())),
                    seed=options.seed,
                    workers=options.workers,
                )
                if solve_result.status == AnalysisStatus.UNIQUE:
                    report = analyze_difficulty(candidate)
                    key = score_candidate(candidate, report, pi_cells)
                    if best_key is None or key < best_key:
                        best, best_key = candidate, key
                        best_minimal = master_optimal
                group_proven_minimal = master_optimal
                break
            if alternative is None:
                break
            differing = {
                cell_id
                for cell_id in number_cells
                if _target_count(topology, target, cell_id) != _target_count(topology, set(alternative), cell_id)
            }
            if not differing:
                break
            counterexamples.append(differing)
            _notify(options, f"π 方案 {group_index + 1}/{len(pi_groups)}，已排除 {len(counterexamples)} 个替代解", (time.monotonic() - started) / options.time_limit)

    elapsed = time.monotonic() - started
    if best is None:
        message = "生成被取消" if _cancelled(options) else "时限内未找到已证明唯一的题目"
        return GenerationResult(None, elapsed, False, message=message, examined_pi_candidates=examined)
    difficulty = analyze_difficulty(best)
    numeric = sum(clue.kind == ClueKind.NUMBER for clue in best.clues)
    pi_count = sum(clue.kind == ClueKind.PI for clue in best.clues)
    best.metadata["generator"] = {
        "seed": options.seed,
        "time_limit": options.time_limit,
        "elapsed_seconds": round(elapsed, 3),
        "numeric_clues": numeric,
        "pi_clues": pi_count,
        "proven_minimal_numbers": best_minimal,
    }
    best.metadata["difficulty"] = difficulty.to_dict()
    _notify(options, "生成完成", 1.0)
    message = "已生成唯一解题目"
    if not best_minimal:
        message += "；当前为可靠基线，可增加时限继续减少提示"
    return GenerationResult(best, elapsed, best_minimal, numeric, pi_count, difficulty, message, examined)
