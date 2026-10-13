"""Materialize a Claude project workspace exposing every repo skill for routing evals.

Claude discovers project skills under <workspace>/.claude/skills/<name>/. Copies
(not symlinks) keep the eval run isolated from the checkout.

    python scripts/prepare_routing_workspace.py .tmp/routing/claude
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import check_repo

TMP_ROOT = check_repo.REPO_ROOT / ".tmp"


def prepare_workspace(out: Path) -> list[str]:
    """Rebuild `out` with all skills; refuse destinations outside .tmp/."""
    out = out.resolve()
    if not out.is_relative_to(TMP_ROOT.resolve()) or out == TMP_ROOT.resolve():
        raise ValueError(f"workspace must be a subdirectory of {TMP_ROOT}: {out}")
    if out.exists():
        shutil.rmtree(out)
    skills_root = out / ".claude" / "skills"
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
    if len(argv) != 2:
        print("usage: prepare_routing_workspace.py <workspace-dir under .tmp/>", file=sys.stderr)
        return 2
    try:
        names = prepare_workspace(Path(argv[1]))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"prepared {len(names)} skills in {argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
