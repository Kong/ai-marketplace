"""Orchestration for .github/workflows/skill-evals.yml, kept out of YAML so it is testable offline.

    python scripts/routing_ci.py select      select job: no secrets, no provider calls
    python scripts/routing_ci.py evaluate    evaluate job: runs the evals for one matrix entry

Inputs arrive only through environment variables (never interpolated into a script).

select:   EVENT_NAME, BASE_SHA, HEAD_SHA (pull_request and merge_group), MODE_INPUT, SKILL_INPUT,
          AGENTS_INPUT, LISTING_INPUT (workflow_dispatch). Writes `skills` (matrix JSON
          `[{skill, mode, scenarios, new, count}]`), `has_skills`, `agents` and `skipped` (JSON `[{skill, reason}]`, for the gate summary) to $GITHUB_OUTPUT and a
          no-spend preview to $GITHUB_STEP_SUMMARY. A skill is selected only when its routing surface
          changed or its scenarios were edited (routing_selection.py); `scenarios` is the comma-separated
          evaluation set. mode is `gate` (lazy control: candidate at 1 trial, control only for failures;
          a new skill runs absolute thresholds) or `snapshot` (manual `all`, or a manual skill run on a
          ref with nothing beyond main). The preview also prints trials and a rough cost range
          (routing_cost.py) and the skills skipped because their routing surface did not change.
          On pull_request a selection problem (for example a new skill below the scenario
          minimums) is a warning; in the merge queue and manual runs it fails the job.
          Dispatch mode `canary` (one skill; scripts/routing_canary.py) selects that skill's own positive
          scenarios; it is the eval of the eval and never part of the merge gate.
evaluate: SKILL, MODE, SCENARIOS, BASE_REF, REQUESTED_AGENTS, EVENT_NAME, MODE_INPUT and
          LISTING_INPUT (a skill-listing preset, claude only, manual skill/changed/canary runs only), plus the provider keys and ROUTING_* ceiling
          variables. Runs only the requested agents that have a key (routing_ci_agents.py), with
          the lazy-control confirmation, and writes `.tmp/routing/reports/<skill>.run.json`
          for routing_gate.py. A routing_fail or infra_error is a recorded result, not a job
          failure (the gate job decides); exit 2 and unknown codes are harness errors and fail.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

import check_repo
import routing_agents as agents_lib
import routing_canary as canary
import routing_ceilings as ceilings
import routing_ci_agents as ci_agents
import routing_cost as cost
import routing_listing as listing_presets
import routing_selection as selection
import routing_surface as surface
import routing_targets as targets
import select_changed
import validate_routing_scenarios as scenarios

SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MODES = ("skill", "changed", "all", "canary")
RUN_MODES = (selection.GATE_MODE, "compare", "snapshot", "canary")
RESULT_EXIT_CODES = (0, 1, 3)
# Variables that would change what CI measures; never let them reach the eval processes.
SCRUBBED = ("ROUTING_CODEX_MODEL", "ROUTING_CODEX_EFFORT", "ROUTING_CLAUDE_MODEL", "ROUTING_CLAUDE_EFFORT", "ROUTING_FORCE_TRIALS", "ROUTING_MAX_TRIALS", "ROUTING_MIN_TRIALS", "ROUTING_SCENARIO_IDS", listing_presets.ENV_VAR)
# Dispatch modes that accept a skill-listing preset; `all` ignores it (both agents, and a full suite is not an experiment).
LISTING_MODES = ("skill", "changed", "canary")


class CiError(Exception):
    """Invalid CI input or selection; the job fails with exit 2."""


def dispatch_listing(env: Mapping[str, str]) -> tuple[str, str | None]:
    """The skill-listing preset a run applies and a notice when the input is ignored.

    Only a manual dispatch in a LISTING_MODES mode applies LISTING_INPUT (an allowlisted preset name,
    never settings content); every other event, and mode `all`, runs with the default. An invalid
    value is a CiError.
    """
    if env.get("EVENT_NAME") != "workflow_dispatch":
        return listing_presets.DEFAULT, None  # the input is not even parsed outside a manual dispatch
    try:
        requested = listing_presets.parse_setting(env.get("LISTING_INPUT"))
    except ValueError as exc:
        raise CiError(str(exc).replace(listing_presets.ENV_VAR, "listing")) from None
    if requested == listing_presets.DEFAULT:
        return requested, None
    if env.get("MODE_INPUT") not in LISTING_MODES:
        return listing_presets.DEFAULT, f"listing={requested} is ignored for mode={env.get('MODE_INPUT')}; this run uses the default listing"
    return requested, None


def _git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True).returncode == 0


def snapshot_entry(skill: str) -> dict[str, Any]:
    ids = [sc.id for sc in selection.load_corpus(scenarios.SCENARIOS_DIR) if sc.owner == skill]
    return {"skill": skill, "mode": "snapshot", "scenarios": ",".join(ids), "new": False, "count": len(ids)}


def select_matrix(env: Mapping[str, str], repo: Path = check_repo.REPO_ROOT) -> dict[str, Any]:
    """Resolve the event to a matrix of {skill, mode, scenarios, ...}, the requested agents, notes and a diff preview."""
    event = env.get("EVENT_NAME", "")
    notes: list[str] = []
    warnings: list[str] = []
    skipped: list[dict[str, str]] = []
    diff: dict[str, Any] | None = None
    covered = targets.covered_skills()
    try:
        agents = list(agents_lib.parse_agents([env.get("AGENTS_INPUT", "")]))
    except ValueError as exc:
        raise CiError(str(exc)) from None

    def from_selection(chosen: dict[str, Any]) -> list[dict[str, Any]]:
        nonlocal diff, notes, skipped
        diff, notes, skipped = chosen["diff"], chosen["notes"], chosen["skipped"]
        return chosen["entries"]

    if event == "workflow_dispatch":
        mode = env.get("MODE_INPUT", "")
        if mode not in MODES:
            raise CiError(f"mode must be one of {', '.join(MODES)}")
        skill = env.get("SKILL_INPUT", "")
        if (mode in ("skill", "canary")) != bool(skill):
            raise CiError("`skill` is required for mode=skill and mode=canary and not accepted otherwise")
        if skill and not SKILL_NAME.match(skill):
            raise CiError("skill must be a kebab-case skill name")
        try:
            if mode == "canary":
                ids = canary.positive_scenarios(skill) if skill in covered else []
                if not ids:
                    raise ValueError(f"skill {skill!r} has no positive scenarios of its own to run the canary on; covered: {sorted(covered)}")
                matrix = [{"skill": skill, "mode": "canary", "scenarios": ",".join(ids), "new": False, "count": len(ids)}]
            elif mode == "all":
                matrix = [snapshot_entry(name) for name in sorted(covered)]
            elif mode == "skill":
                if skill not in covered:
                    raise ValueError(f"no routing scenarios for skill {skill!r}; covered: {sorted(covered)}")
                # A ref with nothing beyond main has no control worth paying for: judge it as a snapshot.
                if _git_ok(repo, "merge-base", "--is-ancestor", "HEAD", "origin/main"):
                    matrix = [snapshot_entry(skill)]
                else:
                    matrix = from_selection(selection.skill_entry(repo, skill, targets.default_base(repo)))
            else:
                matrix = from_selection(selection.select_gate(repo, targets.default_base(repo)))
        except (ValueError, select_changed.SelectionError) as exc:
            raise CiError(str(exc)) from None
    elif event in ("pull_request", "merge_group"):
        base, head = env.get("BASE_SHA", ""), env.get("HEAD_SHA", "")
        if not base or not head:
            raise CiError(f"{event} needs BASE_SHA and HEAD_SHA")
        if head_sha(repo) != head:
            raise CiError("checked-out HEAD is not the event head SHA")
        try:
            matrix = from_selection(selection.select_gate(repo, base))
        except (ValueError, select_changed.SelectionError) as exc:
            if event == "merge_group":
                raise CiError(str(exc)) from None
            matrix, warnings = [], [f"selection problem (blocks the merge queue, advisory here): {exc}"]
    else:
        raise CiError(f"unsupported event {event!r}")
    listing, notice = dispatch_listing(env)
    if notice:
        notes.append(notice)
    try:
        listing_presets.check_agents(listing, agents)
    except ValueError as exc:
        raise CiError(str(exc).replace(listing_presets.ENV_VAR, "listing") + "; set agents=claude") from None
    return {"matrix": matrix, "agents": agents, "notes": notes, "warnings": warnings, "diff": diff, "event": event, "skipped": skipped}


def head_sha(repo: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=False)
    return out.stdout.strip()


def plan(matrix: list[dict[str, Any]]) -> list[dict[str, int]]:
    trials = {sc.id: sc.trials for sc in selection.load_corpus(scenarios.SCENARIOS_DIR)}
    return [cost.entry_trials(entry, trials, trials) for entry in matrix]


def preview(selection_result: Mapping[str, Any], env: Mapping[str, str]) -> str:
    matrix, agents, event = selection_result["matrix"], selection_result["agents"], selection_result["event"]
    lines = ["### Routing eval preview (no provider calls were made)", ""]
    if event == "pull_request":
        lines += ["Pull request pushes only validate and preview. The relevant evals run once in the merge queue.", ""]
    if matrix:
        plans = plan(matrix)
        lines += ["| Skill | Run | Scenarios | Initial trials per agent | Worst-case trials per agent |", "| --- | --- | --- | --- | --- |"]
        lines += [
            f"| {e['skill']} | {e['mode']}{' (new skill, absolute thresholds)' if e.get('new') else ''} | {p['scenarios']} | {p['initial']} | {p['worst']} |"
            for e, p in zip(matrix, plans)
        ]
        lines += [""] + cost.lines(plans, agents)
        ceiling = ceilings.Ceilings.from_env(env).max_cost_usd
        lines.append(f"Hard bound: {len(matrix)} run(s) x {len(agents)} agent(s) x the per-run cost ceiling = ${len(matrix) * len(agents) * ceiling:.2f}.")
        if any(e["mode"] == selection.GATE_MODE and not e.get("new") for e in matrix):
            lines += ["", "Gate runs use lazy control: one candidate trial per scenario, and the control (with the candidate re-run at max(its trials, 3)) only for scenarios that fail."]
    else:
        lines.append("No skill with a changed routing surface and no edited scenario; nothing to evaluate and no provider calls will be made.")
    if selection_result["skipped"]:
        lines += ["", "Skipped (routing surface unchanged or nothing to run):"]
        lines += [f"- {item['skill']}: {item['reason']}" for item in selection_result["skipped"]]
    lines += [""] if selection_result["notes"] or selection_result["warnings"] else []
    lines += [f"- NOTE: {note}" for note in selection_result["notes"]] + [f"- WARNING: {w}" for w in selection_result["warnings"]]
    diff = selection_result["diff"]
    if diff is not None:
        lines += ["", f"Adjacent skills (context only; their scenarios run only when they name a selected skill): {', '.join(diff['adjacent']) or 'none'}"]
        lines += ["", "<details><summary>Skills touched by the diff</summary>", "", "```json", json.dumps(diff, indent=2), "```", "</details>"]
    return "\n".join(lines) + "\n"


def _append(path: str | None, text: str) -> None:
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text if text.endswith("\n") else text + "\n")


def select_main(env: Mapping[str, str]) -> int:
    try:
        chosen = select_matrix(env)
    except CiError as exc:
        print(f"::error title=select::{exc}")
        return 2
    matrix = chosen["matrix"]
    for note in chosen["notes"]:
        print(f"NOTE: {note}")
    for warning in chosen["warnings"]:
        print(f"::warning title=select::{warning}")
    text = preview(chosen, env)
    if chosen["event"] == "workflow_dispatch" and env.get("MODE_INPUT") == "all":
        text += "\nFull suite: manual only, both requested agents, never part of the merge gate.\n"
    _append(env.get("GITHUB_STEP_SUMMARY"), text)
    print(text)
    _append(env.get("GITHUB_OUTPUT"), "\n".join([
        f"skills={json.dumps(matrix, separators=(',', ':'))}",
        f"has_skills={'true' if matrix else 'false'}",
        f"agents={','.join(chosen['agents'])}",
        # One JSON line (json escapes newlines), so a skill name can never inject another output.
        f"skipped={json.dumps(chosen['skipped'], separators=(',', ':'))}",
    ]))
    return 0


def eval_command(skill: str, mode: str, base_ref: str, agents: list[str], scenario_ids: str = "") -> list[str]:
    agent = ",".join(agents)
    if mode == "canary":
        return ["mise", "run", "eval:routing:canary", "--", skill, "--agent", agent]
    if mode == "snapshot":
        return ["mise", "run", "eval:routing", "--", "skill", skill, "--agent", agent]
    command = ["mise", "run", "eval:routing:compare", "--", skill, "--base", base_ref, "--agent", agent]
    if mode == "gate":
        return command + ["--gate"] + (["--scenarios", scenario_ids] if scenario_ids else [])
    return command + ["--confirm"]


def evaluate_main(
    env: Mapping[str, str],
    run: Callable[..., "subprocess.CompletedProcess[Any]"] = subprocess.run,
    repo: Path = check_repo.REPO_ROOT,
) -> int:
    skill, mode, scenario_ids = env.get("SKILL", ""), env.get("MODE", ""), env.get("SCENARIOS", "")
    if not SKILL_NAME.match(skill) or mode not in RUN_MODES:
        print(f"::error title=harness_error::evaluate needs SKILL and MODE ({', '.join(RUN_MODES)})")
        return 2
    if not all(SKILL_NAME.match(sid) for sid in scenario_ids.split(",") if sid):
        print("::error title=harness_error::SCENARIOS must be comma-separated kebab-case scenario ids")
        return 2
    child_env = {k: v for k, v in env.items() if k not in SCRUBBED}
    # Likewise ROUTING_SKILL_LISTING: only a manual dispatch's allowlisted preset name applies.
    try:
        listing, listing_notice = dispatch_listing(env)
    except CiError as exc:
        print(f"::error title=harness_error::{exc}")
        return 2
    if listing_notice:
        print(f"::notice title=listing_ignored::{listing_notice}")
    if listing != listing_presets.DEFAULT:
        child_env[listing_presets.ENV_VAR] = listing
    reports = repo / ".tmp" / "routing" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    summary_path = env.get("GITHUB_STEP_SUMMARY")
    try:
        plan = ci_agents.plan(env, [env.get("REQUESTED_AGENTS", "")])
    except ValueError as exc:
        print(f"::error title=harness_error::{exc}")
        return 2
    agents = plan["agents"]
    try:
        listing_presets.check_agents(listing, plan["requested"])
    except ValueError as exc:
        print(f"::error title=harness_error::{exc}")
        return 2
    record: dict[str, Any] = {
        "skill": skill, "mode": mode, "requested": plan["requested"], "agents": agents,
        "skipped": plan["skipped"], "exit_code": None,
        # A re-run of failed jobs is a new attempt; the gate judges the highest attempt per skill.
        "attempt": int(env.get("GITHUB_RUN_ATTEMPT") or 1),
        "listing": listing,
    }
    record_path = reports / f"{skill}.run.json"

    def write_record() -> None:
        record_path.write_text(json.dumps(record, indent=2) + "\n")

    write_record()  # a crash below leaves exit_code null, which the gate treats as a harness error
    for message in plan["messages"]:
        print(f"::warning title=agent_skipped::{message}")
    heading = f"### Routing eval ({mode}): {skill}\n{plan['summary']}; skill listing: {listing}\n"
    if not agents:
        print(f"::warning title=agent_skipped::{ci_agents.NO_KEYS_MESSAGE}; the gate will fail in the merge queue and manual runs")
        _append(summary_path, heading + f"{ci_agents.NO_KEYS_MESSAGE}; no provider calls were made.\n")
        # A canary that ran nothing answers nothing: fail it rather than report success.
        record["exit_code"] = canary.EXIT_CODES[canary.INCOMPLETE] if mode == "canary" else 0
        write_record()
        return record["exit_code"]

    rc = run(eval_command(skill, mode, env.get("BASE_REF") or "origin/main", agents, scenario_ids), env=child_env, cwd=repo, check=False).returncode
    summary = reports / (
        f"canary-{skill}.canary.json" if mode == "canary"
        else f"{skill}.summary.json" if mode == "snapshot" else f"{skill}.comparison-summary.json"
    )
    body = summary.read_text() if summary.is_file() else "no summary written"
    if mode == "canary" and summary.is_file():
        _append(summary_path, heading + "\n".join(f"- {line.strip()}" for line in canary.render(json.loads(body))) + "\n")
    _append(summary_path, heading + f"<details><summary>summary document</summary>\n\n```json\n{body.rstrip()}\n```\n</details>\n")
    breaches: list[dict[str, Any]] = []
    if summary.is_file():
        try:
            breaches = json.loads(body).get("breaches") or []
        except ValueError:
            pass
    if breaches:
        detail = "; ".join(f"{b['agent']} {b['ceiling']} limit {b['limit']} observed {b['observed']}" for b in breaches)
        print(f"::warning title=ceiling::{skill}: ceiling breached, run stopped as infra_error: {detail}")
    # A partial result is acceptable only when the agents run are exactly those that had keys.
    if summary.is_file():
        error = ci_agents.verify(json.loads(body), agents)
        if error:
            print(f"::error title=partial::{skill} ({mode}): result scope is not explained by the missing API keys: {error}")
            rc = 2
    record["exit_code"] = rc
    write_record()
    if rc == 0:
        return 0
    if mode == "canary" and rc in (1, 3):
        name = canary.MISSED if rc == 1 else canary.INCOMPLETE
        print(f"::error title={name}::{skill}: {'the routing eval did not notice the damaged description (blind spot)' if rc == 1 else 'infrastructure error left the canary undecided'}")
        return rc
    if rc == 1:
        print(f"::warning title=routing_fail::{skill} ({mode}): routing failed on at least one agent; the gate decides (regression-only)")
        return 0
    if rc == 3:
        print(f"::warning title=infra_error::{skill} ({mode}): provider or telemetry failure, result incomplete; the gate fails closed")
        return 0
    print(f"::error title=harness_error::{skill} ({mode}): exit {rc} is a harness or validation error, not a routing result")
    return rc


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "select":
        return select_main(os.environ)
    if len(argv) == 2 and argv[1] == "evaluate":
        return evaluate_main(os.environ)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
