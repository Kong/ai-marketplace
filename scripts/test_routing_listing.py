"""Skill-listing preset tests: constants, workspace settings file, result documents, CI scoping; offline."""
from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import check_repo
import prepare_routing_workspace as prep
import print_routing_config as config
import routing_aliases as aliasing
import routing_canary as canary
import routing_ci as ci
import routing_listing as listing
import routing_results as results
import run_routing_comparison as driver
import run_routing_eval as runner
import validate_routing_scenarios as validator

SKILL = "konnect-gateway-triage"
SCRATCH = check_repo.REPO_ROOT / ".tmp"
NAMES = ["a-skill", "b-skill"]


class PresetTests(unittest.TestCase):
    def test_presets_and_default(self) -> None:
        self.assertEqual(listing.PRESETS, ("default", "wide", "name-only"))
        self.assertEqual(listing.parse_setting(None), "default")
        self.assertEqual(listing.parse_setting("  "), "default")
        self.assertEqual(listing.parse_setting("Wide"), "wide")
        self.assertEqual(listing.selected({"ROUTING_SKILL_LISTING": "name-only"}), "name-only")
        self.assertEqual(listing.selected({}), "default")

    def test_invalid_value_is_an_error(self) -> None:
        for bad in ("narrow", "all", "wide;hooks", "{}"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "ROUTING_SKILL_LISTING must be one of default, wide, name-only"):
                listing.parse_setting(bad)

    def test_settings_documents_are_fixed_constants(self) -> None:
        self.assertIsNone(listing.settings_for("default", NAMES))
        self.assertEqual(listing.settings_for("wide", NAMES), {"skillListingBudgetFraction": 0.25, "skillListingMaxDescChars": 8192})
        self.assertEqual(listing.settings_for("name-only", reversed(NAMES)), {"skillOverrides": {n: "name-only" for n in NAMES}})
        with self.assertRaises(ValueError):
            listing.settings_for("hooks", NAMES)

    def test_wide_values_are_within_the_documented_ranges_and_cover_every_description(self) -> None:
        fraction, cap = listing.WIDE_SETTINGS["skillListingBudgetFraction"], listing.WIDE_SETTINGS["skillListingMaxDescChars"]
        self.assertTrue(0 < fraction <= 1)  # documented: a fraction greater than 0 and at most 1 (default 0.01)
        self.assertIsInstance(cap, int)
        longest = max(len(s.description) for p in check_repo.discover_plugins() for s in check_repo.discover_skills(p))
        self.assertGreaterEqual(cap, longest)

    def test_check_agents_rejects_codex_for_a_non_default_preset(self) -> None:
        listing.check_agents("default", ["claude", "codex"])
        listing.check_agents("wide", ["claude"])
        with self.assertRaisesRegex(ValueError, "claude agent only"):
            listing.check_agents("wide", ["claude", "codex"])

    def test_write_refuses_an_existing_settings_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude/settings.json").write_text("{}")
            for preset in listing.PRESETS:
                with self.assertRaisesRegex(ValueError, "already exists"):
                    listing.write(root, preset, NAMES)
            self.assertEqual((root / ".claude/settings.json").read_text(), "{}")


class WorkspaceCase(unittest.TestCase):
    def workspace_root(self, agent: str) -> Path:
        out = prep.TMP_ROOT / "routing-test-listing" / agent
        self.addCleanup(lambda: shutil.rmtree(out.parent, ignore_errors=True))
        return out


class WorkspaceTests(WorkspaceCase):
    def settings(self, out: Path) -> dict | None:
        path = out / ".claude" / "settings.json"
        return json.loads(path.read_text()) if path.exists() else None

    def test_default_writes_no_settings_file_and_is_unchanged_by_the_environment_default(self) -> None:
        out = self.workspace_root("claude")
        with mock.patch.dict("os.environ", {}, clear=False):
            ws = prep.prepare_workspace(out, aliased=False)
        self.assertEqual(ws.listing, "default")
        self.assertFalse((out / ".claude" / "settings.json").exists())

    def test_wide_and_name_only_write_exactly_the_preset(self) -> None:
        names = sorted(validator.known_skill_names())
        for preset, expected in (
            ("wide", dict(listing.WIDE_SETTINGS)),
            ("name-only", {"skillOverrides": {n: "name-only" for n in names}}),
        ):
            with self.subTest(preset=preset):
                out = self.workspace_root("claude")
                ws = prep.prepare_workspace(out, aliased=False, listing=preset)
                self.assertEqual((ws.listing, self.settings(out)), (preset, expected))

    def test_preset_comes_from_the_environment(self) -> None:
        out = self.workspace_root("claude")
        with mock.patch.dict("os.environ", {"ROUTING_SKILL_LISTING": "wide"}):
            ws = prep.prepare_workspace(out, aliased=False)
        self.assertEqual((ws.listing, self.settings(out)), ("wide", dict(listing.WIDE_SETTINGS)))

    def test_name_only_keys_match_the_directories_real_or_aliased(self) -> None:
        for aliased in (False, True):
            with self.subTest(aliased=aliased):
                out = self.workspace_root("claude")
                ws = prep.prepare_workspace(out, aliased=aliased, listing="name-only")
                keys = set(self.settings(out)["skillOverrides"])
                present = {p.name for p in (out / ".claude" / "skills").iterdir()}
                frontmatter = {check_repo.parse_frontmatter(out / ".claude/skills" / n / "SKILL.md")["name"] for n in present}
                self.assertEqual(keys, present)
                self.assertEqual(keys, frontmatter)
                self.assertEqual(keys, set(ws.aliases.values()) if aliased else set(ws.names))

    def test_codex_rejects_a_non_default_preset_and_default_still_works(self) -> None:
        out = self.workspace_root("codex")
        for preset in ("wide", "name-only"):
            with self.assertRaisesRegex(ValueError, "claude agent only"):
                prep.prepare_workspace(out, "codex", aliased=False, listing=preset)
        with mock.patch.dict("os.environ", {"ROUTING_SKILL_LISTING": "wide"}), self.assertRaises(ValueError):
            prep.prepare_workspace(out, "codex", aliased=False)
        prep.prepare_workspace(out, "codex", aliased=False, listing="default")
        self.assertFalse((out / ".claude").exists())

    def test_cli_exit_codes(self) -> None:
        out = self.workspace_root("claude")
        rel = str(out.relative_to(check_repo.REPO_ROOT))
        for env, agent, code in (
            ({"ROUTING_SKILL_LISTING": "wide"}, "codex", 2),
            ({"ROUTING_SKILL_LISTING": "bogus"}, "claude", 2),
            ({"ROUTING_SKILL_LISTING": "wide"}, "claude", 0),
        ):
            with self.subTest(env=env, agent=agent), mock.patch.dict("os.environ", env):
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(prep.main(["prepare", rel, "--agent", agent]), code)
                if code == 0:
                    self.assertIn("listing: wide", stdout.getvalue())
                else:
                    self.assertIn("ERROR:", stderr.getvalue())

    def test_verify_detects_a_missing_extra_or_tampered_settings_file(self) -> None:
        out = self.workspace_root("claude")
        prep.prepare_workspace(out, aliased=False, listing="wide")
        path = out / ".claude" / "settings.json"
        path.write_text(json.dumps({**listing.WIDE_SETTINGS, "hooks": {}}))
        with self.assertRaisesRegex(prep.WorkspaceIntegrityError, "does not match the wide skill-listing preset"):
            prep.verify_workspace(out, "claude", aliased=False, listing="wide")
        path.unlink()
        with self.assertRaises(prep.WorkspaceIntegrityError):
            prep.verify_workspace(out, "claude", aliased=False, listing="wide")
        prep.verify_workspace(out, "claude", aliased=False, listing="default")  # absent is exactly the default
        path.write_text("{}")
        with self.assertRaises(prep.WorkspaceIntegrityError):
            prep.verify_workspace(out, "claude", aliased=False, listing="default")


class DocumentTests(unittest.TestCase):
    def test_agent_results_summaries_and_failures_record_listing(self) -> None:
        self.assertEqual(results.agent_failure("claude", SKILL, results.PROVIDER, "x")["listing"], "default")
        wide = {"agent": "claude", "listing": "wide"}
        self.assertEqual(results.combined_listing([wide]), "wide")
        self.assertEqual(results.combined_listing([wide, {"agent": "codex"}]), "mixed")
        self.assertEqual(results.combined_listing([]), "default")

    def test_stamp_records_the_workspace_preset_and_summarize_prints_it(self) -> None:
        ws = prep.Workspace(["a"], None, "f" * 12, "name-only")
        doc = runner.evaluate_agent("claude", SKILL, workspace=ws, validation_errors=["bad"])
        self.assertEqual(doc["listing"], "name-only")
        self.assertIn("listing=name-only", runner.summarize({**results.agent_failure("claude", SKILL, results.PROVIDER, "x"), "listing": "name-only"}))
        self.assertEqual(runner.evaluate_agent("claude", SKILL, validation_errors=["bad"])["listing"], "default")


class CanaryTests(WorkspaceCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="listing-canary-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_canary_document_records_listing_and_the_workspace_has_the_settings(self) -> None:
        with mock.patch.dict("os.environ", {"ROUTING_SKILL_LISTING": "name-only", "ROUTING_ALIAS_SKILLS": "1"}):
            doc = canary.run_canary(SKILL, ("claude",), self.dir, fake={})
        self.assertEqual(doc["listing"], "name-only")
        self.assertIn("listing: name-only", "\n".join(canary.render(doc)))
        root = self.dir / "canary" / "claude"
        keys = set(json.loads((root / ".claude" / "settings.json").read_text())["skillOverrides"])
        self.assertEqual(keys, set(aliasing.load(root).values()))

    def test_default_canary_has_no_settings_and_records_default(self) -> None:
        with mock.patch.dict("os.environ", {"ROUTING_SKILL_LISTING": ""}):
            doc = canary.run_canary(SKILL, ("claude",), self.dir, fake={})
        self.assertEqual(doc["listing"], "default")
        self.assertFalse((self.dir / "canary" / "claude" / ".claude" / "settings.json").exists())

    def test_canary_cli_rejects_codex_with_a_preset(self) -> None:
        with mock.patch.dict("os.environ", {"ROUTING_SKILL_LISTING": "wide"}), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
            code = canary.main(["routing_canary.py", SKILL, "--agent", "codex", "--fake-results", "/dev/null"])
        self.assertEqual(code, 2)
        self.assertIn("claude agent only", err.getvalue())


class ComparisonTests(WorkspaceCase):
    def test_comparison_workspaces_use_the_preset_and_the_document_records_it(self) -> None:
        tmp = Path(tempfile.mkdtemp(dir=SCRATCH if SCRATCH.exists() else None, prefix="listing-cmp-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with mock.patch.dict("os.environ", {"ROUTING_SKILL_LISTING": "wide", "ROUTING_ALIAS_SKILLS": "0"}):
            doc = driver.evaluate_variant("candidate", "claude", SKILL, None, ["invalid"], None, tmp)
            ws = prep.prepare_workspace(tmp / "candidate" / "claude", "claude")
        self.assertEqual(doc["listing"], "default")  # no workspace is built when validation failed first
        self.assertEqual(ws.listing, "wide")
        self.assertEqual(json.loads((tmp / "candidate/claude/.claude/settings.json").read_text()), listing.WIDE_SETTINGS)


class ConfigTests(unittest.TestCase):
    def test_config_reports_the_preset(self) -> None:
        with mock.patch.dict("os.environ", {"ROUTING_SKILL_LISTING": "wide"}):
            doc = config.collect()
            text = config.render(doc)
        self.assertEqual((doc["listing"]["preset"], doc["listing"]["source"]), ("wide", "override"))
        self.assertIn("Skill listing preset: wide (override;", text)
        with mock.patch.dict("os.environ", {"ROUTING_SKILL_LISTING": ""}):
            self.assertEqual(config.collect()["listing"]["preset"], "default")


class CiTests(unittest.TestCase):
    def test_dispatch_listing_applies_only_to_manual_skill_changed_canary(self) -> None:
        for mode in ("skill", "changed", "canary"):
            self.assertEqual(ci.dispatch_listing({"EVENT_NAME": "workflow_dispatch", "MODE_INPUT": mode, "LISTING_INPUT": "wide"}), ("wide", None))
        preset, notice = ci.dispatch_listing({"EVENT_NAME": "workflow_dispatch", "MODE_INPUT": "all", "LISTING_INPUT": "wide"})
        self.assertEqual(preset, "default")
        self.assertIn("ignored for mode=all", notice)
        for event in ("merge_group", "pull_request", "push"):
            self.assertEqual(ci.dispatch_listing({"EVENT_NAME": event, "MODE_INPUT": "skill", "LISTING_INPUT": "name-only"}), ("default", None))
        self.assertEqual(ci.dispatch_listing({"EVENT_NAME": "workflow_dispatch", "MODE_INPUT": "skill"}), ("default", None))
        self.assertEqual(ci.dispatch_listing({"EVENT_NAME": "merge_group", "LISTING_INPUT": "bogus"}), ("default", None))
        with self.assertRaises(ci.CiError):
            ci.dispatch_listing({"EVENT_NAME": "workflow_dispatch", "MODE_INPUT": "skill", "LISTING_INPUT": "narrow"})

    def test_the_environment_variable_is_scrubbed(self) -> None:
        self.assertIn("ROUTING_SKILL_LISTING", ci.SCRUBBED)


if __name__ == "__main__":
    unittest.main()
