from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

from shuhui.difficulty import analyze_difficulty, difficulty_display, difficulty_tier
from shuhui.generator import GenerationOptions, generate_puzzle
from shuhui.model import AnalysisStatus, Puzzle
from shuhui.pack import make_target_puzzle
from shuhui.pdf_export import export_booklets
from shuhui.render import export_svg
from shuhui.solver import solve_puzzle
from shuhui.storage import load_puzzle, save_puzzle


ADVANCED_SPECS = [
    {
        "id": 13,
        "level": 4,
        "profile": [10, 11] * 5,
        "seed": 4417,
        "min_edges": 68,
        "max_edges": 79,
        "attempts": 12000,
        "seconds": 300,
    },
    {
        "id": 14,
        "level": 4,
        "profile": [9, 10, 9, 10, 9, 10, 9, 10, 9, 10],
        "seed": 4402,
        "min_edges": 65,
        "max_edges": 120,
        "seconds": 120,
    },
    {
        "id": 15,
        "level": 4,
        "profile": [8, 9] * 5,
        "seed": 4401,
        "min_edges": 55,
        "max_edges": 100,
        "seconds": 120,
    },
    {
        "id": 16,
        "level": 4,
        "profile": [9, 10] * 5,
        "seed": 4416,
        "min_edges": 62,
        "max_edges": 78,
        "attempts": 8000,
        "seconds": 300,
    },
    {
        "id": 17,
        "level": 5,
        "profile": [10, 11, 12, 11] * 3,
        "seed": 5518,
        "min_edges": 130,
        "max_edges": 240,
        "attempts": 30000,
        "seconds": 1800,
    },
    {
        "id": 18,
        "level": 5,
        "profile": [11, 12, 13, 12] * 3,
        "seed": 5520,
        "min_edges": 140,
        "max_edges": 300,
        "attempts": 80000,
        "seconds": 1800,
    },
    {
        "id": 19,
        "level": 5,
        "profile": [11, 12] * 6,
        "seed": 5519,
        "min_edges": 145,
        "max_edges": 270,
        "attempts": 35000,
        "seconds": 1800,
    },
    {
        "id": 20,
        "level": 5,
        "profile": [10, 11, 12, 11] * 3,
        "seed": 5504,
        "min_edges": 150,
        "max_edges": 260,
        "attempts": 20000,
        "seconds": 1800,
    },
]


def _existing_puzzles(output: Path) -> list[Puzzle]:
    result: list[Puzzle] = []
    for folder, level in (("easy", 1), ("medium", 2), ("hard", 3)):
        for path in sorted((output / "puzzles" / folder).glob("*.json")):
            puzzle = load_puzzle(path)
            puzzle.metadata["difficulty_level"] = level
            tier = difficulty_tier(level)
            puzzle.metadata["difficulty_tier"] = tier
            puzzle.metadata["curated_difficulty"] = difficulty_display(tier)
            puzzle.metadata["difficulty"] = analyze_difficulty(puzzle).to_dict()
            save_puzzle(puzzle, path)
            result.append(puzzle)
    return result


def main() -> int:
    output = Path("output")
    existing = _existing_puzzles(output)
    advanced: list[Puzzle] = []
    for spec in ADVANCED_SPECS:
        folder = output / "puzzles" / f"level-{spec['level']}"
        saved_path = folder / f"{spec['id']:02d}.json"
        if "--resume" in sys.argv and saved_path.exists():
            puzzle = load_puzzle(saved_path)
            advanced.append(puzzle)
            print(f"复用已生成的 {puzzle.metadata['id']}", flush=True)
            continue
        checkpoint = output / "candidates" / f"advanced-level-{spec['level']}-latest.json"
        if "--use-checkpoint" in sys.argv and checkpoint.exists():
            puzzle = load_puzzle(checkpoint)
            print(f"采用已证明唯一的 {spec['level']} 级检查点", flush=True)
        else:
            print(f"开始生成 TSH-{spec['id']:02d}（{spec['level']} 级，最长 {spec['seconds']} 秒）", flush=True)
            source = make_target_puzzle(
                spec["profile"],
                spec["seed"],
                minimum_edges=spec["min_edges"],
                maximum_edges=spec["max_edges"],
                attempts=spec.get("attempts", 500),
            )
            result = generate_puzzle(
                source,
                GenerationOptions(
                    time_limit=spec["seconds"],
                    seed=spec["seed"],
                    require_pi=True,
                    prefer_pi=True,
                    target_difficulty=f"level_{spec['level']}",
                    max_pi_candidates=1,
                    greedy_fraction=0.75 if spec["level"] == 4 else 0.95,
                    stop_at_target=True,
                    minimum_target_score=90.0 if spec["level"] == 5 else None,
                    enable_cegis=spec["level"] != 5,
                    progress=lambda message, fraction, puzzle_id=spec["id"]: print(
                        f"TSH-{puzzle_id:02d} {fraction:6.1%} {message}", flush=True
                    ),
                ),
            )
            if result.puzzle is None:
                raise RuntimeError(f"TSH-{spec['id']:02d} 生成失败：{result.message}")
            puzzle = result.puzzle
            save_puzzle(puzzle, checkpoint)
        report = analyze_difficulty(puzzle)
        score_floor = 84.0 if spec["level"] == 5 else 0.0
        if report.level != spec["level"] or report.score < score_floor:
            raise RuntimeError(
                f"TSH-{spec['id']:02d} 自动评为 {report.level} 级而非 {spec['level']} 级；"
                f"score={report.score:.1f}（要求至少 {score_floor:.1f}），"
                f"loop={report.loop_edges}, transitions={report.circle_transitions}"
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
        verified = solve_puzzle(puzzle, time_limit=60)
        if verified.status != AnalysisStatus.UNIQUE or set(verified.solution or []) != set(puzzle.target_solution_edges or []):
            raise RuntimeError(f"TSH-{spec['id']:02d} 独立复验失败")
        folder.mkdir(parents=True, exist_ok=True)
        save_puzzle(puzzle, saved_path)
        export_svg(puzzle, output / "svg" / f"{spec['id']:02d}-puzzle.svg", title=puzzle.metadata["title"])
        export_svg(
            puzzle,
            output / "svg" / f"{spec['id']:02d}-answer.svg",
            solution_edges=verified.solution,
            title=f"{puzzle.metadata['title']} - 答案",
        )
        advanced.append(puzzle)
        numeric_clues = sum(clue.kind.value == "number" for clue in puzzle.clues)
        pi_clues = sum(clue.kind.value == "pi" for clue in puzzle.clues)
        print(
            f"完成 TSH-{spec['id']:02d}: level={report.level}, numbers={numeric_clues}, "
            f"pi={pi_clues}, score={report.score:.1f}, loop={report.loop_edges}, "
            f"transitions={report.circle_transitions}, coverage={report.coverage_ratio:.3f}",
            flush=True,
        )

    all_puzzles = existing + advanced
    export_booklets(
        all_puzzles,
        output / "pdf" / "特色数回-活动题册.pdf",
        output / "pdf" / "特色数回-答案册.pdf",
    )

    verification = []
    for puzzle in all_puzzles:
        solved = solve_puzzle(puzzle, time_limit=60, update=False)
        difficulty = analyze_difficulty(puzzle)
        verification.append(
            {
                "id": puzzle.metadata["id"],
                "difficulty_tier": puzzle.metadata["difficulty_tier"],
                "difficulty_display": puzzle.metadata["curated_difficulty"],
                "status": solved.status.value if solved.status else None,
                "target_matches_unique_solution": set(solved.solution or []) == set(puzzle.target_solution_edges or []),
                "solve_seconds": round(solved.elapsed_seconds, 4),
                "numeric_clues": sum(clue.kind.value == "number" for clue in puzzle.clues),
                "pi_clues": sum(clue.kind.value == "pi" for clue in puzzle.clues),
                "internal_score_band": difficulty.level,
                "automatic_score": round(difficulty.score, 3),
                "loop_edges": difficulty.loop_edges,
                "circle_transitions": difficulty.circle_transitions,
                "coverage_ratio": round(difficulty.coverage_ratio, 3),
                "board_rows": len(puzzle.board.get("row_lengths", [])),
                "board_max_width": max(puzzle.board.get("row_lengths", [0])),
                "playtest_status": puzzle.metadata["playtest_status"],
            }
        )
    (output / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "playtest-record.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["题号", "难度", "试玩者", "日期", "完成用时(分钟)", "是否独立完成", "卡点", "规则歧义", "趣味评分(1-5)", "建议难度", "备注"])
        for item in verification:
            for _ in range(2):
                writer.writerow([item["id"], item["difficulty_display"], "", "", "", "", "", "", "", "", ""])

    lines = [
        "# 特色数回活动题包验证报告",
        "",
        f"- 入选题数量：{len(all_puzzles)}",
        "- 面向参与者采用四级难度：初级 Beginner、中级 Medium、高级 Difficult、专家 Expert。",
        "- 原 easy 与 medium 合并为初级；原 hard、level-4、level-5 依次对应中级、高级、专家。",
        "- 全部题目均经独立求解，唯一解与目标曲线一致；人工试玩仍待完成。",
        "",
        "| 题号 | 难度 | 棋盘 | 数字 | π | 算法分段 | 分数 | 环长 | 跨圆 | 覆盖 | 求解秒 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in verification:
        lines.append(
            f"| {item['id']} | {item['difficulty_display']} | {item['board_rows']}×{item['board_max_width']} | "
            f"{item['numeric_clues']} | {item['pi_clues']} | {item['internal_score_band']} | "
            f"{item['automatic_score']} | {item['loop_edges']} | {item['circle_transitions']} | "
            f"{item['coverage_ratio']} | {item['solve_seconds']} |"
        )
    (output / "验证报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
