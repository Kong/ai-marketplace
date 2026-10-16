"""Canary: an eval of the routing eval. Does the harness notice a destroyed skill description?

    python scripts/routing_canary.py <skill> [--agent claude|codex ...] [--alias default|on|off]
                                     [--fake-results FILE]

Builds a candidate workspace in which only <skill>'s description is replaced by CANARY_DESCRIPTION
(off-domain marketing copy), runs the skill's OWN positive scenarios on each requested agent at one
trial each (candidate only, no control), and decides per agent:

    canary_detected   at least 60% of the positive scenarios failed to route to the skill
                      (the harness noticed the damage)
    canary_missed     fewer did: a blind spot, the eval cannot see description regressions
    canary_incomplete an infrastructure error or ceiling breach left the answer unknown

The overall verdict is canary_missed if any agent missed, else canary_incomplete if any agent is
incomplete, else canary_detected. Exit codes: 0 detected, 1 missed, 2 harness or usage error,
3 incomplete. It never feeds the merge gate; run it after changing models, pins or the harness, and
after enabling the gate (docs/testing.md#canary-eval-of-the-eval).

`--alias` forces skill aliasing on or off for this run (default: ROUTING_ALIAS_SKILLS, else the
repo default, which is off), so the same canary can compare real names with opaque aliases. Aliasing on
suppresses Claude's skill selection, so a canary_detected with aliases proves nothing; a canary_missed
with real names is the known name-driven-routing limitation (a note is printed). The result is written to
`.tmp/routing/reports/canary-<skill>.canary.json`, records `aliased`, the damaged workspace's
fingerprint, usage and measured cost, and the measured cost is printed.

`--fake-results FILE` is the offline mode for tests: no provider call is made. FILE maps agent to
{scenario id: routed true|false}; a scenario it omits counts as routed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import routing_agents as agents_lib
import routing_aliases as aliasing
import routing_ceilings as ceilings
import routing_compare as compare
import routing_results as results
import routing_settings as settings_lib
import run_routing_comparison as driver
import run_routing_eval as runner
import prepare_routing_workspace as workspaces
import validate_routing_scenarios as scenarios

# Off-domain on purpose: nothing here relates to any Kong, Konnect or gateway topic, and the length is
# in the range of the real descriptions (about 250 characters).
CANARY_DESCRIPTION = (
    "Use when writing marketing copy about brand voice: shaping a company's tone, taglines, social media "
    "personality and storytelling style so every campaign sounds consistent, warm and memorable across "
    "newsletters, landing pages and product announcements."
)
THRESHOLD_PERCENT = 60

DETECTED, MISSED, INCOMPLETE = "canary_detected", "canary_missed", "canary_incomplete"
EXIT_CODES = {DETECTED: 0, MISSED: 1, INCOMPLETE: 3}
VARIANT = "canary"  # workspace and report directory label under .tmp/routing
NAME_DRIVEN_NOTE = (
    "note: canary_missed with real skill names indicates the known name-driven-routing limitation: a descriptive "
    "skill name carries routing, so the routing eval cannot detect description-only regressions "
    "(docs/testing.md#known-limitation-routing-is-name-driven)."
)
ALIAS_CHOICES = {"default": None, "on": "1", "off": "0"}


def positive_scenarios(skill: str) -> list[str]:
    """Ids of the skill's own positive scenarios: tagged positive and expecting the skill."""
    return [
        s["id"] for s in scenarios.target_scenarios(scenarios.SCENARIOS_DIR, skill)
        if "positive" in (s.get("tags") or []) and skill in (s.get("expect") or [])
    ]


def judge_agent(result: dict[str, Any], expected_ids: list[str]) -> dict[str, Any]:
    """Verdict for one agent's canary run (an agent result from routing_results)."""
    judged = {s["id"]: s for s in result["scenarios"]}
    failed = sorted(i for i, s in judged.items() if s["state"] == results.ROUTING_FAIL)
    complete = result["complete"] and set(judged) == set(expected_ids) and all(
        s["state"] in (results.PASS, results.ROUTING_FAIL) for s in judged.values()
    )
    total = len(expected_ids)
    if not complete:
        verdict = INCOMPLETE
    else:
        verdict = DETECTED if len(failed) * 100 >= THRESHOLD_PERCENT * total else MISSED
    return {
        "verdict": verdict, "positives": total, "failed": failed,
        "failed_percent": round(100 * len(failed) / total, 1) if total else None,
        "reason": result.get("reason") if verdict == INCOMPLETE else None,
        "fingerprint": result.get("fingerprint"), "usage": result["usage"],
    }


def overall(per_agent: dict[str, dict[str, Any]]) -> str:
    verdicts = {a["verdict"] for a in per_agent.values()}
    if MISSED in verdicts:
        return MISSED
    return INCOMPLETE if INCOMPLETE in verdicts or not verdicts else DETECTED


def fake_runner(root: Path, fake: dict[str, dict[str, bool]], ids: list[str]) -> Any:
    """A Promptfoo runner replacement: one row per positive scenario, routed or not per `fake`."""
    def run(agent: str, skill: str, report: Path, pattern: str | None) -> tuple[str, list[dict[str, Any]]]:
        aliases = aliasing.load(root / VARIANT / agent) or {}  # the map sits beside the workspace
        target = aliases.get(skill, skill)
        rows = []
        for sid in ids:
            routed = bool(fake.get(agent, {}).get(sid, True))
            # An unrouted Claude answer is the observed shape: output NONE and no skillCalls at all.
            metadata = {"skillCalls": [{"name": target}]} if routed else {}
            message = f"Missing required skill(s): {target}. Actual skills: (none)"
            row = {
                "success": routed, "failureReason": 0 if routed else 1, "latencyMs": 1, "cost": 0.0,
                "gradingResult": {"pass": routed, "reason": "ok" if routed else message},
                "response": {"output": "" if routed else "NONE", "metadata": metadata, "tokenUsage": {"total": 1}},
                "testCase": {
                    "description": f"{sid} | {agent} | trial 1/1",
                    "metadata": {"scenario": sid, "trial": 1, "trials": 1, "expected": [target], "forbidden": []},
                },
            }
            if not routed:
                row["error"] = message  # Promptfoo repeats an assertion failure in the row-level error
            rows.append(row)
        return "", rows
    return run


def run_canary(
    skill: str, agents: tuple[str, ...], routing_dir: Path | None = None,
    fake: dict[str, dict[str, bool]] | None = None, ledger: ceilings.Ledger | None = None,
    settings: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the canary for `skill` on `agents` and return the canary document."""
    routing_dir = routing_dir or driver.ROUTING_DIR
    ids = positive_scenarios(skill)
    if not ids:
        raise ValueError(f"skill {skill!r} has no positive scenarios of its own to run the canary on")
    if skill not in scenarios.known_skill_names():
        raise ValueError(f"unknown skill {skill!r}")
    ledger = ledger or ceilings.Ledger(ceilings.Ceilings.from_env())
    per_agent: dict[str, dict[str, Any]] = {}
    usage: list[dict[str, Any]] = []
    aliased = aliasing.enabled()
    for agent in agents:
        result = driver.evaluate_variant(
            VARIANT, agent, skill, None, [], fake_runner(routing_dir, fake, ids) if fake is not None else None,
            routing_dir, ledger, scenario_ids=ids, force_trials=1, description_overrides={skill: CANARY_DESCRIPTION},
        )
        if settings:
            settings_lib.annotate(result, settings)
        per_agent[agent] = judge_agent(result, ids)
        usage.append(result["usage"])
        aliased = bool(result.get("aliased"))
    total = compare._total(*usage) if usage else {"trials": 0, "tokens": 0, "cost_usd": 0.0, "latency_ms": 0}
    verdict = overall(per_agent)
    return {
        "skill": skill, "mode": "canary", "verdict": verdict, "exit_code": EXIT_CODES[verdict],
        "aliased": aliased, "threshold_percent": THRESHOLD_PERCENT, "positives": ids,
        "agents": per_agent, "usage": total, "offline": fake is not None,
        "settings": {a: {"model": settings[a]["model"], "effort": settings[a]["effort"]} for a in agents} if settings else {},
        "overridden": any(settings[a]["overridden"] for a in agents) if settings else False,
        **agents_lib.scope(agents),
    }


def render(doc: dict[str, Any]) -> list[str]:
    lines = [
        f"canary {doc['skill']}: {doc['verdict']} (aliased: {str(doc['aliased']).lower()}; "
        f"detected needs >= {doc['threshold_percent']}% of positive scenarios failing to route)"
    ]
    for agent, a in doc["agents"].items():
        lines.append(
            f"  {agent}: {a['verdict']} {len(a['failed'])}/{a['positives']} positive scenario(s) failed to route "
            f"fingerprint={a['fingerprint'] or '-'}" + (f" ({a['reason']})" if a["reason"] else "")
        )
    if doc["verdict"] == MISSED and not doc["aliased"]:
        lines.append(NAME_DRIVEN_NOTE)
    use = doc["usage"]
    lines.append(f"measured cost: ${use['cost_usd']:.4f} ({use['trials']} trials, {use['tokens']} tokens)")
    return lines


@runner.guarded
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skill")
    parser.add_argument("--agent", action="append", help="claude or codex; repeat or comma-separate (default: both)")
    parser.add_argument("--alias", choices=sorted(ALIAS_CHOICES), default="default", help="force skill aliasing on or off")
    parser.add_argument("--fake-results", type=Path, help="offline mode: JSON {agent: {scenario id: routed}}; no provider calls")
    args = parser.parse_args(argv[1:])
    forced = ALIAS_CHOICES[args.alias]
    if forced is not None:
        os.environ[aliasing.ENV_VAR] = forced
    try:
        agents = agents_lib.parse_agents(args.agent)
        settings = settings_lib.load()
        aliasing.enabled()
        fake = json.loads(args.fake_results.read_text()) if args.fake_results else None
        if warning := settings_lib.warning(settings):
            print(warning, file=sys.stderr)
        doc = run_canary(args.skill, agents, fake=fake, settings=settings)
    except (ValueError, OSError, workspaces.WorkspaceIntegrityError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return runner.HARNESS_ERROR
    runner.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (runner.REPORTS_DIR / f"canary-{args.skill}.canary.json").write_text(json.dumps(doc, indent=2) + "\n")
    print("\n".join(render(doc)))
    return doc["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
