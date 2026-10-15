"""Print the effective routing eval configuration. Offline: no credentials, no model calls.

    python scripts/print_routing_config.py [--json]

Per agent: effective model and effort, marked default or override (ROUTING_CODEX_MODEL,
ROUTING_CODEX_EFFORT, ROUTING_CLAUDE_MODEL, ROUTING_CLAUDE_EFFORT), plus the fixed discovery
settings, trial policy, and ceilings (defaults and variable names) read from their owning
modules. Invalid override values exit 2, as they do for the eval scripts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import routing_agents as agents_lib
import routing_ceilings as ceilings
import routing_selection as selection
import routing_settings as settings_lib
import validate_routing_scenarios as scenarios


def trial_policy() -> dict[str, Any]:
    return {
        "scenario_trials": {"min": scenarios.MIN_TRIALS, "max": scenarios.MAX_TRIALS},
        "new_skill_trials": scenarios.NEW_SKILL_TRIALS,
        "gate_first_pass_trials": 1,
        "max_scenarios_per_skill": selection.MAX_SCENARIOS_PER_SKILL,
        "pass_rule": "a scenario passes with at least ceil(2/3 * trials) passing trials",
    }


def ceiling_defaults() -> dict[str, str]:
    return dict(ceilings.DEFAULTS)


def collect() -> dict[str, Any]:
    loaded = settings_lib.load_all()
    return {
        "agents": loaded["settings"],
        "overridden": any(doc["overridden"] for doc in loaded["settings"].values()),
        "fixed": loaded["fixed"],
        "trials": trial_policy(),
        "ceilings": {"defaults": ceiling_defaults(), "effective": vars(ceilings.Ceilings.from_env())},
        "selectable_agents": list(agents_lib.AGENTS),
        "override_variables": list(settings_lib.OVERRIDE_VARIABLES),
    }


def render(config: dict[str, Any]) -> str:
    lines = ["Routing eval configuration (CI always uses the pinned defaults)", ""]
    for agent, doc in config["agents"].items():
        lines.append(f"{agent}: {settings_lib.describe(doc)}")
    if config["overridden"]:
        active = [name for name in config["override_variables"] if os.environ.get(name)]
        lines.append(f"  overridden: true ({', '.join(active)} set)")
    lines += ["", f"Selectable agents (--agent, repeatable or comma-separated; default all): {', '.join(config['selectable_agents'])}"]
    lines += ["", "Fixed discovery settings (not configurable):"]
    for agent, fixed in config["fixed"].items():
        lines.append(f"  {agent}: " + ", ".join(f"{k}={json.dumps(v)}" for k, v in fixed.items()))
    trials = config["trials"]
    lines += [
        "",
        f"Trials: scenarios {trials['scenario_trials']['min']}-{trials['scenario_trials']['max']}; "
        f"new skills {trials['new_skill_trials']} on positive/near-miss; gate first pass {trials['gate_first_pass_trials']} per scenario "
        f"(failures confirmed at the scenario's own trials), at most {trials['max_scenarios_per_skill']} scenarios per skill; "
        f"{trials['pass_rule']}",
        "",
        "Ceilings (variable: default):",
    ]
    effective = config["ceilings"]["effective"]
    for name, default in config["ceilings"]["defaults"].items():
        lines.append(f"  {name}: {default}")
    lines.append(f"  effective: {json.dumps(effective)}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv[1:])
    try:
        config = collect()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(config, indent=2) if args.json else render(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
