"""Orchestration for .github/workflows/skill-evals.yml, kept out of YAML so it is testable offline.

    python scripts/routing_ci.py select      select job: no secrets, no provider calls
    python scripts/routing_ci.py evaluate    evaluate job: runs the evals for one matrix entry

Inputs arrive only through environment variables (never interpolated into a script).

select:   EVENT_NAME, BASE_SHA, HEAD_SHA (pull_request and merge_group), MODE_INPUT, SKILL_INPUT,
          AGENTS_INPUT (workflow_dispatch). Writes `skills` (matrix JSON `[{skill, mode}]`),
          `has_skills` and `agents` to $GITHUB_OUTPUT and a no-spend preview to $GITHUB_STEP_SUMMARY.
          mode is `compare` (candidate vs merge base, 3 trials), `adjacent` (same, 1 trial) or
          `snapshot` (manual `all`, or a manual skill run on a ref with nothing beyond main).
          On pull_request a selection problem (for example a new skill below the scenario
          minimums) is a warning; in the merge queue and manual runs it fails the job.
evaluate: SKILL, MODE, BASE_REF, REQUESTED_AGENTS, plus the provider keys and ROUTING_* ceiling
          variables. Runs only the requested agents that have a key (routing_ci_agents.py), with
          the regression confirmation re-run, and writes `.tmp/routing/reports/<skill>.run.json`
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
import routing_ceilings as ceilings
import routing_ci_agents as ci_agents
import routing_targets as targets
import select_changed
import validate_routing_scenarios as scenarios

SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MODES = ("skill", "changed", "all")
# Planning assumption for the preview, not a measurement: the pilot corpus used about $2 of Codex
# across 54 trials (candidate + control of a 27-trial skill), so ~$0.04/trial; Claude is assumed the
# same and rounded up. The hard bound is the per-run cost ceiling (routing_ceilings.py).
ASSUMED_USD_PER_TRIAL = 0.05
RESULT_EXIT_CODES = (0, 1, 3)
# Variables that would change what CI measures; never let them reach the eval processes.
SCRUBBED = ("ROUTING_CODEX_MODEL", "ROUTING_CODEX_EFFORT", "ROUTING_CLAUDE_MODEL", "ROUTING_CLAUDE_EFFORT", "ROUTING_FORCE_TRIALS", "ROUTING_MAX_TRIALS")


class CiError(Exception):
    """Invalid CI input or selection; the job fails with exit 2."""


def _git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True).returncode == 0


def entries(skills: list[str], mode: str) -> list[dict[str, str]]:
    return [{"skill": skill, "mode": mode} for skill in skills]


def select_matrix(env: Mapping[str, str], repo: Path = check_repo.REPO_ROOT) -> dict[str, Any]:
    """Resolve the event to a matrix of {skill, mode}, the requested agents, notes and a diff preview."""
    event = env.get("EVENT_NAME", "")
    notes: list[str] = []
    warnings: list[str] = []
    diff: dict[str, Any] | None = None
    covered = targets.covered_skills()
    try:
        agents = list(agents_lib.parse_agents([env.get("AGENTS_INPUT", "")]))
    except ValueError as exc:
        raise CiError(str(exc)) from None
    if event == "workflow_dispatch":
        mode = env.get("MODE_INPUT", "")
        if mode not in MODES:
            raise CiError(f"mode must be one of {', '.join(MODES)}")
        skill = env.get("SKILL_INPUT", "")
        if (mode == "skill") != bool(skill):
            raise CiError("`skill` is required for mode=skill and not accepted otherwise")
        if skill and not SKILL_NAME.match(skill):
            raise CiError("skill must be a kebab-case skill name")
        try:
            if mode == "all":
                matrix = entries(targets.resolve("all", None, None, covered, repo)[0], "snapshot")
            elif mode == "skill":
                # A ref with nothing beyond main has no control worth paying for: judge it as a snapshot.
                run_mode = "snapshot" if _git_ok(repo, "merge-base", "--is-ancestor", "HEAD", "origin/main") else "compare"
                matrix = entries(targets.resolve("skill", skill, None, covered, repo)[0], run_mode)
            else:
                matrix, diff, notes = _diff_matrix(targets.default_base(repo), covered, repo)
        except (ValueError, select_changed.SelectionError) as exc:
            raise CiError(str(exc)) from None
    elif event in ("pull_request", "merge_group"):
        base, head = env.get("BASE_SHA", ""), env.get("HEAD_SHA", "")
        if not base or not head:
            raise CiError(f"{event} needs BASE_SHA and HEAD_SHA")
        if head_sha(repo) != head:
            raise CiError("checked-out HEAD is not the event head SHA")
        try:
            matrix, diff, notes = _diff_matrix(base, covered, repo)
        except (ValueError, select_changed.SelectionError) as exc:
            if event == "merge_group":
                raise CiError(str(exc)) from None
            matrix, warnings = [], [f"selection problem (blocks the merge queue, advisory here): {exc}"]
    else:
        raise CiError(f"unsupported event {event!r}")
    return {"matrix": matrix, "agents": agents, "notes": notes, "warnings": warnings, "diff": diff, "event": event}


def head_sha(repo: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=False)
    return out.stdout.strip()


def _diff_matrix(base: str, covered: set[str], repo: Path) -> tuple[list[dict[str, str]], dict[str, Any], list[str]]:
    diff = select_changed.select(repo, base)
    changed, notes = targets.resolve("changed", None, base, covered, repo)
    adjacent: list[str] = []
    if changed:  # adjacent skills are only context for an evaluated changed skill
        adjacent, adjacent_notes = targets.resolve("adjacent", None, base, covered, repo)
        notes += adjacent_notes
    return entries(changed, "compare") + entries(adjacent, "adjacent"), diff, notes


def trial_count(skill: str, mode: str) -> int:
    """Trials per agent for one matrix entry: 3-trial scenarios, 1 for adjacent, doubled for a control."""
    cap = 1 if mode == "adjacent" else None
    own = sum(min(s["trials"], cap or s["trials"]) for s in scenarios.target_scenarios(scenarios.SCENARIOS_DIR, skill))
    return own * (1 if mode == "snapshot" else 2)


def estimate(matrix: list[dict[str, str]], agents: list[str], env: Mapping[str, str]) -> dict[str, Any]:
    trials = sum(trial_count(e["skill"], e["mode"]) for e in matrix) * len(agents)
    cap = ceilings.Ceilings.from_env(env).max_cost_usd
    return {
        "trials": trials,
        "estimated_usd": round(trials * ASSUMED_USD_PER_TRIAL, 2),
        "ceiling_usd": round(len(matrix) * len(agents) * cap, 2),
        "assumed_usd_per_trial": ASSUMED_USD_PER_TRIAL,
    }


def preview(selection: Mapping[str, Any], env: Mapping[str, str]) -> str:
    matrix, agents, event = selection["matrix"], selection["agents"], selection["event"]
    lines = ["### Routing eval preview (no provider calls were made)", ""]
    if event == "pull_request":
        lines += ["Pull request pushes only validate and preview. The relevant evals run once in the merge queue.", ""]
    if matrix:
        lines += ["| Skill | Run | Trials per agent |", "| --- | --- | --- |"]
        lines += [f"| {e['skill']} | {e['mode']} | {trial_count(e['skill'], e['mode'])} |" for e in matrix]
        est = estimate(matrix, agents, env)
        lines += [
            "",
            f"Agents: {', '.join(agents)}. Planned trials: {est['trials']}, about ${est['estimated_usd']:.2f} at an assumed "
            f"${est['assumed_usd_per_trial']:.2f}/trial (an estimate, not a measurement); confirmation re-runs of regressed scenarios are extra. "
            f"Hard bound: {len(matrix)} run(s) x {len(agents)} agent(s) x the per-run cost ceiling = ${est['ceiling_usd']:.2f}.",
        ]
    else:
        lines.append("No changed or adjacent skills with routing scenarios; nothing to evaluate and no provider calls will be made.")
    lines += [f"- NOTE: {note}" for note in selection["notes"]] + [f"- WARNING: {w}" for w in selection["warnings"]]
    if selection["diff"] is not None:
        lines += ["", "<details><summary>Skills selected from the diff</summary>", "", "```json", json.dumps(selection["diff"], indent=2), "```", "</details>"]
    return "\n".join(lines) + "\n"


def _append(path: str | None, text: str) -> None:
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text if text.endswith("\n") else text + "\n")


def select_main(env: Mapping[str, str]) -> int:
    try:
        selection = select_matrix(env)
    except CiError as exc:
        print(f"::error title=select::{exc}")
        return 2
    matrix = selection["matrix"]
    for note in selection["notes"]:
        print(f"NOTE: {note}")
    for warning in selection["warnings"]:
        print(f"::warning title=select::{warning}")
    text = preview(selection, env)
    if selection["event"] == "workflow_dispatch" and env.get("MODE_INPUT") == "all":
        text += "\nFull suite: manual only, both requested agents, never part of the merge gate.\n"
    _append(env.get("GITHUB_STEP_SUMMARY"), text)
    print(text)
    _append(env.get("GITHUB_OUTPUT"), "\n".join([
        f"skills={json.dumps(matrix, separators=(',', ':'))}",
        f"has_skills={'true' if matrix else 'false'}",
        f"agents={','.join(selection['agents'])}",
    ]))
    return 0


def eval_command(skill: str, mode: str, base_ref: str, agents: list[str]) -> list[str]:
    agent = ",".join(agents)
    if mode == "snapshot":
        return ["mise", "run", "eval:routing", "--", "skill", skill, "--agent", agent]
    return ["mise", "run", "eval:routing:compare", "--", skill, "--base", base_ref, "--agent", agent, "--confirm"]


def evaluate_main(
    env: Mapping[str, str],
    run: Callable[..., "subprocess.CompletedProcess[Any]"] = subprocess.run,
    repo: Path = check_repo.REPO_ROOT,
) -> int:
    skill, mode = env.get("SKILL", ""), env.get("MODE", "")
    if not SKILL_NAME.match(skill) or mode not in ("compare", "adjacent", "snapshot"):
        print("::error title=harness_error::evaluate needs SKILL and MODE (compare, adjacent or snapshot)")
        return 2
    reports = repo / ".tmp" / "routing" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    summary_path = env.get("GITHUB_STEP_SUMMARY")
    try:
        plan = ci_agents.plan(env, [env.get("REQUESTED_AGENTS", "")])
    except ValueError as exc:
        print(f"::error title=harness_error::{exc}")
        return 2
    agents = plan["agents"]
    record: dict[str, Any] = {
        "skill": skill, "mode": mode, "requested": plan["requested"], "agents": agents,
        "skipped": plan["skipped"], "exit_code": None,
        # A re-run of failed jobs is a new attempt; the gate judges the highest attempt per skill.
        "attempt": int(env.get("GITHUB_RUN_ATTEMPT") or 1),
    }
    record_path = reports / f"{skill}.run.json"

    def write_record() -> None:
        record_path.write_text(json.dumps(record, indent=2) + "\n")

    write_record()  # a crash below leaves exit_code null, which the gate treats as a harness error
    for message in plan["messages"]:
        print(f"::warning title=agent_skipped::{message}")
    heading = f"### Routing eval ({mode}): {skill}\n{plan['summary']}\n"
    if not agents:
        print(f"::warning title=agent_skipped::{ci_agents.NO_KEYS_MESSAGE}; the gate will fail in the merge queue and manual runs")
        _append(summary_path, heading + f"{ci_agents.NO_KEYS_MESSAGE}; no provider calls were made.\n")
        record["exit_code"] = 0
        write_record()
        return 0

    child_env = {k: v for k, v in env.items() if k not in SCRUBBED}
    if mode == "adjacent":
        child_env["ROUTING_MAX_TRIALS"] = "1"
    rc = run(eval_command(skill, mode, env.get("BASE_REF") or "origin/main", agents), env=child_env, cwd=repo, check=False).returncode
    summary = reports / (f"{skill}.summary.json" if mode == "snapshot" else f"{skill}.comparison-summary.json")
    body = summary.read_text() if summary.is_file() else "no summary written"
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
