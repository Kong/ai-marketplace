"""Materialize a per-host project workspace exposing every repo skill for routing evals.

Claude discovers project skills under <workspace>/.claude/skills/<name>/ and Codex
under <workspace>/.agents/skills/<name>/. Copies (not symlinks) keep the eval run
isolated from the checkout.

    python scripts/prepare_routing_workspace.py .tmp/routing/claude
    python scripts/prepare_routing_workspace.py .tmp/routing/codex --host codex
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import check_repo

TMP_ROOT = check_repo.REPO_ROOT / ".tmp"
HOST_SKILLS_DIRS = {"claude": Path(".claude/skills"), "codex": Path(".agents/skills")}


def prepare_workspace(out: Path, host: str = "claude") -> list[str]:
    """Rebuild `out` with all skills for `host`; refuse destinations outside .tmp/."""
    out = out.resolve()
    if not out.is_relative_to(TMP_ROOT.resolve()) or out == TMP_ROOT.resolve():
        raise ValueError(f"workspace must be a subdirectory of {TMP_ROOT}: {out}")
    if out.exists():
        shutil.rmtree(out)
    skills_root = out / HOST_SKILLS_DIRS[host]
    skills_root.mkdir(parents=True)
    names: list[str] = []
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
    args = parser.parse_args(argv[1:])
    try:
        names = prepare_workspace(Path(args.workspace), args.host)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"prepared {len(names)} {args.host} skills in {args.workspace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
