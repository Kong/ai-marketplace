"""Decide which changed skills have a changed *routing surface*. Offline: git and YAML only.

An agent picks a skill from what it can see before the skill loads: the SKILL.md frontmatter `name`
and `description`. A body, references or scripts edit cannot change which skill is selected, so it
needs no routing eval. The surface is every top-level frontmatter field except the inert
`license` and `metadata` (repo bookkeeping that no agent reads when choosing a skill, including
`metadata.internal`). Any other key, say a future `disable-model-invocation`, is included so it is
never assumed inert. Frontmatter is parsed and compared as data, so quoting, folding and key order
do not count; the description's exact value does.

    classify(repo, base_ref, head_ref) -> {skill name: status}

Status: `new` (name absent at base, no directory rename), `renamed` (name or directory changed),
`surface_changed`, `body_changed` (SKILL.md text changed, surface did not) and `files_changed`
(only other files in the skill directory changed). The first three trigger an eval. A deleted skill
(`deleted`) is reported by select_changed; nothing remains to evaluate for it, and scenarios that
referenced it must be edited, which the scenario-change rule then evaluates.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

import select_changed

INERT_FIELDS = frozenset({"license", "metadata"})
NEW, RENAMED, SURFACE_CHANGED, BODY_CHANGED, FILES_CHANGED = "new", "renamed", "surface_changed", "body_changed", "files_changed"
TRIGGERS = (NEW, RENAMED, SURFACE_CHANGED)
NOTICES = {
    BODY_CHANGED: "SKILL.md body changed, routing surface unchanged: skipped",
    FILES_CHANGED: "skill files other than SKILL.md changed, routing surface unchanged: skipped",
}


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) != 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def surface(frontmatter: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in frontmatter.items() if key not in INERT_FIELDS}


def _skill_texts(repo: Path, ref: str) -> dict[tuple[str, str], str]:
    """SKILL.md text at `ref` keyed by (plugin, directory)."""
    texts: dict[tuple[str, str], str] = {}
    for path in select_changed.git(repo, "ls-tree", "-r", "--name-only", ref).splitlines():
        match = select_changed.SKILL_MD_PATTERN.match(path)
        if match:
            texts[match.groups()] = select_changed.git(repo, "show", f"{ref}:{path}")
    return texts


def merge_base(repo: Path, base: str, head: str) -> str:
    out = subprocess.run(["git", "merge-base", base, head], cwd=repo, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        raise select_changed.SelectionError(f"cannot find merge base of {base} and {head}: {out.stderr.strip()}")
    return out.stdout.strip()


def classify(repo: Path, base: str, head: str = "HEAD") -> dict[str, str]:
    """Status of every skill touched between the merge base of `base`/`head` and `head`."""
    mb = merge_base(repo, base, head)
    entries = select_changed.diff_entries(repo, mb, head)
    touched = {found for _, paths in entries for found in (select_changed.skill_dir(p) for p in paths) if found}
    base_texts, head_texts = _skill_texts(repo, mb), _skill_texts(repo, head)
    base_by_dir: dict[str, tuple[str, str]] = {}
    for key in base_texts:
        base_by_dir.setdefault(key[1], key)
    base_names = {fm["name"] for fm in (parse_frontmatter(t) for t in base_texts.values()) if fm and isinstance(fm.get("name"), str)}
    renamed_dirs = {
        pair["to"]: pair["from"] for pair in select_changed.select(repo, mb, head)["renamed"]
    }
    status: dict[str, str] = {}
    for key in sorted(touched):
        text = head_texts.get(key)
        fm = parse_frontmatter(text) if text is not None else None
        if fm is None or not isinstance(fm.get("name"), str):
            continue  # deleted, or not a usable skill (lint reports that)
        name = fm["name"]
        old_key = key if key in base_texts else base_by_dir.get(renamed_dirs.get(key[1], ""))
        old_fm = parse_frontmatter(base_texts[old_key]) if old_key else None
        if old_key is None or old_fm is None:
            status[name] = RENAMED if key[1] in renamed_dirs else (NEW if name not in base_names else SURFACE_CHANGED)
        elif old_key != key or old_fm.get("name") != name:
            status[name] = RENAMED
        elif surface(old_fm) != surface(fm):
            status[name] = SURFACE_CHANGED
        elif base_texts[old_key] != text:
            status[name] = BODY_CHANGED
        else:
            status[name] = FILES_CHANGED
    return status
