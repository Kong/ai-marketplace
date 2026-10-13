"""Run-mode resolution tests; no model calls."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def branch_with(self, *names: str) -> None:
        self.git("branch", "base")
        self.git("checkout", "-q", "-b", "work")
        for name in names:
            self.write_skill(name, "edit")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "change")

    def test_adjacent_mode_lists_only_adjacent_skills_with_scenarios(self) -> None:
        self.branch_with("alpha")
        with mock.patch.object(select_changed, "MAX_ADJACENT", 5):
            skills, notices = targets.resolve("adjacent", None, "base", {"alpha", "beta"}, self.repo)
        self.assertEqual(skills, ["beta"])
        self.assertEqual(notices, ["gamma: adjacent but has no routing scenarios, skipped"])

    def test_adjacent_mode_is_capped_and_never_the_full_catalog(self) -> None:
        self.branch_with("alpha")
        selected = select_changed.select(self.repo, "base")
        self.assertLessEqual(len(selected["adjacent"]), select_changed.MAX_ADJACENT)
        skills, _ = targets.resolve("adjacent", None, "base", {"alpha", "beta", "gamma"}, self.repo)
        self.assertEqual(skills, selected["adjacent"])
        self.assertNotIn("alpha", skills)

    def test_changed_skill_that_is_also_adjacent_counts_once_as_changed(self) -> None:
        self.branch_with("alpha", "beta")
        covered = {"alpha", "beta", "gamma"}
        changed, _ = targets.resolve("changed", None, "base", covered, self.repo)
        adjacent, _ = targets.resolve("adjacent", None, "base", covered, self.repo)
        self.assertEqual(changed, ["alpha", "beta"])
        self.assertEqual(adjacent, ["gamma"])

    def test_adjacent_without_any_scenarios_is_a_noop_with_notes(self) -> None:
        self.branch_with("alpha")
        skills, notices = targets.resolve("adjacent", None, "base", set(), self.repo)
        self.assertEqual(skills, [])
        self.assertTrue(notices)

    def test_new_skill_below_minimums_fails_as_scenario_validation(self) -> None:
        self.git("branch", "base")
        self.git("checkout", "-q", "-b", "work")
        self.write_skill("delta")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "new")
        with mock.patch.object(targets, "new_skill_errors", return_value=["needs at least 5 positive scenarios"]) as check:
            with self.assertRaisesRegex(ValueError, "scenario_validation.*positive"):
                self.resolve("changed", base="base")
        check.assert_called_once_with("delta")

    def test_new_skill_meeting_minimums_is_selected(self) -> None:
        self.git("branch", "base")
        self.git("checkout", "-q", "-b", "work")
        self.write_skill("delta")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "new")
        with mock.patch.object(targets, "new_skill_errors", return_value=[]):
            skills, _ = targets.resolve("changed", None, "base", {"delta"}, self.repo)
        self.assertEqual(skills, ["delta"])

    def test_modified_skill_without_scenarios_is_only_a_note_and_never_checked(self) -> None:
        self.branch_with("gamma")
        with mock.patch.object(targets, "new_skill_errors", side_effect=AssertionError("modified skill")):
            skills, notices = self.resolve("changed", base="base")
        self.assertEqual((skills, len(notices)), ([], 1))

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
