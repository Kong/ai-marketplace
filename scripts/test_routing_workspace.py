"""Tests for routing workspace materialization: layout, description rewriting and the integrity check."""
from __future__ import annotations

import unittest
from pathlib import Path

import prepare_routing_workspace as prep
import validate_routing_scenarios as validator


class WorkspaceCase(unittest.TestCase):
    def workspace_root(self, agent: str) -> Path:
        out = prep.TMP_ROOT / "routing-test" / agent
        self.addCleanup(lambda: prep.shutil.rmtree(out.parent, ignore_errors=True))
        return out


class RoutingWorkspaceTests(WorkspaceCase):
    def test_all_skills_materialized_and_rebuilt(self) -> None:
        out = self.workspace_root("claude")
        ws = prep.prepare_workspace(out)
        self.assertEqual(set(ws.names), validator.known_skill_names())
        for name in ws.names:
            self.assertTrue((out / ".claude" / "skills" / name / "SKILL.md").is_file())
            self.assertFalse((out / ".claude" / "skills" / name).is_symlink())
        (out / "stale").write_text("x")
        prep.prepare_workspace(out)
        self.assertFalse((out / "stale").exists())

    def test_codex_workspace_uses_agents_skills_dir(self) -> None:
        out = self.workspace_root("codex")
        ws = prep.prepare_workspace(out, "codex")
        self.assertEqual(set(ws.names), validator.known_skill_names())
        for name in ws.names:
            self.assertTrue((out / ".agents" / "skills" / name / "SKILL.md").is_file())
        self.assertFalse((out / ".claude").exists())

    def test_rejects_destination_outside_tmp(self) -> None:
        with self.assertRaises(ValueError):
            prep.prepare_workspace(Path("/tmp/routing-elsewhere"))
        with self.assertRaises(ValueError):
            prep.prepare_workspace(prep.TMP_ROOT)


class ExposedSkillsTests(unittest.TestCase):
    def test_count_and_order_independent_fingerprint(self) -> None:
        a = prep.exposed_skills("claude", ["b", "a"])
        self.assertEqual(a, prep.exposed_skills("claude", ["a", "b"]))
        self.assertEqual(a["count"], 2)
        self.assertRegex(a["fingerprint"], r"^[0-9a-f]{12}$")
        self.assertNotEqual(a["fingerprint"], prep.exposed_skills("claude", ["a", "c"])["fingerprint"])
        self.assertEqual(prep.describe_exposure(a), f"2:{a['fingerprint']}")

    def test_codex_has_no_explicit_list(self) -> None:
        self.assertIsNone(prep.exposed_skills("codex", ["a"]))
        self.assertEqual(prep.describe_exposure(None), "-")


class FingerprintTests(WorkspaceCase):
    def test_fingerprint_changes_with_a_description(self) -> None:
        out = self.workspace_root("claude")
        plain = prep.prepare_workspace(out)
        self.assertEqual(len(plain.fingerprint), 12)
        name = sorted(plain.names)[0]
        damaged = prep.prepare_workspace(out, description_overrides={name: "Brand voice copy."})
        self.assertNotEqual(damaged.fingerprint, plain.fingerprint)
        self.assertEqual(prep.workspace_info(out, "claude").fingerprint, damaged.fingerprint)
        self.assertEqual(prep.workspace_info(out, "claude").names, sorted(plain.names))


class RewriteDescriptionTests(unittest.TestCase):
    def test_only_the_description_changes_and_continuations_are_dropped(self) -> None:
        text = "---\nname: a\ndescription: >-\n  old words\n  more old\nlicense: MIT\n---\nBody: here\n"
        out = prep.rewrite_description(text, 'New "quoted": text')
        self.assertEqual(out, '---\nname: a\ndescription: "New \\"quoted\\": text"\nlicense: MIT\n---\nBody: here\n')

    def test_missing_frontmatter_or_description_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            prep.rewrite_description("no frontmatter", "x")
        with self.assertRaises(ValueError):
            prep.rewrite_description("---\nname: a\n---\nbody\n", "x")


class IntegrityTests(WorkspaceCase):
    def build(self) -> tuple[Path, prep.Workspace]:
        out = self.workspace_root("claude")
        return out, prep.prepare_workspace(out)

    def skill_md(self, out: Path, ws: prep.Workspace, index: int = 0) -> Path:
        return out / ".claude/skills" / sorted(ws.names)[index] / "SKILL.md"

    def test_a_fresh_workspace_verifies_and_returns_the_fingerprint(self) -> None:
        out, ws = self.build()
        self.assertEqual(prep.verify_workspace(out, "claude").fingerprint, ws.fingerprint)

    def test_tampered_description_is_rejected(self) -> None:
        out, ws = self.build()
        path = self.skill_md(out, ws)
        path.write_text(prep.rewrite_description(path.read_text(), "Marketing copy about brand voice."))
        with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "description differs from the source revision"):
            prep.verify_workspace(out, "claude")

    def test_tampered_name_missing_or_extra_skill_are_rejected(self) -> None:
        out, ws = self.build()
        path = self.skill_md(out, ws)
        original = path.read_text()
        path.write_text(original.replace("name: ", "name: x-", 1))
        with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "frontmatter name"):
            prep.verify_workspace(out, "claude")
        path.write_text(original)
        (out / ".claude/skills/extra").mkdir()
        with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "unexpected skill directory 'extra'"):
            prep.verify_workspace(out, "claude")
        (out / ".claude/skills/extra").rmdir()
        prep.shutil.rmtree(path.parent)
        with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "is missing"):
            prep.verify_workspace(out, "claude")

    def test_override_is_accepted_only_when_declared(self) -> None:
        out = self.workspace_root("claude")
        name = sorted(validator.known_skill_names())[0]
        prep.prepare_workspace(out, description_overrides={name: "Brand voice."})
        with self.assertRaises(prep.WorkspaceIntegrityError):
            prep.verify_workspace(out, "claude")
        prep.verify_workspace(out, "claude", description_overrides={name: "Brand voice."})
        with self.assertRaisesRegex(ValueError, "unknown skill"):
            prep.prepare_workspace(out, description_overrides={"no-such-skill": "x"})


if __name__ == "__main__":
    unittest.main()
