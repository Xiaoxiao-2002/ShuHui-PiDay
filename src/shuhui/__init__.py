"""特色数回题目生产系统。"""

from .generator import GenerationOptions, GenerationResult, generate_puzzle
from .model import AnalysisStatus, Clue, ClueKind, Puzzle, Variant
from .solver import SolveResult, solve_puzzle, validate_solution_edges, validate_target_solution
from .storage import load_puzzle, save_puzzle

__all__ = [
    "AnalysisStatus",
    "Clue",
    "ClueKind",
    "GenerationOptions",
    "GenerationResult",
    "Puzzle",
    "SolveResult",
    "Variant",
    "generate_puzzle",
    "load_puzzle",
    "save_puzzle",
    "solve_puzzle",
    "validate_solution_edges",
    "validate_target_solution",
]

__version__ = "0.1.0"
