from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import PuzzleFormatError
from .model import Analysis, AnalysisStatus, Clue, ClueKind, Puzzle, SCHEMA_VERSION, Variant


def _expect_object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PuzzleFormatError(f"{name} 必须是对象")
    return value


def puzzle_content_hash(puzzle: Puzzle) -> str:
    content = {
        "schema_version": puzzle.schema_version,
        "variant": puzzle.variant.value,
        "board": puzzle.board,
        "clues": [clue.to_dict() for clue in sorted(puzzle.clues, key=lambda c: c.cell_id)],
    }
    raw = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def puzzle_from_dict(data: dict[str, Any]) -> Puzzle:
    data = _expect_object(data, "根节点")
    version = data.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise PuzzleFormatError(f"不支持 schema_version={version}，当前仅支持 {SCHEMA_VERSION}")
    try:
        variant = Variant(data["variant"])
    except KeyError as exc:
        raise PuzzleFormatError("缺少 variant") from exc
    except ValueError as exc:
        raise PuzzleFormatError(f"未知 variant: {data.get('variant')}") from exc
    board = _expect_object(data.get("board"), "board")
    raw_clues = data.get("clues", [])
    if not isinstance(raw_clues, list):
        raise PuzzleFormatError("clues 必须是数组")
    clues: list[Clue] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_clues):
        raw = _expect_object(raw, f"clues[{index}]")
        cell_id = raw.get("cell_id")
        if not isinstance(cell_id, str) or not cell_id:
            raise PuzzleFormatError(f"clues[{index}].cell_id 无效")
        if cell_id in seen:
            raise PuzzleFormatError(f"单元格 {cell_id} 存在重复提示")
        seen.add(cell_id)
        try:
            kind = ClueKind(raw.get("kind"))
        except ValueError as exc:
            raise PuzzleFormatError(f"clues[{index}].kind 无效") from exc
        value = raw.get("value")
        if kind == ClueKind.NUMBER and (not isinstance(value, int) or isinstance(value, bool)):
            raise PuzzleFormatError(f"数字提示 {cell_id} 缺少整数 value")
        if kind == ClueKind.PI and value is not None:
            raise PuzzleFormatError(f"π 提示 {cell_id} 不能同时含数字")
        clues.append(Clue(cell_id, kind, value, bool(raw.get("locked", False))))

    raw_target = data.get("target_solution_edges")
    if raw_target is not None and (not isinstance(raw_target, list) or not all(isinstance(x, str) for x in raw_target)):
        raise PuzzleFormatError("target_solution_edges 必须为空或字符串数组")

    raw_analysis = _expect_object(data.get("analysis", {}), "analysis")
    raw_status = raw_analysis.get("status")
    try:
        status = AnalysisStatus(raw_status) if raw_status is not None else None
    except ValueError as exc:
        raise PuzzleFormatError(f"未知 analysis.status: {raw_status}") from exc
    raw_solution = raw_analysis.get("solution_edges")
    if raw_solution is not None and (not isinstance(raw_solution, list) or not all(isinstance(x, str) for x in raw_solution)):
        raise PuzzleFormatError("analysis.solution_edges 必须为空或字符串数组")
    analysis = Analysis(
        status=status,
        solution_edges=raw_solution,
        puzzle_hash=raw_analysis.get("puzzle_hash"),
        elapsed_seconds=raw_analysis.get("elapsed_seconds"),
        message=raw_analysis.get("message"),
    )
    metadata = _expect_object(data.get("metadata", {}), "metadata")
    puzzle = Puzzle(variant, board, clues, raw_target, analysis, metadata, version)
    if analysis.puzzle_hash and analysis.puzzle_hash != puzzle_content_hash(puzzle):
        puzzle.clear_analysis()
    return puzzle


def load_puzzle(path: str | os.PathLike[str]) -> Puzzle:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return puzzle_from_dict(json.load(handle))
    except json.JSONDecodeError as exc:
        raise PuzzleFormatError(f"JSON 解析失败：{exc}") from exc
    except OSError as exc:
        raise PuzzleFormatError(f"无法读取题目：{exc}") from exc


def save_puzzle(puzzle: Puzzle, path: str | os.PathLike[str]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(puzzle.to_dict(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
