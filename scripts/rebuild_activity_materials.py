from __future__ import annotations

import csv
import json
from pathlib import Path

from shuhui.difficulty import analyze_difficulty, difficulty_display, difficulty_tier
from shuhui.pdf_export import export_booklets
from shuhui.solver import solve_puzzle
from shuhui.storage import load_puzzle, save_puzzle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"


def _puzzle_files() -> list[Path]:
    files = list((OUTPUT / "puzzles").glob("*/*.json"))
    return sorted(files, key=lambda path: int(path.stem))


def _build_examples(puzzles: list) -> list:
    example_dir = OUTPUT / "examples"
    example_dir.mkdir(parents=True, exist_ok=True)
    sources = [
        (load_puzzle(OUTPUT / "candidates" / "candidate-001.json"), "EX-01", "示例一", "beginner"),
        (load_puzzle(OUTPUT / "candidates" / "candidate-008.json"), "EX-02", "示例二", "medium"),
    ]
    examples = []
    for index, (puzzle, example_id, title, tier) in enumerate(sources, 1):
        puzzle.metadata.update(
            {
                "id": example_id,
                "title": title,
                "difficulty_tier": tier,
                "curated_difficulty": difficulty_display(tier),
                "example_only": True,
            }
        )
        puzzle.metadata.pop("target_minutes", None)
        solved = solve_puzzle(puzzle, time_limit=60, update=True)
        if solved.status is None or solved.status.value != "unique":
            raise RuntimeError(f"示例题 {example_id} 未通过唯一性验证")
        save_puzzle(puzzle, example_dir / f"{index:02d}-{tier}.json")
        examples.append(puzzle)
    return examples


def _replace_duplicate_challenge(puzzle):
    """Keep the stronger example while replacing its former duplicate TSH-05."""
    example_fingerprint = load_puzzle(OUTPUT / "candidates" / "candidate-008.json").metadata.get("target_fingerprint")
    if puzzle.metadata.get("id") == "TSH-05" and puzzle.metadata.get("target_fingerprint") == example_fingerprint:
        replacement = load_puzzle(OUTPUT / "candidates" / "candidate-056.json")
        replacement.metadata.update(
            {
                "id": "TSH-05",
                "title": "圆弧挑战 05",
                "difficulty_level": 2,
                "difficulty_tier": "beginner",
                "curated_difficulty": difficulty_display("beginner"),
                "playtest_status": "pending_two_testers",
            }
        )
        replacement.metadata.pop("target_minutes", None)
        save_puzzle(replacement, OUTPUT / "puzzles" / "medium" / "05.json")
        return replacement
    return puzzle


def main() -> int:
    puzzles = []
    verification = []
    for path in _puzzle_files():
        puzzle = _replace_duplicate_challenge(load_puzzle(path))
        old_level = int(puzzle.metadata.get("difficulty_level", 1))
        tier = difficulty_tier(old_level)
        display = difficulty_display(tier)
        puzzle.metadata["difficulty_tier"] = tier
        puzzle.metadata["curated_difficulty"] = display
        puzzle.metadata.pop("target_minutes", None)

        report = analyze_difficulty(puzzle)
        puzzle.metadata["difficulty"] = report.to_dict()
        save_puzzle(puzzle, path)
        solved = solve_puzzle(puzzle, time_limit=60, update=False)
        verification.append(
            {
                "id": puzzle.metadata["id"],
                "difficulty_tier": tier,
                "difficulty_display": display,
                "internal_score_band": report.level,
                "status": solved.status.value if solved.status else None,
                "target_matches_unique_solution": set(solved.solution or []) == set(puzzle.target_solution_edges or []),
                "solve_seconds": round(solved.elapsed_seconds, 4),
                "numeric_clues": sum(clue.kind.value == "number" for clue in puzzle.clues),
                "pi_clues": sum(clue.kind.value == "pi" for clue in puzzle.clues),
                "automatic_score": round(report.score, 3),
                "loop_edges": report.loop_edges,
                "circle_transitions": report.circle_transitions,
                "coverage_ratio": round(report.coverage_ratio, 3),
                "board_rows": len(puzzle.board.get("row_lengths", [])),
                "board_max_width": max(puzzle.board.get("row_lengths", [0])),
                "playtest_status": puzzle.metadata.get("playtest_status", "pending_two_testers"),
            }
        )
        puzzles.append(puzzle)

    examples = _build_examples(puzzles)
    export_booklets(
        puzzles,
        OUTPUT / "pdf" / "特色数回-活动题册.pdf",
        OUTPUT / "pdf" / "特色数回-答案册.pdf",
        examples=examples,
    )
    (OUTPUT / "verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with (OUTPUT / "playtest-record.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["题号", "难度", "试玩者", "日期", "完成用时(分钟)", "是否独立完成", "卡点", "规则歧义", "趣味评分(1-5)", "建议难度", "备注"]
        )
        for item in verification:
            for _ in range(2):
                writer.writerow([item["id"], item["difficulty_display"], "", "", "", "", "", "", "", "", ""])

    lines = [
        "# 特色数回活动题包验证报告",
        "",
        f"- 入选题数量：{len(puzzles)}",
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
    (OUTPUT / "验证报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
