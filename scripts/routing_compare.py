"""Compare candidate and control host results, or judge a new skill on absolute thresholds.

Pure functions over the host result documents from `routing_results.py`; no I/O and
no model calls. Nothing here is a stored baseline: both sides come from the same run.

Rates count judged trials only (`pass` + `routing_fail`); `infra_error` trials are
excluded and make the document `complete: false`.

Comparison document (`compare_host`, modified skill)
    {
      "host", "skill", "mode": "comparison",
      "state": <candidate host state>,      # the delta is reported, not gated
      "complete": bool,                     # both sides complete
      "candidate_state", "control_state",
      "failure_kinds": [...], "reason": str|None,   # union / first of both sides' infra failures
      "aggregate": {"candidate": side, "control": side, "delta": float|None},
      "scenarios": [{"id", "candidate": side|None, "control": side|None, "delta": float|None}]
    }
    side = {"state", "passes", "trials", "rate": float|None}
    delta = candidate rate - control rate; negative means candidate routes worse.

New-skill document (`evaluate_new_skill`, no control exists)
    {
      "host", "skill", "mode": "new_skill", "control": "skipped",
      "state": pass|routing_fail|infra_error, "complete": bool,
      "failure_kinds": [...], "reason": str|None,   # from the host result, e.g. scenario_validation
      "expectations": {
        "positive_recall": check, "near_miss_specificity": check
      },
      "siblings": side             # reported only, not thresholded
    }
    check = {"required": float, "passes", "trials", "rate", "met": bool}
"""
from __future__ import annotations

from typing import Any

import routing_results as results

POSITIVE_RECALL = 0.90
NEAR_MISS_SPECIFICITY = 0.95


def _side(trials: list[dict[str, Any]], state: str) -> dict[str, Any]:
    judged = [t for t in trials if t["state"] in (results.PASS, results.ROUTING_FAIL)]
    passes = sum(t["state"] == results.PASS for t in judged)
    return {"state": state, "passes": passes, "trials": len(judged), "rate": passes / len(judged) if judged else None}


def _delta(candidate: dict[str, Any] | None, control: dict[str, Any] | None) -> float | None:
    if not candidate or not control or candidate["rate"] is None or control["rate"] is None:
        return None
    return round(candidate["rate"] - control["rate"], 4)


def _by_scenario(host_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["id"]: _side(s["trials"], s["state"]) for s in host_result["scenarios"]}


def _all_trials(host_result: dict[str, Any]) -> list[dict[str, Any]]:
    return [t for s in host_result["scenarios"] for t in s["trials"]]


def compare_host(candidate: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    """Per-scenario and aggregate candidate/control deltas for one host."""
    cand, ctrl = _by_scenario(candidate), _by_scenario(control)
    aggregate = {
        "candidate": _side(_all_trials(candidate), candidate["state"]),
        "control": _side(_all_trials(control), control["state"]),
    }
    aggregate["delta"] = _delta(aggregate["candidate"], aggregate["control"])
    return {
        "host": candidate["host"],
        "skill": candidate["skill"],
        "mode": "comparison",
        "state": candidate["state"],
        "complete": candidate["complete"] and control["complete"],
        "candidate_state": candidate["state"],
        "control_state": control["state"],
        "failure_kinds": sorted(set(candidate["failure_kinds"]) | set(control["failure_kinds"])),
        "reason": candidate["reason"] or control["reason"],
        "aggregate": aggregate,
        "scenarios": [
            {"id": sid, "candidate": cand.get(sid), "control": ctrl.get(sid), "delta": _delta(cand.get(sid), ctrl.get(sid))}
            for sid in sorted(set(cand) | set(ctrl))
        ],
    }


def _check(trials: list[dict[str, Any]], required: float) -> dict[str, Any]:
    side = _side(trials, results.PASS)
    rate = side["rate"]
    return {
        "required": required,
        "passes": side["passes"],
        "trials": side["trials"],
        "rate": rate,
        "met": rate is not None and rate >= required,
    }


def evaluate_new_skill(host_result: dict[str, Any], tags: dict[str, list[str]]) -> dict[str, Any]:
    """Judge one host of a new skill: >=90% positive recall and >=95% near-miss specificity.

    `tags` maps scenario id to its tags (the host result does not carry them). A scenario
    tagged both positive and near-miss counts toward both; sibling trials are reported only.
    """
    def trials_tagged(tag: str) -> list[dict[str, Any]]:
        return [t for s in host_result["scenarios"] if tag in tags.get(s["id"], []) for t in s["trials"]]

    checks = {
        "positive_recall": _check(trials_tagged("positive"), POSITIVE_RECALL),
        "near_miss_specificity": _check(trials_tagged("near-miss"), NEAR_MISS_SPECIFICITY),
    }
    if not host_result["complete"]:
        state = results.INFRA_ERROR
    else:
        state = results.PASS if all(c["met"] for c in checks.values()) else results.ROUTING_FAIL
    return {
        "host": host_result["host"],
        "skill": host_result["skill"],
        "mode": "new_skill",
        "control": "skipped",
        "state": state,
        "complete": host_result["complete"],
        "failure_kinds": host_result["failure_kinds"],
        "reason": host_result["reason"],
        "expectations": checks,
        "siblings": _side(trials_tagged("sibling"), results.PASS),
    }
