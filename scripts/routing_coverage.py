"""List which skills have routing eval scenarios. Offline: no credentials, no model calls.

    python scripts/routing_coverage.py [--json]

Every skill under plugins/*/skills/ is covered (a scenario file under evals/routing/ targets
it; counts by tag are shown) or uncovered. For covered skills it also reports, as information
only, whether the corpus currently meets the new-skill minimums (validate_routing_scenarios.py).
Evals are advisory, so this never fails on gaps: exit 0, or 2 on a real error.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import validate_routing_scenarios as scenarios

TAGS = sorted(scenarios.KIND_TAGS)
DESIGN_TAGS = sorted(scenarios.DESIGN_TAGS)


def skill_entry(name: str) -> dict[str, Any]:
    found = scenarios.target_scenarios(scenarios.SCENARIOS_DIR, name)
    if not found:
        return {"skill": name, "covered": False}
    counts = {tag: sum(tag in (s.get("tags") or []) for s in found) for tag in TAGS}
    gaps = scenarios.new_skill_minimum_errors(scenarios.SCENARIOS_DIR, name, scenarios.adjacent_skills(name))
    return {
        "skill": name,
        "covered": True,
        "scenarios": len(found),
        "tags": counts,
        "design_tags": {tag: sum(tag in (s.get("tags") or []) for s in found) for tag in DESIGN_TAGS},
        "meets_new_skill_minimums": not gaps,
        "new_skill_gaps": gaps,
    }


def collect() -> dict[str, Any]:
    entries = [skill_entry(name) for name in sorted(scenarios.known_skill_names())]
    covered = sum(entry["covered"] for entry in entries)
    return {
        "summary": f"{covered} of {len(entries)} skills covered",
        "covered": covered,
        "total": len(entries),
        "skills": entries,
    }


def render(report: dict[str, Any]) -> str:
    lines = [report["summary"], ""]
    for entry in report["skills"]:
        if not entry["covered"]:
            lines.append(f"uncovered  {entry['skill']}")
            continue
        mix = ", ".join(f"{entry['tags'][tag]} {tag}" for tag in TAGS)
        design = ", ".join(f"{count} {tag}" for tag, count in entry["design_tags"].items() if count)
        mix = f"{mix}; design: {design}" if design else mix
        minimums = "meets" if entry["meets_new_skill_minimums"] else "below"
        lines.append(f"covered    {entry['skill']}: {entry['scenarios']} scenarios ({mix}); {minimums} new-skill minimums")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv[1:])
    try:
        report = collect()
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
