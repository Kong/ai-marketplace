"""Run-mode resolution tests; no model calls."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import routing_targets as targets
import select_changed

COVERED = {"alpha", "beta"}


class ResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = Path(__file__).resolve().parents[1] / ".tmp"
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.git("init", "-q", "-b", "main")
        for name in ("alpha", "beta", "gamma"):
            self.write_skill(name)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.repo, check=True, capture_output=True,
        )

    def write_skill(self, name: str, extra: str = "") -> None:
        path = self.repo / f"plugins/p/skills/{name}/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"---\nname: {name}\ndescription: {name} things\nlicense: MIT\n"
            f"metadata:\n  product: x\n  category: domain\n  tags:\n    - kong\n---\n{extra}\n"
        )

    def resolve(self, mode: str, name: str | None = None, base: str | None = None):
        return targets.resolve(mode, name, base, COVERED, self.repo)

    def test_skill_mode_returns_the_named_skill(self) -> None:
        self.assertEqual(self.resolve("skill", "alpha"), (["alpha"], []))

    def test_skill_mode_rejects_uncovered_or_unknown_skill(self) -> None:
        for name in ("gamma", "ghost"):
            with self.assertRaises(ValueError):
                self.resolve("skill", name)

    def test_all_mode_returns_every_covered_skill(self) -> None:
        self.assertEqual(self.resolve("all"), (["alpha", "beta"], []))

    def test_changed_mode_keeps_covered_changes_and_reports_the_rest(self) -> None:
        self.git("branch", "base")
        self.git("checkout", "-q", "-b", "work")
        self.write_skill("alpha", "edit")
        self.write_skill("gamma", "edit")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "change")
        skills, notices = self.resolve("changed", base="base")
        self.assertEqual(skills, ["alpha"])
        self.assertEqual(len(notices), 1)
        self.assertIn("gamma", notices[0])

    def test_changed_mode_with_no_skill_changes_selects_nothing(self) -> None:
        self.git("branch", "base")
        self.assertEqual(self.resolve("changed", base="base"), ([], []))

    def test_changed_mode_without_base_refs_fails(self) -> None:
        self.git("branch", "-m", "work")
        with self.assertRaises(select_changed.SelectionError):
            self.resolve("changed")

    def test_default_base_prefers_main(self) -> None:
        self.assertEqual(targets.default_base(self.repo), "main")

    def test_real_corpus_covers_the_pilot_skills(self) -> None:
        self.assertTrue(
            {"konnect-platform-router", "konnect-gateway-triage", "kongctl-declarative"} <= targets.covered_skills()
        )


if __name__ == "__main__":
    unittest.main()
