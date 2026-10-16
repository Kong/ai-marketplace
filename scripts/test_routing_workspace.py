"""Tests for routing workspace materialization: layout, aliasing and the integrity check."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import check_repo
import prepare_routing_workspace as prep
import routing_aliases as aliasing
import validate_routing_scenarios as validator


class WorkspaceCase(unittest.TestCase):
    def workspace_root(self, agent: str) -> Path:
        out = prep.TMP_ROOT / "routing-test" / agent
        self.addCleanup(lambda: prep.shutil.rmtree(out.parent, ignore_errors=True))
        return out


class RoutingWorkspaceTests(WorkspaceCase):
    def test_all_skills_materialized_and_rebuilt(self) -> None:
        out = self.workspace_root("claude")
        ws = prep.prepare_workspace(out, aliased=False)
        self.assertEqual(set(ws.names), validator.known_skill_names())
        self.assertIsNone(ws.aliases)
        for name in ws.names:
            self.assertTrue((out / ".claude" / "skills" / name / "SKILL.md").is_file())
            self.assertFalse((out / ".claude" / "skills" / name).is_symlink())
        self.assertFalse(aliasing.aliases_path(out).exists())
        (out / "stale").write_text("x")
        prep.prepare_workspace(out, aliased=False)
        self.assertFalse((out / "stale").exists())

    def test_codex_workspace_uses_agents_skills_dir(self) -> None:
        out = self.workspace_root("codex")
        ws = prep.prepare_workspace(out, "codex", aliased=False)
        self.assertEqual(set(ws.names), validator.known_skill_names())
        for name in ws.names:
            self.assertTrue((out / ".agents" / "skills" / name / "SKILL.md").is_file())
        self.assertFalse((out / ".claude").exists())

    def test_rejects_destination_outside_tmp(self) -> None:
        with self.assertRaises(ValueError):
            prep.prepare_workspace(Path("/tmp/routing-elsewhere"))
        with self.assertRaises(ValueError):
            prep.prepare_workspace(prep.TMP_ROOT)


class AliasedWorkspaceTests(WorkspaceCase):
    def test_directories_and_frontmatter_names_are_aliases_and_descriptions_are_kept(self) -> None:
        for agent, skills_dir in (("claude", ".claude/skills"), ("codex", ".agents/skills")):
            with self.subTest(agent=agent):
                out = self.workspace_root(agent)
                ws = prep.prepare_workspace(out, agent, aliased=True)
                names = validator.known_skill_names()
                self.assertEqual(ws.aliases, aliasing.build_aliases(names))
                self.assertEqual(json.loads(aliasing.aliases_path(out).read_text()), ws.aliases)
                self.assertEqual(aliasing.aliases_path(out), out.with_name(out.name + ".aliases.json"))
                self.assertFalse(list(out.rglob("*aliases*")))  # nothing the agent can read in its workspace
                self.assertEqual({p.name for p in (out / skills_dir).iterdir()}, set(ws.aliases.values()))
                by_name = {s.name: s for p in check_repo.discover_plugins() for s in check_repo.discover_skills(p)}
                for name, alias in ws.aliases.items():
                    front = check_repo.parse_frontmatter(out / skills_dir / alias / "SKILL.md")
                    self.assertEqual(front["name"], alias)
                    self.assertEqual(front["description"], aliasing.alias_description(by_name[name].description, ws.aliases))
                    self.assertFalse((out / skills_dir / name).exists())
                    # the body is not rewritten
                    src = (check_repo.PLUGINS_DIR / by_name[name].plugin_name / "skills" / by_name[name].dir_name / "SKILL.md").read_text()
                    self.assertEqual((out / skills_dir / alias / "SKILL.md").read_text().split("\n---\n", 1)[1], src.split("\n---\n", 1)[1])

    def test_aliases_match_between_agents_and_runs(self) -> None:
        a = prep.prepare_workspace(self.workspace_root("claude"), "claude", aliased=True)
        b = prep.prepare_workspace(self.workspace_root("codex"), "codex", aliased=True)
        self.assertEqual(a.aliases, b.aliases)
        self.assertEqual(a.fingerprint, b.fingerprint)

    def test_fingerprint_changes_with_aliasing_and_with_a_description(self) -> None:
        out = self.workspace_root("claude")
        plain = prep.prepare_workspace(out, aliased=False)
        aliased = prep.prepare_workspace(out, aliased=True)
        self.assertEqual(len(aliased.fingerprint), 12)
        name = sorted(plain.names)[0]
        damaged = prep.prepare_workspace(out, aliased=True, description_overrides={name: "Brand voice copy."})
        self.assertNotEqual(damaged.fingerprint, aliased.fingerprint)
        self.assertEqual(prep.workspace_info(out, "claude").fingerprint, damaged.fingerprint)


class IntegrityTests(WorkspaceCase):
    def build(self, aliased: bool) -> tuple[Path, prep.Workspace]:
        out = self.workspace_root("claude")
        return out, prep.prepare_workspace(out, aliased=aliased)

    def skill_md(self, out: Path, ws: prep.Workspace, index: int = 0) -> Path:
        name = sorted(ws.names)[index]
        return out / ".claude/skills" / (ws.aliases[name] if ws.aliases else name) / "SKILL.md"

    def test_a_fresh_workspace_verifies_and_returns_the_fingerprint(self) -> None:
        for aliased in (False, True):
            out, ws = self.build(aliased)
            self.assertEqual(prep.verify_workspace(out, "claude", aliased=aliased).fingerprint, ws.fingerprint)

    def test_tampered_description_is_rejected(self) -> None:
        for aliased in (False, True):
            with self.subTest(aliased=aliased):
                out, ws = self.build(aliased)
                path = self.skill_md(out, ws)
                path.write_text(aliasing.rewrite_skill_md(path.read_text(), None, "Marketing copy about brand voice."))
                with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "description differs from the source revision"):
                    prep.verify_workspace(out, "claude", aliased=aliased)

    def test_tampered_name_missing_or_extra_skill_and_wrong_alias_state_are_rejected(self) -> None:
        out, ws = self.build(True)
        path = self.skill_md(out, ws)
        original = path.read_text()
        path.write_text(original.replace("name: ", "name: x-", 1))
        with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "frontmatter name"):
            prep.verify_workspace(out, "claude", aliased=True)
        path.write_text(original)
        (out / ".claude/skills/extra").mkdir()
        with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "unexpected skill directory 'extra'"):
            prep.verify_workspace(out, "claude", aliased=True)
        (out / ".claude/skills/extra").rmdir()
        prep.shutil.rmtree(path.parent)
        with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "is missing"):
            prep.verify_workspace(out, "claude", aliased=True)

    def test_workspace_built_with_the_other_alias_setting_is_rejected(self) -> None:
        out, _ = self.build(True)
        with self.assertRaises(prep.WorkspaceIntegrityError):
            prep.verify_workspace(out, "claude", aliased=False)
        out, _ = self.build(False)
        with self.assertRaises(prep.WorkspaceIntegrityError):
            prep.verify_workspace(out, "claude", aliased=True)

    def test_rebuilding_without_aliases_removes_a_stale_alias_map(self) -> None:
        out = self.workspace_root("claude")
        prep.prepare_workspace(out, aliased=True)
        self.assertTrue(aliasing.aliases_path(out).is_file())
        prep.prepare_workspace(out, aliased=False)
        self.assertFalse(aliasing.aliases_path(out).exists())

    def test_stale_aliases_file_is_rejected(self) -> None:
        out, ws = self.build(True)
        aliasing.write(out, {**ws.aliases, "bogus": "s-000000"})
        with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "alias map .* does not match"):
            prep.verify_workspace(out, "claude", aliased=True)

    def test_override_is_accepted_only_when_declared(self) -> None:
        out = self.workspace_root("claude")
        name = sorted(validator.known_skill_names())[0]
        prep.prepare_workspace(out, aliased=True, description_overrides={name: "Brand voice."})
        with self.assertRaises(prep.WorkspaceIntegrityError):
            prep.verify_workspace(out, "claude", aliased=True)
        prep.verify_workspace(out, "claude", aliased=True, description_overrides={name: "Brand voice."})
        with self.assertRaisesRegex(ValueError, "unknown skill"):
            prep.prepare_workspace(out, aliased=True, description_overrides={"no-such-skill": "x"})


if __name__ == "__main__":
    unittest.main()
