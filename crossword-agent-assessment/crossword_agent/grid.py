"""Grid parsing and crossword entry extraction."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Entry:
    id: str
    number: int
    direction: str
    clue: str
    cells: tuple[tuple[int, int], ...]

    @property
    def length(self) -> int:
        return len(self.cells)


def normalize_grid(rows: list[str]) -> list[list[str]]:
    if not rows or not rows[0]:
        raise ValueError("grid must contain at least one non-empty row")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("grid rows must have equal width")
    allowed = set("#.ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    grid = [list(row.upper()) for row in rows]
    if any(cell not in allowed for row in grid for cell in row):
        raise ValueError("grid cells must be '#', '.', or A-Z")
    return grid


def extract_entries(rows: list[str], clues: dict[str, str] | None = None) -> tuple[list[list[str]], list[Entry]]:
    """Extract numbered Across/Down entries using the usual crossword convention."""
    grid = normalize_grid(rows)
    clues = clues or {}
    h, w = len(grid), len(grid[0])
    entries: list[Entry] = []
    number = 0
    for r in range(h):
        for c in range(w):
            if grid[r][c] == "#":
                continue
            starts_across = c == 0 or grid[r][c - 1] == "#"
            starts_down = r == 0 or grid[r - 1][c] == "#"
            if not (starts_across or starts_down):
                continue
            number += 1
            for direction, starts, dr, dc, key_suffix in (
                ("A", starts_across, 0, 1, "A"),
                ("D", starts_down, 1, 0, "D"),
            ):
                if not starts:
                    continue
                cells: list[tuple[int, int]] = []
                rr, cc = r, c
                while rr < h and cc < w and grid[rr][cc] != "#":
                    cells.append((rr, cc))
                    rr += dr
                    cc += dc
                if len(cells) < 2:
                    continue
                eid = f"{number}{key_suffix}"
                entries.append(Entry(eid, number, direction, clues.get(eid, ""), tuple(cells)))
    return grid, entries


def crossings(entries: list[Entry]) -> dict[str, list[tuple[str, int, int]]]:
    """For each entry, return (other_entry_id, own_offset, other_offset) crossings."""
    by_cell: dict[tuple[int, int], list[tuple[str, int]]] = {}
    for entry in entries:
        for offset, cell in enumerate(entry.cells):
            by_cell.setdefault(cell, []).append((entry.id, offset))
    result = {entry.id: [] for entry in entries}
    for occupants in by_cell.values():
        if len(occupants) != 2:
            continue
        (a, ai), (b, bi) = occupants
        result[a].append((b, ai, bi))
        result[b].append((a, bi, ai))
    return result


def puzzle_from_dict(data: dict[str, Any]) -> tuple[list[list[str]], list[Entry]]:
    rows = data.get("grid") or data.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, str) for row in rows):
        raise ValueError("puzzle requires grid: [row strings]")
    clues = data.get("clues", {})
    grid, entries = extract_entries(rows, clues)
    if not entries:
        raise ValueError("grid contains no entries of length 2 or more")
    return grid, entries
