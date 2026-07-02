from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from .model import Puzzle, Variant
from .topology import Topology, build_topology


@dataclass(slots=True)
class CycleSampleOptions:
    minimum_edges: int = 8
    maximum_edges: int = 36
    attempts: int = 500


def sample_simple_cycle(topology: Topology, rng: random.Random, options: CycleSampleOptions | None = None) -> list[str]:
    options = options or CycleSampleOptions()
    vertices = list(topology.vertices)
    adjacency: dict[str, list[tuple[str, str]]] = {vertex_id: [] for vertex_id in vertices}
    for edge_id, edge in topology.edges.items():
        a, b = edge.vertices
        adjacency[a].append((edge_id, b))
        adjacency[b].append((edge_id, a))

    for _ in range(options.attempts):
        start = rng.choice(vertices)
        current = start
        visited = {start}
        path: list[str] = []
        while len(path) < options.maximum_edges:
            choices = []
            for edge_id, other in adjacency[current]:
                if other == start and len(path) + 1 >= options.minimum_edges:
                    return sorted(path + [edge_id])
                if other not in visited:
                    choices.append((edge_id, other))
            if not choices:
                break
            edge_id, current = rng.choice(choices)
            path.append(edge_id)
            visited.add(current)
    raise RuntimeError("未能在给定拓扑中采样到足够长的简单闭环")


def cycle_fingerprint(edge_ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(edge_ids)).encode("utf-8")).hexdigest()[:16]


def make_target_puzzle(
    row_lengths: list[int],
    seed: int,
    *,
    minimum_edges: int,
    maximum_edges: int,
    attempts: int = 500,
) -> Puzzle:
    puzzle = Puzzle(Variant.CIRCLE_PACK, {"row_lengths": row_lengths}, metadata={"seed": seed})
    topology = build_topology(puzzle)
    rng = random.Random(seed)
    puzzle.target_solution_edges = sample_simple_cycle(
        topology,
        rng,
        CycleSampleOptions(minimum_edges, maximum_edges, attempts),
    )
    puzzle.metadata["target_fingerprint"] = cycle_fingerprint(puzzle.target_solution_edges)
    puzzle.metadata["target_edge_count"] = len(puzzle.target_solution_edges)
    return puzzle
