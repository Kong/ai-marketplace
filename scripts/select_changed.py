"""Select skills for a routing evaluation from a base/head git diff.

Deterministic: no model calls, no network. Prints JSON:

    changed   skill names whose directory changed and still exists at head
    adjacent  routers, then skills named in a changed SKILL.md, then the
              nearest descriptions, capped at MAX_ADJACENT in total
    selected  changed + adjacent; empty when no skill directory changed
    removed   skill directories deleted at head (nothing to evaluate)
    renamed   old -> new skill directory pairs (new is selected)
    ignored   diagnostics for unusable paths or unknown skill references

Usage: select_changed.py BASE [HEAD]   (HEAD defaults to HEAD)

The diff is BASE...HEAD, so only changes since the merge base count. Paths
outside plugins/<plugin>/skills/<skill>/ never select anything, and there is no
fallback to the full catalog, and a diff that would select every skill is refused.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

import check_repo

MAX_ADJACENT = 5
ROUTER_CATEGORY = "routing"
SKILL_MD_PATTERN = re.compile(r"^plugins/([^/]+)/skills/([^/]+)/SKILL\.md$")
SKILL_PATH_PATTERN = re.compile(r"^plugins/([^/]+)/skills/([^/]+)/")
BACKTICKED_PATTERN = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")
# "Use `name`" handoff sentences; a hyphenated name that is not a skill is an invalid reference.
HANDOFF_PATTERN = re.compile(r"\b[Uu]se `([a-z0-9]+(?:-[a-z0-9]+)+)`")


class SelectionError(Exception):
    pass


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SelectionError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def skill_dir(path: str) -> tuple[str, str] | None:
    match = SKILL_PATH_PATTERN.match(path)
    return (match.group(1), match.group(2)) if match else None


def diff_entries(repo: Path, base: str, head: str) -> list[tuple[str, list[str]]]:
    """Return (status letter, paths) per entry of `git diff -M BASE...HEAD`."""
    tokens = git(repo, "diff", "--name-status", "-M", "-z", f"{base}...{head}").split("\0")
    entries: list[tuple[str, list[str]]] = []
    index = 0
    while index < len(tokens) and tokens[index]:
        status = tokens[index][0]
        width = 2 if status in {"R", "C"} else 1
        entries.append((status, tokens[index + 1 : index + 1 + width]))
        index += 1 + width
    return entries


def load_catalog(repo: Path, head: str) -> tuple[dict[tuple[str, str], check_repo.Skill], dict[str, str]]:
    """Read every skill at head from git, keyed by (plugin, dir). Also return SKILL.md text by name."""
    catalog: dict[tuple[str, str], check_repo.Skill] = {}
    texts: dict[str, str] = {}
    for path in git(repo, "ls-tree", "-r", "--name-only", head).splitlines():
        match = SKILL_MD_PATTERN.match(path)
        if not match:
            continue
        text = git(repo, "show", f"{head}:{path}")
        parts = text.split("---", 2)
        frontmatter = yaml.safe_load(parts[1]) if text.startswith("---") and len(parts) == 3 else None
        if not isinstance(frontmatter, dict) or not isinstance(frontmatter.get("name"), str):
            continue
        metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
        plugin, dirname = match.groups()
        name = frontmatter["name"]
        catalog[(plugin, dirname)] = check_repo.Skill(
            plugin_name=plugin,
            dir_name=dirname,
            name=name,
            description=str(frontmatter.get("description") or ""),
            license=str(frontmatter.get("license") or ""),
            product=str(metadata.get("product") or ""),
            category=str(metadata.get("category") or ""),
            tags=list(metadata.get("tags") or []),
        )
        texts[name] = text
    return catalog, texts


def named_siblings(text: str, own: str, known: set[str]) -> list[str]:
    """Known skill names backticked in a SKILL.md, in order of first appearance."""
    found = dict.fromkeys(BACKTICKED_PATTERN.findall(text))
    return [name for name in found if name in known and name != own]


def nearest_neighbours(target: check_repo.Skill, others: list[check_repo.Skill]) -> list[str]:
    """Other skills ranked by description term overlap (Jaccard), as in the repo overlap lint."""
    target_terms = check_repo.description_terms(target)
    scored: list[tuple[float, str]] = []
    for other in others:
        terms = check_repo.description_terms(other)
        union = target_terms | terms
        score = len(target_terms & terms) / len(union) if union else 0.0
        if score > 0:
            scored.append((-score, other.name))
    return [name for _, name in sorted(scored)]


def adjacent_for(
    target: check_repo.Skill, catalog: list[check_repo.Skill], texts: dict[str, str]
) -> list[str]:
    """Priority-ordered adjacent candidates for one changed skill: routers, named siblings, nearest."""
    others = [skill for skill in catalog if skill.name != target.name]
    known = {skill.name for skill in others}
    routers = [skill.name for skill in others if skill.category == ROUTER_CATEGORY]
    siblings = named_siblings(texts[target.name], target.name, known)
    return list(dict.fromkeys(routers + siblings + nearest_neighbours(target, others)))


def merge_round_robin(lists: list[list[str]], exclude: set[str], cap: int) -> list[str]:
    """Interleave per-skill candidate lists so no changed skill starves the others, up to cap."""
    merged: list[str] = []
    for rank in range(max((len(items) for items in lists), default=0)):
        for items in lists:
            if rank < len(items) and items[rank] not in exclude and items[rank] not in merged:
                merged.append(items[rank])
                if len(merged) == cap:
                    return merged
    return merged


def select(repo: Path, base: str, head: str = "HEAD") -> dict[str, object]:
    entries = diff_entries(repo, base, head)
    ignored: list[str] = []
    touched: set[tuple[str, str]] = set()
    renamed: list[dict[str, str]] = []
    for status, paths in entries:
        dirs = [found for found in (skill_dir(path) for path in paths) if found]
        touched.update(dirs)
        if status == "R" and len(dirs) == 2 and dirs[0] != dirs[1]:
            renamed.append({"from": dirs[0][1], "to": dirs[1][1]})

    catalog, texts = load_catalog(repo, head)
    renamed_from = {pair["from"] for pair in renamed}
    changed_skills: list[check_repo.Skill] = []
    removed: list[str] = []
    for key in sorted(touched):
        if key in catalog:
            changed_skills.append(catalog[key])
        elif key[1] in renamed_from:
            continue
        else:
            removed.append(key[1])
            ignored.append(f"plugins/{key[0]}/skills/{key[1]}: no SKILL.md at head, not selected")

    all_skills = list(catalog.values())
    known = {skill.name for skill in all_skills}
    for skill in changed_skills:
        for name in sorted(set(HANDOFF_PATTERN.findall(texts[skill.name])) - known):
            ignored.append(f"{skill.name}: references unknown skill {name!r}")

    changed = [skill.name for skill in changed_skills]
    adjacent = merge_round_robin(
        [adjacent_for(skill, all_skills, texts) for skill in changed_skills], set(changed), MAX_ADJACENT
    )
    if len(all_skills) > MAX_ADJACENT + 1 and {skill.name for skill in all_skills} <= set(changed) | set(adjacent):
        raise SelectionError("selection would cover the full catalog; run named skills manually instead")
    return {
        "changed": changed,
        "adjacent": adjacent,
        "selected": changed + adjacent,
        "removed": removed,
        "renamed": renamed,
        "ignored": ignored,
    }


def main(argv: list[str]) -> int:
    if not 1 <= len(argv) <= 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        result = select(check_repo.REPO_ROOT, argv[0], argv[1] if len(argv) == 2 else "HEAD")
    except SelectionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
