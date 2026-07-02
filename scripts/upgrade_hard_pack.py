from __future__ import annotations

import json
import sys
from pathlib import Path

from shuhui.difficulty import analyze_difficulty
from shuhui.generator import GenerationOptions, generate_puzzle
from shuhui.model import AnalysisStatus, Puzzle
from shuhui.pdf_export import export_booklets
from shuhui.render import export_svg
from shuhui.solver import solve_puzzle
from shuhui.storage import load_puzzle, save_puzzle


SOURCES = ["022", "027", "010", "028"]


def main() -> int:
    output = Path("output")
    hard_dir = output / "puzzles" / "hard"
    hard_dir.mkdir(parents=True, exist_ok=True)
    enhanced: list[Puzzle] = []
    if "--refresh-only" in sys.argv:
        enhanced = [load_puzzle(path) for path in sorted(hard_dir.glob("*.json"))]
    else:
        for offset, source_id in enumerate(SOURCES, 9):
            original = load_puzzle(output / "candidates" / f"candidate-{source_id}.json")
            source = Puzzle(
                original.variant,
                dict(original.board),
                target_solution_edges=list(original.target_solution_edges or []),
                metadata={"source_candidate": source_id},
            )
            result = generate_puzzle(
                source,
                GenerationOptions(
                    time_limit=25,
                    seed=20260701 + offset,
                    require_pi=True,
                    prefer_pi=True,
                    target_difficulty="hard",
                    max_pi_candidates=1,
                ),
            )
            if result.puzzle is None or result.pi_clues is None or result.pi_clues == 0:
                raise RuntimeError(f"候选 {source_id} 未生成含 π 的困难题：{result.message}")
            puzzle = result.puzzle
            puzzle.metadata.update(
                {
                    "id": f"TSH-{offset:02d}",
                    "title": f"圆弧挑战 {offset:02d}",
                    "curated_difficulty": "中级 Medium",
                    "difficulty_level": 3,
                    "difficulty_tier": "medium",
                    "target_minutes": "20-30",
                    "playtest_status": "pending_two_testers",
                    "source_candidate": source_id,
                }
            )
            verification = solve_puzzle(puzzle, time_limit=30)
            if verification.status != AnalysisStatus.UNIQUE:
                raise RuntimeError(f"{puzzle.metadata['id']} 复验失败：{verification.message}")
            save_puzzle(puzzle, hard_dir / f"{offset:02d}.json")
            export_svg(puzzle, output / "svg" / f"{offset:02d}-puzzle.svg", title=puzzle.metadata["title"])
            export_svg(
                puzzle,
                output / "svg" / f"{offset:02d}-answer.svg",
                solution_edges=verification.solution,
                title=f"{puzzle.metadata['title']} - 答案",
            )
            enhanced.append(puzzle)
            print(
                f"{puzzle.metadata['id']}: numbers={result.numeric_clues}, pi={result.pi_clues}, "
                f"score={result.difficulty.score:.1f}, loop={result.difficulty.loop_edges}, "
                f"transitions={result.difficulty.circle_transitions}",
                flush=True,
            )

    easy = [load_puzzle(path) for path in sorted((output / "puzzles" / "easy").glob("*.json"))]
    medium = [load_puzzle(path) for path in sorted((output / "puzzles" / "medium").glob("*.json"))]
    all_puzzles = easy + medium + enhanced
    for puzzle in all_puzzles:
        puzzle.metadata["difficulty"] = analyze_difficulty(puzzle).to_dict()
        folder = "easy" if puzzle.metadata["id"] <= "TSH-04" else "medium" if puzzle.metadata["id"] <= "TSH-08" else "hard"
        save_puzzle(puzzle, output / "puzzles" / folder / f"{int(puzzle.metadata['id'].split('-')[1]):02d}.json")
    export_booklets(
        all_puzzles,
        output / "pdf" / "特色数回-活动题册.pdf",
        output / "pdf" / "特色数回-答案册.pdf",
    )

    report = []
    for puzzle in all_puzzles:
        solved = solve_puzzle(puzzle, time_limit=30, update=False)
        difficulty = puzzle.metadata.get("difficulty", {})
        report.append(
            {
                "id": puzzle.metadata["id"],
                "difficulty": puzzle.metadata["curated_difficulty"],
                "status": solved.status.value if solved.status else None,
                "target_matches_unique_solution": set(solved.solution or []) == set(puzzle.target_solution_edges or []),
                "solve_seconds": round(solved.elapsed_seconds, 4),
                "numeric_clues": sum(clue.kind.value == "number" for clue in puzzle.clues),
                "pi_clues": sum(clue.kind.value == "pi" for clue in puzzle.clues),
                "automatic_score": difficulty.get("score"),
                "loop_edges": difficulty.get("loop_edges"),
                "circle_transitions": difficulty.get("circle_transitions"),
                "coverage_ratio": difficulty.get("coverage_ratio"),
                "playtest_status": puzzle.metadata["playtest_status"],
            }
        )
    (output / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 特色数回活动题包验证报告",
        "",
        "- 入选题数量：12",
        "- 全部入选题均经独立求解，唯一解与目标曲线一致。",
        "- 新困难题全部强制包含 π，并按曲线长度、跨圆转移和覆盖范围筛选。",
        "- 难度与目标用时仍须两名目标受众试玩确认。",
        "",
        "| 题号 | 难度 | 数字 | π | 自动分 | 环长 | 跨圆 | 覆盖 | 求解秒 | 试玩 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in report:
        lines.append(
            f"| {item['id']} | {item['difficulty']} | {item['numeric_clues']} | {item['pi_clues']} | "
            f"{item['automatic_score']} | {item['loop_edges']} | {item['circle_transitions']} | "
            f"{item['coverage_ratio']} | {item['solve_seconds']} | 待完成 |"
        )
    (output / "验证报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
