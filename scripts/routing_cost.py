"""Rough, no-spend trial and cost estimates for a routing eval selection. Offline.

The per-trial prices are planning assumptions, not measurements: one routing trial is a short
discovery-only agent turn. Change them here only; the preview, the docs and the tests read these
constants. The hard bound on spend is the per-run cost ceiling (routing_ceilings.py), not this file.
"""
from __future__ import annotations

from typing import Any, Mapping

import routing_compare as compare

CLAUDE_USD_PER_TRIAL = 0.04
CODEX_USD_PER_TRIAL = (0.05, 0.10)  # (low, high)

GATE, COMPARE, SNAPSHOT = "gate", "compare", "snapshot"


def usd_range(agent: str) -> tuple[float, float]:
    return (CLAUDE_USD_PER_TRIAL, CLAUDE_USD_PER_TRIAL) if agent == "claude" else CODEX_USD_PER_TRIAL


def entry_trials(entry: Mapping[str, Any], trials_by_id: Mapping[str, int], all_trials: Mapping[str, int]) -> dict[str, int]:
    """Trials per agent for one matrix entry: `initial` (expected when nothing fails) and `worst`.

    gate, modified skill: one candidate trial per scenario; worst case every scenario fails and is
                          confirmed on candidate and control at max(its trials, CONFIRM_TRIALS).
    gate, new skill:      no control and no adaptive pass: every scenario at its own trials.
    compare:              candidate and control at the scenarios' own trials; the confirmation re-run
                          of regressed scenarios is the worst case.
    snapshot:             the skill's own file at its own trials (`all_trials` covers the whole corpus).
    """
    ids = [i for i in str(entry.get("scenarios") or "").split(",") if i]
    own = sum(trials_by_id.get(i, all_trials.get(i, 1)) for i in ids)
    confirm = sum(max(trials_by_id.get(i, all_trials.get(i, 1)), compare.CONFIRM_TRIALS) for i in ids)
    mode = entry["mode"]
    if mode == GATE and not entry.get("new"):
        return {"scenarios": len(ids), "initial": len(ids), "worst": len(ids) + 2 * confirm}
    if mode == COMPARE:
        return {"scenarios": len(ids), "initial": 2 * own, "worst": 4 * own}
    return {"scenarios": len(ids), "initial": own, "worst": own}


def estimate(plans: list[dict[str, int]], agents: list[str]) -> dict[str, Any]:
    """Totals per agent and overall, as trials and a (low, high) USD range for the expected and worst case."""
    initial, worst = sum(p["initial"] for p in plans), sum(p["worst"] for p in plans)
    per_agent = {}
    for agent in agents:
        low, high = usd_range(agent)
        per_agent[agent] = {
            "initial_trials": initial, "worst_trials": worst,
            "expected_usd": (round(initial * low, 2), round(initial * high, 2)),
            "worst_usd": (round(worst * low, 2), round(worst * high, 2)),
        }
    total = lambda key, i: round(sum(a[key][i] for a in per_agent.values()), 2)  # noqa: E731
    return {
        "scenarios": sum(p["scenarios"] for p in plans),
        "agents": per_agent,
        "expected_usd": (total("expected_usd", 0), total("expected_usd", 1)),
        "worst_usd": (total("worst_usd", 0), total("worst_usd", 1)),
    }


def _range(pair: tuple[float, float]) -> str:
    return f"${pair[0]:.2f}" if pair[0] == pair[1] else f"${pair[0]:.2f}-${pair[1]:.2f}"


def assumptions_text() -> str:
    low, high = CODEX_USD_PER_TRIAL
    return (f"rough assumptions, not measurements: ~${CLAUDE_USD_PER_TRIAL:.2f}/trial Claude, ${low:.2f}-${high:.2f}/trial Codex "
            "(scripts/routing_cost.py)")


def lines(plans: list[dict[str, int]], agents: list[str]) -> list[str]:
    """Markdown lines for the select job summary."""
    est = estimate(plans, agents)
    out = [
        f"Evaluation set: {est['scenarios']} scenario(s).",
        "",
        "| Agent | Initial trials | Worst-case trials | Expected cost | Worst-case cost |",
        "| --- | --- | --- | --- | --- |",
    ]
    out += [
        f"| {agent} | {a['initial_trials']} | {a['worst_trials']} | {_range(a['expected_usd'])} | {_range(a['worst_usd'])} |"
        for agent, a in est["agents"].items()
    ]
    out += [
        "",
        f"Total expected {_range(est['expected_usd'])}; worst case (every scenario fails and is confirmed on candidate and control) "
        f"{_range(est['worst_usd'])}. Cost is {assumptions_text()}. The hard bound is the per-run cost ceiling.",
    ]
    return out
