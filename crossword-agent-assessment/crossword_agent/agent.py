"""Agent orchestration: candidate generation stays separate from deterministic solving."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .grid import puzzle_from_dict
from .providers import Candidate, FixtureProvider, OpenAICompatibleProvider
from .solver import SolveResult, solve


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def solve_puzzle(data: dict[str, Any], provider: str = "fixture", *, max_nodes: int = 100_000) -> SolveResult:
    grid, entries = puzzle_from_dict(data)
    if provider == "fixture":
        source = FixtureProvider(data.get("candidates", {}))
    elif provider == "llm":
        source = OpenAICompatibleProvider()
    else:
        raise ValueError("provider must be 'fixture' or 'llm'")
    candidate_map: dict[str, list[Candidate]] = {}
    for entry in entries:
        pattern = "".join(grid[r][c] if grid[r][c] != "." else "." for r, c in entry.cells)
        candidate_map[entry.id] = source.candidates(entry, pattern)
    return solve(grid, entries, candidate_map, max_nodes=max_nodes)


def render_grid(grid: list[list[str]]) -> str:
    return "\n".join(" ".join("■" if cell == "#" else cell for cell in row) for row in grid)
