"""Compare a skill's routing in the PR (candidate) with its merge-base (control), per host.

    python scripts/run_routing_comparison.py <skill> [--base REF]    (REF defaults to origin/main)

Two isolated workspaces are materialized under `.tmp/routing/{candidate,control}/<host>`:
candidate skills come from the working tree, control skills from `git merge-base REF HEAD`.
Both runs use the same scenarios, host configs, models, tools, and trial counts; only the
workspace differs. Reports land in `.tmp/routing/reports/{candidate,control}/`, and the
comparison in `.tmp/routing/reports/<host>-<skill>.comparison.json` (shape documented in
routing_compare.py). No score baseline is stored anywhere.

A skill absent at the merge base is new: control is skipped, the scenario minimums are
enforced as scenario validation, and the candidate is judged on absolute thresholds.

Exit codes are tabulated in docs/testing.md; scenario validation failures (including the new-skill
minimums) and unexpected exceptions exit 2 before any provider call. For a modified skill the
state is the candidate's own; deltas are reported, not gated.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import check_repo
import prepare_routing_workspace as workspaces
import routing_ceilings as ceilings
import routing_compare as compare
import routing_results as results
import run_routing_eval as runner
import select_changed
import validate_routing_scenarios as scenarios

ROUTING_DIR = check_repo.REPO_ROOT / ".tmp" / "routing"
VARIANTS = ("candidate", "control")


def merge_base(base: str) -> str:
    out = subprocess.run(
        ["git", "merge-base", base, "HEAD"], cwd=check_repo.REPO_ROOT, capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        raise ValueError(f"cannot find merge base of {base} and HEAD: {out.stderr.strip()}")
    return out.stdout.strip()


def skills_at(ref: str) -> set[str]:
    catalog, _ = select_changed.load_catalog(check_repo.REPO_ROOT, ref)
    return {skill.name for skill in catalog.values()}


def evaluate_variant(
    variant: str,
    host: str,
    skill: str,
    ref: str | None,
    validation_errors: list[str],
    run: runner.PromptfooRunner | None = None,
    routing_dir: Path | None = None,
    ledger: ceilings.Ledger | None = None,
) -> dict[str, Any]:
    """Materialize one variant's workspace for `host` and reduce its routing run.

    The workspace root is handed to the Promptfoo configs through ROUTING_WORKSPACE_ROOT;
    nothing else differs between variants. `ref` None means the working tree.
    """
    routing_dir = routing_dir or ROUTING_DIR
    root = routing_dir / variant
    if not validation_errors:
        workspaces.prepare_workspace(root / host, host, ref)
    ledger = ledger or ceilings.Ledger(ceilings.Ceilings.from_env())
    run = run or (lambda h, s, report, pattern: runner.run_promptfoo(
        h, s, report, pattern, env={"ROUTING_WORKSPACE_ROOT": str(root)}, ledger=ledger
    ))
    return runner.evaluate_host(
        host, skill, run, reports_dir=routing_dir / "reports" / variant, validation_errors=validation_errors, ledger=ledger
    )


def usage_note(doc: dict[str, Any]) -> str:
    use = doc["usage"]
    return f" tokens={use['tokens']} cost=${use['cost_usd']:.4f} latency={use['latency_ms'] / 1000:.1f}s" + (
        f" BREACH: {'; '.join(ceilings.describe(b) for b in doc['breaches'])}" if doc["breaches"] else ""
    )


def describe(doc: dict[str, Any]) -> str:
    return _describe(doc) + usage_note(doc)


def _describe(doc: dict[str, Any]) -> str:
    if doc["mode"] == "new_skill":
        parts = [
            f"{name}={c['passes']}/{c['trials']} (need {c['required']:.0%}, {'met' if c['met'] else 'NOT met'})"
            for name, c in doc["expectations"].items()
        ]
        return f"{doc['host']}: {doc['state']}{'' if doc['complete'] else ' [incomplete]'} new skill, control skipped: " + ", ".join(parts)
    agg = doc["aggregate"]
    fmt = lambda s: "n/a" if s["rate"] is None else f"{s['passes']}/{s['trials']}"  # noqa: E731
    delta = "n/a" if agg["delta"] is None else f"{agg['delta']:+.2f}"
    return (
        f"{doc['host']}: {doc['state']}{'' if doc['complete'] else ' [incomplete]'} "
        f"candidate {fmt(agg['candidate'])} control {fmt(agg['control'])} delta {delta}"
    )


@runner.guarded
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skill")
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args(argv[1:])
    skill = args.skill
    try:
        base = merge_base(args.base)
        known = scenarios.known_skill_names()
        if skill not in known:
            raise ValueError(f"unknown skill {skill!r}")
        is_new = skill not in skills_at(base)
        validation_errors = scenarios.validate_scenarios(scenarios.SCENARIOS_DIR, known)
        if is_new:
            validation_errors += scenarios.new_skill_minimum_errors(
                scenarios.SCENARIOS_DIR, skill, scenarios.adjacent_skills(skill)
            )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return runner.HARNESS_ERROR
    if validation_errors:
        for error in validation_errors:
            print(f"ERROR: scenario_validation: {error}", file=sys.stderr)
        return runner.HARNESS_ERROR

    try:
        ledger = ceilings.Ledger(ceilings.Ceilings.from_env())  # one budget for candidate, control, and retries
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return runner.HARNESS_ERROR
    tags = {s["id"]: s.get("tags") or [] for s in scenarios.target_scenarios(scenarios.SCENARIOS_DIR, skill)}
    print(f"{skill}: {'new skill (no control)' if is_new else 'modified'}; merge base {base[:12]}")
    docs = []
    for host in results.HOSTS:
        candidate = evaluate_variant("candidate", host, skill, None, validation_errors, ledger=ledger)
        if is_new:
            doc = compare.evaluate_new_skill(candidate, tags)
        else:
            control = evaluate_variant("control", host, skill, base, validation_errors, ledger=ledger)
            doc = compare.compare_host(candidate, control)
        docs.append(doc)

    runner.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        (runner.REPORTS_DIR / f"{doc['host']}-{skill}.comparison.json").write_text(json.dumps(doc, indent=2) + "\n")
        print(describe(doc))
    combined = results.combine_hosts(docs)
    (runner.REPORTS_DIR / f"{skill}.comparison-summary.json").write_text(json.dumps(combined, indent=2) + "\n")
    print(f"overall: {combined['state']}")
    return runner.EXIT_CODES[combined["state"]]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
