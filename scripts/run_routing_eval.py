"""Run the routing eval for one skill on each host and reduce each host to a state.

    python scripts/run_routing_eval.py <skill>

Per host: validate scenarios offline, run Promptfoo, classify every trial (see
routing_results.py), retry infrastructure errors once, then write
`.tmp/routing/reports/<host>-<skill>.result.json`. Only the infra-errored trials
are retried; a missing or unreadable report retries the whole host run. Scenario
validation failures are deterministic and never retried. Hosts run independently;
a combined summary is written to `.tmp/routing/reports/<skill>.summary.json`.

Exit code: 0 all hosts pass, 1 any host routing_fail, 3 otherwise (infra_error or
incomplete host).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import check_repo
import routing_results as results
import validate_routing_scenarios as scenarios

REPORTS_DIR = check_repo.REPO_ROOT / ".tmp" / "routing" / "reports"
PROMPTFOO = check_repo.REPO_ROOT / "node_modules" / ".bin" / "promptfoo"
EXIT_CODES = {results.PASS: 0, results.ROUTING_FAIL: 1, results.INFRA_ERROR: 3}

# (host, skill, report_path, description_pattern or None) -> (promptfoo output text, parsed rows or None)
PromptfooRunner = Callable[[str, str, Path, "str | None"], "tuple[str, list[dict[str, Any]] | None]"]


def run_promptfoo(host: str, skill: str, report: Path, pattern: str | None) -> tuple[str, list[dict[str, Any]] | None]:
    """Run one Promptfoo eval and return its console text and parsed result rows.

    Promptfoo exits non-zero for failing or erroring tests, so success is judged by
    whether a readable report was written, not by the exit code.
    """
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    command = [
        str(PROMPTFOO), "eval", "-c", f"evals/promptfoo/{host}.config.js",
        "--no-cache", "--no-table", "--output", str(report),
    ]
    if pattern:
        command += ["--filter-pattern", pattern]
    else:
        command.append(str(report.with_suffix(".html")))
    proc = subprocess.run(
        command, cwd=check_repo.REPO_ROOT, env={**os.environ, "ROUTING_SKILL": skill},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False,
    )
    try:
        rows = json.loads(report.read_text())["results"]["results"]
    except (OSError, ValueError, KeyError, TypeError):
        rows = None
    return proc.stdout, rows


def retry_pattern(descriptions: list[str]) -> str:
    """Anchored regex matching exactly these test descriptions."""
    escaped = [re.sub(r"[.*+?^${}()|\[\]\\]", r"\\\g<0>", text) for text in descriptions]
    return "^(?:" + "|".join(escaped) + ")$"


def evaluate_host(
    host: str,
    skill: str,
    runner: PromptfooRunner = run_promptfoo,
    reports_dir: Path = REPORTS_DIR,
    validation_errors: list[str] | None = None,
) -> dict[str, Any]:
    """Run, retry once on infrastructure error, and reduce one host."""
    if validation_errors:
        return results.host_failure(host, skill, results.SCENARIO_VALIDATION, "; ".join(validation_errors))

    base = reports_dir / f"{host}-{skill}.json"
    output, rows = runner(host, skill, base, None)
    if rows is None:
        print(output)
        output, rows = runner(host, skill, base.with_suffix(".retry.json"), None)
        if rows is None:
            print(output)
            return results.host_failure(host, skill, results.PROVIDER, _last_line(output) or "no Promptfoo report", retries=1)
        return results.reduce_host(host, skill, [[], rows])

    attempts = [rows]
    broken = [
        row for row in rows
        if results.reduce_trial(row, host)["state"] == results.INFRA_ERROR
    ]
    if broken:
        descriptions = [(row.get("testCase") or {}).get("description") for row in broken]
        _, retried = runner(host, skill, base.with_suffix(".retry.json"), retry_pattern([d for d in descriptions if d]))
        attempts.append(retried or [])
    return results.reduce_host(host, skill, attempts)


def _last_line(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def summarize(result: dict[str, Any]) -> str:
    detail = ", ".join(f"{k}={v}" for k, v in result["counts"].items() if v)
    kinds = ",".join(result["failure_kinds"]) or "-"
    retry = f" retries={result['retries']}" if result["retries"] else ""
    note = f" ({result['reason']})" if result["reason"] else ""
    return f"{result['host']}: {result['state']}{'' if result['complete'] else ' [incomplete]'} trials[{detail}] kinds={kinds}{retry}{note}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    skill = argv[1]
    try:
        validation_errors = scenarios.validate_scenarios(scenarios.SCENARIOS_DIR, scenarios.known_skill_names())
    except ValueError as exc:
        validation_errors = [str(exc)]
    outcomes = [
        evaluate_host(host, skill, validation_errors=validation_errors) for host in results.HOSTS
    ]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for outcome in outcomes:
        (REPORTS_DIR / f"{outcome['host']}-{skill}.result.json").write_text(json.dumps(outcome, indent=2) + "\n")
        print(summarize(outcome))
    combined = results.combine_hosts(outcomes)
    (REPORTS_DIR / f"{skill}.summary.json").write_text(json.dumps(combined, indent=2) + "\n")
    print(f"overall: {combined['state']}")
    return EXIT_CODES[combined["state"]]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
