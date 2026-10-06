# Evaluation methodology

## Current executable benchmark

`evaluate.py` uses a fixed PRNG seed (`20261006`) to create 22 cases from 11 hand-authored 3×3 and 4×4 word-square templates. Each clue entry gets two candidates: the intended answer and a non-answer distractor deliberately ranked first. Cases are retained only when the answer set is the consistent fill under crossing constraints. This makes the benchmark useful for testing deterministic domain filtering and crossing recovery, but intentionally easy to game and unlike natural clue distributions.

The baseline independently chooses rank 1 for each clue. The agent receives both candidates and applies crossing consistency. Metrics include exact word accuracy, per-letter accuracy, full puzzle completion, crossing violations, local solver latency, candidate tries/backtracks, and provider call/token/cost counters. Provider telemetry is null because the benchmark is offline.

## Reported measurements

The actual run is stored in `artifacts/benchmark.json`; `README.md` summarizes it. The reported figures are for this synthetic suite only. Local timings are environment-specific and exclude model/network latency.

## Proposed production-grade evaluation

- Dataset: 100+ licensed or original standard-size puzzles, stratified by size/difficulty/theme, deduplicated and split by puzzle into development and locked test sets.
- Gold: verified grid, normalized answer per clue, source/license metadata, and adjudicated ambiguity flags.
- Baselines: model top-1 per clue; candidate top-k without cross constraints; candidate top-k with propagation; full search-enabled agent.
- Metrics: candidate recall@k, clue exact accuracy, word/letter accuracy, full-puzzle solve rate, crossing violations, abstention/partial-fill quality, and calibration (Brier score/reliability plot if confidence is exposed).
- Operations: end-to-end latency (median/p95), provider calls, input/output tokens, actual API-reported cost, retries/errors, and max memory.
- Reproducibility: fixed prompt/model/temperature/candidate-k/search limit; pinned code and dataset hashes; at least three model samples when stochastic; bootstrap confidence intervals; no tuning against held-out cases.
- Error review: categorize misses into clue interpretation, missing candidate, parsing, theme/rebus, ranking, search limit, and provider failure.

No quality or cost claims for a live LLM should be made until this protocol has been run with actual provider credentials and licensed evaluation data.
