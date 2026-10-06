"""Constraint propagation and bounded backtracking for crossword candidate domains."""
from __future__ import annotations
from dataclasses import dataclass, field
from time import perf_counter
from .grid import Entry, crossings
from .providers import Candidate, normalize_answer


@dataclass
class SolveResult:
    solved: bool
    answers: dict[str, str] = field(default_factory=dict)
    grid: list[list[str]] = field(default_factory=list)
    nodes: int = 0
    backtracks: int = 0
    elapsed_ms: float = 0.0
    events: list[str] = field(default_factory=list)
    mean_candidate_score: float = 0.0
    reason: str = ""


def _letter_grid(initial: list[list[str]], entries: list[Entry], answers: dict[str, str]) -> list[list[str]]:
    grid = [row[:] for row in initial]
    for entry in entries:
        answer = answers.get(entry.id)
        if answer:
            for (r, c), ch in zip(entry.cells, answer):
                grid[r][c] = ch
    return grid


def solve(initial_grid: list[list[str]], entries: list[Entry], candidate_map: dict[str, list[Candidate]],
          max_nodes: int = 100_000) -> SolveResult:
    started = perf_counter()
    events: list[str] = []
    by_id = {e.id: e for e in entries}
    ids = [e.id for e in entries]
    links = crossings(entries)
    id_to_idx = {eid: i for i, eid in enumerate(ids)}
    neighbors: dict[str, set[str]] = {eid: set() for eid in ids}
    for eid, arcs in links.items():
        neighbors[eid] = {other for other, _, _ in arcs}

    domains: dict[str, list[Candidate]] = {}
    for entry in entries:
        known = "".join(initial_grid[r][c] for r, c in entry.cells)
        pattern = "".join("." if ch == "." else ch for ch in known)
        options = []
        seen = set()
        for candidate in candidate_map.get(entry.id, []):
            answer = normalize_answer(candidate.answer)
            if len(answer) != entry.length or answer in seen:
                continue
            if any(p != "." and p != ch for p, ch in zip(pattern, answer)):
                continue
            seen.add(answer)
            options.append(Candidate(answer, max(0.0, min(1.0, candidate.score)), candidate.rationale))
        domains[entry.id] = sorted(options, key=lambda c: c.score, reverse=True)
        if not options:
            return SolveResult(False, grid=initial_grid, elapsed_ms=(perf_counter()-started)*1000,
                               events=[f"No candidates for {entry.id} ({entry.length} letters)."],
                               reason=f"empty domain: {entry.id}")

    # Each directed arc stores the offsets whose letters must agree.
    def propagate(current: dict[str, list[Candidate]], queue: list[tuple[str, str]]) -> bool:
        while queue:
            left, right = queue.pop()
            left_off = right_off = None
            for other, own_i, other_i in links[left]:
                if other == right:
                    left_off, right_off = own_i, other_i
                    break
            if left_off is None:
                continue
            support = {c.answer[right_off] for c in current[right]}
            kept = [c for c in current[left] if c.answer[left_off] in support]
            if len(kept) != len(current[left]):
                current[left] = kept
                if not kept:
                    return False
                for third in neighbors[left] - {right}:
                    queue.append((third, left))
        return True

    if not propagate(domains, [(a, b) for a in ids for b in neighbors[a]]):
        return SolveResult(False, grid=initial_grid, elapsed_ms=(perf_counter()-started)*1000,
                           events=["Crossing-letter propagation found a contradiction."], reason="inconsistent domains")

    nodes = 0
    backtracks = 0
    solution: dict[str, Candidate] | None = None

    def search(current: dict[str, list[Candidate]]) -> bool:
        nonlocal nodes, backtracks, solution
        if nodes >= max_nodes:
            return False
        unresolved = [eid for eid in ids if len(current[eid]) > 1]
        if not unresolved:
            solution = {eid: current[eid][0] for eid in ids}
            return True
        # MRV, then greatest number of crossing constraints; deterministic tie-break by ID.
        eid = min(unresolved, key=lambda x: (len(current[x]), -len(neighbors[x]), x))
        for candidate in current[eid]:
            nodes += 1
            trial = {key: values[:] for key, values in current.items()}
            trial[eid] = [candidate]
            events.append(f"Try {eid}={candidate.answer} (score {candidate.score:.2f}).")
            if propagate(trial, [(neighbor, eid) for neighbor in neighbors[eid]]) and search(trial):
                return True
            backtracks += 1
            events.append(f"Backtrack from {eid}={candidate.answer}: crossing conflict or dead end.")
            if nodes >= max_nodes:
                return False
        return False

    ok = search(domains)
    elapsed = (perf_counter() - started) * 1000
    if not ok or solution is None:
        reason = f"No consistent assignment found (search limit: {max_nodes} candidate tries)." if nodes >= max_nodes else "No consistent assignment found."
        return SolveResult(False, grid=initial_grid, nodes=nodes, backtracks=backtracks,
                           elapsed_ms=elapsed, events=events, reason=reason)
    answers = {eid: cand.answer for eid, cand in solution.items()}
    score = sum(c.score for c in solution.values()) / len(solution) if solution else 0.0
    events.append(f"Solved {len(answers)} entries with {nodes} candidate tries and {backtracks} backtracks.")
    return SolveResult(True, answers, _letter_grid(initial_grid, entries, answers), nodes, backtracks,
                       elapsed, events, score, "all crossings consistent")
