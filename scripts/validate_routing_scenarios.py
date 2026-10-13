"""Offline validation for routing scenarios under evals/routing/.

Each *.yaml file declares one target skill and a list of scenarios:

    skill: konnect-gateway-triage
    scenarios:
      - id: gateway-triage-positive-1   # unique across all files
        prompt: "..."
        expect: [konnect-gateway-triage]  # skills that must activate
        forbid: []                        # skills that must not activate
        trials: 3                         # 1-5
        tags: [positive]                  # positive | near-miss | sibling

No provider credentials or model calls are used.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

import check_repo

SCENARIOS_DIR = check_repo.REPO_ROOT / "evals" / "routing"
ALLOWED_TAGS = {"positive", "near-miss", "sibling"}
MIN_TRIALS = 1
MAX_TRIALS = 5
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FILE_KEYS = {"skill", "scenarios"}
SCENARIO_KEYS = {"id", "prompt", "expect", "forbid", "trials", "tags"}


def known_skill_names() -> set[str]:
    return {
        skill.name
        for plugin in check_repo.discover_plugins()
        for skill in check_repo.discover_skills(plugin)
    }


def skill_list(value: object, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        errors.append(f"{label} must be a list of skill names")
        return []
    if len(set(value)) != len(value):
        errors.append(f"{label} contains duplicate skills")
    return value


def validate_scenario(
    scenario: object, label: str, skills: set[str], seen_ids: dict[str, str]
) -> list[str]:
    if not isinstance(scenario, dict):
        return [f"{label}: scenario must be a mapping"]
    errors: list[str] = []
    for key in sorted(set(scenario) - SCENARIO_KEYS):
        errors.append(f"{label}: unknown field {key!r}")
    for key in sorted(SCENARIO_KEYS - set(scenario)):
        errors.append(f"{label}: missing field {key!r}")

    scenario_id = scenario.get("id")
    if isinstance(scenario_id, str) and ID_PATTERN.match(scenario_id):
        label = f"{label} ({scenario_id})"
        if scenario_id in seen_ids:
            errors.append(f"{label}: duplicate id, first defined in {seen_ids[scenario_id]}")
        else:
            seen_ids[scenario_id] = label
    elif "id" in scenario:
        errors.append(f"{label}: id must be lowercase kebab-case")

    prompt = scenario.get("prompt")
    if "prompt" in scenario and (not isinstance(prompt, str) or not prompt.strip()):
        errors.append(f"{label}: prompt must be a non-empty string")

    expect = skill_list(scenario["expect"], f"{label}: expect", errors) if "expect" in scenario else []
    forbid = skill_list(scenario["forbid"], f"{label}: forbid", errors) if "forbid" in scenario else []
    if "expect" in scenario and "forbid" in scenario and not expect and not forbid:
        errors.append(f"{label}: expect and forbid cannot both be empty")
    for name in sorted(set(expect + forbid) - skills):
        errors.append(f"{label}: unknown skill {name!r}")
    for name in sorted(set(expect) & set(forbid)):
        errors.append(f"{label}: skill {name!r} is both expected and forbidden")

    trials = scenario.get("trials")
    if "trials" in scenario and (
        not isinstance(trials, int) or isinstance(trials, bool) or not MIN_TRIALS <= trials <= MAX_TRIALS
    ):
        errors.append(f"{label}: trials must be an integer from {MIN_TRIALS} to {MAX_TRIALS}")

    tags = scenario.get("tags")
    if "tags" in scenario:
        if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) for tag in tags):
            errors.append(f"{label}: tags must be a non-empty list of strings")
        else:
            for tag in sorted(set(tags) - ALLOWED_TAGS):
                errors.append(f"{label}: unknown tag {tag!r}; allowed: {sorted(ALLOWED_TAGS)}")
    return errors


def validate_file(path: Path, skills: set[str], seen_ids: dict[str, str]) -> list[str]:
    label = str(path.relative_to(check_repo.REPO_ROOT)) if path.is_relative_to(check_repo.REPO_ROOT) else str(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        return [f"{label}: unparseable YAML: {exc}"]
    if not isinstance(data, dict):
        return [f"{label}: top level must be a mapping"]

    errors = [f"{label}: unknown field {key!r}" for key in sorted(set(data) - FILE_KEYS)]
    target = data.get("skill")
    if not isinstance(target, str) or target not in skills:
        errors.append(f"{label}: target skill {target!r} is not a known skill")
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append(f"{label}: scenarios must be a non-empty list")
        return errors
    for index, scenario in enumerate(scenarios, start=1):
        errors.extend(validate_scenario(scenario, f"{label}#{index}", skills, seen_ids))
    return errors


def validate_scenarios(directory: Path, skills: set[str]) -> list[str]:
    if not directory.is_dir():
        return []
    seen_ids: dict[str, str] = {}
    errors: list[str] = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix in {".yaml", ".yml"}:
            errors.extend(validate_file(path, skills, seen_ids))
        elif path.is_file():
            errors.append(f"{path}: scenario files must use .yaml or .yml")
    return errors


def main() -> int:
    try:
        skills = known_skill_names()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    errors = validate_scenarios(SCENARIOS_DIR, skills)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print("routing-scenarios-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
