from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .generator import GenerationOptions, generate_puzzle
from .render import export_svg
from .solver import solve_puzzle, validate_target_solution
from .storage import load_puzzle, save_puzzle
from .topology import build_topology


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="特色数回命令行工具")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "solve"):
        command = subparsers.add_parser(name)
        command.add_argument("path")
    generate = subparsers.add_parser("generate")
    generate.add_argument("path")
    generate.add_argument("-o", "--output", required=True)
    generate.add_argument("--seconds", type=float, default=60.0)
    generate.add_argument("--seed", type=int, default=0)
    generate.add_argument("--no-auto-pi", action="store_true")
    export = subparsers.add_parser("export-svg")
    export.add_argument("path")
    export.add_argument("-o", "--output", required=True)
    export.add_argument("--solution", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        puzzle = load_puzzle(args.path)
        if args.command == "validate":
            topology = build_topology(puzzle)
            target_ok, target_message = validate_target_solution(puzzle) if puzzle.target_solution_edges is not None else (True, "未提供目标曲线")
            print(json.dumps({"valid": target_ok, "vertices": len(topology.vertices), "edges": len(topology.edges), "cells": len(topology.cells), "target": target_message}, ensure_ascii=False, indent=2))
            return 0 if target_ok else 2
        if args.command == "solve":
            result = solve_puzzle(puzzle)
            save_puzzle(puzzle, args.path)
            print(json.dumps({"status": result.status.value if result.status else None, "elapsed_seconds": result.elapsed_seconds, "message": result.message}, ensure_ascii=False, indent=2))
            return 0 if result.status else 3
        if args.command == "generate":
            result = generate_puzzle(puzzle, GenerationOptions(args.seconds, args.seed, not args.no_auto_pi))
            if result.puzzle is None:
                print(result.message, file=sys.stderr)
                return 4
            save_puzzle(result.puzzle, args.output)
            print(json.dumps({"numeric_clues": result.numeric_clues, "pi_clues": result.pi_clues, "difficulty": result.difficulty.label if result.difficulty else None, "elapsed_seconds": result.elapsed_seconds}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "export-svg":
            solution = puzzle.analysis.solution_edges if args.solution else None
            export_svg(puzzle, args.output, solution_edges=solution, title=puzzle.metadata.get("title"))
            return 0
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

