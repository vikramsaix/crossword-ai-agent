"""Candidate providers. The solver is independent of any inference vendor."""
from __future__ import annotations
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol
from .grid import Entry


@dataclass(frozen=True)
class Candidate:
    answer: str
    score: float
    rationale: str = ""


class CandidateProvider(Protocol):
    def candidates(self, entry: Entry, pattern: str) -> list[Candidate]: ...


class FixtureProvider:
    """Offline provider for examples and reproducible tests."""
    def __init__(self, entries: dict[str, list[dict]]):
        self.entries = entries

    def candidates(self, entry: Entry, pattern: str) -> list[Candidate]:
        out = []
        for item in self.entries.get(entry.id, []):
            answer = normalize_answer(str(item.get("answer", "")))
            if len(answer) == entry.length and pattern_matches(pattern, answer):
                out.append(Candidate(answer, float(item.get("score", 0.5)), str(item.get("rationale", "fixture"))))
        return sorted(out, key=lambda c: c.score, reverse=True)


def normalize_answer(value: str) -> str:
    return re.sub(r"[^A-Z]", "", value.upper())


def pattern_matches(pattern: str, answer: str) -> bool:
    return len(pattern) == len(answer) and all(p in (".", "?", "_") or p == a for p, a in zip(pattern.upper(), answer))


class OpenAICompatibleProvider:
    """Minimal Chat Completions adapter; works with Token Factory or compatible APIs."""
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None, timeout: float = 45.0, limit: int = 8):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("CROSSWORD_API_KEY")
        self.base_url = (base_url or os.getenv("CROSSWORD_API_BASE", "https://api.tokenfactory.nebius.com/v1")).rstrip("/")
        self.model = model or os.getenv("CROSSWORD_MODEL")
        self.timeout, self.limit = timeout, limit
        self.calls = 0
        self.elapsed_seconds = 0.0
        if not self.api_key:
            raise ValueError("Set OPENAI_API_KEY or CROSSWORD_API_KEY before using the live provider.")
        if not self.model:
            raise ValueError("Set CROSSWORD_MODEL to a model available in your provider account.")

    def candidates(self, entry: Entry, pattern: str) -> list[Candidate]:
        self.calls += 1
        prompt = (
            "Solve one crossword clue. Return ONLY valid JSON with a 'candidates' array; each item has "
            "'answer' (letters only), 'confidence' (0..1), and 'reason' (short). Include up to "
            f"{self.limit} plausible candidates, best first. Exact answer length is {entry.length}. "
            f"Known-letter pattern: {pattern.replace('.', '?')}. Clue: {entry.clue!r}. "
            "Do not invent a candidate that violates known letters."
        )
        payload = {"model": self.model,
                   "messages": [{"role": "system", "content": "You are a careful crossword clue solver."},
                                {"role": "user", "content": prompt}],
                   "temperature": 0.15}
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST")
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Provider returned HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Provider request failed: {exc}") from exc
        finally:
            self.elapsed_seconds += time.perf_counter() - start
        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.S)
            if not match:
                raise RuntimeError("Model response did not contain JSON candidate data.")
            decoded = json.loads(match.group(0))
        result = []
        for item in decoded.get("candidates", []):
            answer = normalize_answer(str(item.get("answer", "")))
            if len(answer) != entry.length or not pattern_matches(pattern, answer):
                continue
            try:
                score = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
            except (TypeError, ValueError):
                score = 0.5
            result.append(Candidate(answer, score, str(item.get("reason", ""))))
        # Deduplicate while preserving the highest-ranked occurrence.
        unique = {}
        for candidate in sorted(result, key=lambda c: c.score, reverse=True):
            unique.setdefault(candidate.answer, candidate)
        return list(unique.values())[:self.limit]
