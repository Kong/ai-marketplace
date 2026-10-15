"""Materialize a per-agent project workspace exposing every repo skill for routing evals.

Claude discovers project skills under <workspace>/.claude/skills/<name>/ and Codex
under <workspace>/.agents/skills/<name>/. Copies (not symlinks) keep the eval run
isolated from the checkout.

    python scripts/prepare_routing_workspace.py .tmp/routing/claude
    python scripts/prepare_routing_workspace.py .tmp/routing/codex --agent codex
    python scripts/prepare_routing_workspace.py .tmp/routing/control/claude --ref <merge-base>

With --ref, skills come from that git revision instead of the working tree (the control).

Skills are renamed to opaque aliases unless ROUTING_ALIAS_SKILLS=0 (routing_aliases.py); the
real->alias map is written to <workspace>/aliases.json. After every build the workspace is checked
against the source revision (`verify_workspace`): a mismatch exits 2, so a stale or wrong workspace
never feeds an eval. The run prints a fingerprint, the hash of every description in the workspace.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import check_repo
import routing_aliases as aliasing
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
    names: list[str]  # real skill names
    aliases: dict[str, str] | None  # real -> alias, None when not aliased
    fingerprint: str


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
    out: Path, agent: str, ref: str | None = None, aliased: bool | None = None,
    description_overrides: Mapping[str, str] | None = None,
) -> Workspace:
    """Assert the workspace's SKILL.md frontmatter derives exactly from the source revision.

    Per skill the expected description is the source description with real skill names replaced by
    aliases (or the explicit override, used verbatim: the canary), and the expected name is the
    alias or the real name. The directory set, the directory/name pairing and aliases.json must
    match too. Raises WorkspaceIntegrityError listing every mismatch; returns the fingerprint.
    """
    aliased = aliasing.enabled() if aliased is None else aliased
    overrides = dict(description_overrides or {})
    source = source_skills(ref)
    unknown = sorted(set(overrides) - set(source))
    if unknown:
        raise WorkspaceIntegrityError(f"description override for unknown skill(s): {', '.join(unknown)}")
    aliases = aliasing.build_aliases(source) if aliased else None
    problems: list[str] = []
    root = skills_root_of(out, agent)
    present = {entry.name for entry in root.iterdir() if entry.is_dir()} if root.is_dir() else set()
    expected = {(aliases or {}).get(name, name): name for name in source}
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
        want_description = overrides[real] if real in overrides else (
            aliasing.alias_description(source[real][2], aliases) if aliases else source[real][2]
        )
        descriptions[dir_name] = str(frontmatter.get("description"))
        if frontmatter.get("name") != dir_name:
            problems.append(f"{dir_name}: frontmatter name {frontmatter.get('name')!r} should be {dir_name!r}")
        if descriptions[dir_name] != want_description:
            problems.append(f"{dir_name} ({real}): description differs from the source revision")
    try:
        on_disk = aliasing.load(out)
    except ValueError as exc:
        problems.append(str(exc))
        on_disk = None
    if on_disk != aliases:
        problems.append(f"{aliasing.ALIASES_FILE} does not match the expected aliases (aliasing {'on' if aliased else 'off'})")
    if problems:
        shown = "; ".join(problems[:8]) + (f"; and {len(problems) - 8} more" if len(problems) > 8 else "")
        raise WorkspaceIntegrityError(f"workspace {out} does not match {ref or 'the working tree'}: {shown}")
    return Workspace(sorted(source), aliases, fingerprint_of(descriptions))


def workspace_info(out: Path, agent: str) -> Workspace:
    """Alias map and fingerprint of an already built workspace (no source check)."""
    aliases = aliasing.load(out)
    return Workspace(sorted(aliases or []), aliases, fingerprint_of(workspace_descriptions(out, agent)))


def _install(dest: Path, real: str, aliases: Mapping[str, str] | None, description: str | None) -> None:
    alias = aliases[real] if aliases else None
    if alias is None and description is None:
        return
    skill_md = dest / "SKILL.md"
    skill_md.write_text(aliasing.rewrite_skill_md(skill_md.read_text(encoding="utf-8"), alias, description), encoding="utf-8")


def prepare_workspace(
    out: Path, agent: str = "claude", ref: str | None = None, aliased: bool | None = None,
    description_overrides: Mapping[str, str] | None = None,
) -> Workspace:
    """Rebuild `out` with all skills for `agent`; refuse destinations outside .tmp/.

    Skills come from the working tree, or from git revision `ref` when given. With `aliased` (default:
    ROUTING_ALIAS_SKILLS) each skill directory and frontmatter name become its opaque alias and
    real skill names inside descriptions are replaced by aliases. `description_overrides` (real name ->
    text, used verbatim) replaces descriptions: the canary only. The result is verified against the source.
    """
    out = out.resolve()
    if not out.is_relative_to(TMP_ROOT.resolve()) or out == TMP_ROOT.resolve():
        raise ValueError(f"workspace must be a subdirectory of {TMP_ROOT}: {out}")
    aliased = aliasing.enabled() if aliased is None else aliased
    overrides = dict(description_overrides or {})
    source = source_skills(ref)
    aliases = aliasing.build_aliases(source) if aliased else None
    unknown = sorted(set(overrides) - set(source))
    if unknown:
        raise ValueError(f"description override for unknown skill(s): {', '.join(unknown)}")
    if out.exists():
        shutil.rmtree(out)
    skills_root = skills_root_of(out, agent)
    skills_root.mkdir(parents=True)
    for real, (plugin, dir_name, description) in source.items():
        dest = skills_root / (aliases[real] if aliases else real)
        if ref is not None:
            copy_skill_at_ref(plugin, dir_name, ref, dest)
        else:
            shutil.copytree(check_repo.PLUGINS_DIR / plugin / "skills" / dir_name, dest)
        new_description = overrides[real] if real in overrides else (aliasing.alias_description(description, aliases) if aliases else None)
        if new_description == description:
            new_description = None
        _install(dest, real, aliases, new_description)
    if aliases:
        aliasing.write(out, aliases)
    return verify_workspace(out, agent, ref, aliased, overrides)


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
        f"(aliased: {str(workspace.aliases is not None).lower()}, fingerprint {workspace.fingerprint})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
