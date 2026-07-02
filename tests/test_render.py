from shuhui.model import Clue, ClueKind, Puzzle, Variant
from shuhui.render import render_svg


def test_svg_contains_clues_and_arc_paths():
    puzzle = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": [2, 1]}, [Clue("circle:0:0", ClueKind.PI)])
    svg = render_svg(puzzle, title="特色数回")
    assert svg.startswith("<svg")
    assert "π" in svg
    assert " A " in svg
    assert "特色数回" in svg

