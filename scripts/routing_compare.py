"""Compare candidate and control agent results, or judge a new skill on absolute thresholds.

Pure functions over the agent result documents from `routing_results.py`; no I/O and
no model calls. Nothing here is a stored baseline: both sides come from the same run.

Rates count judged trials only (`pass` + `routing_fail`); `infra_error` trials are
excluded and make the document `complete: false`.

Comparison document (`compare_agent`, modified skill)
    {
      "agent", "skill", "mode": "comparison",
      "state": <candidate agent state>,      # the delta is reported, not gated; infra_error on a ceiling breach
      "complete": bool,                     # both sides complete
      "candidate_state", "control_state",
      "failure_kinds": [...], "reason": str|None,   # union / first of both sides' infra failures
      "usage": {"trials", "tokens", "cost_usd", "latency_ms"},   # candidate + control, incl. retries
      "settings", "overridden",             # effective model/effort for both sides (same for candidate and control)
      "usage_by_side": {"candidate": usage, "control": usage},
      "breaches": [...],                    # ceilings reached on either side; non-empty => infra_error
      "aggregate": {"candidate": side, "control": side, "delta": float|None},
      "scenarios": [{"id", "candidate": side|None, "control": side|None, "delta": float|None}]
    }
    side = {"state", "passes", "trials", "rate": float|None}
    delta = candidate rate - control rate; negative means candidate routes worse.
    Optional "confirmation" (added by `with_confirmation` when the gate re-runs regressions):
      {"trials": 3, "regressions": [ids], "state": pass|routing_fail|infra_error, "complete": bool,
       "reason": str|None, "usage": usage, "breaches": [...],
       "scenarios": [{"id", "candidate": side, "control": side, "confirmed": bool}]}
    A regression is a scenario that passes on control and fails on candidate (scenario pass rule);
    it is *confirmed* when it still does so in the 3-trial re-run. Only confirmed regressions gate.

Lazy comparison document (`lazy_compare`, the merge gate's modified-skill path; control only where needed)
    The candidate runs every selected scenario once. Only scenarios that failed are confirmed: the
    candidate again at max(the scenario's trials, CONFIRM_TRIALS) and, for those still failing, the control at the
    same trials. A scenario that passed the first pass cannot be a regression, so it never runs on
    the control. Unlike `compare_agent` there are no aggregate deltas (AC-14 behaviour stays with
    `eval:routing:compare` without `--gate`).
    {
      "agent", "skill", "mode": "lazy_comparison",
      "state",                              # candidate's first-pass state; infra_error if incomplete or a ceiling breach
      "complete": bool, "candidate_state", "failure_kinds": [...], "reason": str|None,
      "usage", "usage_by_phase": {"initial": usage, "confirmation": usage}, "breaches": [...],
      "settings", "overridden",
      "failed": [ids],                      # failed the first pass
      "scenarios": [{"id", "candidate": side|None}],        # first-pass sides
      "confirmation": None | {"state": pass|routing_fail|infra_error, "complete": bool, "reason": str|None,
          "scenarios": [{"id", "candidate": side|None, "control": side|None,
                         "outcome": confirmed|preexisting|cleared|incomplete}]}
    }
    outcome: confirmed = candidate still fails and control passes (a regression); preexisting = both
    fail (a warning); cleared = the candidate passed on re-run (flake); incomplete = no judged result.

New-skill document (`evaluate_new_skill`, no control exists)
    {
      "agent", "skill", "mode": "new_skill", "control": "skipped",
      "state": pass|routing_fail|infra_error, "complete": bool,
      "failure_kinds": [...], "reason": str|None,   # from the agent result, e.g. scenario_validation
      "usage": usage, "breaches": [...],            # from the agent result
      "settings", "overridden",                     # effective model/effort, as above
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

CONFIRM_TRIALS = 3
LAZY = "lazy_comparison"
CONFIRMED, PREEXISTING, CLEARED, INCOMPLETE = "confirmed", "preexisting", "cleared", "incomplete"
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


def _by_scenario(agent_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["id"]: _side(s["trials"], s["state"]) for s in agent_result["scenarios"]}


def _all_trials(agent_result: dict[str, Any]) -> list[dict[str, Any]]:
    return [t for s in agent_result["scenarios"] for t in s["trials"]]


def _total(*usages: dict[str, Any]) -> dict[str, Any]:
    keys = ("trials", "tokens", "cost_usd", "latency_ms")
    return {k: round(sum(u[k] for u in usages), 6) if k == "cost_usd" else sum(u[k] for u in usages) for k in keys}


def compare_agent(candidate: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    """Per-scenario and aggregate candidate/control deltas for one agent."""
    cand, ctrl = _by_scenario(candidate), _by_scenario(control)
    aggregate = {
        "candidate": _side(_all_trials(candidate), candidate["state"]),
        "control": _side(_all_trials(control), control["state"]),
    }
    aggregate["delta"] = _delta(aggregate["candidate"], aggregate["control"])
    breaches = candidate["breaches"] + [b for b in control["breaches"] if b not in candidate["breaches"]]
    return {
        "agent": candidate["agent"],
        "skill": candidate["skill"],
        "mode": "comparison",
        "state": results.INFRA_ERROR if breaches else candidate["state"],
        "complete": candidate["complete"] and control["complete"],
        "candidate_state": candidate["state"],
        "control_state": control["state"],
        "failure_kinds": sorted(set(candidate["failure_kinds"]) | set(control["failure_kinds"])),
        "reason": candidate["reason"] or control["reason"],
        "usage": _total(candidate["usage"], control["usage"]),
        "usage_by_side": {"candidate": candidate["usage"], "control": control["usage"]},
        "breaches": breaches,
        "aggregate": aggregate,
        "scenarios": [
            {"id": sid, "candidate": cand.get(sid), "control": ctrl.get(sid), "delta": _delta(cand.get(sid), ctrl.get(sid))}
            for sid in sorted(set(cand) | set(ctrl))
        ],
    }


def _state(scenario: dict[str, Any] | None) -> str | None:
    return scenario["state"] if scenario else None


def regressions(doc: dict[str, Any]) -> list[str]:
    """Scenario ids that pass on control and fail on candidate (judged, not infra_error)."""
    return [
        s["id"] for s in doc["scenarios"]
        if _state(s["control"]) == results.PASS and _state(s["candidate"]) == results.ROUTING_FAIL
    ]


def preexisting_failures(doc: dict[str, Any]) -> list[str]:
    """Scenario ids failing on both sides: not regressions, reported as warnings."""
    return [
        s["id"] for s in doc["scenarios"]
        if _state(s["control"]) == results.ROUTING_FAIL and _state(s["candidate"]) == results.ROUTING_FAIL
    ]


def with_confirmation(doc: dict[str, Any], candidate: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    """Attach the 3-trial re-run of this document's regressions (candidate and control results).

    Confirmed = candidate still fails and control still passes. Anything that leaves a re-run
    scenario without a judged result on either side makes the confirmation infra_error and the
    document incomplete, so the gate can fail closed instead of guessing.
    """
    ids = regressions(doc)
    cand, ctrl = _by_scenario(candidate), _by_scenario(control)
    rows = []
    for sid in ids:
        c, k = cand.get(sid), ctrl.get(sid)
        rows.append({
            "id": sid, "candidate": c, "control": k,
            "confirmed": _state(c) == results.ROUTING_FAIL and _state(k) == results.PASS,
        })
    complete = (
        candidate["complete"] and control["complete"]
        and all(_state(r["candidate"]) in (results.PASS, results.ROUTING_FAIL) and _state(r["control"]) in (results.PASS, results.ROUTING_FAIL) for r in rows)
    )
    state = results.INFRA_ERROR if not complete else (results.ROUTING_FAIL if any(r["confirmed"] for r in rows) else results.PASS)
    breaches = candidate["breaches"] + [b for b in control["breaches"] if b not in candidate["breaches"]]
    out = dict(doc)
    out["confirmation"] = {
        "trials": CONFIRM_TRIALS,
        "regressions": ids,
        "state": state,
        "complete": complete,
        "reason": candidate["reason"] or control["reason"] or (None if complete else "re-run left a regressed scenario without a judged result"),
        "usage": _total(candidate["usage"], control["usage"]),
        "breaches": breaches,
        "scenarios": rows,
    }
    out["usage"] = _total(doc["usage"], out["confirmation"]["usage"])
    if breaches:
        out["breaches"] = doc["breaches"] + [b for b in breaches if b not in doc["breaches"]]
        out["state"], out["complete"] = results.INFRA_ERROR, False
    return out


def failed_scenarios(agent_result: dict[str, Any]) -> list[str]:
    """Scenario ids judged routing_fail (infra_error scenarios are not failures)."""
    return [s["id"] for s in agent_result["scenarios"] if s["state"] == results.ROUTING_FAIL]


def _union(*breach_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for breaches in breach_lists:
        merged += [b for b in breaches if b not in merged]
    return merged


def lazy_compare(
    initial: dict[str, Any],
    confirm_candidate: dict[str, Any] | None = None,
    confirm_control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Judge one agent from the first candidate pass and, when something failed, its confirmation runs.

    `confirm_candidate` must cover every failed scenario and `confirm_control` every scenario that
    still failed on the candidate; a missing or unjudged result makes the confirmation incomplete
    so the gate can fail closed (`routing_gate.judge_agent`).
    """
    failed = failed_scenarios(initial) if initial["complete"] else []
    rows: list[dict[str, Any]] = []
    cand = _by_scenario(confirm_candidate) if confirm_candidate else {}
    ctrl = _by_scenario(confirm_control) if confirm_control else {}
    for sid in failed:
        c, k = cand.get(sid), ctrl.get(sid)
        if _state(c) == results.PASS:
            outcome = CLEARED
        elif _state(c) == results.ROUTING_FAIL and _state(k) == results.PASS:
            outcome = CONFIRMED
        elif _state(c) == results.ROUTING_FAIL and _state(k) == results.ROUTING_FAIL:
            outcome = PREEXISTING
        else:
            outcome = INCOMPLETE
        rows.append({"id": sid, "candidate": c, "control": k, "outcome": outcome})
    phases = [r for r in (confirm_candidate, confirm_control) if r is not None]
    confirmation_complete = (
        bool(failed) and confirm_candidate is not None
        and all(r["complete"] for r in phases) and all(r["outcome"] != INCOMPLETE for r in rows)
    )
    breaches = _union(initial["breaches"], *(r["breaches"] for r in phases))
    complete = initial["complete"] and not breaches and (not failed or confirmation_complete)
    confirmation = None
    if failed:
        confirmation = {
            "state": results.INFRA_ERROR if not confirmation_complete else (results.ROUTING_FAIL if any(r["outcome"] == CONFIRMED for r in rows) else results.PASS),
            "complete": confirmation_complete,
            "reason": next((r["reason"] for r in phases if r["reason"]), None) or (None if confirmation_complete else "confirmation left a failed scenario without a judged result"),
            "scenarios": rows,
        }
    usage = _total(initial["usage"], *(r["usage"] for r in phases))
    confirm_usage = _total(*(r["usage"] for r in phases)) if phases else {"trials": 0, "tokens": 0, "cost_usd": 0.0, "latency_ms": 0}
    return {
        "agent": initial["agent"],
        "skill": initial["skill"],
        "mode": LAZY,
        "state": results.INFRA_ERROR if not complete else initial["state"],
        "complete": complete,
        "candidate_state": initial["state"],
        "failure_kinds": sorted(set(initial["failure_kinds"]) | {k for r in phases for k in r["failure_kinds"]}),
        "reason": initial["reason"] or next((r["reason"] for r in phases if r["reason"]), None),
        "usage": usage,
        "usage_by_phase": {"initial": initial["usage"], "confirmation": confirm_usage},
        "breaches": breaches,
        "failed": failed,
        "scenarios": [{"id": s["id"], "candidate": _side(s["trials"], s["state"])} for s in initial["scenarios"]],
        "confirmation": confirmation,
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


def evaluate_new_skill(agent_result: dict[str, Any], tags: dict[str, list[str]]) -> dict[str, Any]:
    """Judge one agent of a new skill: >=90% positive recall and >=95% near-miss specificity.

    `tags` maps scenario id to its tags (the agent result does not carry them). A scenario
    tagged both positive and near-miss counts toward both; sibling trials are reported only.
    """
    def trials_tagged(tag: str) -> list[dict[str, Any]]:
        return [t for s in agent_result["scenarios"] if tag in tags.get(s["id"], []) for t in s["trials"]]

    checks = {
        "positive_recall": _check(trials_tagged("positive"), POSITIVE_RECALL),
        "near_miss_specificity": _check(trials_tagged("near-miss"), NEAR_MISS_SPECIFICITY),
    }
    if not agent_result["complete"]:
        state = results.INFRA_ERROR
    else:
        state = results.PASS if all(c["met"] for c in checks.values()) else results.ROUTING_FAIL
    return {
        "agent": agent_result["agent"],
        "skill": agent_result["skill"],
        "mode": "new_skill",
        "control": "skipped",
        "state": state,
        "complete": agent_result["complete"],
        "failure_kinds": agent_result["failure_kinds"],
        "reason": agent_result["reason"],
        "usage": agent_result["usage"],
        "breaches": agent_result["breaches"],
        "expectations": checks,
        "siblings": _side(trials_tagged("sibling"), results.PASS),
    }
