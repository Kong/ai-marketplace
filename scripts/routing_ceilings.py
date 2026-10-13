"""Spend, token, concurrency, and timeout ceilings for routing evals.

No model calls. Ceilings come from defaults overridden by environment variables, so CI
(`vars`) and contributors can tune them without editing code. Nothing is stored as a baseline.

    ROUTING_MAX_TOKENS          total tokens per host across candidate, control, and retries
    ROUTING_MAX_COST_USD        estimated spend per host, same scope
    ROUTING_MAX_CONCURRENCY     Promptfoo `--max-concurrency` for each run
    ROUTING_RUN_TIMEOUT_SECONDS wall clock for one Promptfoo run; the run is killed on breach
    ROUTING_JOB_TIMEOUT_SECONDS wall clock for the whole eval; keep it below the CI job timeout
                                so a breach is reported instead of the job being cancelled

Promptfoo reports usage only when a run ends, so token and cost ceilings are checked after
each run and before launching the next one (retry, control, next host). A breach therefore
stops further spend and can overshoot by at most one in-flight run. A breach is an
`infra_error` of kind `ceiling` (the run could not be judged), never `routing_fail`.
Timeouts kill the run itself.

A breach document is `{"ceiling": name, "limit": number, "observed": number, "host": str}`.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

TOKENS = "tokens"
COST = "cost_usd"
RUN_TIMEOUT = "run_timeout_seconds"
JOB_TIMEOUT = "job_timeout_seconds"

# Sized from the pilot corpus: Codex used ~1.6M tokens and ~$2 for one skill (candidate + control), so ~2x headroom.
DEFAULTS = {
    "ROUTING_MAX_TOKENS": "4000000",
    "ROUTING_MAX_COST_USD": "6",
    "ROUTING_MAX_CONCURRENCY": "4",
    "ROUTING_RUN_TIMEOUT_SECONDS": "240",
    "ROUTING_JOB_TIMEOUT_SECONDS": "480",
}


class CeilingBreach(Exception):
    """A ceiling was reached; the host run stops as infra_error."""

    def __init__(self, breach: dict[str, Any]):
        super().__init__(describe(breach))
        self.breach = breach


@dataclass(frozen=True)
class Ceilings:
    max_tokens: float
    max_cost_usd: float
    max_concurrency: int
    run_timeout_seconds: float
    job_timeout_seconds: float

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Ceilings":
        merged = {**DEFAULTS, **{k: v for k, v in (env if env is not None else os.environ).items() if k in DEFAULTS and v != ""}}

        def number(key: str, minimum: float) -> float:
            try:
                value = float(merged[key])
            except ValueError:
                raise ValueError(f"{key} must be a number, got {merged[key]!r}") from None
            if value < minimum:
                raise ValueError(f"{key} must be >= {minimum:g}, got {merged[key]!r}")
            return value

        return cls(
            max_tokens=number("ROUTING_MAX_TOKENS", 0),
            max_cost_usd=number("ROUTING_MAX_COST_USD", 0),
            max_concurrency=int(number("ROUTING_MAX_CONCURRENCY", 1)),
            run_timeout_seconds=number("ROUTING_RUN_TIMEOUT_SECONDS", 1),
            job_timeout_seconds=number("ROUTING_JOB_TIMEOUT_SECONDS", 1),
        )


def describe(breach: dict[str, Any]) -> str:
    return f"{breach['host']}: {breach['ceiling']} ceiling {breach['limit']:g} reached (observed {breach['observed']:g})"


def usage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum tokens, cost, and latency over Promptfoo result rows. Missing numbers count as zero."""
    def num(value: Any) -> float:
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0

    tokens = cost = latency = 0.0
    for row in rows:
        response = row.get("response") if isinstance(row.get("response"), dict) else {}
        token_usage = response.get("tokenUsage") if isinstance(response.get("tokenUsage"), dict) else {}
        tokens += num(token_usage.get("total"))
        cost += num(row.get("cost"))
        latency += num(row.get("latencyMs"))
    return {"trials": len(rows), "tokens": int(tokens), "cost_usd": round(cost, 6), "latency_ms": int(latency)}


@dataclass
class Ledger:
    """Spend per host and elapsed time for one eval, shared by every run of that eval."""

    ceilings: Ceilings
    clock: Callable[[], float] = time.monotonic
    started: float = field(init=False)
    spent: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.started = self.clock()

    def record(self, host: str, rows: list[dict[str, Any]]) -> None:
        total = self.spent.setdefault(host, {"tokens": 0, "cost_usd": 0.0})
        used = usage(rows)
        total["tokens"] += used["tokens"]
        total["cost_usd"] += used["cost_usd"]

    def breaches(self, host: str) -> list[dict[str, Any]]:
        """Every ceiling currently reached or exceeded for `host`."""
        spent = self.spent.get(host, {"tokens": 0, "cost_usd": 0.0})
        elapsed = self.clock() - self.started
        found = []
        for name, limit, observed in (
            (TOKENS, self.ceilings.max_tokens, spent["tokens"]),
            (COST, self.ceilings.max_cost_usd, spent["cost_usd"]),
            (JOB_TIMEOUT, self.ceilings.job_timeout_seconds, elapsed),
        ):
            # A zero or tiny ceiling is reached by the first call; spend equal to the limit is a breach.
            if observed >= limit and (observed > 0 or limit == 0):
                found.append({"ceiling": name, "limit": limit, "observed": round(observed, 6), "host": host})
        return found

    def check(self, host: str) -> None:
        found = self.breaches(host)
        if found:
            raise CeilingBreach(found[0])

    def run_timeout(self) -> float:
        """Seconds the next Promptfoo run may take: the run ceiling, capped by the job time left."""
        remaining = self.ceilings.job_timeout_seconds - (self.clock() - self.started)
        return max(min(self.ceilings.run_timeout_seconds, remaining), 1.0)

    def timeout_breach(self, host: str) -> dict[str, Any]:
        """Breach to report when a run was killed: whichever of run/job timeout was the binding one."""
        remaining = self.ceilings.job_timeout_seconds - (self.clock() - self.started)
        if remaining < self.ceilings.run_timeout_seconds:
            return {"ceiling": JOB_TIMEOUT, "limit": self.ceilings.job_timeout_seconds, "observed": round(self.clock() - self.started, 3), "host": host}
        return {"ceiling": RUN_TIMEOUT, "limit": self.ceilings.run_timeout_seconds, "observed": self.ceilings.run_timeout_seconds, "host": host}
