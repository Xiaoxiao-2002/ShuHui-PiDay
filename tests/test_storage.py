import json

import pytest

from shuhui.errors import PuzzleFormatError
from shuhui.model import Analysis, AnalysisStatus, Clue, ClueKind, Puzzle, Variant
from shuhui.storage import load_puzzle, puzzle_content_hash, save_puzzle


def test_round_trip_all_nullable_fields(tmp_path):
    puzzle = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": [2, 1]}, metadata={"title": "测试 π"})
    path = tmp_path / "题目.json"
    save_puzzle(puzzle, path)
    loaded = load_puzzle(path)
    assert loaded.to_dict() == puzzle.to_dict()
    assert loaded.analysis.status is None
    assert loaded.target_solution_edges is None


def test_stale_analysis_is_cleared(tmp_path):
    puzzle = Puzzle(Variant.CLASSIC, {"rows": 1, "cols": 1}, [Clue("cell:0:0", ClueKind.NUMBER, 4)])
    puzzle.analysis = Analysis(AnalysisStatus.UNIQUE, ["h:0:0"], puzzle_content_hash(puzzle))
    data = puzzle.to_dict()
    data["clues"][0]["value"] = 0
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_puzzle(path)
    assert loaded.analysis.status is None
    assert loaded.analysis.solution_edges is None


def test_rejects_duplicate_clues(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps({
            "schema_version": 1,
            "variant": "classic",
            "board": {"rows": 1, "cols": 1},
            "clues": [
                {"cell_id": "cell:0:0", "kind": "number", "value": 1},
                {"cell_id": "cell:0:0", "kind": "number", "value": 2},
            ],
        }),
        encoding="utf-8",
    )
    with pytest.raises(PuzzleFormatError):
        load_puzzle(path)

