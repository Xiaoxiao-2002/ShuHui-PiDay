from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

SCHEMA_VERSION = 1


class Variant(StrEnum):
    CLASSIC = "classic"
    CIRCLE_PACK = "circle_pack"


class ClueKind(StrEnum):
    NUMBER = "number"
    PI = "pi"


class AnalysisStatus(StrEnum):
    INVALID = "invalid"
    UNIQUE = "unique"
    MULTIPLE = "multiple"
    UNSATISFIABLE = "unsatisfiable"


@dataclass(slots=True)
class Clue:
    cell_id: str
    kind: ClueKind
    value: int | None = None
    locked: bool = False

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "cell_id": self.cell_id,
            "kind": self.kind.value,
            "locked": self.locked,
        }
        if self.kind == ClueKind.NUMBER:
            result["value"] = self.value
        return result


@dataclass(slots=True)
class Analysis:
    status: AnalysisStatus | None = None
    solution_edges: list[str] | None = None
    puzzle_hash: str | None = None
    elapsed_seconds: float | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value if self.status else None,
            "solution_edges": self.solution_edges,
            "puzzle_hash": self.puzzle_hash,
            "elapsed_seconds": self.elapsed_seconds,
            "message": self.message,
        }


@dataclass(slots=True)
class Puzzle:
    variant: Variant
    board: dict[str, Any]
    clues: list[Clue] = field(default_factory=list)
    target_solution_edges: list[str] | None = None
    analysis: Analysis = field(default_factory=Analysis)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def clue_map(self) -> dict[str, Clue]:
        return {clue.cell_id: clue for clue in self.clues}

    def clear_analysis(self) -> None:
        self.analysis = Analysis()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "variant": self.variant.value,
            "board": self.board,
            "clues": [clue.to_dict() for clue in sorted(self.clues, key=lambda c: c.cell_id)],
            "target_solution_edges": sorted(self.target_solution_edges) if self.target_solution_edges is not None else None,
            "analysis": self.analysis.to_dict(),
            "metadata": self.metadata,
        }

