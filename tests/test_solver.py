from shuhui.model import AnalysisStatus, Clue, ClueKind, Puzzle, Variant
from shuhui.solver import solve_puzzle, validate_solution_edges, validate_target_solution
from shuhui.topology import build_topology


def test_classic_statuses():
    unique = Puzzle(Variant.CLASSIC, {"rows": 1, "cols": 1}, [Clue("cell:0:0", ClueKind.NUMBER, 4)])
    unsat = Puzzle(Variant.CLASSIC, {"rows": 1, "cols": 1}, [Clue("cell:0:0", ClueKind.NUMBER, 0)])
    multiple = Puzzle(Variant.CLASSIC, {"rows": 1, "cols": 2})
    assert solve_puzzle(unique).status == AnalysisStatus.UNIQUE
    assert len(unique.analysis.solution_edges) == 4
    assert solve_puzzle(unsat).status == AnalysisStatus.UNSATISFIABLE
    assert solve_puzzle(multiple).status == AnalysisStatus.MULTIPLE


def test_player_solution_can_be_validated_without_replacing_target():
    puzzle = Puzzle(Variant.CLASSIC, {"rows": 1, "cols": 1}, [Clue("cell:0:0", ClueKind.NUMBER, 4)])
    topology = build_topology(puzzle)
    answer = list(topology.cells["cell:0:0"].edge_ids)
    valid, _ = validate_solution_edges(puzzle, answer)
    assert valid
    assert puzzle.target_solution_edges is None
    invalid, message = validate_solution_edges(puzzle, answer[:-1])
    assert not invalid
    assert "端点" in message


def test_disconnected_target_is_rejected():
    puzzle = Puzzle(Variant.CLASSIC, {"rows": 1, "cols": 3})
    topology = build_topology(puzzle)
    puzzle.target_solution_edges = sorted(set(topology.cells["cell:0:0"].edge_ids) | set(topology.cells["cell:0:2"].edge_ids))
    valid, message = validate_target_solution(puzzle)
    assert not valid
    assert "多个" in message


def test_pi_constraint_and_shared_edge_deduplication():
    puzzle = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": [2, 1]})
    topology = build_topology(puzzle)
    puzzle.target_solution_edges = list(topology.cells["circle:0:0"].edge_ids)
    triangle_id = next(cell.id for cell in topology.cells.values() if cell.kind == "triangle")
    puzzle.clues = [Clue("circle:0:0", ClueKind.PI), Clue(triangle_id, ClueKind.PI)]
    valid, _ = validate_target_solution(puzzle)
    assert valid
    assert solve_puzzle(puzzle).status == AnalysisStatus.UNIQUE
