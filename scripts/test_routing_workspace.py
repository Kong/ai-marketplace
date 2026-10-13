"""Tests for routing workspace materialization."""
from __future__ import annotations

import unittest
from pathlib import Path

import prepare_routing_workspace as prep
import validate_routing_scenarios as validator


class RoutingWorkspaceTests(unittest.TestCase):
    def test_all_skills_materialized_and_rebuilt(self) -> None:
        out = prep.TMP_ROOT / "routing-test" / "claude"
        self.addCleanup(lambda: prep.shutil.rmtree(out.parent, ignore_errors=True))
        names = prep.prepare_workspace(out)
        self.assertEqual(set(names), validator.known_skill_names())
        for name in names:
            self.assertTrue((out / ".claude" / "skills" / name / "SKILL.md").is_file())
            self.assertFalse((out / ".claude" / "skills" / name).is_symlink())
        (out / "stale").write_text("x")
        prep.prepare_workspace(out)
        self.assertFalse((out / "stale").exists())

    def test_rejects_destination_outside_tmp(self) -> None:
        with self.assertRaises(ValueError):
            prep.prepare_workspace(Path("/tmp/routing-elsewhere"))
        with self.assertRaises(ValueError):
            prep.prepare_workspace(prep.TMP_ROOT)


if __name__ == "__main__":
    unittest.main()
