"""Materialize a per-host project workspace exposing every repo skill for routing evals.

Claude discovers project skills under <workspace>/.claude/skills/<name>/ and Codex
under <workspace>/.agents/skills/<name>/. Copies (not symlinks) keep the eval run
isolated from the checkout.

    python scripts/prepare_routing_workspace.py .tmp/routing/claude
    python scripts/prepare_routing_workspace.py .tmp/routing/codex --host codex
    python scripts/prepare_routing_workspace.py .tmp/routing/control/claude --ref <merge-base>

With --ref, skills come from that git revision instead of the working tree (the control).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import check_repo
import select_changed

TMP_ROOT = check_repo.REPO_ROOT / ".tmp"
HOST_SKILLS_DIRS = {"claude": Path(".claude/skills"), "codex": Path(".agents/skills")}


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


def prepare_workspace(out: Path, host: str = "claude", ref: str | None = None) -> list[str]:
    """Rebuild `out` with all skills for `host`; refuse destinations outside .tmp/.

    Skills come from the working tree, or from git revision `ref` when given.
    """
    out = out.resolve()
    if not out.is_relative_to(TMP_ROOT.resolve()) or out == TMP_ROOT.resolve():
        raise ValueError(f"workspace must be a subdirectory of {TMP_ROOT}: {out}")
    if out.exists():
        shutil.rmtree(out)
    skills_root = out / HOST_SKILLS_DIRS[host]
    skills_root.mkdir(parents=True)
    names: list[str] = []
    if ref is not None:
        catalog, _ = select_changed.load_catalog(check_repo.REPO_ROOT, ref)
        for (plugin, dir_name), skill in sorted(catalog.items()):
            if skill.name in names:
                raise ValueError(f"duplicate skill name {skill.name!r}")
            copy_skill_at_ref(plugin, dir_name, ref, skills_root / skill.name)
            names.append(skill.name)
        return names
    for plugin in check_repo.discover_plugins():
        for skill in check_repo.discover_skills(plugin):
            if skill.name in names:
                raise ValueError(f"duplicate skill name {skill.name!r}")
            shutil.copytree(plugin.skills_dir / skill.dir_name, skills_root / skill.name)
            names.append(skill.name)
    return names


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workspace", help="workspace directory under .tmp/")
    parser.add_argument("--host", choices=sorted(HOST_SKILLS_DIRS), default="claude")
    parser.add_argument("--ref", help="git revision to read skills from instead of the working tree")
    args = parser.parse_args(argv[1:])
    try:
        names = prepare_workspace(Path(args.workspace), args.host, args.ref)
    except (ValueError, subprocess.CalledProcessError, select_changed.SelectionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"prepared {len(names)} {args.host} skills in {args.workspace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
