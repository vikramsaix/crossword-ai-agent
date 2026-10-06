# Crossword-solving AI agent

The implementation, tests, evaluation methodology, and demonstration are in
[`crossword-agent-assessment/`](crossword-agent-assessment/).

## Run the agent

Requires Python 3.10 or later. The offline example and tests use only the Python
standard library. Run these commands from this repository's root:

```sh
cd crossword-agent-assessment
python3 -m crossword_agent.cli data/sample_puzzle.json
python3 -m unittest discover -s tests -v
python3 benchmarks/evaluate.py
```

The example supplies candidate answers to demonstrate crossing-constraint solving.
For live LLM setup, architecture, and limitations, see the
[project README](crossword-agent-assessment/README.md).

- [Evaluation methodology](crossword-agent-assessment/benchmarks/METHODOLOGY.md)
- [Benchmark results](crossword-agent-assessment/artifacts/benchmark.json)
- [Narrated demo (51 seconds)](crossword-agent-assessment/demo/crossword-agent-demo.mp4)
- [Demo rendering instructions](crossword-agent-assessment/demo/README.md)

The synthetic benchmark measures constraint recovery, not real-world clue accuracy.
