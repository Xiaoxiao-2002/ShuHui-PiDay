from shuhui.difficulty import analyze_difficulty
from shuhui.model import Puzzle, Variant
from shuhui.pack import make_target_puzzle
from shuhui.topology import build_topology


def test_cell_perimeter_is_level_one_even_with_few_clues():
    puzzle = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": [2, 1]})
    topology = build_topology(puzzle)
    puzzle.target_solution_edges = list(topology.cells["circle:0:0"].edge_ids)
    report = analyze_difficulty(puzzle)
    assert report.level == 1


def test_large_board_with_level_three_style_structure_is_level_four():
    puzzle = make_target_puzzle(
        [8, 9, 8, 9, 8, 9, 8, 9, 8, 9],
        4401,
        minimum_edges=55,
        maximum_edges=100,
    )
    report = analyze_difficulty(puzzle)
    assert report.level == 4
    assert report.loop_edges >= 55


def test_extreme_large_board_is_level_five():
    puzzle = make_target_puzzle(
        [10, 11, 12, 11, 10, 11, 12, 11, 10, 11, 12, 11],
        5504,
        minimum_edges=150,
        maximum_edges=260,
        attempts=20000,
    )
    report = analyze_difficulty(puzzle)
    assert report.level == 5
    assert report.circle_transitions >= 30
