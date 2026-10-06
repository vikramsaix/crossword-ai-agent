from __future__ import annotations
import argparse
import json
import sys
from .agent import load_json, render_grid, solve_puzzle
from .grid import puzzle_from_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid crossword solver: clue candidates + crossing constraints.")
    parser.add_argument("puzzle", help="Path to puzzle JSON")
    parser.add_argument("--provider", choices=["fixture", "llm"], default="fixture")
    parser.add_argument("--json", action="store_true", help="Emit result JSON")
    args = parser.parse_args()
    try:
        data = load_json(args.puzzle)
        _, entries = puzzle_from_dict(data)
        result = solve_puzzle(data, args.provider)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"solved": result.solved, "answers": result.answers, "grid": result.grid,
                          "nodes": result.nodes, "backtracks": result.backtracks,
                          "elapsed_ms": round(result.elapsed_ms, 3),
                          "mean_candidate_score": result.mean_candidate_score,
                          "score_semantics": "uncalibrated provider ranking; not a probability",
                          "reason": result.reason}, indent=2))
        return 0 if result.solved else 1
    print(f"{data.get('title', 'Crossword puzzle')} — {len(entries)} entries")
    for event in result.events:
        print(f"[solver] {event}")
    if result.solved:
        print("\nSolved grid:\n" + render_grid(result.grid))
        for entry in entries:
            print(f"{entry.id:>3} {entry.direction}: {result.answers[entry.id]}")
        print(f"\nMean provider score (not calibrated confidence): {result.mean_candidate_score:.2f}")
        print(f"Search: {result.nodes} candidate tries, {result.backtracks} backtracks, {result.elapsed_ms:.2f} ms")
        return 0
    print(f"\nUnsolved: {result.reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
