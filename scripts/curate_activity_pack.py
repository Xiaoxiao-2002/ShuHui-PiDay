from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from shuhui.model import AnalysisStatus
from shuhui.pdf_export import export_booklets
from shuhui.render import export_svg
from shuhui.solver import solve_puzzle, validate_target_solution
from shuhui.storage import load_puzzle, save_puzzle


def _spread(items: list, count: int) -> list:
    if len(items) < count:
        raise RuntimeError(f"可选题只有 {len(items)} 道，少于所需 {count} 道")
    if count == 1:
        return [items[len(items) // 2]]
    return [items[round(i * (len(items) - 1) / (count - 1))] for i in range(count)]


def curate(output: Path) -> None:
    candidates = [load_puzzle(path) for path in sorted((output / "candidates").glob("*.json"))]
    fallback = [p for p in candidates if p.metadata.get("generator", {}).get("fallback_full_clues")]
    optimized = [p for p in candidates if not p.metadata.get("generator", {}).get("fallback_full_clues")]
    if len(candidates) < 60:
        raise RuntimeError(f"候选题应不少于 60 道，当前为 {len(candidates)} 道")
    if len(optimized) < 8:
        raise RuntimeError(f"中高难需要至少 8 道删提示优化题，当前为 {len(optimized)} 道")

    fallback.sort(key=lambda p: (len(p.board["row_lengths"]), p.metadata["target_edge_count"], p.metadata["target_fingerprint"]))
    optimized.sort(key=lambda p: (p.metadata["difficulty"]["score"], p.metadata["generator"]["numeric_clues"]))
    easy = _spread(fallback, 4)
    medium_pool = optimized[: max(4, len(optimized) // 2)]
    hard_pool = optimized[max(4, len(optimized) // 2) :]
    if len(hard_pool) < 4:
        hard_pool = optimized[-4:]
    selected = _spread(medium_pool, 4) + _spread(hard_pool, 4)
    selected = easy + selected

    puzzles_dir = output / "puzzles"
    svg_dir = output / "svg"
    pdf_dir = output / "pdf"
    for directory in (puzzles_dir, svg_dir, pdf_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)

    labels = [("easy", "初级 Beginner", "5-20", 1), ("medium", "初级 Beginner", "5-20", 2), ("hard", "中级 Medium", "20-30", 3)]
    verification = []
    for index, puzzle in enumerate(selected, 1):
        folder, label, minutes, level = labels[(index - 1) // 4]
        puzzle.metadata.update({
            "id": f"TSH-{index:02d}",
            "title": f"圆弧挑战 {index:02d}",
            "curated_difficulty": label,
            "difficulty_level": level,
            "difficulty_tier": "beginner" if level <= 2 else "medium",
            "target_minutes": minutes,
            "playtest_status": "pending_two_testers",
        })
        target_ok, target_message = validate_target_solution(puzzle)
        result = solve_puzzle(puzzle, time_limit=10)
        if not target_ok or result.status != AnalysisStatus.UNIQUE or set(result.solution or []) != set(puzzle.target_solution_edges or []):
            raise RuntimeError(f"{puzzle.metadata['id']} 复验失败：{target_message}; {result.message}")
        folder_path = puzzles_dir / folder
        folder_path.mkdir(exist_ok=True)
        save_puzzle(puzzle, folder_path / f"{index:02d}.json")
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
            "optimized_clues": not puzzle.metadata["generator"].get("fallback_full_clues", False),
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
    lines = [
        "# 特色数回活动题包验证报告", "",
        f"- 候选题数量：{len(candidates)}", f"- 完成删提示优化的候选题：{len(optimized)}", "- 入选题数量：12",
        "- 全部入选题均经独立求解，唯一解与目标曲线一致。", "- 简单题采用全提示候选；中高难题全部采用删提示优化候选。",
        "- 难度与目标用时仍须两名目标受众试玩确认。", "",
        "| 题号 | 难度 | 数字 | π | 自动分 | 求解秒 | 提示优化 | 试玩 |", "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in verification:
        lines.append(f"| {item['id']} | {item['difficulty']} | {item['numeric_clues']} | {item['pi_clues']} | {item['automatic_score']} | {item['solve_seconds']} | {'是' if item['optimized_clues'] else '全提示'} | 待完成 |")
    (output / "验证报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    curate(Path("output"))
