"""Listing probe: ask the routing harness's own Claude what skills and descriptions it can see.

    python scripts/routing_listing_probe.py [--listing default|name-only] [--fake-output FILE]
    python scripts/routing_listing_probe.py --compare

Diagnosis only, never the gate. The routing evals never verified what the model is shown: whether the
skill descriptions reach it at all, and whether the workspace `.claude/settings.json` of a listing
preset (routing_listing.py) is honoured by the SDK run. The probe prepares the Claude workspace exactly
like the evals (prepare_routing_workspace.py, preset, integrity check) and runs ONE Promptfoo test
through evals/promptfoo/claude.probe.config.js, which shares every provider setting with the routing
config (claude.provider.js) and only changes the prompt (PROMPT below). Nothing is asserted on skill use.

The model's reply is parsed (one `<name> | <description or NAME ONLY>` line per skill) and compared with
the workspace's SKILL.md frontmatter. Per skill: listed, description shown, similarity of the shown text to
the real one (tolerant of truncation) and shown length. Verdict, as the share of workspace skills whose shown
description matches (similarity >= MATCH_THRESHOLD):

    descriptions_visible  >= 90%
    partial               10% to 90%
    names_only            < 10%
    inconclusive          the reply listed none of the workspace skills (refusal or unparseable): no verdict

Claude's provider passes the workspace skill names as an explicit `skills` list (claude.provider.js), so the
model should see only workspace skills, with descriptions: the expected verdict is descriptions_visible. Any
listed skill that is not in the workspace (bundled Claude Code skills, user skills) is a leak: it is counted
(`counts.leaked`, `leaked_skills`), flagged `scope: leaking` and shown in the verdict line. A leak does not change
the verdict, but it means those skills share the listing budget and the description-visibility result may be
the budget's doing. Before the explicit list the probe showed NAME ONLY for every workspace skill next to
described bundled skills (docs/testing.md, "Listing budget finding").

`--listing` defaults to ROUTING_SKILL_LISTING. The report `.tmp/routing/reports/probe-<listing>.json` holds the
verdict, counts, per-skill rows, workspace fingerprint, the settings that were REQUESTED (the settings.json
written), the provider model and effort, the raw model output and the response metadata.

The probe cannot by itself prove the settings were honoured: it only shows what the model reports seeing.
Run it for both presets and `--compare` the two reports: if the default and name-only runs show the same
descriptions, name-only was not honoured; if default already shows names only, the harness does not show
descriptions at all and the preset cannot be told apart.

`--fake-output FILE` is the offline mode: FILE is used as the model output and no provider call is made.
Exit codes: 0 verdict reached, 2 harness or usage error, 3 incomplete (provider error, ceiling breach,
no skills listed).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import prepare_routing_workspace as workspaces
import routing_agents as agents_lib
import routing_ceilings as ceilings
import routing_listing as listing_presets
import routing_settings as settings_lib
import run_routing_comparison as driver
import run_routing_eval as runner

AGENT = "claude"
PROBE_SKILL = "listing-probe"  # artifact name only: the probe belongs to no skill
PROBE_CONFIG = "evals/promptfoo/claude.probe.config.js"
PROMPT_ENV = "ROUTING_PROBE_PROMPT"
PROMPT = (
    "Do not call any tool. List every skill that is available to you through the Skill tool. "
    "For each skill give its exact name and its description exactly as it appears in your context, verbatim; "
    "if you only see the name, write NAME ONLY. Output one line per skill as: <name> | <description or NAME ONLY>."
)

DESCRIPTIONS_VISIBLE, PARTIAL, NAMES_ONLY, INCONCLUSIVE = "descriptions_visible", "partial", "names_only", "inconclusive"
WORKSPACE_ONLY, LEAKING = "workspace_only", "leaking"  # whether the model's listing held skills outside the workspace
VISIBLE_SHARE, NAMES_ONLY_SHARE = 0.9, 0.1
PARTLY_HONOURED_DROP = 0.25  # share of skills by which name-only must lower the matching count to count as an effect (run-to-run noise is below it)
MATCH_THRESHOLD = 0.85  # similarity at which a shown description counts as the real one
MIN_PREFIX = 25  # a truncated description shorter than this is not evidence of a match by prefix alone
EXIT_OK, EXIT_INCOMPLETE = 0, 3

NOTE = (
    "The probe reports what the model says it sees; it cannot by itself prove the workspace settings were honoured. "
    "Compare the default and name-only reports (--compare): identical descriptions mean name-only was not honoured."
)

_LINE = re.compile(r"^\s*(?:[-*•]|\d+[.)])?\s*`?\*{0,2}([A-Za-z0-9][\w.:/-]*)\*{0,2}`?\s*\|\s*(.*?)\s*$")
_NAME_ONLY = re.compile(r"^\W*name only\b", re.IGNORECASE)
_ELLIPSIS = re.compile(r"\s*(?:\.{3}|…)\s*$")


def normalize(text: str) -> str:
    """Comparison form: lower case, collapsed whitespace, no wrapping quotes and no trailing ellipsis."""
    text = " ".join(text.split()).strip("`\"'")
    return _ELLIPSIS.sub("", text).lower().strip()


def similarity(shown: str, real: str) -> float:
    """0..1: how much of `real` the shown text reproduces; a truncated copy (prefix, ellipsis) scores 1.0."""
    s, r = normalize(shown), normalize(real)
    if not s or not r:
        return 0.0
    if s == r or r in s:
        return 1.0
    enough = min(MIN_PREFIX, len(r))
    if len(s) >= enough and r.startswith(s):
        return 1.0
    aligned = r[:len(s)] if len(s) < len(r) else r  # a shorter reply is judged against the same stretch of the real text
    ratio = SequenceMatcher(None, s, aligned, autojunk=False).ratio()
    return round(ratio * min(1.0, len(s) / enough), 3)  # a stub shorter than MIN_PREFIX is weak evidence


def parse_output(output: str, names: list[str]) -> dict[str, Any]:
    """Parse the model's reply against the workspace skill names.

    Returns `listed` (skill name -> shown description, None for NAME ONLY), `unknown` (names shown that are
    not workspace skills, such as built-in skills) and `ignored` (lines that were not `<name> | <text>`).
    A `plugin:name` form matches `name`; the first line per skill wins; a markdown table is tolerated.
    """
    by_lower = {name.lower(): name for name in names}
    listed: dict[str, str | None] = {}
    unknown: list[str] = []
    ignored = 0
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("|"):
            line = line[1:].removesuffix("|")  # a table row: `| name | description |`
        match = _LINE.match(line)
        if not match:
            ignored += 1
            continue
        token, text = match.group(1), match.group(2).strip().strip("`\"'").strip()
        name = by_lower.get(token.lower()) or by_lower.get(token.lower().rsplit(":", 1)[-1])
        if name is None:
            if token.lower() not in ("name", "skill") and token not in unknown:  # not a table header
                unknown.append(token)
            continue
        if name not in listed:
            listed[name] = None if not text or (len(text) < 40 and _NAME_ONLY.match(text)) else text
    return {"listed": listed, "unknown": unknown, "ignored": ignored}


def judge(real: dict[str, str], parsed: dict[str, Any]) -> dict[str, Any]:
    """Per-skill rows, counts and the verdict for the real descriptions (`name -> description`) and a parse."""
    rows = []
    for name in sorted(real):
        listed = name in parsed["listed"]
        shown = parsed["listed"].get(name)
        score = similarity(shown, real[name]) if shown else None
        rows.append({
            "skill": name, "listed": listed, "description_shown": shown is not None,
            "similarity": score, "matches": score is not None and score >= MATCH_THRESHOLD,
            "shown_length": len(shown) if shown else 0, "real_length": len(real[name]),
            "shown": shown,
        })
    total = len(rows)
    counts = {
        "skills": total, "listed": sum(r["listed"] for r in rows),
        "description_shown": sum(r["description_shown"] for r in rows), "matching": sum(r["matches"] for r in rows),
        "unknown": len(parsed["unknown"]), "leaked": len(parsed["unknown"]), "ignored_lines": parsed["ignored"],
    }
    share = counts["matching"] / total if total else 0.0
    if not counts["listed"]:
        verdict = INCONCLUSIVE
    elif share >= VISIBLE_SHARE:
        verdict = DESCRIPTIONS_VISIBLE
    elif share < NAMES_ONLY_SHARE:
        verdict = NAMES_ONLY
    else:
        verdict = PARTIAL
    return {
        "verdict": verdict, "matching_share": round(share, 3), "counts": counts, "skills": rows, "unknown_listed": parsed["unknown"],
        "leaked_skills": list(parsed["unknown"]), "scope": LEAKING if parsed["unknown"] else WORKSPACE_ONLY,
    }


def compare(default: dict[str, Any], name_only: dict[str, Any]) -> dict[str, Any]:
    """Was the name-only preset honoured? Judged from the two probe reports (default listing, name-only listing)."""
    problems = []
    if default.get("listing") != listing_presets.DEFAULT or name_only.get("listing") != listing_presets.NAME_ONLY:
        problems.append("expected a default report and a name-only report")
    if default.get("fingerprint") != name_only.get("fingerprint"):
        problems.append("the reports were made from different workspaces (fingerprints differ)")
    total = default["counts"]["skills"]
    d, n = default["counts"]["matching"], name_only["counts"]["matching"]
    if problems:
        conclusion, why = "not_comparable", "; ".join(problems)
    elif INCONCLUSIVE in (default["verdict"], name_only["verdict"]):
        conclusion, why = "inconclusive", "a run listed none of the skills; repeat it"
    elif default["verdict"] == NAMES_ONLY:
        conclusion = "indeterminate"
        why = "the default listing already shows no descriptions: the harness does not show descriptions at all, so the preset cannot be told apart"
    elif n / total < NAMES_ONLY_SHARE:
        conclusion, why = "honoured", f"name-only removed the descriptions ({d} -> {n} of {total} matching)"
    elif (d - n) / total >= PARTLY_HONOURED_DROP:
        conclusion, why = "partly_honoured", f"name-only reduced the matching descriptions ({d} -> {n} of {total}) but did not remove them"
    else:
        conclusion, why = "not_honoured", f"name-only shows the same descriptions as default ({d} vs {n} of {total} matching): the settings file had no effect"
    return {
        "conclusion": conclusion, "why": why, "default": {"verdict": default["verdict"], "matching": d},
        "name_only": {"verdict": name_only["verdict"], "matching": n}, "skills": total,
    }


def _first_row(rows: list[dict[str, Any]] | None) -> tuple[str, dict[str, Any], str | None]:
    """(model output, response metadata and usage, error) of the probe's single result row."""
    if not rows:
        return "", {}, "no Promptfoo result row"
    row = rows[0]
    response = row.get("response") or {}
    output = response.get("output")
    error = row.get("error") or response.get("error")
    detail = {"metadata": response.get("metadata") or {}, "tokenUsage": response.get("tokenUsage"), "cost": row.get("cost"), "latencyMs": row.get("latencyMs")}
    if not error and not isinstance(output, str):
        error = "the probe produced no text output"
    return output if isinstance(output, str) else "", detail, str(error) if error else None


def run_probe(
    listing: str, fake_output: str | None = None, routing_dir: Path | None = None,
    ledger: ceilings.Ledger | None = None, settings: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prepare the Claude workspace for `listing`, ask the question once and return the probe document."""
    routing_dir = routing_dir or driver.ROUTING_DIR
    root = routing_dir / f"probe-{listing}"
    workspace = workspaces.prepare_workspace(root / AGENT, AGENT, listing=listing)
    real = workspaces.workspace_descriptions(root / AGENT, AGENT)
    requested = listing_presets.read(root / AGENT)
    error: str | None = None
    detail: dict[str, Any] = {}
    usage = {"tokens": 0, "cost_usd": 0.0}
    if fake_output is not None:
        output = fake_output
    else:
        ledger = ledger or ceilings.Ledger(ceilings.Ceilings.from_env())
        report = routing_dir / "reports" / f"probe-{listing}" / f"{AGENT}-probe.json"
        env = {"ROUTING_WORKSPACE_ROOT": str(root), PROMPT_ENV: PROMPT}
        try:
            ledger.check(AGENT)
            console, rows = runner.run_promptfoo(AGENT, PROBE_SKILL, report, None, env=env, ledger=ledger, config=PROBE_CONFIG)
            if rows is None:
                print(console)
            else:
                ledger.record(AGENT, rows)
            output, detail, error = _first_row(rows)
            usage = {k: round(v, 6) if isinstance(v, float) else v for k, v in ledger.spent.get(AGENT, usage).items()}
        except ceilings.CeilingBreach as exc:
            output, error = "", f"ceiling breached: {ceilings.describe(exc.breach)}"
    body = judge(real, parse_output(output, sorted(real)))
    complete = error is None and body["verdict"] != INCONCLUSIVE
    reason = error or ("the reply listed none of the workspace skills" if body["verdict"] == INCONCLUSIVE else None)
    return {
        "mode": "probe", "agent": AGENT, "listing": listing, "fingerprint": workspace.fingerprint,
        "complete": complete, "reason": reason, "exit_code": EXIT_OK if complete else EXIT_INCOMPLETE, **body,
        "exposed_skills": workspaces.exposed_skills(AGENT, real),
        "settings_requested": {"file": str(listing_presets.SETTINGS_FILE) if requested is not None else None, "content": requested},
        "provider": {"model": settings[AGENT]["model"]["value"], "effort": settings[AGENT]["effort"]["value"], "overridden": settings[AGENT]["overridden"]} if settings else {},
        "prompt": PROMPT, "raw_output": output, "response": detail, "usage": usage, "offline": fake_output is not None,
        "note": NOTE, **agents_lib.scope((AGENT,)),
    }


def render(doc: dict[str, Any]) -> list[str]:
    c = doc["counts"]
    lines = [
        f"listing probe ({doc['agent']}, listing={doc['listing']}, fingerprint {doc['fingerprint']}): {doc['verdict']}"
        f"{'' if doc['complete'] else ' [INCOMPLETE: ' + str(doc['reason']) + ']'}"
        f"{' [LEAK: ' + str(c['leaked']) + ' listed skill(s) not in the workspace: ' + ', '.join(doc.get('leaked_skills') or []) + ']' if doc.get('leaked_skills') else ''}",
        f"exposed skills (explicit list given to the model): {workspaces.describe_exposure(doc.get('exposed_skills'))}",
        f"{c['matching']}/{c['skills']} skills show a matching description; {c['description_shown']} show any description; "
        f"{c['listed']} listed; {c['unknown']} unknown names; {c['ignored_lines']} ignored lines",
        "",
        "| Skill | Listed | Description shown | Similarity | Shown / real length |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in doc["skills"]:
        score = "-" if r["similarity"] is None else f"{r['similarity']:.2f}{'' if r['matches'] else ' (no match)'}"
        lines.append(f"| {r['skill']} | {'yes' if r['listed'] else 'no'} | {'yes' if r['description_shown'] else 'no'} | {score} | {r['shown_length']} / {r['real_length']} |")
    requested = doc["settings_requested"]
    if not doc["offline"]:
        lines += ["", f"measured cost: ${doc['usage']['cost_usd']:.4f} ({doc['usage']['tokens']} tokens)"]
    lines += ["", f"settings requested: {json.dumps(requested['content']) if requested['content'] is not None else 'none (default listing writes no settings file)'}", doc["note"]]
    return lines


def render_comparison(doc: dict[str, Any]) -> list[str]:
    return [
        f"name-only honoured: {doc['conclusion']}",
        doc["why"],
        f"default: {doc['default']['verdict']} ({doc['default']['matching']}/{doc['skills']} matching); name-only: {doc['name_only']['verdict']} ({doc['name_only']['matching']}/{doc['skills']} matching)",
    ]


def report_path(listing: str) -> Path:
    return runner.REPORTS_DIR / f"probe-{listing}.json"


@runner.guarded
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--listing", help="default or name-only (default: ROUTING_SKILL_LISTING)")
    parser.add_argument("--fake-output", type=Path, help="offline mode: use this file as the model output; no provider call")
    parser.add_argument("--compare", action="store_true", help="compare the saved default and name-only probe reports (offline)")
    args = parser.parse_args(argv[1:])
    if args.compare:
        try:
            docs = [json.loads(report_path(name).read_text()) for name in listing_presets.PRESETS]
            result = compare(*docs)
        except (OSError, ValueError, KeyError) as exc:
            print(f"ERROR: need both probe reports from the same workspace ({report_path('default')}, {report_path('name-only')}): {exc}", file=sys.stderr)
            return runner.HARNESS_ERROR
        print("\n".join(render_comparison(result)))
        return EXIT_OK
    try:
        listing = listing_presets.selected() if args.listing is None else listing_presets.parse_setting(args.listing)
        settings = settings_lib.load()
        fake = args.fake_output.read_text() if args.fake_output else None
        if warning := settings_lib.warning(settings):
            print(warning, file=sys.stderr)
        doc = run_probe(listing, fake_output=fake, settings=settings)
    except (ValueError, OSError, workspaces.WorkspaceIntegrityError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return runner.HARNESS_ERROR
    runner.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path(listing).write_text(json.dumps(doc, indent=2) + "\n")
    print("\n".join(render(doc)))
    return doc["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
