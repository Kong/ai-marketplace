"""Skill-listing presets for the Claude routing eval workspace. Offline; no model calls.

Opt-in and experimental, for diagnosis, never the gate. Claude is shown a listing of every skill's
name and description (https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short). The
listing has a character budget; when it overflows, descriptions are dropped starting with the least
used skills and only names reach the model. These presets run the same eval with a different listing,
to test whether descriptions reach the model at all in this workspace:

    default   no extra settings: current behaviour
    wide      raise the budget and the per-description cap so every description is listed in full
    name-only every skill set to "name-only" through `skillOverrides`: names only, no descriptions

A preset is written as `<workspace>/.claude/settings.json` (project settings, read because the Claude
config keeps `setting_sources: ['project']`). Presets are fixed constants: nothing else is ever
written, so a dispatch input cannot smuggle in settings such as hooks. Codex has no equivalent.

ROUTING_SKILL_LISTING (default, wide, name-only; unset or empty means default) selects the preset; an
invalid value is an error (exit 2 in the scripts).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT = "default"
WIDE = "wide"
NAME_ONLY = "name-only"
PRESETS = (DEFAULT, WIDE, NAME_ONLY)
ENV_VAR = "ROUTING_SKILL_LISTING"
SETTINGS_FILE = Path(".claude/settings.json")

# skillListingBudgetFraction is a fraction of the context window in (0, 1] (documented default 0.01);
# skillListingMaxDescChars is a positive integer (documented default 1536). Both are far above what
# the workspace needs, so no description is dropped or cut.
WIDE_SETTINGS: dict[str, Any] = {"skillListingBudgetFraction": 0.25, "skillListingMaxDescChars": 8192}
NAME_ONLY_STATE = "name-only"


def parse_setting(value: str | None) -> str:
    """Parse ROUTING_SKILL_LISTING; unset or empty means the default, anything else invalid is an error."""
    if value is None or value.strip() == "":
        return DEFAULT
    lowered = value.strip().lower()
    if lowered in PRESETS:
        return lowered
    raise ValueError(f"{ENV_VAR} must be one of {', '.join(PRESETS)}, got {value!r}")


def selected(env: Mapping[str, str] | None = None) -> str:
    return parse_setting((os.environ if env is None else env).get(ENV_VAR))


def settings_for(preset: str, skill_names: Iterable[str]) -> dict[str, Any] | None:
    """The settings document of `preset` for a workspace holding `skill_names`; None for default.

    `skill_names` are the names as they appear in the workspace (the aliases when aliased), which is
    what `skillOverrides` matches.
    """
    if preset not in PRESETS:
        raise ValueError(f"unknown skill listing preset {preset!r}; expected one of {', '.join(PRESETS)}")
    if preset == WIDE:
        return dict(WIDE_SETTINGS)
    if preset == NAME_ONLY:
        return {"skillOverrides": {name: NAME_ONLY_STATE for name in sorted(skill_names)}}
    return None


def settings_path(workspace: Path) -> Path:
    return workspace / SETTINGS_FILE


def write(workspace: Path, preset: str, skill_names: Iterable[str]) -> None:
    """Write the preset's settings file into a Claude workspace; default writes nothing.

    An existing settings file is an error, never merged: the preset must be the only settings.
    """
    document = settings_for(preset, skill_names)
    path = settings_path(workspace)
    if path.exists():
        raise ValueError(f"{path} already exists; refusing to merge skill listing settings into it")
    if document is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def read(workspace: Path) -> dict[str, Any] | None:
    """The workspace's settings document, or None when it has none."""
    path = settings_path(workspace)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"{path}: not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path}: settings must be a JSON object")
    return data


def check_agents(preset: str, agents: Iterable[str]) -> None:
    """ValueError when a non-default preset would run on an agent other than claude."""
    others = sorted(set(agents) - {"claude"})
    if preset != DEFAULT and others:
        raise ValueError(f"{ENV_VAR}={preset} applies to the claude agent only; {', '.join(others)} has no skill-listing settings (run with --agent claude)")
