"""Reproducible synthetic benchmark for constraint recovery under noisy rankings.

This evaluates CSP behavior, not open-domain clue understanding. See the report for limits.
"""
from __future__ import annotations
import json, random, statistics, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from crossword_agent.grid import extract_entries
from crossword_agent.providers import Candidate
from crossword_agent.solver import solve

SQUARES = [
    ["BALL", "AREA", "LEAD", "LADY"],
    ["WALL", "AREA", "LEAD", "LADY"],
    ["FALL", "AREA", "LEAD", "LADY"],
    ["CALL", "AREA", "LEAD", "LADY"],
    ["CARE", "AREA", "REAR", "EARS"],
    ["CAT", "ARE", "TEN"],
    ["BAT", "ARE", "TEN"],
    ["MAN", "AGE", "NEW"],
    ["EAR", "ARE", "RED"],
    ["SEA", "EAT", "ATE"],
    ["DOG", "ORE", "GET"],
]
POOLS = {3: "MAP CAR DOG PEN SUN SKY HAT CUP BED ICE OAK ELM BEE ANT COW PIG RUN SIT EAT SEE TOO LOW HOT SAD RED OLD NEW TOP OUT OFF CAN MAN AGE SEA ARE TEN CAT BAT EAR",
         4: "MARS LION NOTE SAND ROPE FORK TIDE MINT BIRD COLD WARM TENT HATE MEAL KIND RING STAR MOON GAME HAND WIND ROAD SHIP TREE FIRE BOOK TIME HOME BLUE PINK FISH BALL AREA LEAD LADY WALL FALL CALL CARE REAR EARS"}
DEFINITIONS = {
 "BALL":"Round object used in games", "AREA":"Region or amount of space", "LEAD":"Guide or go in front", "LADY":"Woman, in a courteous form", "WALL":"Vertical barrier around a room", "FALL":"Drop down under gravity", "CALL":"Phone someone or shout", "CARE":"Look after or feel concern", "REAR":"Back part", "EARS":"Organs used for hearing", "CAT":"Feline pet", "BAT":"Flying mammal or sports implement", "ARE":"Plural form of the verb be", "TEN":"Number after nine", "MAN":"Adult human male", "AGE":"How old someone is", "NEW":"Recently made or discovered", "EAR":"Organ used for hearing", "RED":"Color of a stop sign", "SEA":"Large body of salt water", "EAT":"Consume food", "ATE":"Consumed food", "DOG":"Common domestic canine", "ORE":"Rock containing useful minerals", "GET":"Obtain or receive"}


def make_case(rows: list[str], rng: random.Random, index: int):
    n = len(rows)
    clues = {}
    grid, entries = extract_entries(["."*n for _ in range(n)], {})
    # Re-extract with stable IDs, while gold letters come from the target word square.
    target_grid = [list(r) for r in rows]
    _, entries = extract_entries(["."*n for _ in range(n)], {})
    gold = {e.id: "".join(target_grid[r][c] for r,c in e.cells) for e in entries}
    for e in entries:
        word = gold[e.id]
        clue = DEFINITIONS.get(word, f"Common {len(word)}-letter answer, puzzle {index}")
        if e.direction == "D": clue = f"Down: {clue.lower()}"
        clues[e.id] = clue
    initial, entries = extract_entries(["."*n for _ in range(n)], clues)
    pool = POOLS[n]
    for attempt in range(200):
        candidates = {}
        for e in entries:
            wrongs = [w for w in pool.split() if w != gold[e.id]]
            wrong = rng.choice(wrongs)
            # Deliberately rank the distractor above the correct clue answer.
            candidates[e.id] = [Candidate(wrong, .93, "synthetic top-ranked distractor"),
                                Candidate(gold[e.id], .82, "gold candidate included in top-2")]
        result = solve(initial, entries, candidates, max_nodes=10000)
        if result.solved and result.answers == gold:
            return initial, entries, gold, candidates, result
    raise RuntimeError(f"Could not create uniquely recoverable case {index} for {rows}")


def grid_letters(rows):
    return sum(1 for row in rows for c in row if c != "#")


def violations(entries, answers):
    cells = {}
    for e in entries:
        ans = answers[e.id]
        for i, cell in enumerate(e.cells):
            cells.setdefault(cell, []).append(ans[i])
    return sum(1 for vals in cells.values() if len(vals) > 1 and len(set(vals)) > 1)


def run(trials_per_template=2):
    rng = random.Random(20261006)
    totals = {"entries":0,"baseline_correct":0,"agent_correct":0,"baseline_letters":0,"agent_letters":0,
              "gold_letters":0,"baseline_full":0,"agent_full":0,"baseline_crossing_violations":0,
              "agent_crossing_violations":0,"nodes":0,"backtracks":0,"ms":[]}
    case_rows = []
    for si, square in enumerate(SQUARES):
        for trial in range(trials_per_template):
            initial, entries, gold, candidates, result = make_case(square, rng, f"{si+1}.{trial+1}")
            top = {eid: opts[0].answer for eid, opts in candidates.items()}
            agent = result.answers
            word_n = len(gold)
            totals["entries"] += word_n
            totals["baseline_correct"] += sum(top[eid] == gold[eid] for eid in gold)
            totals["agent_correct"] += sum(agent[eid] == gold[eid] for eid in gold)
            totals["baseline_letters"] += sum(sum(a==b for a,b in zip(top[eid],gold[eid])) for eid in gold)
            totals["agent_letters"] += sum(sum(a==b for a,b in zip(agent[eid],gold[eid])) for eid in gold)
            totals["gold_letters"] += sum(map(len,gold.values()))
            totals["baseline_full"] += int(top == gold)
            totals["agent_full"] += int(agent == gold)
            totals["baseline_crossing_violations"] += violations(entries, top)
            totals["agent_crossing_violations"] += violations(entries, agent)
            totals["nodes"] += result.nodes
            totals["backtracks"] += result.backtracks
            totals["ms"].append(result.elapsed_ms)
            case_rows.append({"case":f"{si+1}.{trial+1}","size":f"{len(square)}x{len(square)}","entries":word_n,
                              "baseline_exact_words":sum(top[eid]==gold[eid] for eid in gold),"agent_exact_words":sum(agent[eid]==gold[eid] for eid in gold),
                              "baseline_crossing_violations":violations(entries,top),"search_nodes":result.nodes,"backtracks":result.backtracks})
    puzzles = len(case_rows)
    out = {
      "suite":"Crossword CSP synthetic recovery v1", "seed":20261006,"puzzles":puzzles,"templates":len(SQUARES),
      "entries":totals["entries"], "baseline":"independent top-ranked candidate per clue; no crossing validation",
      "agent":"top-2 clue candidates + arc consistency + MRV backtracking",
      "metrics":{
        "baseline_word_accuracy":totals["baseline_correct"]/totals["entries"],
        "agent_word_accuracy":totals["agent_correct"]/totals["entries"],
        "baseline_letter_accuracy":totals["baseline_letters"]/totals["gold_letters"],
        "agent_letter_accuracy":totals["agent_letters"]/totals["gold_letters"],
        "baseline_full_puzzle_rate":totals["baseline_full"]/puzzles,
        "agent_full_puzzle_rate":totals["agent_full"]/puzzles,
        "baseline_crossing_violations_total":totals["baseline_crossing_violations"],
        "agent_crossing_violations_total":totals["agent_crossing_violations"],
        "mean_candidate_tries_per_puzzle":totals["nodes"]/puzzles,
        "mean_backtracks_per_puzzle":totals["backtracks"]/puzzles,
        "median_solver_ms":statistics.median(totals["ms"]),
        "p95_solver_ms":sorted(totals["ms"])[max(0,int(.95*len(totals["ms"]))-1)],
        "provider_calls":0,"provider_tokens":None,"provider_cost":None
      }, "cases":case_rows,
      "scope_note":"Synthetic, tiny word-square fixtures with deliberately noisy candidate rankings. This isolates constraint recovery and is not evidence of real-world clue-solving accuracy. Provider calls/cost are not measured."
    }
    return out

if __name__ == "__main__":
    result = run()
    out = ROOT / "artifacts" / "benchmark.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
