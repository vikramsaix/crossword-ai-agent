import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from crossword_agent.agent import load_json, solve_puzzle
from crossword_agent.grid import extract_entries, crossings
from crossword_agent.providers import Candidate
from crossword_agent.solver import solve

class CrosswordTests(unittest.TestCase):
    def test_standard_numbering_and_crossings(self):
        grid, entries = extract_entries(["...", ".#.", "..."], {"1A":"row", "1D":"col"})
        ids = {e.id for e in entries}
        self.assertIn("1A", ids)
        self.assertIn("1D", ids)
        self.assertTrue(crossings(entries)["1A"])

    def test_sample_solves_offline(self):
        data = load_json(ROOT / "data/sample_puzzle.json")
        result = solve_puzzle(data)
        self.assertTrue(result.solved, result.reason)
        self.assertEqual(result.answers["1A"], "BALL")
        self.assertEqual(result.answers["5A"], "AREA")
        self.assertEqual(result.answers["6A"], "LEAD")
        self.assertEqual(result.answers["7A"], "LADY")

    def test_conflicting_singletons_fail(self):
        grid, entries = extract_entries(["..", ".."], {})
        domains = {e.id: [Candidate("AA", .8)] for e in entries}
        # A 2x2 open grid cannot contradict when all entries are AA.
        self.assertTrue(solve(grid, entries, domains).solved)
        bad = {e.id: [Candidate("AA" if e.direction == "A" else "BB", .8)] for e in entries}
        self.assertFalse(solve(grid, entries, bad).solved)

    def test_empty_domain_is_reported(self):
        grid, entries = extract_entries(["..", ".."], {})
        domains = {e.id: [] for e in entries}
        result = solve(grid, entries, domains)
        self.assertFalse(result.solved)
        self.assertIn("empty domain", result.reason)

    def test_backtracking_rejects_globally_inconsistent_loop(self):
        from crossword_agent.grid import Entry
        # Three pairwise crossings impose an odd parity loop. Every value has
        # local support (so propagation alone cannot reject it), but no global
        # assignment exists; search must branch and backtrack.
        entries = [
            Entry("A", 1, "A", "", ((0, 0), (1, 0))),
            Entry("B", 2, "D", "", ((0, 0), (0, 1))),
            Entry("C", 3, "A", "", ((0, 1), (1, 0))),
        ]
        domains = {
            "A": [Candidate("AA", .9), Candidate("BB", .8)],
            "B": [Candidate("AA", .9), Candidate("BB", .8)],
            "C": [Candidate("AB", .9), Candidate("BA", .8)],
        }
        result = solve([[".", "."], [".", "."]], entries, domains)
        self.assertFalse(result.solved)
        self.assertGreater(result.backtracks, 0)

if __name__ == "__main__":
    unittest.main()
