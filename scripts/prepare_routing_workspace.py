"""Materialize a per-agent project workspace exposing every repo skill for routing evals.

Claude discovers project skills under <workspace>/.claude/skills/<name>/ and Codex
under <workspace>/.agents/skills/<name>/. Copies (not symlinks) keep the eval run
isolated from the checkout.

    python scripts/prepare_routing_workspace.py .tmp/routing/claude
    python scripts/prepare_routing_workspace.py .tmp/routing/codex --agent codex
    python scripts/prepare_routing_workspace.py .tmp/routing/control/claude --ref <merge-base>

With --ref, skills come from that git revision instead of the working tree (the control).

Skills keep their real names. For Claude only, ROUTING_SKILL_LISTING (routing_listing.py: default,
name-only; experimental, diagnosis only) writes <workspace>/.claude/settings.json; Codex rejects a
non-default preset (exit 2). After every build the workspace is checked
against the source revision (`verify_workspace`): a mismatch exits 2, so a stale or wrong workspace
never feeds an eval. The run prints a fingerprint, the hash of every description in the workspace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import check_repo
import routing_listing as listing_presets
import select_changed

TMP_ROOT = check_repo.REPO_ROOT / ".tmp"
AGENT_SKILLS_DIRS = {"claude": Path(".claude/skills"), "codex": Path(".agents/skills")}


def copy_skill_at_ref(plugin: str, dir_name: str, ref: str, dest: Path) -> None:
    """Write the files of one skill directory as of git `ref` into `dest`."""
    prefix = f"plugins/{plugin}/skills/{dir_name}/"
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", ref, "--", prefix],
        cwd=check_repo.REPO_ROOT, capture_output=True, check=True,
    ).stdout.decode()
    for path in filter(None, listing.split("\0")):
        blob = subprocess.run(
            ["git", "show", f"{ref}:{path}"], cwd=check_repo.REPO_ROOT, capture_output=True, check=True
        ).stdout
        target = dest / path[len(prefix):]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)


class WorkspaceIntegrityError(ValueError):
    """The workspace does not match the source revision it was built from."""


@dataclass(frozen=True)
class Workspace:
    names: list[str]  # skill names
    fingerprint: str
    listing: str = listing_presets.DEFAULT  # skill-listing preset the workspace was built with


def resolve_listing(agent: str, listing: str | None) -> str:
    """The skill-listing preset for `agent` (default: ROUTING_SKILL_LISTING); only Claude accepts a non-default one."""
    preset = listing_presets.selected() if listing is None else listing_presets.parse_setting(listing)
    if preset != listing_presets.DEFAULT and agent != "claude":
        raise ValueError(f"{listing_presets.ENV_VAR}={preset} applies to the claude agent only; {agent} has no skill-listing settings (run with --agent claude)")
    return preset


def source_skills(ref: str | None) -> dict[str, tuple[str, str, str]]:
    """Real skill name -> (plugin, dir name, description) as of `ref`, or the working tree when None."""
    found: dict[str, tuple[str, str, str]] = {}
    if ref is not None:
        catalog, _ = select_changed.load_catalog(check_repo.REPO_ROOT, ref)
        entries = [(plugin, dir_name, skill) for (plugin, dir_name), skill in sorted(catalog.items())]
    else:
        entries = [(plugin.name, skill.dir_name, skill) for plugin in check_repo.discover_plugins() for skill in check_repo.discover_skills(plugin)]
    for plugin, dir_name, skill in entries:
        if skill.name in found:
            raise ValueError(f"duplicate skill name {skill.name!r}")
        found[skill.name] = (plugin, dir_name, skill.description)
    return found


def fingerprint_of(descriptions: Mapping[str, str]) -> str:
    """Short hash of every (skill dir, description) pair in a workspace."""
    digest = hashlib.sha256()
    for name in sorted(descriptions):
        digest.update(f"{name}\0{descriptions[name]}\n".encode("utf-8"))
    return digest.hexdigest()[:12]


def skills_root_of(out: Path, agent: str) -> Path:
    return out / AGENT_SKILLS_DIRS[agent]


def workspace_descriptions(out: Path, agent: str) -> dict[str, str]:
    """Skill dir name -> frontmatter description as the workspace has it on disk."""
    root = skills_root_of(out, agent)
    return {
        entry.name: str(check_repo.parse_frontmatter(entry / "SKILL.md").get("description"))
        for entry in sorted(root.iterdir()) if entry.is_dir()
    }


def verify_workspace(
    out: Path, agent: str, ref: str | None = None,
    description_overrides: Mapping[str, str] | None = None, listing: str | None = None,
) -> Workspace:
    """Assert the workspace's SKILL.md frontmatter derives exactly from the source revision.

    Per skill the expected description is the source description (or the explicit override, used
    verbatim: the canary) and the expected name is the skill name. The directory set and the
    directory/name pairing must match too, as must the skill-listing settings file (exactly the
    preset's, absent for default). Raises WorkspaceIntegrityError listing every mismatch; returns the
    fingerprint.
    """
    listing = resolve_listing(agent, listing)
    overrides = dict(description_overrides or {})
    source = source_skills(ref)
    unknown = sorted(set(overrides) - set(source))
    if unknown:
        raise WorkspaceIntegrityError(f"description override for unknown skill(s): {', '.join(unknown)}")
    problems: list[str] = []
    root = skills_root_of(out, agent)
    present = {entry.name for entry in root.iterdir() if entry.is_dir()} if root.is_dir() else set()
    expected = {name: name for name in source}
    for missing in sorted(set(expected) - present):
        problems.append(f"skill directory {missing!r} ({expected[missing]}) is missing")
    for extra in sorted(present - set(expected)):
        problems.append(f"unexpected skill directory {extra!r}")
    descriptions: dict[str, str] = {}
    for dir_name in sorted(present & set(expected)):
        real = expected[dir_name]
        try:
            frontmatter = check_repo.parse_frontmatter(root / dir_name / "SKILL.md")
        except (OSError, ValueError) as exc:
            problems.append(f"{dir_name}: unreadable SKILL.md frontmatter: {exc}")
            continue
        want_description = overrides[real] if real in overrides else source[real][2]
        descriptions[dir_name] = str(frontmatter.get("description"))
        if frontmatter.get("name") != dir_name:
            problems.append(f"{dir_name}: frontmatter name {frontmatter.get('name')!r} should be {dir_name!r}")
        if descriptions[dir_name] != want_description:
            problems.append(f"{dir_name} ({real}): description differs from the source revision")
    try:
        if listing_presets.read(out) != listing_presets.settings_for(listing, expected):
            problems.append(f"{listing_presets.SETTINGS_FILE} does not match the {listing} skill-listing preset")
    except ValueError as exc:
        problems.append(str(exc))
    if problems:
        shown = "; ".join(problems[:8]) + (f"; and {len(problems) - 8} more" if len(problems) > 8 else "")
        raise WorkspaceIntegrityError(f"workspace {out} does not match {ref or 'the working tree'}: {shown}")
    return Workspace(sorted(source), fingerprint_of(descriptions), listing)


def workspace_info(out: Path, agent: str) -> Workspace:
    """Skill names and fingerprint of an already built workspace (no source check)."""
    descriptions = workspace_descriptions(out, agent)
    return Workspace(sorted(descriptions), fingerprint_of(descriptions))


def rewrite_description(text: str, description: str) -> str:
    """A SKILL.md with its frontmatter `description` replaced; the rest is kept byte for byte."""
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("SKILL.md has no YAML frontmatter")
    head, rest = text[4:].split("\n---\n", 1)
    out: list[str] = []
    found = skipping = False
    for line in head.split("\n"):
        if skipping and line[:1] in (" ", "\t"):
            continue  # continuation of the replaced multi-line value
        skipping = False
        if not found and re.match(r"^description:", line):
            found = skipping = True
            # A JSON string is a valid double-quoted YAML scalar, whatever punctuation the text holds.
            out.append(f"description: {json.dumps(description, ensure_ascii=False)}")
            continue
        out.append(line)
    if not found:
        raise ValueError("SKILL.md frontmatter lacks description")
    return "---\n" + "\n".join(out) + "\n---\n" + rest


def prepare_workspace(
    out: Path, agent: str = "claude", ref: str | None = None,
    description_overrides: Mapping[str, str] | None = None, listing: str | None = None,
) -> Workspace:
    """Rebuild `out` with all skills for `agent`; refuse destinations outside .tmp/.

    Skills come from the working tree, or from git revision `ref` when given. `description_overrides`
    (skill name -> text, used verbatim) replaces descriptions: the canary only. `listing` (default: ROUTING_SKILL_LISTING) is a
    skill-listing preset written as .claude/settings.json (Claude only; another agent raises ValueError). The result is verified against the source.
    """
    out = out.resolve()
    if not out.is_relative_to(TMP_ROOT.resolve()) or out == TMP_ROOT.resolve():
        raise ValueError(f"workspace must be a subdirectory of {TMP_ROOT}: {out}")
    listing = resolve_listing(agent, listing)
    overrides = dict(description_overrides or {})
    source = source_skills(ref)
    unknown = sorted(set(overrides) - set(source))
    if unknown:
        raise ValueError(f"description override for unknown skill(s): {', '.join(unknown)}")
    if out.exists():
        shutil.rmtree(out)
    skills_root = skills_root_of(out, agent)
    skills_root.mkdir(parents=True)
    for real, (plugin, dir_name, description) in source.items():
        dest = skills_root / real
        if ref is not None:
            copy_skill_at_ref(plugin, dir_name, ref, dest)
        else:
            shutil.copytree(check_repo.PLUGINS_DIR / plugin / "skills" / dir_name, dest)
        if real in overrides and overrides[real] != description:
            skill_md = dest / "SKILL.md"
            skill_md.write_text(rewrite_description(skill_md.read_text(encoding="utf-8"), overrides[real]), encoding="utf-8")
    if agent == "claude":
        listing_presets.write(out, listing, [entry.name for entry in skills_root.iterdir()])
    return verify_workspace(out, agent, ref, overrides, listing)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workspace", help="workspace directory under .tmp/")
    parser.add_argument("--agent", choices=sorted(AGENT_SKILLS_DIRS), default="claude")
    parser.add_argument("--ref", help="git revision to read skills from instead of the working tree")
    args = parser.parse_args(argv[1:])
    try:
        workspace = prepare_workspace(Path(args.workspace), args.agent, args.ref)
    except (ValueError, subprocess.CalledProcessError, select_changed.SelectionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        f"prepared {len(workspace.names)} {args.agent} skills in {args.workspace} "
        f"(listing: {workspace.listing}, fingerprint {workspace.fingerprint})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
