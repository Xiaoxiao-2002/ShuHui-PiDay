from __future__ import annotations

from pathlib import Path

from shuhui.difficulty import analyze_difficulty, difficulty_display, difficulty_tier
from shuhui.generator import GenerationOptions, generate_puzzle
from shuhui.model import AnalysisStatus
from shuhui.pack import make_target_puzzle
from shuhui.render import export_svg
from shuhui.solver import solve_puzzle
from shuhui.storage import load_puzzle, save_puzzle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

SPECS = [
    {"id": 13, "level": 4, "profile": [10, 11] * 5, "seed": 4417, "min_edges": 68, "max_edges": 79, "attempts": 12000, "seconds": 300},
    {"id": 16, "level": 4, "profile": [9, 10] * 5, "seed": 4416, "min_edges": 62, "max_edges": 78, "attempts": 8000, "seconds": 300},
    {"id": 17, "level": 5, "profile": [10, 11, 12, 11] * 3, "seed": 5518, "min_edges": 130, "max_edges": 240, "attempts": 30000, "seconds": 1800},
    {"id": 18, "level": 5, "profile": [11, 12, 13, 12] * 3, "seed": 5520, "min_edges": 140, "max_edges": 300, "attempts": 80000, "seconds": 1800},
    {"id": 19, "level": 5, "profile": [11, 12] * 6, "seed": 5519, "min_edges": 145, "max_edges": 270, "attempts": 35000, "seconds": 1800},
]


def _generate(spec: dict) -> object:
    print(f"开始生成 TSH-{spec['id']:02d}，最长 {spec['seconds']} 秒", flush=True)
    source = make_target_puzzle(
        spec["profile"],
        spec["seed"],
        minimum_edges=spec["min_edges"],
        maximum_edges=spec["max_edges"],
        attempts=spec["attempts"],
    )
    result = generate_puzzle(
        source,
        GenerationOptions(
            time_limit=spec["seconds"],
            seed=spec["seed"],
            require_pi=True,
            prefer_pi=True,
            target_difficulty="difficult" if spec["level"] == 4 else "expert",
            max_pi_candidates=2 if spec["level"] == 4 else 1,
            greedy_fraction=0.78 if spec["level"] == 4 else 0.95,
            stop_at_target=True,
            minimum_target_score=80.0 if spec["level"] == 5 else 60.0,
            enable_cegis=spec["level"] == 4,
            progress=lambda message, fraction: print(
                f"TSH-{spec['id']:02d} {fraction:6.1%} {message}", flush=True
            ),
        ),
    )
    if result.puzzle is None:
        raise RuntimeError(f"TSH-{spec['id']:02d} 生成失败：{result.message}")
    return result.puzzle


def main() -> int:
    for spec in SPECS:
        folder = OUTPUT / "puzzles" / f"level-{spec['level']}"
        path = folder / f"{spec['id']:02d}.json"
        if path.exists():
            puzzle = load_puzzle(path)
            print(f"复用 {puzzle.metadata['id']}", flush=True)
        else:
            puzzle = _generate(spec)
        report = analyze_difficulty(puzzle)
        if report.level != spec["level"] or (spec["level"] == 5 and report.score < 80):
            raise RuntimeError(
                f"TSH-{spec['id']:02d} 难度未达标：level={report.level}, score={report.score:.1f}, "
                f"loop={report.loop_edges}, transitions={report.circle_transitions}, coverage={report.coverage_ratio:.3f}"
            )
        puzzle.metadata.update(
            {
                "id": f"TSH-{spec['id']:02d}",
                "title": f"圆弧挑战 {spec['id']:02d}",
                "difficulty_level": spec["level"],
                "difficulty_tier": difficulty_tier(spec["level"]),
                "curated_difficulty": difficulty_display(difficulty_tier(spec["level"])),
                "playtest_status": "pending_two_testers",
                "difficulty": report.to_dict(),
                "advanced_generation_spec": spec,
            }
        )
        puzzle.metadata.pop("target_minutes", None)
        verified = solve_puzzle(puzzle, time_limit=120, update=True)
        if verified.status != AnalysisStatus.UNIQUE or set(verified.solution or []) != set(puzzle.target_solution_edges or []):
            raise RuntimeError(f"TSH-{spec['id']:02d} 独立唯一性复验失败")
        folder.mkdir(parents=True, exist_ok=True)
        save_puzzle(puzzle, path)
        export_svg(puzzle, OUTPUT / "svg" / f"{spec['id']:02d}-puzzle.svg", title=puzzle.metadata["title"])
        export_svg(
            puzzle,
            OUTPUT / "svg" / f"{spec['id']:02d}-answer.svg",
            solution_edges=verified.solution,
            title=f"{puzzle.metadata['title']} - 答案",
        )
        print(
            f"完成 TSH-{spec['id']:02d}: level={report.level}, score={report.score:.1f}, "
            f"numbers={sum(c.kind.value == 'number' for c in puzzle.clues)}, "
            f"pi={sum(c.kind.value == 'pi' for c in puzzle.clues)}, loop={report.loop_edges}, "
            f"transitions={report.circle_transitions}, coverage={report.coverage_ratio:.3f}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
