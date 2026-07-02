from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from shuhui.generator import GenerationOptions, generate_puzzle
from shuhui.difficulty import analyze_difficulty
from shuhui.model import AnalysisStatus, Clue, ClueKind, Puzzle
from shuhui.pack import make_target_puzzle
from shuhui.pdf_export import export_booklets
from shuhui.render import export_svg
from shuhui.solver import solve_puzzle, validate_target_solution
from shuhui.storage import save_puzzle
from shuhui.topology import build_topology


PROFILES = [
    ([3, 4, 3, 4], 8, 18),
    ([4, 3, 4, 3], 8, 20),
    ([3, 4, 5, 4, 3], 12, 28),
    ([4, 5, 4, 5, 4], 14, 32),
    ([4, 5, 6, 5, 4, 5], 18, 38),
    ([5, 4, 5, 6, 5, 4], 18, 40),
]


def _clean(directory: Path) -> None:
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)


def _full_clue_fallback(source: Puzzle, seconds: float) -> Puzzle | None:
    topology = build_topology(source)
    target = set(source.target_solution_edges or [])
    clues = [
        Clue(cell_id, ClueKind.NUMBER, len(target.intersection(cell.edge_ids)))
        for cell_id, cell in sorted(topology.cells.items())
    ]
    puzzle = Puzzle(source.variant, dict(source.board), clues, sorted(target), metadata=dict(source.metadata))
    result = solve_puzzle(puzzle, time_limit=max(1.0, seconds))
    if result.status != AnalysisStatus.UNIQUE or set(result.solution or []) != target:
        return None
    difficulty = analyze_difficulty(puzzle)
    puzzle.metadata["generator"] = {
        "seed": source.metadata["seed"],
        "time_limit": seconds,
        "elapsed_seconds": round(result.elapsed_seconds, 3),
        "numeric_clues": len(clues),
        "pi_clues": 0,
        "proven_minimal_numbers": False,
        "fallback_full_clues": True,
    }
    puzzle.metadata["difficulty"] = difficulty.to_dict()
    return puzzle


def build(output: Path, count: int, seconds: float, seed: int) -> None:
    candidates_dir = output / "candidates"
    puzzles_dir = output / "puzzles"
    svg_dir = output / "svg"
    pdf_dir = output / "pdf"
    for directory in (candidates_dir, puzzles_dir, svg_dir, pdf_dir):
        _clean(directory)

    candidates = []
    seen: set[str] = set()
    attempts = 0
    maximum_attempts = max(count * 4, 100)
    while len(candidates) < count and attempts < maximum_attempts:
        candidate_seed = seed + attempts * 7919
        profile, minimum, maximum = PROFILES[attempts % len(PROFILES)]
        attempts += 1
        try:
            source = make_target_puzzle(profile, candidate_seed, minimum_edges=minimum, maximum_edges=maximum)
        except RuntimeError:
            continue
        fingerprint = source.metadata["target_fingerprint"]
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        result = generate_puzzle(
            source,
            GenerationOptions(
                time_limit=seconds,
                seed=candidate_seed,
                auto_pi=True,
                max_pi_candidates=3,
            ),
        )
        puzzle = result.puzzle or _full_clue_fallback(source, seconds)
        if puzzle is None:
            continue
        puzzle.metadata["candidate_index"] = len(candidates) + 1
        puzzle.metadata["playtest_status"] = "pending"
        path = candidates_dir / f"candidate-{len(candidates) + 1:03d}.json"
        save_puzzle(puzzle, path)
        candidates.append(puzzle)
        generator = puzzle.metadata["generator"]
        print(f"[{len(candidates):02d}/{count}] {profile} clues={generator['numeric_clues']}+{generator['pi_clues']} score={puzzle.metadata['difficulty']['score']:.1f}", flush=True)

    if len(candidates) < 12:
        raise RuntimeError(f"仅生成 {len(candidates)} 道已验证候选题，少于题包所需 12 道")

    ranked = sorted(candidates, key=lambda p: (p.metadata["difficulty"]["score"], p.metadata["generator"]["numeric_clues"]))
    positions = [
        *[round(i * (len(ranked) - 1) / 15) for i in range(4)],
        *[round((6 + i) * (len(ranked) - 1) / 15) for i in range(4)],
        *[round((12 + i) * (len(ranked) - 1) / 15) for i in range(4)],
    ]
    selected = []
    used: set[int] = set()
    for position in positions:
        while position in used and position + 1 < len(ranked):
            position += 1
        used.add(position)
        selected.append(ranked[position])

    labels = [("easy", "初级 Beginner", "5-20", 1), ("medium", "初级 Beginner", "5-20", 2), ("hard", "中级 Medium", "20-30", 3)]
    verification = []
    for index, puzzle in enumerate(selected, 1):
        folder, label, minutes, level = labels[(index - 1) // 4]
        puzzle.metadata["id"] = f"TSH-{index:02d}"
        puzzle.metadata["title"] = f"圆弧挑战 {index:02d}"
        puzzle.metadata["curated_difficulty"] = label
        puzzle.metadata["difficulty_level"] = level
        puzzle.metadata["difficulty_tier"] = "beginner" if level <= 2 else "medium"
        puzzle.metadata["target_minutes"] = minutes
        puzzle.metadata["playtest_status"] = "pending_two_testers"
        valid_target, target_message = validate_target_solution(puzzle)
        result = solve_puzzle(puzzle, time_limit=10)
        passed = valid_target and result.status == AnalysisStatus.UNIQUE and set(result.solution or []) == set(puzzle.target_solution_edges or [])
        if not passed:
            raise RuntimeError(f"题目 {index} 独立复验失败：{target_message}; {result.message}")
        folder_path = puzzles_dir / folder
        folder_path.mkdir(exist_ok=True)
        json_path = folder_path / f"{index:02d}.json"
        save_puzzle(puzzle, json_path)
        export_svg(puzzle, svg_dir / f"{index:02d}-puzzle.svg", title=puzzle.metadata["title"])
        export_svg(puzzle, svg_dir / f"{index:02d}-answer.svg", solution_edges=result.solution, title=f"{puzzle.metadata['title']} - 答案")
        verification.append({
            "id": puzzle.metadata["id"],
            "difficulty": label,
            "status": result.status.value,
            "target_matches_unique_solution": True,
            "solve_seconds": round(result.elapsed_seconds, 4),
            "numeric_clues": puzzle.metadata["generator"]["numeric_clues"],
            "pi_clues": puzzle.metadata["generator"]["pi_clues"],
            "automatic_score": puzzle.metadata["difficulty"]["score"],
            "playtest_status": puzzle.metadata["playtest_status"],
        })

    export_booklets(selected, pdf_dir / "特色数回-活动题册.pdf", pdf_dir / "特色数回-答案册.pdf")
    (output / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "playtest-record.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["题号", "试玩者", "日期", "完成用时(分钟)", "是否独立完成", "卡点", "规则歧义", "趣味评分(1-5)", "建议难度", "备注"])
        for item in verification:
            writer.writerow([item["id"], "", "", "", "", "", "", "", "", ""])
            writer.writerow([item["id"], "", "", "", "", "", "", "", "", ""])
    report_lines = ["# 特色数回活动题包验证报告", "", f"- 候选题数量：{len(candidates)}", "- 入选题数量：12", "- 全部题目：唯一解且与目标曲线一致", "- 人工试玩：待两名目标受众填写 `playtest-record.csv`", "", "| 题号 | 难度 | 数字 | π | 自动分 | 求解秒 | 试玩 |", "|---|---:|---:|---:|---:|---:|---|" ]
    for item in verification:
        report_lines.append(f"| {item['id']} | {item['difficulty']} | {item['numeric_clues']} | {item['pi_clues']} | {item['automatic_score']} | {item['solve_seconds']} | 待完成 |")
    (output / "验证报告.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--seconds", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=20260701)
    args = parser.parse_args()
    build(args.output, args.count, args.seconds, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
