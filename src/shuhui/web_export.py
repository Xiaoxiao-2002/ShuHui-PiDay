from __future__ import annotations

import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .model import Puzzle
from .solver import solve_puzzle, validate_target_solution
from .storage import load_puzzle, puzzle_content_hash
from .topology import Topology, build_topology


WEB_SCHEMA_VERSION = 1
DATA_VERSION = "piday-2026-v1"
TIER_LABELS = {
    "beginner": "初级 Beginner",
    "medium": "中级 Medium",
    "difficult": "高级 Difficult",
    "expert": "专家 Expert",
}


def _tier(puzzle: Puzzle) -> str:
    value = str(puzzle.metadata.get("difficulty_tier", ""))
    if value not in TIER_LABELS:
        raise ValueError(f"{puzzle.metadata.get('id', '?')} 缺少有效 difficulty_tier")
    return value


def playable_payload(puzzle: Puzzle, topology: Topology | None = None) -> dict[str, Any]:
    topology = topology or build_topology(puzzle)
    puzzle_id = str(puzzle.metadata.get("id", ""))
    if not puzzle_id:
        raise ValueError("题目缺少 metadata.id")
    tier = _tier(puzzle)
    vertices = [
        {"id": item.id, "x": item.x, "y": item.y}
        for item in sorted(topology.vertices.values(), key=lambda item: item.id)
    ]
    edges = []
    for item in sorted(topology.edges.values(), key=lambda item: item.id):
        edge: dict[str, Any] = {
            "id": item.id,
            "vertices": list(item.vertices),
            "sector": item.sector,
        }
        if item.circle_center is not None:
            edge["circle"] = {
                "center": list(item.circle_center),
                "radius": item.circle_radius,
                "startAngle": item.start_angle,
                "spanAngle": item.span_angle,
            }
        edges.append(edge)
    cells = [
        {
            "id": item.id,
            "edgeIds": list(item.edge_ids),
            "center": list(item.center),
            "kind": item.kind,
        }
        for item in sorted(topology.cells.values(), key=lambda item: item.id)
    ]
    xs = [item.x for item in topology.vertices.values()]
    ys = [item.y for item in topology.vertices.values()]
    return {
        "schemaVersion": WEB_SCHEMA_VERSION,
        "dataVersion": DATA_VERSION,
        "sourceHash": puzzle_content_hash(puzzle),
        "id": puzzle_id,
        "difficulty": tier,
        "difficultyLabel": TIER_LABELS[tier],
        "clues": [
            {
                "cellId": clue.cell_id,
                "kind": clue.kind.value,
                **({"value": clue.value} if clue.kind.value == "number" else {}),
            }
            for clue in sorted(puzzle.clues, key=lambda clue: clue.cell_id)
        ],
        "topology": {
            "bounds": {"minX": min(xs), "maxX": max(xs), "minY": min(ys), "maxY": max(ys)},
            "vertices": vertices,
            "edges": edges,
            "cells": cells,
            "incidentEdges": {key: value for key, value in sorted(topology.incident_edges.items())},
        },
    }


def _atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def export_web_bundle(puzzle_paths: Iterable[Path], destination: Path) -> list[dict[str, Any]]:
    puzzles = [load_puzzle(path) for path in puzzle_paths]
    puzzles.sort(key=lambda puzzle: str(puzzle.metadata.get("id", "")))
    expected_ids = [f"TSH-{index:02d}" for index in range(1, 21)]
    actual_ids = [str(puzzle.metadata.get("id", "")) for puzzle in puzzles]
    if actual_ids != expected_ids:
        raise ValueError(f"正式题编号必须连续为 TSH-01 至 TSH-20，实际为 {actual_ids}")
    distribution = Counter(_tier(puzzle) for puzzle in puzzles)
    if distribution != Counter({"beginner": 8, "medium": 4, "difficult": 4, "expert": 4}):
        raise ValueError(f"难度分布错误：{dict(distribution)}")

    index_items: list[dict[str, Any]] = []
    for puzzle in puzzles:
        valid, message = validate_target_solution(puzzle)
        if not valid:
            raise ValueError(f"{puzzle.metadata['id']} 目标答案无效：{message}")
        solved = solve_puzzle(puzzle, time_limit=120, update=False)
        if solved.status is None or solved.status.value != "unique":
            raise ValueError(f"{puzzle.metadata['id']} 未通过唯一解复验")
        if set(solved.solution or []) != set(puzzle.target_solution_edges or []):
            raise ValueError(f"{puzzle.metadata['id']} 唯一解与目标答案不一致")
        payload = playable_payload(puzzle)
        forbidden = {"target_solution_edges", "targetSolutionEdges", "analysis", "solution_edges", "solutionEdges"}
        if forbidden.intersection(payload):
            raise AssertionError(f"{puzzle.metadata['id']} 网页数据包含答案字段")
        _atomic_json(destination / f"{puzzle.metadata['id']}.json", payload)
        index_items.append(
            {
                "id": payload["id"],
                "difficulty": payload["difficulty"],
                "difficultyLabel": payload["difficultyLabel"],
                "sourceHash": payload["sourceHash"],
                "file": f"{payload['id']}.json",
            }
        )
    index = {"schemaVersion": WEB_SCHEMA_VERSION, "dataVersion": DATA_VERSION, "puzzles": index_items}
    _atomic_json(destination / "index.json", index)
    return index_items
