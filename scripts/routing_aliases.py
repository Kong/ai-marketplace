"""Opaque skill aliases for routing evals. Offline; no model calls.

A descriptive skill name (`konnect-gateway-triage`) lets an agent route without reading the
description, so a destroyed description goes unnoticed. In the eval workspaces every skill is
renamed to a deterministic opaque alias, so routing can only come from the description.

    alias = "s-" + first 6 hex of sha1(real name)

The alias depends on the name alone: stable across runs, between candidate and control, and
independent of which other skills exist. Two names that collide raise an error.

ROUTING_ALIAS_SKILLS (1/0/true/false) turns aliasing on or off; unset or empty means
DEFAULT_ALIAS_SKILLS. An invalid value is an error (exit 2 in the scripts).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

# The one place the default lives. Flip it here to change what CI and local runs measure.
DEFAULT_ALIAS_SKILLS = True
ENV_VAR = "ROUTING_ALIAS_SKILLS"
ALIASES_FILE = "aliases.json"
PREFIX = "s-"
DIGEST_LENGTH = 6

_TRUE, _FALSE = ("1", "true"), ("0", "false")


def parse_setting(value: str | None) -> bool:
    """Parse ROUTING_ALIAS_SKILLS; unset or empty means the default, anything else invalid is an error."""
    if value is None or value.strip() == "":
        return DEFAULT_ALIAS_SKILLS
    lowered = value.strip().lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ValueError(f"{ENV_VAR} must be one of 1, 0, true, false, got {value!r}")


def enabled(env: Mapping[str, str] | None = None) -> bool:
    return parse_setting((os.environ if env is None else env).get(ENV_VAR))


def alias_for(name: str) -> str:
    return PREFIX + hashlib.sha1(name.encode("utf-8")).hexdigest()[:DIGEST_LENGTH]


def build_aliases(names: Iterable[str]) -> dict[str, str]:
    """Map each real skill name to its alias; ValueError on a duplicate name or an alias collision."""
    aliases: dict[str, str] = {}
    owners: dict[str, str] = {}
    for name in sorted(names):
        if name in aliases:
            raise ValueError(f"duplicate skill name {name!r}")
        alias = alias_for(name)
        if alias in owners:
            raise ValueError(f"skill alias collision: {owners[alias]!r} and {name!r} both map to {alias}")
        aliases[name] = alias
        owners[alias] = name
    return aliases


def _whole_word_pattern(names: Iterable[str]) -> re.Pattern[str] | None:
    # Longest first so `a-b-c` wins over `a-b`; the lookarounds keep a match from starting or ending
    # inside a longer kebab-case word.
    ordered = sorted(names, key=lambda n: (-len(n), n))
    if not ordered:
        return None
    return re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(n) for n in ordered) + r")(?![\w-])")


def substitute(text: str, mapping: Mapping[str, str]) -> str:
    """Replace whole-word occurrences of any mapping key by its value, in one pass, longest key first."""
    pattern = _whole_word_pattern(mapping)
    return pattern.sub(lambda m: mapping[m.group(0)], text) if pattern else text


def alias_description(description: str, aliases: Mapping[str, str]) -> str:
    """A description with every real skill name replaced by its alias, so cross-references stay consistent."""
    return substitute(description, aliases)


def reverse(aliases: Mapping[str, str]) -> dict[str, str]:
    return {alias: name for name, alias in aliases.items()}


def to_real(text: str, aliases: Mapping[str, str] | None) -> str:
    """Rewrite aliases in free text (a skill name, a grading reason) back to real names."""
    return substitute(text, reverse(aliases)) if aliases else text


def write(workspace: Path, aliases: Mapping[str, str]) -> None:
    (workspace / ALIASES_FILE).write_text(json.dumps(dict(sorted(aliases.items())), indent=2) + "\n")


def load(workspace: Path) -> dict[str, str] | None:
    """The workspace's real->alias map, or None when the workspace is not aliased."""
    path = workspace / ALIASES_FILE
    if not path.is_file():
        return None
    data: Any = json.loads(path.read_text())
    if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
        raise ValueError(f"{path}: aliases must map skill names to alias strings")
    return data


def rewrite_skill_md(text: str, alias: str | None, description: str | None) -> str:
    """Rewrite one SKILL.md frontmatter: `name` to `alias` and/or `description` to the new text.

    Only those two top-level fields change; the rest of the frontmatter and the whole body are kept
    byte for byte. `None` leaves a field alone.
    """
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("SKILL.md has no YAML frontmatter")
    head, rest = text[4:].split("\n---\n", 1)
    replacements = {"name": alias, "description": description}
    out: list[str] = []
    found: set[str] = set()
    skipping = False
    for line in head.split("\n"):
        if skipping and line[:1] in (" ", "\t"):
            continue  # continuation of a replaced multi-line value
        skipping = False
        key = re.match(r"^(name|description):", line)
        if key and key.group(1) not in found and replacements[key.group(1)] is not None:
            found.add(key.group(1))
            # A JSON string is a valid double-quoted YAML scalar, whatever punctuation the text holds.
            out.append(f"{key.group(1)}: {json.dumps(replacements[key.group(1)], ensure_ascii=False)}")
            skipping = True
            continue
        out.append(line)
    missing = {k for k, v in replacements.items() if v is not None} - found
    if missing:
        raise ValueError(f"SKILL.md frontmatter lacks {', '.join(sorted(missing))}")
    return "---\n" + "\n".join(out) + "\n---\n" + rest
