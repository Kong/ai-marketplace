"""Resolve which skills a routing eval run covers, one skill name per line.

    routing_targets.py skill NAME
    routing_targets.py all
    routing_targets.py changed [--base REF]   (default base: origin/main, else main)
    routing_targets.py adjacent [--base REF]

`skill` requires the named skill to have scenarios. `all`, `changed` and `adjacent` cover
only skills that have scenarios under evals/routing/ and report the rest on stderr, so a
skill without a corpus is never silently counted as passing. `changed` and `adjacent` use
select_changed.py: `changed` lists changed skills, `adjacent` lists their (capped) adjacent
skills, kept for the preview and local use (the workflow selects at scenario level through
routing_selection.py and no longer runs adjacent skills wholesale). A changed skill that is new at the
merge base must already meet the new-skill scenario minimums (exit 2 otherwise), so a new
skill cannot pass by having no corpus. Modified skills without scenarios are only a NOTE.
No model calls.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

import check_repo
import select_changed
import validate_routing_scenarios as scenarios


def covered_skills(directory: Path = scenarios.SCENARIOS_DIR) -> set[str]:
    """Target skills declared by scenario files; run the validator first for malformed files."""
    found: set[str] = set()
    for path in sorted(directory.rglob("*.y*ml")) if directory.is_dir() else []:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("skill"), str):
            found.add(data["skill"])
    return found


def default_base(repo: Path) -> str:
    for ref in ("origin/main", "main"):
        if subprocess.run(["git", "rev-parse", "--verify", "-q", ref], cwd=repo, capture_output=True).returncode == 0:
            return ref
    raise select_changed.SelectionError("no origin/main or main ref; pass --base")


def new_skills(repo: Path, base: str, changed: list[str]) -> list[str]:
    """Changed skills absent at the merge base of `base` and HEAD."""
    out = subprocess.run(["git", "merge-base", base, "HEAD"], cwd=repo, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        raise select_changed.SelectionError(f"cannot find merge base of {base} and HEAD: {out.stderr.strip()}")
    catalog, _ = select_changed.load_catalog(repo, out.stdout.strip())
    existing = {skill.name for skill in catalog.values()}
    return [skill for skill in changed if skill not in existing]


def new_skill_errors(skill: str) -> list[str]:
    return scenarios.new_skill_minimum_errors(scenarios.SCENARIOS_DIR, skill, scenarios.adjacent_skills(skill))


def resolve(mode: str, name: str | None, base: str | None, covered: set[str], repo: Path) -> tuple[list[str], list[str]]:
    """Return (skills to evaluate, notices)."""
    if mode == "skill":
        if name not in covered:
            raise ValueError(f"no routing scenarios for skill {name!r}; covered: {sorted(covered)}")
        return [name], []
    if mode == "all":
        return sorted(covered), []
    base = base or default_base(repo)
    result = select_changed.select(repo, base)
    if mode == "adjacent":
        adjacent = [skill for skill in result["adjacent"] if skill in covered]
        notices = [f"{skill}: adjacent but has no routing scenarios, skipped" for skill in result["adjacent"] if skill not in covered]
        return adjacent, notices
    errors = [error for skill in new_skills(repo, base, result["changed"]) for error in new_skill_errors(skill)]
    if errors:
        raise ValueError("scenario_validation: " + "; ".join(errors))
    changed = [skill for skill in result["changed"] if skill in covered]
    notices = [f"{skill}: changed but has no routing scenarios, skipped" for skill in result["changed"] if skill not in covered]
    return changed, notices


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["changed", "adjacent", "skill", "all"])
    parser.add_argument("name", nargs="?", help="skill name (skill mode only)")
    parser.add_argument("--base", help="git base ref for changed mode")
    args = parser.parse_args(argv)
    if (args.mode == "skill") != bool(args.name):
        parser.error("a skill name is required for `skill` mode and not accepted otherwise")
    try:
        skills, notices = resolve(args.mode, args.name, args.base, covered_skills(), check_repo.REPO_ROOT)
    except (ValueError, select_changed.SelectionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for notice in notices:
        print(f"NOTE: {notice}", file=sys.stderr)
    if not skills:
        print("NOTE: no skills with routing scenarios selected", file=sys.stderr)
    print("\n".join(skills))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
