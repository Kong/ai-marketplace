"""Run the routing eval for one skill on each agent and reduce each agent to a state.

    python scripts/run_routing_eval.py <skill> [--agent claude|codex ...]

Per agent: validate scenarios offline, run Promptfoo, classify every trial (see
routing_results.py), retry infrastructure errors once, then write
`.tmp/routing/reports/<agent>-<skill>.result.json`. Only the infra-errored trials
are retried; a missing or unreadable report retries the whole agent run. Scenario
validation failures are deterministic and never retried. Agents run independently;
a combined summary is written to `.tmp/routing/reports/<skill>.summary.json`.

Ceilings (routing_ceilings.py; env-configurable) bound tokens, cost, concurrency, and
wall clock. A breach stops the agent as `infra_error` of kind `ceiling` with the breach
recorded in the result; a breached agent is never retried. Each result also reports
tokens, estimated cost, latency, and retries.

`--agent` limits the run to some agents (repeatable or comma-separated); the summary then records
`agents_run` and `partial: true`. Exit codes are tabulated in docs/testing.md. Invalid scenarios, usage errors and
unexpected exceptions exit 2 before any provider call (or as a harness error), never as
a routing result.
"""
from __future__ import annotations

import argparse
import functools
import json
import os
import re
import signal
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

import check_repo
import prepare_routing_workspace as workspaces
import routing_agents as agents_lib
import routing_aliases as aliasing
import routing_ceilings as ceilings
import routing_results as results
import routing_settings as settings_lib
import validate_routing_scenarios as scenarios

REPORTS_DIR = check_repo.REPO_ROOT / ".tmp" / "routing" / "reports"
PROMPTFOO = check_repo.REPO_ROOT / "node_modules" / ".bin" / "promptfoo"
EXIT_CODES = {results.PASS: 0, results.ROUTING_FAIL: 1, results.INFRA_ERROR: 3}

# (agent, skill, report_path, description_pattern or None) -> (promptfoo output text, parsed rows or None)
PromptfooRunner = Callable[[str, str, Path, "str | None"], "tuple[str, list[dict[str, Any]] | None]"]


def run_promptfoo(
    agent: str,
    skill: str,
    report: Path,
    pattern: str | None,
    env: dict[str, str] | None = None,
    ledger: ceilings.Ledger | None = None,
) -> tuple[str, list[dict[str, Any]] | None]:
    """Run one Promptfoo eval and return its console text and parsed result rows.

    Promptfoo exits non-zero for failing or erroring tests, so success is judged by
    whether a readable report was written, not by the exit code. The run is capped by the
    ledger's concurrency and timeout; on timeout its whole process group is killed and
    `CeilingBreach` is raised.
    """
    ledger = ledger or ceilings.Ledger(ceilings.Ceilings.from_env())
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    command = [
        str(PROMPTFOO), "eval", "-c", f"evals/promptfoo/{agent}.config.js",
        "--no-cache", "--no-table", "--max-concurrency", str(ledger.ceilings.max_concurrency),
        "--output", str(report),  # keep last: the variadic list takes the extra report paths below
    ]
    if pattern:
        command += ["--filter-pattern", pattern]
    else:
        command += [str(report.with_suffix(".html")), str(report.with_suffix(".junit.xml"))]
    merged = {**os.environ, **(env or {})}
    # Always explicit, so the Promptfoo configs can refuse a workspace built with the other setting.
    merged[aliasing.ENV_VAR] = "1" if aliasing.enabled(merged) else "0"
    # Own process group so a timeout also stops the agent CLIs Promptfoo spawned.
    proc = subprocess.Popen(
        command, cwd=check_repo.REPO_ROOT, env={**merged, "ROUTING_SKILL": skill},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
    )
    try:
        stdout, _ = proc.communicate(timeout=ledger.run_timeout())
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise ceilings.CeilingBreach(ledger.timeout_breach(agent)) from None
    try:
        rows = json.loads(report.read_text())["results"]["results"]
    except (OSError, ValueError, KeyError, TypeError):
        rows = None
    return stdout, rows


def retry_pattern(descriptions: list[str]) -> str:
    """Anchored regex matching exactly these test descriptions."""
    escaped = [re.sub(r"[.*+?^${}()|\[\]\\]", r"\\\g<0>", text) for text in descriptions]
    return "^(?:" + "|".join(escaped) + ")$"


def scenario_pattern(scenario_ids: list[str]) -> str:
    """Regex matching every trial description of exactly these scenarios (`<id> | <agent> | ...`)."""
    return "^(?:" + "|".join(re.sub(r"[.*+?^${}()|\[\]\\]", r"\\\g<0>", sid) for sid in scenario_ids) + ") \\| "


def evaluate_agent(
    agent: str,
    skill: str,
    runner: PromptfooRunner | None = None,
    reports_dir: Path = REPORTS_DIR,
    validation_errors: list[str] | None = None,
    ledger: ceilings.Ledger | None = None,
    pattern: str | None = None,
    workspace: workspaces.Workspace | None = None,
) -> dict[str, Any]:
    """Run, retry once on infrastructure error, and reduce one agent.

    `pattern` (see `scenario_pattern`) limits every launch to some scenarios. `workspace` is the built
    workspace the agent ran in: its aliases map result names back to real skill names, and the result
    records `aliased` and the workspace `fingerprint`.

    Ceilings are checked before every Promptfoo launch and after the last run. A breach
    stops the agent (no retry) as infra_error; trials already judged stay in the result.
    """
    aliases = workspace.aliases if workspace else None

    def stamp(doc: dict[str, Any]) -> dict[str, Any]:
        doc["aliased"] = aliases is not None
        doc["fingerprint"] = workspace.fingerprint if workspace else None
        return doc

    if validation_errors:
        return stamp(results.agent_failure(agent, skill, results.SCENARIO_VALIDATION, "; ".join(validation_errors)))

    ledger = ledger or ceilings.Ledger(ceilings.Ceilings.from_env())
    runner = runner or functools.partial(run_promptfoo, ledger=ledger)
    base = reports_dir / f"{agent}-{skill}.json"
    retry_report = base.with_suffix(".retry.json")
    attempts: list[list[dict[str, Any]]] = []
    retries = 0

    def launch(report: Path, pattern: str | None) -> tuple[str, list[dict[str, Any]] | None]:
        ledger.check(agent)
        output, rows = runner(agent, skill, report, pattern)
        if rows is not None:
            ledger.record(agent, rows)
        return output, rows

    try:
        output, rows = launch(base, pattern)
        if rows is None:
            print(output)
            retries = 1
            output, rows = launch(retry_report, pattern)
            if rows is None:
                print(output)
                return stamp(results.agent_failure(agent, skill, results.PROVIDER, _last_line(output) or "no Promptfoo report", retries=1))
            attempts = [[], rows]
        else:
            attempts = [rows]
            broken = [row for row in rows if results.reduce_trial(row, agent)["state"] == results.INFRA_ERROR]
            if broken:
                descriptions = [(row.get("testCase") or {}).get("description") for row in broken]
                _, retried = launch(retry_report, retry_pattern([d for d in descriptions if d]))
                attempts.append(retried or [])
        breaches = ledger.breaches(agent)
    except ceilings.CeilingBreach as exc:
        breaches = [exc.breach]

    if not attempts:
        return stamp(results.agent_failure(
            agent, skill, results.CEILING, ceilings.describe(breaches[0]), retries=retries, breaches=breaches
        ))
    return stamp(results.reduce_agent(agent, skill, attempts, breaches, aliases))


def _last_line(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def summarize(result: dict[str, Any]) -> str:
    detail = ", ".join(f"{k}={v}" for k, v in result["counts"].items() if v)
    kinds = ",".join(result["failure_kinds"]) or "-"
    use = result["usage"]
    usage = f" tokens={use['tokens']} cost=${use['cost_usd']:.4f} latency={use['latency_ms'] / 1000:.1f}s retries={result['retries']}"
    note = f" ({result['reason']})" if result["reason"] else ""
    config = f" {settings_lib.describe(result['settings'])}" if "settings" in result else ""
    config += f" aliased={str(result.get('aliased', False)).lower()} fingerprint={result.get('fingerprint') or '-'}"
    return f"{result['agent']}: {result['state']}{'' if result['complete'] else ' [incomplete]'}{config} trials[{detail}] kinds={kinds}{usage}{note}"


HARNESS_ERROR = 2  # exit 1 is routing_fail, which is also Python's uncaught-traceback code


def guarded(entry: Callable[[list[str]], int]) -> Callable[[list[str]], int]:
    """Turn an unexpected exception into a harness error (exit 2) instead of a routing_fail-looking 1."""

    @functools.wraps(entry)
    def wrapper(argv: list[str]) -> int:
        try:
            return entry(argv)
        except Exception:  # noqa: BLE001 - last-resort boundary
            traceback.print_exc()
            print(f"ERROR: harness crashed in {entry.__module__}; not a routing result", file=sys.stderr)
            return HARNESS_ERROR

    return wrapper


@guarded
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skill")
    parser.add_argument("--agent", action="append", help="claude or codex; repeat or comma-separate (default: both)")
    args = parser.parse_args(argv[1:])
    skill = args.skill
    try:
        agents = agents_lib.parse_agents(args.agent)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return HARNESS_ERROR
    if agents_lib.is_partial(agents):
        print(f"WARNING: partial run, {', '.join(agents)} only; not a both-agent result", file=sys.stderr)
    try:
        settings = settings_lib.load()  # fail fast on invalid ROUTING_*_MODEL / _EFFORT
        aliased = aliasing.enabled()  # and on an invalid ROUTING_ALIAS_SKILLS
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return HARNESS_ERROR
    if warning := settings_lib.warning(settings):
        print(warning, file=sys.stderr)
    try:
        validation_errors = scenarios.validate_scenarios(scenarios.SCENARIOS_DIR, scenarios.known_skill_names())
    except ValueError as exc:
        validation_errors = [str(exc)]
    if validation_errors:
        for error in validation_errors:
            print(f"ERROR: scenario_validation: {error}", file=sys.stderr)
        return HARNESS_ERROR
    try:
        ledger = ceilings.Ledger(ceilings.Ceilings.from_env())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return HARNESS_ERROR
    # The workspaces were built by `prepare_routing_workspace.py`; refuse one that is stale or built with
    # the other alias setting before any provider call.
    built: dict[str, workspaces.Workspace] = {}
    for agent in agents:
        try:
            built[agent] = workspaces.verify_workspace(workspaces.TMP_ROOT / "routing" / agent, agent, aliased=aliased)
        except (workspaces.WorkspaceIntegrityError, OSError, ValueError) as exc:
            print(f"ERROR: workspace_integrity: {exc}", file=sys.stderr)
            return HARNESS_ERROR
        print(f"{agent}: workspace aliased={str(aliased).lower()} fingerprint={built[agent].fingerprint}")
    outcomes = [evaluate_agent(agent, skill, ledger=ledger, workspace=built[agent]) for agent in agents]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for outcome in outcomes:
        settings_lib.annotate(outcome, settings).update(agents_lib.scope(agents))
        (REPORTS_DIR / f"{outcome['agent']}-{skill}.result.json").write_text(json.dumps(outcome, indent=2) + "\n")
        print(summarize(outcome))
    combined = results.combine_agents(outcomes, required=agents)
    (REPORTS_DIR / f"{skill}.summary.json").write_text(json.dumps(combined, indent=2) + "\n")
    print(f"overall: {agents_lib.label(combined['state'], agents)}")
    return EXIT_CODES[combined["state"]]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
