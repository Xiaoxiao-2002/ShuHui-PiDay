import random

from pypdf import PdfReader

from shuhui.model import Puzzle, Variant
from shuhui.difficulty import difficulty_display, difficulty_tier
from shuhui.pack import CycleSampleOptions, sample_simple_cycle
from shuhui.pdf_export import export_booklets, export_single_pdf
from shuhui.solver import validate_target_solution
from shuhui.topology import build_topology


def test_sampled_cycle_is_valid():
    puzzle = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": [3, 4, 3, 4]})
    topology = build_topology(puzzle)
    puzzle.target_solution_edges = sample_simple_cycle(topology, random.Random(4), CycleSampleOptions(8, 20))
    valid, _ = validate_target_solution(puzzle)
    assert valid


def test_public_difficulty_uses_four_tiers():
    assert [difficulty_tier(level) for level in range(1, 6)] == [
        "beginner", "beginner", "medium", "difficult", "expert"
    ]
    assert difficulty_display("expert") == "专家 Expert"


def test_pdf_exports_have_expected_pages(tmp_path):
    puzzle = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": [2, 1]}, metadata={"title": "测试题"})
    topology = build_topology(puzzle)
    puzzle.target_solution_edges = list(topology.cells["circle:0:0"].edge_ids)
    single = tmp_path / "single.pdf"
    questions = tmp_path / "questions.pdf"
    answers = tmp_path / "answers.pdf"
    export_single_pdf(puzzle, single, show_solution=True)
    export_booklets([puzzle], questions, answers)
    assert len(PdfReader(single).pages) == 1
    assert len(PdfReader(questions).pages) == 3
    assert len(PdfReader(answers).pages) == 3
