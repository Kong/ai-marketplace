"""Skill alias tests: determinism, collisions, description substitution, setting parsing, result mapping."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import routing_aliases as aliasing
import routing_results as r
import test_routing_results as fixtures

SKILL_MD = (
    "---\nname: konnect-gateway-triage\n"
    "description: Use when triaging gateways; hand off to konnect-gateway and konnect-gateway-triage-extra, not konnect-gateway-triage2.\n"
    "license: MIT\nmetadata:\n  product: konnect\n---\n# Body mentions konnect-gateway-triage\n"
)


class AliasTests(unittest.TestCase):
    def test_alias_is_a_stable_opaque_hash_of_the_name_alone(self) -> None:
        digest = hashlib.sha1(b"konnect-gateway-triage").hexdigest()[:6]
        self.assertEqual(aliasing.alias_for("konnect-gateway-triage"), f"s-{digest}")
        self.assertRegex(aliasing.alias_for("x"), r"^s-[0-9a-f]{6}$")
        # independent of which other skills exist
        small = aliasing.build_aliases(["a", "b"])
        large = aliasing.build_aliases(["a", "b", "c", "d"])
        self.assertEqual({k: large[k] for k in small}, small)
        self.assertEqual(aliasing.build_aliases(["b", "a"]), aliasing.build_aliases(["a", "b"]))

    def test_collisions_and_duplicates_are_errors(self) -> None:
        with mock.patch.object(aliasing, "alias_for", lambda name: "s-aaaaaa"):
            with self.assertRaisesRegex(ValueError, "collision"):
                aliasing.build_aliases(["a", "b"])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            aliasing.build_aliases(["a", "a"])

    def test_descriptions_replace_whole_word_names_longest_first(self) -> None:
        aliases = aliasing.build_aliases(["konnect-gateway", "konnect-gateway-triage", "konnect-gateway-triage-extra"])
        text = aliasing.alias_description(SKILL_MD, aliases)
        self.assertIn(f"hand off to {aliases['konnect-gateway']} and {aliases['konnect-gateway-triage-extra']}", text)
        # a longer unknown word that merely starts with a known name is untouched
        self.assertIn("not konnect-gateway-triage2", text)
        self.assertNotIn("konnect-gateway-triage-extra", text)
        self.assertEqual(aliasing.alias_description("none here", aliases), "none here")
        self.assertEqual(aliasing.alias_description("(konnect-gateway), konnect-gateway.", aliases), f"({aliases['konnect-gateway']}), {aliases['konnect-gateway']}.")

    def test_rewrite_changes_only_name_and_description(self) -> None:
        out = aliasing.rewrite_skill_md(SKILL_MD, "s-abc123", "New: text with 'quotes' # and colon")
        self.assertIn('name: "s-abc123"\n', out)
        self.assertIn('description: "New: text with \'quotes\' # and colon"\n', out)
        self.assertEqual(out.split("\n---\n", 1)[1], SKILL_MD.split("\n---\n", 1)[1])  # body untouched
        self.assertIn("license: MIT\nmetadata:\n  product: konnect\n", out)
        self.assertEqual(aliasing.rewrite_skill_md(SKILL_MD, None, None), SKILL_MD)

    def test_rewrite_replaces_multiline_descriptions_whole(self) -> None:
        text = "---\nname: a\ndescription: >-\n  folded one\n  folded two\nlicense: MIT\n---\nbody\n"
        out = aliasing.rewrite_skill_md(text, "s-1", "plain")
        self.assertEqual(out, '---\nname: "s-1"\ndescription: "plain"\nlicense: MIT\n---\nbody\n')

    def test_aliases_file_round_trips_and_absent_means_unaliased(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(aliasing.load(Path(tmp)))
            aliasing.write(Path(tmp), {"b": "s-2", "a": "s-1"})
            self.assertEqual(aliasing.load(Path(tmp)), {"a": "s-1", "b": "s-2"})


class SettingTests(unittest.TestCase):
    def test_default_is_one_constant(self) -> None:
        self.assertIsInstance(aliasing.DEFAULT_ALIAS_SKILLS, bool)
        for value in (None, "", "  "):
            self.assertEqual(aliasing.parse_setting(value), aliasing.DEFAULT_ALIAS_SKILLS)
        with mock.patch.object(aliasing, "DEFAULT_ALIAS_SKILLS", False):
            self.assertFalse(aliasing.parse_setting(""))
        with mock.patch.object(aliasing, "DEFAULT_ALIAS_SKILLS", True):
            self.assertTrue(aliasing.parse_setting(None))

    def test_accepted_values(self) -> None:
        for value in ("1", "true", "TRUE", " True "):
            self.assertTrue(aliasing.parse_setting(value))
        for value in ("0", "false", "False"):
            self.assertFalse(aliasing.parse_setting(value))

    def test_invalid_values_are_errors(self) -> None:
        for value in ("yes", "2", "on", "off", "tru"):
            with self.assertRaisesRegex(ValueError, "ROUTING_ALIAS_SKILLS must be one of 1, 0, true, false"):
                aliasing.parse_setting(value)

    def test_enabled_reads_the_given_environment(self) -> None:
        self.assertFalse(aliasing.enabled({"ROUTING_ALIAS_SKILLS": "0"}))
        self.assertTrue(aliasing.enabled({"ROUTING_ALIAS_SKILLS": "1"}))


ALIASES = {"alpha": "s-aaaaaa", "beta": "s-bbbbbb"}


class ReducedReportTests(unittest.TestCase):
    """Raw Promptfoo rows carry aliases; reduced documents carry real names."""

    def row(self, **kw):
        return fixtures.row(expected=("s-aaaaaa",), calls=kw.pop("calls", ["s-aaaaaa"]), **kw)

    def test_trial_maps_expected_forbidden_observed_and_reason_to_real_names(self) -> None:
        bad = self.row(calls=["s-bbbbbb"], success=False)
        bad["testCase"]["metadata"]["forbidden"] = ["s-bbbbbb"]
        bad["gradingResult"]["reason"] = "Missing required skill(s): s-aaaaaa. Actual skills: s-bbbbbb"
        trial = r.reduce_trial(bad, "claude", ALIASES)
        self.assertEqual((trial["expected"], trial["forbidden"], trial["observed"]), (["alpha"], ["beta"], ["beta"]))
        self.assertEqual(trial["reason"], "Missing required skill(s): alpha. Actual skills: beta")
        self.assertEqual([c["name"] for c in trial["evidence"]["skill_calls"]], ["beta"])
        self.assertEqual(bad["response"]["metadata"]["skillCalls"], [{"name": "s-bbbbbb"}])  # raw row untouched

    def test_agent_document_records_aliased_and_real_names(self) -> None:
        doc = r.reduce_agent("claude", "alpha", [[self.row()]], aliases=ALIASES)
        self.assertTrue(doc["aliased"])
        self.assertEqual(doc["scenarios"][0]["trials"][0]["observed"], ["alpha"])
        plain = r.reduce_agent("codex", "alpha", [[fixtures.row()]])
        self.assertFalse(plain["aliased"])
        self.assertEqual(plain["scenarios"][0]["trials"][0]["observed"], ["alpha"])

    def test_without_aliases_names_pass_through_unchanged(self) -> None:
        trial = r.reduce_trial(fixtures.row(calls=["s-aaaaaa"]), "claude")
        self.assertEqual(trial["observed"], ["s-aaaaaa"])

    def test_combined_summary_records_aliased(self) -> None:
        aliased = r.reduce_agent("claude", "alpha", [[self.row()]], aliases=ALIASES)
        plain = r.reduce_agent("codex", "alpha", [[fixtures.row()]])
        self.assertTrue(r.combine_agents([aliased], required=("claude",))["aliased"])
        self.assertFalse(r.combine_agents([plain], required=("codex",))["aliased"])
        self.assertFalse(r.combine_agents([aliased, plain])["aliased"])
        self.assertFalse(r.agent_failure("claude", "alpha", r.PROVIDER, "x")["aliased"])


if __name__ == "__main__":
    unittest.main()
