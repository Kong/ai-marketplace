"""Compare a skill's routing in the PR (candidate) with its merge-base (control), per agent.

    python scripts/run_routing_comparison.py <skill> [--base REF] [--agent claude|codex ...] [--confirm]
    python scripts/run_routing_comparison.py <skill> --gate [--scenarios id,id,...] [--base REF] [--agent ...]
    (REF defaults to origin/main; --agent defaults to both and a subset run is marked partial)

Two isolated workspaces are materialized under `.tmp/routing/{candidate,control}/<agent>`:
candidate skills come from the working tree, control skills from `git merge-base REF HEAD`.
Both runs use the same scenarios, agent configs, models, tools, and trial counts; only the
workspace differs. Reports land in `.tmp/routing/reports/{candidate,control}/`, and the
comparison in `.tmp/routing/reports/<agent>-<skill>.comparison.json` (shape documented in
routing_compare.py). No score baseline is stored anywhere.

`--confirm` (the merge gate) re-runs just the scenarios that regressed (pass on control, fail on
candidate) at 3 trials on both sides, in the same workspaces and under the same ceilings, and records
the result as `confirmation` in the comparison document (routing_compare.with_confirmation).

`--gate` (the merge gate and manual CI runs) is the lazy-control path for a modified skill. The
candidate runs the selected scenarios (`--scenarios`, default: the skill's reverse-index set from
routing_selection.py) at one trial each. Only scenarios that failed are confirmed: the candidate again
at max(the scenario's `trials`, CONFIRM_TRIALS=3), then the control, at the same trials, for those still failing. The
control never runs for a scenario that passed, and control workspaces are built only when needed.
The result is a `lazy_comparison` document (routing_compare.lazy_compare) with no aggregate deltas; the
full candidate-vs-control run without `--gate` keeps its per-scenario and aggregate deltas.

A skill absent at the merge base is new: control is skipped, the scenario minimums are
enforced as scenario validation, and the candidate is judged on absolute thresholds.

Exit codes are tabulated in docs/testing.md; scenario validation failures (including the new-skill
minimums) and unexpected exceptions exit 2 before any provider call. For a modified skill the
state is the candidate's own; deltas are reported here and judged regression-only by routing_gate.py.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

import check_repo
import routing_agents as agents_lib
import prepare_routing_workspace as workspaces
import routing_listing as listing_presets
import routing_ceilings as ceilings
import routing_compare as compare
import routing_results as results
import routing_selection as selection
import routing_settings as settings_lib
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
    agent: str,
    skill: str,
    ref: str | None,
    validation_errors: list[str],
    run: runner.PromptfooRunner | None = None,
    routing_dir: Path | None = None,
    ledger: ceilings.Ledger | None = None,
    confirm: list[str] | None = None,
    scenario_ids: list[str] | None = None,
    force_trials: int | None = None,
    confirm_trials: int | None = compare.CONFIRM_TRIALS,
    min_trials: int | None = None,
    prepare: bool | None = None,
    description_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Materialize one variant's workspace for `agent` and reduce its routing run.

    The workspace root is handed to the Promptfoo configs through ROUTING_WORKSPACE_ROOT;
    nothing else differs between variants. `ref` None means the working tree. `confirm`
    re-runs only those scenarios in the already prepared workspace (reports under
    `<variant>-confirm/`, same ledger so ceilings still apply) at `confirm_trials` trials, or at
    each scenario's own `trials` when that is None, raised to `min_trials` when given (the gate: at least
    CONFIRM_TRIALS, so a `trials: 1` sibling is never confirmed by one flaky trial). `scenario_ids` selects scenarios across files
    (ROUTING_SCENARIO_IDS); `force_trials` forces the trial count of a first pass. `prepare`
    defaults to building the workspace unless this is a confirmation; the gate builds the control's
    workspace at its first and only use. A built or reused workspace is always verified against its
    source (`WorkspaceIntegrityError`, exit 2 in the scripts) and its fingerprint is recorded
    in the result. `description_overrides` is for the canary only.
    """
    routing_dir = routing_dir or ROUTING_DIR
    root = routing_dir / variant
    workspace = None
    if not validation_errors:
        if confirm is None if prepare is None else prepare:
            workspace = workspaces.prepare_workspace(root / agent, agent, ref, description_overrides=description_overrides)
        else:
            workspace = workspaces.verify_workspace(root / agent, agent, ref, description_overrides=description_overrides)
        print(f"{agent} {variant}: workspace listing={workspace.listing} fingerprint={workspace.fingerprint}")
    ledger = ledger or ceilings.Ledger(ceilings.Ceilings.from_env())
    env = {"ROUTING_WORKSPACE_ROOT": str(root)}
    if scenario_ids:
        env["ROUTING_SCENARIO_IDS"] = ",".join(scenario_ids)
    if confirm is not None:
        env.update({
            "ROUTING_FORCE_TRIALS": str(confirm_trials) if confirm_trials else "", "ROUTING_MAX_TRIALS": "",
            "ROUTING_MIN_TRIALS": str(min_trials) if min_trials else "",
        })
    elif force_trials:
        env.update({"ROUTING_FORCE_TRIALS": str(force_trials), "ROUTING_MAX_TRIALS": ""})
    run = run or (lambda h, s, report, pattern: runner.run_promptfoo(h, s, report, pattern, env=env, ledger=ledger))
    return runner.evaluate_agent(
        agent, skill, run,
        reports_dir=routing_dir / "reports" / (f"{variant}-confirm" if confirm is not None else variant),
        validation_errors=validation_errors, ledger=ledger,
        pattern=runner.scenario_pattern(confirm) if confirm else None, workspace=workspace,
    )


def confirm_regressions(
    doc: dict[str, Any], agent: str, skill: str, base: str, ledger: ceilings.Ledger,
    evaluate: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Re-run this comparison's regressed scenarios on candidate and control; no regressions, no spend."""
    evaluate = evaluate or evaluate_variant
    ids = compare.regressions(doc) if doc["complete"] and doc["mode"] == "comparison" else []
    if not ids:
        return doc
    print(f"{agent}: confirming {len(ids)} regressed scenario(s) at {compare.CONFIRM_TRIALS} trials: {', '.join(ids)}")
    candidate = evaluate("candidate", agent, skill, None, [], ledger=ledger, confirm=ids)
    control = evaluate("control", agent, skill, base, [], ledger=ledger, confirm=ids)
    return compare.with_confirmation(doc, candidate, control)


def gate_agent(
    agent: str, skill: str, base: str, scenario_ids: list[str], ledger: ceilings.Ledger,
    evaluate: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Lazy-control gate for one agent of a modified skill.

    First pass: candidate only, one trial per scenario. Failed scenarios are re-run on the candidate
    at max(own trials, 3); the control runs only for those still failing. Passing scenarios cost one
    candidate trial and nothing else.
    """
    evaluate = evaluate or evaluate_variant
    initial = evaluate("candidate", agent, skill, None, [], ledger=ledger, scenario_ids=scenario_ids, force_trials=1)
    failed = compare.failed_scenarios(initial) if initial["complete"] else []
    if not failed:
        return compare.lazy_compare(initial)
    print(f"{agent}: {len(failed)} of {len(scenario_ids)} scenario(s) failed the one-trial pass; confirming on candidate: {', '.join(failed)}")
    candidate = evaluate("candidate", agent, skill, None, [], ledger=ledger, scenario_ids=scenario_ids, confirm=failed, confirm_trials=None, min_trials=compare.CONFIRM_TRIALS)
    still = compare.failed_scenarios(candidate) if candidate["complete"] else []
    control = None
    if still:
        print(f"{agent}: {len(still)} still failing; running the control on them: {', '.join(still)}")
        control = evaluate(
            "control", agent, skill, base, [], ledger=ledger, scenario_ids=scenario_ids, confirm=still, confirm_trials=None, min_trials=compare.CONFIRM_TRIALS, prepare=True
        )
    return compare.lazy_compare(initial, candidate, control)


def usage_note(doc: dict[str, Any]) -> str:
    use = doc["usage"]
    return f" tokens={use['tokens']} cost=${use['cost_usd']:.4f} latency={use['latency_ms'] / 1000:.1f}s" + (
        f" BREACH: {'; '.join(ceilings.describe(b) for b in doc['breaches'])}" if doc["breaches"] else ""
    )


def describe(doc: dict[str, Any]) -> str:
    return _describe(doc) + confirmation_note(doc) + usage_note(doc)


def confirmation_note(doc: dict[str, Any]) -> str:
    conf = doc.get("confirmation")
    if not conf or doc["mode"] == compare.LAZY:
        return ""
    confirmed = [r["id"] for r in conf["scenarios"] if r["confirmed"]]
    return f" confirmation[{conf['trials']} trials: {conf['state']}; confirmed={','.join(confirmed) or '-'}]"


def _describe(doc: dict[str, Any]) -> str:
    config = f" [{settings_lib.describe(doc['settings'])}]" if "settings" in doc else ""
    config += f" listing={doc.get('listing', listing_presets.DEFAULT)}"
    return _describe_state(doc).replace(":", f"{config}:", 1)


def _describe_state(doc: dict[str, Any]) -> str:
    if doc["mode"] == "new_skill":
        parts = [
            f"{name}={c['passes']}/{c['trials']} (need {c['required']:.0%}, {'met' if c['met'] else 'NOT met'})"
            for name, c in doc["expectations"].items()
        ]
        return f"{doc['agent']}: {doc['state']}{'' if doc['complete'] else ' [incomplete]'} new skill, control skipped: " + ", ".join(parts)
    if doc["mode"] == compare.LAZY:
        total = len(doc["scenarios"])
        conf = doc["confirmation"]
        outcomes = {}
        for row in (conf or {}).get("scenarios", []):
            outcomes.setdefault(row["outcome"], []).append(row["id"])
        detail = "; ".join(f"{name}={','.join(ids)}" for name, ids in outcomes.items()) or "-"
        return (
            f"{doc['agent']}: {doc['state']}{'' if doc['complete'] else ' [incomplete]'} gate, control only on failures: "
            f"first pass {total - len(doc['failed'])}/{total} scenarios passed; confirmation[{(conf or {}).get('state', 'not needed')}: {detail}]"
        )
    agg = doc["aggregate"]
    fmt = lambda s: "n/a" if s["rate"] is None else f"{s['passes']}/{s['trials']}"  # noqa: E731
    delta = "n/a" if agg["delta"] is None else f"{agg['delta']:+.2f}"
    return (
        f"{doc['agent']}: {doc['state']}{'' if doc['complete'] else ' [incomplete]'} "
        f"candidate {fmt(agg['candidate'])} control {fmt(agg['control'])} delta {delta}"
    )


def run_agent(
    agent: str, skill: str, base: str, args: argparse.Namespace, is_new: bool, scenario_ids: list[str],
    validation_errors: list[str], ledger: ceilings.Ledger, tags: dict[str, list[str]],
    settings: dict[str, dict[str, Any]], agents: tuple[str, ...],
) -> dict[str, Any]:
    """One agent's comparison document: gate (lazy control), new skill (absolute), or full comparison."""
    if args.gate and not is_new:
        doc = gate_agent(agent, skill, base, scenario_ids, ledger)
    else:
        candidate = evaluate_variant("candidate", agent, skill, None, validation_errors, ledger=ledger)
        if is_new:
            doc = compare.evaluate_new_skill(candidate, tags)
        else:
            control = evaluate_variant("control", agent, skill, base, validation_errors, ledger=ledger)
            doc = compare.compare_agent(candidate, control)
            if args.confirm:
                doc = confirm_regressions(doc, agent, skill, base, ledger)
    settings_lib.annotate(doc, settings)
    doc.update(agents_lib.scope(agents))
    return doc


@runner.guarded
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skill")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--confirm", action="store_true", help="re-run regressed scenarios at 3 trials on both sides")
    parser.add_argument("--gate", action="store_true", help="lazy control: candidate at 1 trial, control only for scenarios that fail and re-fail")
    parser.add_argument("--scenarios", help="comma-separated scenario ids to run (with --gate); default: the skill's reverse-index set")
    parser.add_argument("--agent", action="append", help="claude or codex; repeat or comma-separate (default: both)")
    args = parser.parse_args(argv[1:])
    skill = args.skill
    if args.gate and args.confirm:
        print("ERROR: --gate always confirms failures; do not combine it with --confirm", file=sys.stderr)
        return runner.HARNESS_ERROR
    if args.scenarios and not args.gate:
        print("ERROR: --scenarios needs --gate", file=sys.stderr)
        return runner.HARNESS_ERROR
    try:
        agents = agents_lib.parse_agents(args.agent)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return runner.HARNESS_ERROR
    if agents_lib.is_partial(agents):
        print(f"WARNING: partial run, {', '.join(agents)} only; not a both-agent result", file=sys.stderr)
    try:
        # Candidate and control inherit the same environment, so both use these effective settings.
        settings = settings_lib.load()
        listing_presets.check_agents(listing_presets.selected(), agents)  # fail fast on an invalid ROUTING_SKILL_LISTING
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return runner.HARNESS_ERROR
    if warning := settings_lib.warning(settings):
        print(warning, file=sys.stderr)
    try:
        base = merge_base(args.base)
        known = scenarios.known_skill_names()
        if skill not in known:
            raise ValueError(f"unknown skill {skill!r}")
        is_new = skill not in skills_at(base)
        validation_errors = scenarios.validate_scenarios(scenarios.SCENARIOS_DIR, known)
        scenario_ids: list[str] = []
        if args.gate and not is_new:
            corpus = selection.load_corpus(scenarios.SCENARIOS_DIR)
            scenario_ids = [i for i in (args.scenarios or "").split(",") if i] or selection.evaluation_set(corpus, skill)[0]
            validation_errors += [f"unknown scenario id {i!r}" for i in scenario_ids if i not in {sc.id for sc in corpus}]
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
    docs: list[dict[str, Any]] = []
    try:
        for agent in agents:
            docs.append(run_agent(agent, skill, base, args, is_new, scenario_ids, validation_errors, ledger, tags, settings, agents))
    except workspaces.WorkspaceIntegrityError as exc:
        print(f"ERROR: workspace_integrity: {exc}", file=sys.stderr)
        return runner.HARNESS_ERROR

    runner.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        (runner.REPORTS_DIR / f"{doc['agent']}-{skill}.comparison.json").write_text(json.dumps(doc, indent=2) + "\n")
        print(describe(doc))
    combined = results.combine_agents(docs, required=agents)
    (runner.REPORTS_DIR / f"{skill}.comparison-summary.json").write_text(json.dumps(combined, indent=2) + "\n")
    print(f"overall: {agents_lib.label(combined['state'], agents)}")
    return runner.EXIT_CODES[combined["state"]]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
