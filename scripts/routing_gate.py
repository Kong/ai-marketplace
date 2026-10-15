"""Reduce routing eval results to one merge-gate verdict. Offline: no model calls, no network.

    python scripts/routing_gate.py REPORTS_DIR MATRIX_JSON [--informational]
                                   [--summary FILE] [--json FILE]

REPORTS_DIR is searched recursively for `<skill>.run.json` records written by routing_ci.py
(one per evaluate job attempt, the highest attempt wins; CI downloads every `routing-reports-*` artifact into it). MATRIX_JSON is the
select job's matrix `[{"skill", "mode"}]`, so a job that never produced a record is noticed.
`--summary` appends a Markdown table (the job summary); `--json` writes the machine-readable verdict.
Exit codes are tabulated once in docs/testing.md.

Per agent that was supposed to run (its API key was present):
    gate                 modified skill, LAZY CONTROL (routing_compare.lazy_compare): the candidate ran
                         each selected scenario once; only failed scenarios were confirmed (candidate,
                         then control, at max(own trials, 3)). Fails only when the candidate
                         still fails and the control passes (`routing_regression`); a scenario that
                         also fails on control is a `preexisting_failure` warning; a candidate that
                         passes the re-run is a `regression_not_confirmed` warning. A clean first pass
                         never runs the control.
    gate, new skill      absolute thresholds (routing_compare.evaluate_new_skill), no control.
    compare              full candidate-vs-control run (manual `eval:routing:compare --confirm`): REGRESSION-ONLY.
                         A regression is a scenario that passes on control and fails on candidate; it
                         fails only when the 3-trial confirmation re-run (routing_compare.with_confirmation)
                         reproduces it. A scenario failing on both sides is a warning, never a failure.
    snapshot             manual runs only: the agent's own state; routing_fail is a failure.
    infra_error          incomplete after the single retry, a ceiling breach, a missing result or
                         confirmation, or a harness error: FAIL CLOSED (`blocked_infra`).
An agent skipped for a missing key only warns while another agent ran; if no agent ran in any job
the verdict is `fail_no_agents`.

Verdict precedence: fail_no_agents > fail > blocked_infra > pass_with_warnings > pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import routing_compare as compare
import routing_results as results

PASS, PASS_WITH_WARNINGS, FAIL, BLOCKED_INFRA, FAIL_NO_AGENTS = (
    "pass", "pass_with_warnings", "fail", "blocked_infra", "fail_no_agents"
)
HARNESS_ERROR = 2
EXIT_CODES = {PASS: 0, PASS_WITH_WARNINGS: 0, FAIL: 1, BLOCKED_INFRA: 3, FAIL_NO_AGENTS: 4}
RUN_SUFFIX = ".run.json"
MODES = ("gate", "compare", "snapshot")
# Evaluate exit codes that are results (docs/testing.md); anything else is a harness or validation error.
RESULT_EXIT_CODES = (0, 1, 3)

# Reason codes (machine-readable). Failures first, then blockers, then warnings.
ROUTING_REGRESSION = "routing_regression"
NEW_SKILL_THRESHOLD = "new_skill_threshold"
ROUTING_FAIL = "routing_fail"
INFRA_ERROR = "infra_error"
CONFIRMATION_MISSING = "confirmation_missing"
MISSING_RESULT = "missing_result"
HARNESS = "harness_error"
NO_AGENTS = "no_agents"
AGENT_SKIPPED = "agent_skipped"
UNCONFIRMED_CLEARED = "regression_not_confirmed"
PREEXISTING = "preexisting_failure"
FAILING = (ROUTING_REGRESSION, NEW_SKILL_THRESHOLD, ROUTING_FAIL)
WARNINGS = (AGENT_SKIPPED, UNCONFIRMED_CLEARED, PREEXISTING)


class GateInputError(Exception):
    """Unreadable or malformed gate input; a harness error (exit 2), never a verdict."""


def _reason(code: str, skill: str, detail: str, agent: str | None = None) -> dict[str, Any]:
    return {"code": code, "skill": skill, "agent": agent, "detail": detail}


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise GateInputError(f"{path}: {exc}") from None
    if not isinstance(data, dict):
        raise GateInputError(f"{path}: expected a JSON object")
    return data


def load_runs(reports: Path) -> dict[tuple[str, str], tuple[dict[str, Any], Path]]:
    """Run records keyed by (skill, mode), each with its directory (where the result documents live)."""
    runs: dict[tuple[str, str], tuple[dict[str, Any], Path]] = {}
    for path in sorted(reports.rglob(f"*{RUN_SUFFIX}")):
        record = _read(path)
        key = (record.get("skill"), record.get("mode"))
        if not isinstance(key[0], str) or key[1] not in MODES:
            raise GateInputError(f"{path}: record needs a string `skill` and a `mode` of {MODES}")
        if key not in runs or int(record.get("attempt") or 1) >= int(runs[key][0].get("attempt") or 1):
            runs[key] = (record, path.parent)  # a re-run supersedes the earlier attempt's record
    return runs


def _agent_document(record: dict[str, Any], agent: str, directory: Path) -> dict[str, Any] | None:
    suffix = "result" if record["mode"] == "snapshot" else "comparison"
    path = directory / f"{agent}-{record['skill']}.{suffix}.json"
    return _read(path) if path.is_file() else None


def _state(side: dict[str, Any] | None) -> str | None:
    return side["state"] if side else None


def judge_agent(skill: str, mode: str, agent: str, doc: dict[str, Any] | None) -> tuple[str, str, list[dict[str, Any]]]:
    """Return (result label, detail, reasons) for one agent of one skill; reasons carry the verdict."""
    if doc is None:
        return "blocked", "no result document", [_reason(MISSING_RESULT, skill, "no result document was produced", agent)]
    incomplete = not doc.get("complete", True) or doc.get("state") == results.INFRA_ERROR or doc.get("breaches")
    kinds = ",".join(doc.get("failure_kinds") or []) or "unknown"
    broken = [x["id"] for x in doc.get("scenarios", []) if "infra_error" in (_state(x.get("candidate")), _state(x.get("control")), x.get("state"))]
    why = f"incomplete after retry ({kinds})" + (f": {doc['reason']}" if doc.get("reason") else "") + (f"; scenarios: {', '.join(broken)}" if broken else "")
    blocked = ("blocked", why, [_reason(INFRA_ERROR, skill, why, agent)])

    if doc.get("mode") == "new_skill":
        if incomplete:
            return blocked
        unmet = [
            f"{name} {c['passes']}/{c['trials']} (need {c['required']:.0%})"
            for name, c in doc["expectations"].items() if not c["met"]
        ]
        if unmet:
            detail = "new skill below threshold: " + "; ".join(unmet)
            return "fail", detail, [_reason(NEW_SKILL_THRESHOLD, skill, detail, agent)]
        return "pass", "new skill meets thresholds", []

    if doc.get("mode") == compare.LAZY:
        if incomplete:
            return blocked
        failed = doc.get("failed") or []
        total = len(doc.get("scenarios") or [])
        if not failed:
            return "pass", f"{total} scenario(s) passed the first pass; control not run", []
        conf = doc.get("confirmation")
        if conf is None:
            detail = f"{', '.join(failed)} failed the first pass but the confirmation did not happen"
            return "blocked", detail, [_reason(CONFIRMATION_MISSING, skill, detail, agent)]
        if not conf.get("complete", False) or conf.get("state") == results.INFRA_ERROR:
            detail = "confirmation incomplete" + (f": {conf['reason']}" if conf.get("reason") else "")
            return "blocked", detail, [_reason(INFRA_ERROR, skill, detail, agent)]
        by_outcome: dict[str, list[dict[str, Any]]] = {}
        for row in conf["scenarios"]:
            by_outcome.setdefault(row["outcome"], []).append(row)
        sides = lambda r: f"{r['id']} (candidate {r['candidate']['passes']}/{r['candidate']['trials']}, control {r['control']['passes']}/{r['control']['trials']})"  # noqa: E731
        reasons = []
        notes = []
        if by_outcome.get(compare.PREEXISTING):
            note = "also failing on control (not a regression): " + ", ".join(sides(r) for r in by_outcome[compare.PREEXISTING])
            notes.append(note)
            reasons.append(_reason(PREEXISTING, skill, note, agent))
        if by_outcome.get(compare.CLEARED):
            note = "failed the first pass but not reproduced on re-run: " + ", ".join(r["id"] for r in by_outcome[compare.CLEARED])
            notes.append(note)
            reasons.append(_reason(UNCONFIRMED_CLEARED, skill, note, agent))
        if by_outcome.get(compare.CONFIRMED):
            detail = "regression confirmed vs control: " + ", ".join(sides(r) for r in by_outcome[compare.CONFIRMED])
            return "fail", detail, [*reasons, _reason(ROUTING_REGRESSION, skill, detail, agent)]
        return "pass", "; ".join(notes), reasons

    if doc.get("mode") == "comparison":
        if incomplete:
            return blocked
        reasons = []
        notes = []
        both = compare.preexisting_failures(doc)
        if both:
            note = f"also failing on control (not a regression): {', '.join(both)}"
            notes.append(note)
            reasons.append(_reason(PREEXISTING, skill, note, agent))
        regressed = compare.regressions(doc)
        if not regressed:
            return "pass", "; ".join(notes) or "no regression vs control", reasons
        conf = doc.get("confirmation")
        if conf is None:
            detail = f"regressed {', '.join(regressed)} but the confirmation re-run did not happen"
            return "blocked", detail, [_reason(CONFIRMATION_MISSING, skill, detail, agent)]
        if not conf.get("complete", False) or conf.get("state") == results.INFRA_ERROR:
            detail = "confirmation re-run incomplete" + (f": {conf['reason']}" if conf.get("reason") else "")
            return "blocked", detail, [_reason(INFRA_ERROR, skill, detail, agent)]
        confirmed = [r["id"] for r in conf["scenarios"] if r["confirmed"]]
        if confirmed:
            detail = f"regression confirmed at {conf['trials']} trials: " + ", ".join(
                f"{r['id']} (candidate {r['candidate']['passes']}/{r['candidate']['trials']}, "
                f"control {r['control']['passes']}/{r['control']['trials']})"
                for r in conf["scenarios"] if r["confirmed"]
            )
            return "fail", detail, [_reason(ROUTING_REGRESSION, skill, detail, agent)]
        note = f"regression not reproduced at {conf['trials']} trials: {', '.join(regressed)}"
        reasons.append(_reason(UNCONFIRMED_CLEARED, skill, note, agent))
        return "pass", "; ".join([*notes, note]), reasons

    # snapshot: an agent result document (run_routing_eval.py)
    if doc.get("complete") is False or doc.get("state") == results.INFRA_ERROR:
        return blocked
    if doc.get("state") == results.ROUTING_FAIL:
        failing = [s["id"] for s in doc.get("scenarios", []) if s["state"] == results.ROUTING_FAIL]
        detail = f"routing_fail: {', '.join(failing) or 'see report'}"
        return "fail", detail, [_reason(ROUTING_FAIL, skill, detail, agent)]
    return "pass", "all scenarios met their route", []


def judge(matrix: list[dict[str, str]], runs: dict[tuple[str, str], tuple[dict[str, Any], Path]]) -> dict[str, Any]:
    """Reduce every expected (skill, mode) to the gate verdict document."""
    rows: list[dict[str, Any]] = []
    reasons: list[dict[str, Any]] = []
    agents_run: set[str] = set()
    agents_skipped: set[str] = set()
    any_agents = False
    for entry in matrix:
        skill, mode = entry["skill"], entry["mode"]
        found = runs.get((skill, mode))
        if found is None:
            detail = "the evaluate job produced no result record (failed, timed out, or was cancelled)"
            rows.append({"skill": skill, "mode": mode, "agent": "-", "result": "blocked", "detail": detail})
            reasons.append(_reason(MISSING_RESULT, skill, detail))
            continue
        record, directory = found
        exit_code = record.get("exit_code")
        agents = list(record.get("agents") or [])
        for item in record.get("skipped") or []:
            agents_skipped.add(item["agent"])
            detail = f"{item['env']} is not set"
            rows.append({"skill": skill, "mode": mode, "agent": item["agent"], "result": "skipped", "detail": detail})
            reasons.append(_reason(AGENT_SKIPPED, skill, detail, item["agent"]))
        if not agents:
            detail = "no requested agent has an API key; nothing was evaluated"
            rows.append({"skill": skill, "mode": mode, "agent": "-", "result": "blocked", "detail": detail})
            reasons.append(_reason(NO_AGENTS, skill, detail))
            continue
        any_agents = True
        if exit_code not in RESULT_EXIT_CODES:
            detail = f"evaluate exited {exit_code}: a harness or validation error, not a routing result"
            rows.append({"skill": skill, "mode": mode, "agent": ",".join(agents), "result": "blocked", "detail": detail})
            reasons.append(_reason(HARNESS, skill, detail))
            continue
        for agent in agents:
            document = _agent_document(record, agent, directory)
            result, detail, agent_reasons = judge_agent(skill, mode, agent, document)
            rows.append({"skill": skill, "mode": mode, "agent": agent, "result": result, "detail": detail})
            reasons.extend(agent_reasons)
            if document is not None:
                agents_run.add(agent)

    codes = {r["code"] for r in reasons}
    if matrix and not any_agents and NO_AGENTS in codes and codes <= {NO_AGENTS, AGENT_SKIPPED}:
        verdict = FAIL_NO_AGENTS
    elif codes & set(FAILING):
        verdict = FAIL
    elif codes - set(FAILING) - set(WARNINGS):
        verdict = BLOCKED_INFRA
    elif codes & set(WARNINGS):
        verdict = PASS_WITH_WARNINGS
    else:
        verdict = PASS
    return {
        "verdict": verdict,
        "exit_code": EXIT_CODES[verdict],
        "reasons": reasons,
        "agents_run": sorted(agents_run),
        "agents_skipped": sorted(agents_skipped),
        "skills": rows,
    }


def markdown(doc: dict[str, Any]) -> str:
    lines = [f"### routing-evals-gate: `{doc['verdict']}`", ""]
    if doc["skills"]:
        lines += ["| Skill | Run | Agent | Result | Detail |", "| --- | --- | --- | --- | --- |"]
        lines += [
            f"| {r['skill']} | {r['mode']} | {r['agent']} | {r['result']} | {r['detail'].replace('|', '/')} |"
            for r in doc["skills"]
        ]
        lines.append("")
    lines.append(f"Agents run: {', '.join(doc['agents_run']) or 'none'}; skipped for a missing key: {', '.join(doc['agents_skipped']) or 'none'}")
    blocking = [r for r in doc["reasons"] if r["code"] not in WARNINGS]
    if blocking:
        lines += ["", "Reasons:"] + [f"- `{r['code']}` {r['skill']}{'/' + r['agent'] if r['agent'] else ''}: {r['detail']}" for r in blocking]
    hints = {
        BLOCKED_INFRA: "Blocked by an infrastructure or harness problem, not a routing verdict: re-run the failed jobs, or have an admin override the check.",
        FAIL_NO_AGENTS: "No agent could run: configure ANTHROPIC_API_KEY and/or OPENAI_API_KEY as `skill-evals` environment secrets, then re-run.",
        FAIL: "A routing regression was confirmed on at least one agent; see the table and the routing-reports artifacts.",
    }
    if doc["verdict"] in hints:
        lines += ["", hints[doc["verdict"]]]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("reports", type=Path)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--informational", action="store_true", help="report the verdict but exit 0 for fail and blocked_infra")
    parser.add_argument("--summary", type=Path, help="append the Markdown summary here")
    parser.add_argument("--json", type=Path, help="write the verdict document here")
    args = parser.parse_args(argv)
    try:
        matrix = json.loads(args.matrix.read_text())
        if not isinstance(matrix, list) or not all(isinstance(e, dict) and {"skill", "mode"} <= set(e) for e in matrix):
            raise GateInputError(f"{args.matrix}: expected a list of {{skill, mode}} objects")
        doc = judge(matrix, load_runs(args.reports))
    except (OSError, ValueError, KeyError, GateInputError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return HARNESS_ERROR
    text = markdown(doc)
    print(text, end="")
    if args.summary:
        with args.summary.open("a") as handle:
            handle.write(text)
    if args.json:
        args.json.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"verdict: {doc['verdict']}")
    if args.informational and doc["verdict"] in (FAIL, BLOCKED_INFRA):
        print("informational run: verdict reported, exit 0")
        return 0
    return doc["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
