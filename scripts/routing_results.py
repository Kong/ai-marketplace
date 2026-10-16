"""Reduce Promptfoo routing results into per-agent states: pass, routing_fail, infra_error.

Pure functions, no I/O and no model calls. `run_routing_eval.py` feeds this module
Promptfoo JSON rows; later consumers (candidate/control comparison) read the
documents it returns.

States
    pass           every scenario met its route.
    routing_fail   the agent answered and telemetry was valid, but a route was wrong.
    infra_error    the run could not be judged; never attributed to skill quality.
                   A persistent one leaves the agent *incomplete* (`complete: false`).

Failure kinds (why a trial or agent is not `pass`)
    invocation           routing_fail: expected skill not invoked, or forbidden one was.
    provider             infra_error: provider error, missing credentials, or no usable
                         report from Promptfoo.
    ceiling              infra_error: a token, cost, or timeout ceiling was reached
                         (routing_ceilings.py); the run is stopped, never a routing_fail.
    telemetry            infra_error: response arrived but skill-call telemetry is malformed.
    scenario_validation  infra_error: scenarios failed offline validation; nothing was run.

Agent result document (`reduce_agent` / `agent_failure`)
    {
      "agent": "codex", "skill": "<target>",
      "state": "pass|routing_fail|infra_error",
      "complete": bool,              # false only for infra_error
      "retries": int,                # retry attempts run for this agent (0 or 1)
      "failure_kinds": ["invocation"|"provider"|"telemetry"|"ceiling"|"scenario_validation"],
      "usage": {"trials", "tokens", "cost_usd", "latency_ms"},   # all attempts, incl. retries
      "breaches": [{"ceiling", "limit", "observed", "agent"}],    # non-empty => infra_error
      "settings": {"model": {"value", "source"}, "effort": {"value"|null, "source"}},
                                     # effective agent settings; source is "default" or "override"
      "agents_run": [...], "partial": bool,   # run scripts add these; partial = fewer than all agents ran
      "aliased": bool,               # skills had opaque aliases in the workspace (routing_aliases.py); every name
                                     # in this document is the REAL skill name, mapped back from the aliases
      "fingerprint": str | None,     # hash of every description in the workspace (run scripts add it)
      "overridden": bool,            # any ROUTING_*_MODEL / _EFFORT override was active
                                     # (settings/overridden are added by the run scripts, not reduce_agent)
      "counts": {"pass": n, "routing_fail": n, "infra_error": n},   # final trials
      "scenarios": [{
        "id", "state", "passes", "required_passes", "trials": [trial, ...]
      }],
      "reason": str | None           # agent-level failures only (no scenarios ran)
    }
    trial = {
      "scenario", "trial", "trials", "state", "kind", "reason",
      "expected": [...], "forbidden": [...], "observed": [skill names],
      "attempts": int,               # 1, or 2 if retried
      "evidence": {"skill_calls": [...], "error": str|None, "output": str|None,
                   "latency_ms", "tokens", "cost"}
    }
Rules
    * A scenario passes when passing trials >= ceil(2/3 * trials) (3 -> 2, 1 -> 1).
    * Any trial still infra_error after retry makes its scenario, and the agent,
      infra_error (incomplete). Scenario-level states stay visible so real routing
      failures in the same run are not hidden.
    * Any ceiling breach makes the agent infra_error (incomplete) even if trials were
      judged; the judged scenarios stay visible but are not trusted as a full result.
    * Otherwise any failed scenario makes the agent routing_fail.

Cross-agent document (`combine_agents`):
`{"state", "complete", "agents": {agent: state}, "usage": {agent: usage}, "breaches": [...]}`.
Agents never offset each other: routing_fail on any agent wins, then infra_error
(including an agent with no result), and only all-pass is pass.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

import routing_aliases as aliasing
import routing_ceilings as ceilings

PASS = "pass"
ROUTING_FAIL = "routing_fail"
INFRA_ERROR = "infra_error"

INVOCATION = "invocation"
PROVIDER = "provider"
TELEMETRY = "telemetry"
CEILING = "ceiling"
SCENARIO_VALIDATION = "scenario_validation"

AGENTS = ("claude", "codex")
# Promptfoo ResultFailureReason: 0 none, 1 assertion, 2 error.
FAILURE_REASON_ERROR = 2
MAX_TEXT = 300


def _clip(text: Any) -> str | None:
    if not isinstance(text, str) or not text:
        return None
    first = text.strip().splitlines()[0] if text.strip() else ""
    return first[:MAX_TEXT] or None


def _answered_none(response: dict[str, Any]) -> bool:
    """The agent explicitly replied NONE (no skill) and the provider reported no error."""
    output = response.get("output")
    return isinstance(output, str) and output.strip().upper() == "NONE" and not response.get("error")


def telemetry_problem(response: Any, agent: str) -> str | None:
    """Return why a provider response cannot be trusted as routing telemetry, else None.

    Promptfoo's skill assertions silently treat missing or malformed `skillCalls` as
    "no skill used", which would turn a broken run into a false pass or routing_fail.
    Claude reports `skillCalls` whenever it called a skill (even when a hook ends the turn,
    so its output is not required). When the agent selects no skill it may omit the field
    entirely (observed live with the stop-on-activation hook provider: output `NONE`,
    `stop_reason: end_turn`, no `metadata.skillCalls`). The prompt tells the agent to reply
    with only the skill name or NONE, so for Claude a missing `skillCalls` is a valid "no
    skill used" only when the stripped output equals `NONE` (case-insensitive) and no error
    is present. Any other output with no `skillCalls` (a skill name, empty, garbage) could
    be a lost Skill call and stays a telemetry problem. A present empty list is always valid.
    Codex omits `skillCalls` when no SKILL.md was read, so absence is valid there, but the
    response must still carry a string output.
    """
    if not isinstance(response, dict):
        return "provider returned no response object"
    if agent == "codex" and not isinstance(response.get("output"), str):
        return "response output is missing or not a string"
    metadata = response.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        return "response metadata is not an object"
    calls = (metadata or {}).get("skillCalls")
    if calls is None:
        return None if agent != "claude" or _answered_none(response) else "response has no skillCalls telemetry"
    if not isinstance(calls, list):
        return "skillCalls is not a list"
    for call in calls:
        if not isinstance(call, dict) or not isinstance(call.get("name"), str):
            return "skillCalls entry has no string name"
    return None


def _identity(row: dict[str, Any]) -> tuple[str, int, int, dict[str, Any]]:
    case = row.get("testCase") or {}
    meta = case.get("metadata") or {}
    scenario = meta.get("scenario") or case.get("description") or "unknown"
    return scenario, int(meta.get("trial") or 1), int(meta.get("trials") or 1), meta


def _real_calls(calls: list[dict[str, Any]], aliases: Mapping[str, str] | None) -> list[dict[str, Any]]:
    if not aliases:
        return calls
    return [{**c, "name": aliasing.to_real(c["name"], aliases)} if isinstance(c.get("name"), str) else c for c in calls]


def reduce_trial(row: dict[str, Any], agent: str, aliases: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Classify one Promptfoo result row.

    `aliases` (real -> alias) is the workspace's map when skills were aliased: the row carries
    aliases, the returned trial carries real names (expected, forbidden, observed, call names and the
    quoted reason). The raw Promptfoo JSON is never rewritten.
    """
    scenario, trial, trials, meta = _identity(row)
    response = row.get("response")
    calls: list[dict[str, Any]] = []
    if isinstance(response, dict) and isinstance((response.get("metadata") or {}).get("skillCalls"), list):
        calls = [c for c in response["metadata"]["skillCalls"] if isinstance(c, dict)]
    error = row.get("error") or (response.get("error") if isinstance(response, dict) else None)
    grading = row.get("gradingResult") or {}

    if error or row.get("failureReason") == FAILURE_REASON_ERROR:
        state, kind, reason = INFRA_ERROR, PROVIDER, _clip(error) or "provider error"
    elif (problem := telemetry_problem(response, agent)) is not None:
        state, kind, reason = INFRA_ERROR, TELEMETRY, problem
    elif row.get("success"):
        state, kind, reason = PASS, None, _clip(grading.get("reason"))
    else:
        state, kind = ROUTING_FAIL, INVOCATION
        reason = _clip(grading.get("reason")) or "routing assertion failed"
    reason = aliasing.to_real(reason, aliases) if reason else reason

    output = _clip(response.get("output") if isinstance(response, dict) else None)
    usage = (response or {}).get("tokenUsage") if isinstance(response, dict) else None
    return {
        "scenario": scenario,
        "trial": trial,
        "trials": trials,
        "state": state,
        "kind": kind,
        "reason": reason,
        "expected": [aliasing.to_real(n, aliases) for n in meta.get("expected") or []],
        "forbidden": [aliasing.to_real(n, aliases) for n in meta.get("forbidden") or []],
        "observed": [c["name"] for c in _real_calls(calls, aliases) if isinstance(c.get("name"), str) and c.get("is_error") is not True],
        "attempts": 1,
        "evidence": {
            "skill_calls": _real_calls(calls, aliases),
            "error": _clip(error),
            "output": aliasing.to_real(output, aliases) if output else None,
            "latency_ms": row.get("latencyMs"),
            "tokens": usage.get("total") if isinstance(usage, dict) else None,
            "cost": row.get("cost"),
        },
    }


def _scenario_state(passes: int, required: int, trials: list[dict[str, Any]]) -> str:
    if any(t["state"] == INFRA_ERROR for t in trials):
        return INFRA_ERROR
    return PASS if passes >= required else ROUTING_FAIL


def reduce_agent(
    agent: str, skill: str, attempts: list[list[dict[str, Any]]], breaches: list[dict[str, Any]] | None = None,
    aliases: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Reduce Promptfoo rows to an agent result.

    `attempts[0]` is the full run; each later entry holds only the retried trials.
    The latest row for a (scenario, trial) wins, so a transient failure that passes
    on retry reports `pass` with `attempts: 2`. `breaches` are ceilings reached during
    the run; any of them makes the agent infra_error.
    """
    breaches = breaches or []
    merged: dict[tuple[str, int], dict[str, Any]] = {}
    for number, rows in enumerate(attempts, start=1):
        for row in rows:
            trial = reduce_trial(row, agent, aliases)
            trial["attempts"] = number
            merged[(trial["scenario"], trial["trial"])] = trial

    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for key in sorted(merged):
        by_scenario.setdefault(key[0], []).append(merged[key])

    scenarios = []
    for scenario_id, trials in by_scenario.items():
        passes = sum(t["state"] == PASS for t in trials)
        required = math.ceil(2 * trials[0]["trials"] / 3)
        scenarios.append({
            "id": scenario_id,
            "state": _scenario_state(passes, required, trials),
            "passes": passes,
            "required_passes": required,
            "trials": trials,
        })

    states = {s["state"] for s in scenarios}
    state = INFRA_ERROR if INFRA_ERROR in states or not scenarios or breaches else (ROUTING_FAIL if ROUTING_FAIL in states else PASS)
    all_trials = [t for s in scenarios for t in s["trials"]]
    kinds = sorted({t["kind"] for t in all_trials if t["kind"]} | ({CEILING} if breaches else set()))
    return {
        "agent": agent,
        "skill": skill,
        "state": state,
        "complete": state != INFRA_ERROR,
        "retries": max(len(attempts) - 1, 0),
        "aliased": aliases is not None,
        "failure_kinds": kinds if scenarios else [PROVIDER],
        "counts": {s: sum(t["state"] == s for t in all_trials) for s in (PASS, ROUTING_FAIL, INFRA_ERROR)},
        "usage": ceilings.usage([row for rows in attempts for row in rows]),
        "breaches": breaches,
        "scenarios": scenarios,
        "reason": ceilings.describe(breaches[0]) if breaches else (None if scenarios else "no results were produced"),
    }


def agent_failure(
    agent: str, skill: str, kind: str, reason: str, retries: int = 0, breaches: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Agent result for a failure outside any trial: no report, crash, invalid scenarios, or a ceiling."""
    if kind not in (PROVIDER, TELEMETRY, SCENARIO_VALIDATION, CEILING):
        raise ValueError(f"agent-level failure kind must be infrastructure, got {kind!r}")
    return {
        "agent": agent,
        "skill": skill,
        "state": INFRA_ERROR,
        "complete": False,
        "retries": retries,
        "aliased": False,
        "failure_kinds": [kind],
        "counts": {PASS: 0, ROUTING_FAIL: 0, INFRA_ERROR: 0},
        "usage": ceilings.usage([]),
        "breaches": breaches or [],
        "scenarios": [],
        "reason": _clip(reason) or kind,
    }


def combine_agents(results: list[dict[str, Any]], required: tuple[str, ...] = AGENTS) -> dict[str, Any]:
    """Combine independent agent results; a passing agent never offsets another.

    `required` defaults to every agent, so a missing agent is infra_error. A subset run passes only
    the agents it ran; the document then says `partial: true` and lists `agents_run`, so it can
    never be mistaken for a complete result (the state covers only those agents).
    """
    # An incomplete agent (e.g. an infra_error control behind a passing candidate) is never a pass.
    by_agent = {r["agent"]: (r["state"] if r.get("complete", True) or r["state"] != PASS else INFRA_ERROR) for r in results}
    agents = {agent: by_agent.get(agent, INFRA_ERROR) for agent in required}
    states = set(agents.values())
    state = ROUTING_FAIL if ROUTING_FAIL in states else (INFRA_ERROR if INFRA_ERROR in states else PASS)
    return {
        "state": state,
        "complete": INFRA_ERROR not in states,
        "agents_run": list(required),
        "partial": set(required) != set(AGENTS),
        "agents": agents,
        "usage": {r["agent"]: r["usage"] for r in results if "usage" in r},
        "breaches": [b for r in results for b in r.get("breaches") or []],
        "settings": {r["agent"]: r["settings"] for r in results if "settings" in r},
        "overridden": any(r.get("overridden") for r in results),
        "aliased": bool(results) and all(r.get("aliased") for r in results),
    }
