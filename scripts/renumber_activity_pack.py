from __future__ import annotations

from pathlib import Path

from shuhui.pdf_export import _puzzle_tier
from shuhui.render import export_svg
from shuhui.solver import solve_puzzle
from shuhui.storage import load_puzzle, save_puzzle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
PUZZLES = OUTPUT / "puzzles"
TIER_RANK = {"beginner": 0, "medium": 1, "difficult": 2, "expert": 3}


def _score(puzzle) -> float:
    difficulty = puzzle.metadata.get("difficulty", {})
    return float(difficulty.get("score", 0.0)) if isinstance(difficulty, dict) else 0.0


def _folder_for(index: int) -> str:
    if index <= 4:
        return "easy"
    if index <= 8:
        return "medium"
    if index <= 12:
        return "hard"
    if index <= 16:
        return "level-4"
    return "level-5"


def main() -> int:
    source_paths = list(PUZZLES.glob("*/*.json"))
    puzzles = [load_puzzle(path) for path in source_paths]
    if len(puzzles) != 20:
        raise RuntimeError(f"预期 20 道正式题，实际找到 {len(puzzles)} 道")
    puzzles.sort(key=lambda puzzle: (TIER_RANK[_puzzle_tier(puzzle)], _score(puzzle), puzzle.metadata.get("id", "")))

    destinations: set[Path] = set()
    mapping: list[tuple[str, str]] = []
    for index, puzzle in enumerate(puzzles, 1):
        old_id = str(puzzle.metadata.get("id", ""))
        new_id = f"TSH-{index:02d}"
        mapping.append((old_id, new_id))
        puzzle.metadata["id"] = new_id
        puzzle.metadata["title"] = new_id
        spec = puzzle.metadata.get("advanced_generation_spec")
        if isinstance(spec, dict):
            spec["id"] = index
        result = solve_puzzle(puzzle, time_limit=120, update=True)
        if result.status is None or result.status.value != "unique":
            raise RuntimeError(f"{old_id} 改名后唯一性复验失败")
        destination = PUZZLES / _folder_for(index) / f"{index:02d}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        save_puzzle(puzzle, destination)
        destinations.add(destination.resolve())
        export_svg(puzzle, OUTPUT / "svg" / f"{index:02d}-puzzle.svg", title=new_id)
        export_svg(
            puzzle,
            OUTPUT / "svg" / f"{index:02d}-answer.svg",
            solution_edges=result.solution,
            title=f"{new_id} - 答案",
        )

    # Remove only superseded JSON names after every new file has been written
    # and independently verified.
    for path in PUZZLES.glob("*/*.json"):
        if path.resolve() not in destinations:
            path.unlink()

    print("编号映射：")
    for old_id, new_id in mapping:
        print(f"  {old_id} -> {new_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
