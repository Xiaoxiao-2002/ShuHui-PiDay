from shuhui.generator import GenerationOptions, generate_puzzle
from shuhui.model import AnalysisStatus, ClueKind, Puzzle, Variant
from shuhui.solver import solve_puzzle
from shuhui.topology import build_topology


def test_generator_can_choose_pi_and_prove_uniqueness():
    source = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": [2, 1]})
    topology = build_topology(source)
    source.target_solution_edges = list(topology.cells["circle:0:0"].edge_ids)
    result = generate_puzzle(source, GenerationOptions(time_limit=5, seed=7, max_pi_candidates=4))
    assert result.puzzle is not None
    assert result.numeric_clues == 0
    assert result.pi_clues == 1
    assert any(clue.kind == ClueKind.PI for clue in result.puzzle.clues)
    assert solve_puzzle(result.puzzle).status == AnalysisStatus.UNIQUE


def test_generation_is_reproducible():
    source = Puzzle(Variant.CLASSIC, {"rows": 1, "cols": 2})
    topology = build_topology(source)
    source.target_solution_edges = list(topology.cells["cell:0:0"].edge_ids)
    one = generate_puzzle(source, GenerationOptions(time_limit=5, seed=22, auto_pi=False))
    two = generate_puzzle(source, GenerationOptions(time_limit=5, seed=22, auto_pi=False))
    assert one.puzzle is not None and two.puzzle is not None
    assert [clue.to_dict() for clue in one.puzzle.clues] == [clue.to_dict() for clue in two.puzzle.clues]


def test_short_budget_returns_proven_full_clue_baseline():
    source = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": [2, 1]})
    topology = build_topology(source)
    source.target_solution_edges = list(topology.cells["circle:0:0"].edge_ids)
    result = generate_puzzle(
        source,
        GenerationOptions(time_limit=0.5, seed=3, auto_pi=False, prefer_pi=False),
    )
    assert result.puzzle is not None
    assert solve_puzzle(result.puzzle).status == AnalysisStatus.UNIQUE


def test_required_pi_never_returns_pi_free_puzzle():
    source = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": [2, 1]})
    topology = build_topology(source)
    source.target_solution_edges = list(topology.cells["circle:0:0"].edge_ids)
    result = generate_puzzle(
        source,
        GenerationOptions(time_limit=3, seed=9, require_pi=True, max_pi_candidates=1),
    )
    assert result.puzzle is not None
    assert result.pi_clues and result.pi_clues > 0
    assert all(clue.kind == ClueKind.PI for clue in result.puzzle.clues)
