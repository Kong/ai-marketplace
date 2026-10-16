"""Name-only ablation: which of a skill's scenarios actually depend on the descriptions?

    python scripts/routing_ablation.py <skill> [--agent claude] [--fake-results FILE]

Runs the skill's OWN scenarios (every tag) on Claude at one trial each, twice and candidate only:
once with the `default` skill listing and once with the `name-only` listing preset, where Claude sees
skill names and no descriptions (routing_listing.py). The runs use the same runner, ceilings and
reducer as every other eval, in separate workspaces and report directories
(`.tmp/routing/ablation-default`, `.tmp/routing/ablation-name-only`). Each scenario is then classified:

    description_dependent   passes with the default listing, fails name-only: the description carries it
    name_solvable           passes both: the skill name alone is enough, so the scenario says nothing
                            about the description
    failing                 fails with the default listing (a routing failure, whatever name-only did)
    incomplete              an infrastructure error or ceiling breach left it undecided

Counts and percentages are reported overall and per scenario tag (positive, near-miss, sibling) as JSON
(`.tmp/routing/reports/ablation-<skill>.ablation.json`) and a table. Diagnostic only: it never feeds the
merge gate and a high name_solvable share is a finding, not a failure. Exit codes: 0 complete, 2 harness
or usage error (the preset is Claude only), 3 incomplete. See docs/testing.md#scenario-design-description-dependence.

`--fake-results FILE` is the offline mode for tests: no provider call is made. FILE maps a listing
(`default`, `name-only`) to {scenario id: passed true|false}; a scenario it omits passes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import routing_agents as agents_lib
import routing_ceilings as ceilings
import routing_compare as compare
import routing_listing as listing_presets
import routing_results as results
import routing_settings as settings_lib
import run_routing_comparison as driver
import run_routing_eval as runner
import prepare_routing_workspace as workspaces
import validate_routing_scenarios as scenarios

DESCRIPTION_DEPENDENT, NAME_SOLVABLE, FAILING, INCOMPLETE = "description_dependent", "name_solvable", "failing", "incomplete"
CLASSES = (DESCRIPTION_DEPENDENT, NAME_SOLVABLE, FAILING)
LISTINGS = (listing_presets.DEFAULT, listing_presets.NAME_ONLY)
AGENT = "claude"  # the name-only preset is a Claude setting; Codex has none
EXIT_OK, EXIT_INCOMPLETE = 0, 3


def own_scenarios(skill: str) -> list[dict[str, Any]]:
    """The skill's own scenarios, every tag, in file order."""
    return [s for s in scenarios.target_scenarios(scenarios.SCENARIOS_DIR, skill) if isinstance(s.get("id"), str)]


def variant(listing: str) -> str:
    return f"ablation-{listing}"


def classify(default_state: str | None, name_only_state: str | None) -> str:
    """Class of one scenario from its state (pass, routing_fail, infra_error or None) under each listing."""
    judged = (results.PASS, results.ROUTING_FAIL)
    if default_state == results.ROUTING_FAIL:
        return FAILING
    if default_state not in judged or name_only_state not in judged:
        return INCOMPLETE
    return NAME_SOLVABLE if name_only_state == results.PASS else DESCRIPTION_DEPENDENT


def _states(result: dict[str, Any]) -> dict[str, str]:
    return {s["id"]: s["state"] for s in result["scenarios"]}


def _counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    counts = {name: sum(r["class"] == name for r in rows) for name in (*CLASSES, INCOMPLETE)}
    percent = {name: round(100 * counts[name] / total, 1) if total else None for name in CLASSES}
    return {"total": total, **counts, "percent": percent}


def judge(scenario_rows: list[dict[str, Any]], tags: dict[str, list[str]], by_listing: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The ablation document body from the two listings' agent results; `tags` maps scenario id to its tags."""
    default, name_only = (_states(by_listing[name]) for name in LISTINGS)
    rows = [
        {
            "id": s["id"], "tags": tags[s["id"]], "default": default.get(s["id"]), "name_only": name_only.get(s["id"]),
            "class": classify(default.get(s["id"]), name_only.get(s["id"])),
        }
        for s in scenario_rows
    ]
    per_tag = {
        tag: _counts([r for r in rows if tag in r["tags"]])
        for tag in sorted({t for r in rows for t in r["tags"]})
    }
    complete = all(by_listing[name]["complete"] for name in LISTINGS) and all(r["class"] != INCOMPLETE for r in rows)
    return {"scenarios": rows, "counts": _counts(rows), "by_tag": per_tag, "complete": complete}


def fake_runner(fake: dict[str, dict[str, bool]], listing: str, rows: list[dict[str, Any]]) -> Any:
    """A Promptfoo runner replacement: one row per scenario, passed or not per `fake[listing]`."""
    def run(agent: str, skill: str, report: Path, pattern: str | None) -> tuple[str, list[dict[str, Any]]]:
        out = []
        for scenario in rows:
            sid, expect, forbid = scenario["id"], scenario.get("expect") or [], scenario.get("forbid") or []
            passed = bool(fake.get(listing, {}).get(sid, True))
            # Observed shapes: routing to a skill is a skillCalls entry; answering no skill is output NONE and no skillCalls.
            routed = (expect[0] if passed else None) if expect else (None if passed else forbid[0] if forbid else None)
            message = "ok" if passed else f"Missing required skill(s): {', '.join(expect)}. Actual skills: (none)"
            row = {
                "success": passed, "failureReason": 0 if passed else 1, "latencyMs": 1, "cost": 0.0,
                "gradingResult": {"pass": passed, "reason": message},
                "response": {
                    "output": routed or "NONE", "tokenUsage": {"total": 1},
                    "metadata": {"skillCalls": [{"name": routed}]} if routed else {},
                },
                "testCase": {
                    "description": f"{sid} | {agent} | trial 1/1",
                    "metadata": {"scenario": sid, "trial": 1, "trials": 1, "expected": expect, "forbidden": forbid},
                },
            }
            if not passed:
                row["error"] = message  # Promptfoo repeats an assertion failure in the row-level error
            out.append(row)
        return "", out
    return run


def run_ablation(
    skill: str, agents: tuple[str, ...] = (AGENT,), routing_dir: Path | None = None,
    fake: dict[str, dict[str, bool]] | None = None, ledger: ceilings.Ledger | None = None,
    settings: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the ablation for `skill` and return the ablation document."""
    listing_presets.check_agents(listing_presets.NAME_ONLY, agents)
    routing_dir = routing_dir or driver.ROUTING_DIR
    if skill not in scenarios.known_skill_names():
        raise ValueError(f"unknown skill {skill!r}")
    rows = own_scenarios(skill)
    if not rows:
        raise ValueError(f"skill {skill!r} has no scenarios of its own to run the ablation on")
    ids = [s["id"] for s in rows]
    tags = {s["id"]: [str(t) for t in s.get("tags") or []] for s in rows}
    ledger = ledger or ceilings.Ledger(ceilings.Ceilings.from_env())
    by_listing: dict[str, dict[str, Any]] = {}
    for listing in LISTINGS:
        result = driver.evaluate_variant(
            variant(listing), AGENT, skill, None, [], fake_runner(fake, listing, rows) if fake is not None else None,
            routing_dir, ledger, scenario_ids=ids, force_trials=1, listing=listing,
        )
        if settings:
            settings_lib.annotate(result, settings)
        by_listing[listing] = result
    body = judge(rows, tags, by_listing)
    usage = compare._total(*(r["usage"] for r in by_listing.values()))
    complete = body["complete"]
    return {
        "skill": skill, "mode": "ablation", "agent": AGENT, "complete": complete,
        "exit_code": EXIT_OK if complete else EXIT_INCOMPLETE, "trials_per_scenario": 1, **body,
        "listings": {
            name: {
                "state": r["state"], "complete": r["complete"], "reason": r["reason"] if not r["complete"] else None,
                "fingerprint": r.get("fingerprint"), "usage": r["usage"],
            }
            for name, r in by_listing.items()
        },
        "usage": usage, "offline": fake is not None,
        "settings": {AGENT: {"model": settings[AGENT]["model"], "effort": settings[AGENT]["effort"]}} if settings else {},
        "overridden": bool(settings and settings[AGENT]["overridden"]),
        **agents_lib.scope(agents),
    }


def _row(label: str, c: dict[str, Any]) -> str:
    pct = c["percent"]
    cell = lambda name: f"{c[name]} ({pct[name]:.0f}%)" if pct[name] is not None else "-"  # noqa: E731
    return f"| {label} | {c['total']} | {cell(DESCRIPTION_DEPENDENT)} | {cell(NAME_SOLVABLE)} | {cell(FAILING)} | {c[INCOMPLETE]} |"


def render(doc: dict[str, Any]) -> list[str]:
    lines = [
        f"ablation {doc['skill']} ({doc['agent']}, 1 trial per scenario, default vs name-only listing): "
        f"{'complete' if doc['complete'] else 'INCOMPLETE'}",
        "",
        "| Tag | Scenarios | description_dependent | name_solvable | failing | incomplete |",
        "| --- | --- | --- | --- | --- | --- |",
        _row("all", doc["counts"]),
        *(_row(tag, c) for tag, c in doc["by_tag"].items()),
        "",
    ]
    for name in (DESCRIPTION_DEPENDENT, FAILING, INCOMPLETE):
        ids = [r["id"] for r in doc["scenarios"] if r["class"] == name]
        if ids:
            lines.append(f"{name}: {', '.join(ids)}")
    for name, listing in doc["listings"].items():
        if not listing["complete"]:
            lines.append(f"{name} listing incomplete: {listing['reason']}")
    use = doc["usage"]
    lines.append(f"measured cost: ${use['cost_usd']:.4f} ({use['trials']} trials, {use['tokens']} tokens)")
    return lines


@runner.guarded
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skill")
    parser.add_argument("--agent", action="append", help="claude (the only agent with a name-only listing)")
    parser.add_argument("--fake-results", type=Path, help="offline mode: JSON {listing: {scenario id: passed}}; no provider calls")
    args = parser.parse_args(argv[1:])
    try:
        agents = agents_lib.parse_agents(args.agent or [AGENT])
        listing_presets.check_agents(listing_presets.NAME_ONLY, agents)
        settings = settings_lib.load()
        fake = json.loads(args.fake_results.read_text()) if args.fake_results else None
        if warning := settings_lib.warning(settings):
            print(warning, file=sys.stderr)
        doc = run_ablation(args.skill, agents, fake=fake, settings=settings)
    except (ValueError, OSError, workspaces.WorkspaceIntegrityError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return runner.HARNESS_ERROR
    runner.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (runner.REPORTS_DIR / f"ablation-{args.skill}.ablation.json").write_text(json.dumps(doc, indent=2) + "\n")
    print("\n".join(render(doc)))
    return doc["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
