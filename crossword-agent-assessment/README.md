# Crossword Agent

A small, testable crossword-solving agent that combines **language-model clue candidates** with a deterministic **constraint-satisfaction solver**. It does not trust a single model completion: answers must fit their slot length and agree at every Across/Down crossing.

[Watch the narrated 51-second client demo](demo/crossword-agent-demo.mp4) · [View the frame sheet](demo/preview-contact-sheet.png)

## Quick start

Requires Python 3.10+; the core and tests use only the standard library.

```bash
git clone <repository-url>
cd crossword-agent
python3 -m crossword_agent.cli data/sample_puzzle.json
python3 -m unittest discover -s tests -v
python3 benchmarks/evaluate.py
```

The example runs offline with checked-in fixture candidates; no API key or network call is needed. To install the command entry point locally:

```bash
python3 -m pip install -e .
crossword-agent data/sample_puzzle.json
```

## Use a live LLM provider

The provider boundary uses the OpenAI Chat Completions request shape, so a compatible endpoint can be configured without changing the solver. Token Factory is the intended optional example; verify the current endpoint and model names in your account before use.

```bash
cp .env.example .env
# Edit .env locally. Do not commit it or paste a key into source code.
set -a && . ./.env && set +a
python3 -m crossword_agent.cli data/sample_puzzle.json --provider llm
```

Required values: `CROSSWORD_API_KEY` (or `OPENAI_API_KEY`) and `CROSSWORD_MODEL`. Optional: `CROSSWORD_API_BASE` (defaults to `https://api.tokenfactory.nebius.com/v1`). API keys are read from the environment only. No live provider call is made by the benchmark. See the [official Token Factory API introduction](https://docs.tokenfactory.nebius.com/api-reference/introduction) and [official cookbook request example](https://github.com/nebius/token-factory-cookbook/blob/main/api/api_native.ipynb) for the current compatible API setup.

## Puzzle format

A puzzle is JSON with `grid` (equal-width strings: `#` black, `.` unknown, A-Z fixed cells), a `clues` map keyed by conventional entry IDs such as `1A` and `4D`, and optionally a `candidates` map. Each candidate has `answer`, `score` (0–1 provider ranking, **not calibrated probability**), and optional `rationale`.

```json
{
  "title": "Example",
  "grid": ["....", "....", "....", "...."],
  "clues": {"1A": "Round object used in many sports"},
  "candidates": {"1A": [{"answer": "BALL", "score": 0.9}]}
}
```

For arbitrary puzzles, supply complete clue text. The parser assigns standard crossword numbering from the grid. The current input path expects a text grid; image OCR and clue extraction from screenshots are deliberately out of scope.

## Design

```text
Grid + clues
   → numbered Across/Down entries + cell intersections
   → provider proposes ranked answers (length/pattern checked)
   → arc consistency prunes letters unsupported at crossings
   → MRV + degree tie-break + bounded backtracking
   → filled grid, answer map, trace, and search metrics
```

- `crossword_agent/grid.py`: grid validation, conventional numbering, entries, crossing graph.
- `crossword_agent/providers.py`: offline fixture provider and provider-neutral OpenAI-compatible adapter.
- `crossword_agent/solver.py`: candidate-domain filtering, AC-3-style propagation, MRV search, node limit, and trace.
- `crossword_agent/agent.py`, `cli.py`: orchestration and CLI.
- `benchmarks/evaluate.py`: seeded synthetic comparison with an independent top-1 baseline.

### Design decisions and trade-offs

1. **Separate semantic uncertainty from crossing certainty.** A model may misread a clue; a known cell mismatch is deterministic. The CSP may therefore reject a high-scoring candidate when crossings prove it inconsistent.
2. **Ranked candidates rather than one answer.** Keeping a small candidate set gives crossings alternatives to select among. Candidate recall is still a hard ceiling: if the right word never appears in a domain, this solver cannot invent it.
3. **Propagation before search.** Arc consistency is cheap and often resolves compact puzzles without branching. MRV picks the smallest remaining domain first; a node cap prevents unbounded work.
4. **Provider-neutral interface.** The included live adapter is intentionally small and uses an OpenAI-compatible API shape. It does not hide provider-specific rate limits, model availability, or billing.
5. **Scores are rankings, not calibrated confidence.** The displayed mean score is only a descriptive provider score. Production confidence should be calibrated on held-out labeled puzzles, and should include candidate-set uncertainty and crossing evidence.

## Benchmark and evaluation methodology

Run the seeded evaluation:

```bash
python3 benchmarks/evaluate.py
```

It writes `artifacts/benchmark.json`. The checked-in suite uses **22 tiny synthetic word-square puzzles** (11 templates × 2 candidate-noise trials; 152 entries). Each entry receives one deliberately over-ranked distractor and the intended answer as a second candidate. The comparison is independent top-1 fill versus top-2 candidates plus crossing constraints.

### Measured result (seed 20261006)

| Metric | Independent top-1 | CSP agent |
|---|---:|---:|
| Exact word accuracy | 0% (0/152) | 100% (152/152) |
| Letter accuracy | 12.1% | 100% |
| Fully correct puzzles | 0/22 | 22/22 |
| Crossing violations | 248 | 0 |
| Median solver time | — | 0.15 ms |
| p95 solver time | — | 0.22 ms |

These timings measure only the local constraint solver in this sandbox, not clue generation or network latency. In this fixture suite, crossing propagation alone resolves all cases (zero search nodes/backtracks); the test suite separately checks that the bounded search path rejects a globally inconsistent loop. Provider calls, tokens, and cost are **not measured** (zero calls in the offline benchmark).

> **Interpretation:** This is a mechanics test, not a representative crossword leaderboard. Its deliberately noisy rankings and small word-square grids demonstrate that crossing constraints can recover a consistent fill when the intended candidates are present. The 100% result must not be presented as real-world clue-solving accuracy.

### Proposed next evaluation (the meaningful quality test)

1. Freeze a licensed, de-identified set of at least 100 standard crossword grids and clues, split by puzzle/date into development and held-out test sets. Record source, license, grid dimensions, theme/difficulty, and answer key.
2. Measure candidate recall@k and clue-answer exact accuracy before search; then report final exact word accuracy, letter accuracy, full-puzzle rate, and invalid crossings.
3. Compare (a) one-shot top-1, (b) top-k plus crossings, and (c) top-k plus crossings and backtracking. Keep prompts, model version, temperature, candidate count, and solver limits fixed.
4. Run each model/prompt at least three times where nondeterministic. Report mean and confidence intervals; stratify by word length, theme, rebus/abbreviation, and clue type.
5. Record end-to-end latency, provider request count, input/output tokens, errors/timeouts, and cost from actual provider usage fields. Do not infer cost from this offline test.
6. Audit a sample of failed cases: candidate recall failure, clue ambiguity, grid/parser error, theme knowledge, or solver cap. Do not tune on the held-out set.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests cover conventional entry numbering, crossing extraction, offline solving, empty domains, inconsistent crossings, and bounded search behavior.

## Limitations and next steps

- No screenshot/image OCR, rebus cells, multiword answer normalization beyond removing non-letters, themed gimmick inference, or puzzle acquisition.
- LLM candidate quality has not been live-benchmarked here; a compatible account key and model are needed for that experiment.
- The offline evaluation is intentionally tiny and synthetic. It is not sufficient for deployment claims.
- The adapter currently makes one request per entry sequentially. A production version should add bounded parallelism, retries/backoff, provider usage logging, and a cache.
- A production system should also support partial fills, user correction, ambiguity display, telemetry, and human override.

## Interview discussion guide

- **Why not ask the LLM for the whole filled grid?** A single completion hides local errors and cannot guarantee crossing consistency; candidate domains expose uncertainty to a deterministic validator.
- **What is the biggest quality ceiling?** Candidate recall and semantic clue quality; CSP can only choose among proposed answers.
- **Why show a weak synthetic benchmark?** It validates a narrow subsystem without pretending to validate language understanding. The next meaningful gate is held-out, licensed, standard puzzles with live provider telemetry.
- **When might this fail?** An answer omitted from top-k, ambiguous clue/theme, malformed grid, unsupported rebus, or search limit exhaustion.
- **What would you improve next?** Add a broader benchmark and calibration first, then parallel provider calls, confidence intervals, OCR/UI only if product needs them.

## Security

Never commit `.env`, credentials, promo codes, or account screenshots. `.gitignore` excludes local environment files. Do not share card details in source control or interview artifacts.

## License

MIT for this project code. Benchmark fixtures are original small examples created for this assessment; no newspaper puzzle data is redistributed.
