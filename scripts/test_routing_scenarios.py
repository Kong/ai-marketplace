"""Validator tests for routing scenarios, using good and bad fixtures."""
from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

import validate_routing_scenarios as validator

SKILLS = {"alpha", "beta"}
GOOD = """
skill: alpha
scenarios:
  - id: alpha-positive-1
    prompt: Do the alpha thing.
    expect: [alpha]
    forbid: []
    trials: 3
    tags: [positive]
  - id: alpha-sibling-1
    prompt: Do the beta thing.
    expect: [beta]
    forbid: [alpha]
    trials: 1
    tags: [sibling]
"""


class RoutingScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = Path(__file__).resolve().parents[1] / ".tmp"
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)

    def validate(self, *files: str) -> list[str]:
        for index, content in enumerate(files):
            (self.dir / f"f{index}.yaml").write_text(textwrap.dedent(content))
        return validator.validate_scenarios(self.dir, SKILLS)

    def assertRejects(self, content: str, fragment: str) -> None:
        errors = self.validate(content)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_valid_file_passes(self) -> None:
        self.assertEqual(self.validate(GOOD), [])

    def test_missing_directory_passes(self) -> None:
        self.assertEqual(validator.validate_scenarios(self.dir / "absent", SKILLS), [])

    def test_repo_scenarios_are_valid(self) -> None:
        self.assertEqual(validator.validate_scenarios(validator.SCENARIOS_DIR, validator.known_skill_names()), [])

    def test_malformed_yaml(self) -> None:
        self.assertRejects("skill: [unclosed", "unparseable YAML")

    def test_top_level_not_mapping(self) -> None:
        self.assertRejects("- a\n- b\n", "top level must be a mapping")

    def test_empty_scenarios(self) -> None:
        self.assertRejects("skill: alpha\nscenarios: []\n", "non-empty list")

    def test_missing_fields(self) -> None:
        self.assertRejects("skill: alpha\nscenarios:\n  - id: a-1\n", "missing field 'prompt'")

    def test_unknown_field(self) -> None:
        self.assertRejects(GOOD.replace("trials: 3", "trials: 3\n    extra: 1"), "unknown field 'extra'")

    def test_unknown_target_skill(self) -> None:
        self.assertRejects(GOOD.replace("skill: alpha", "skill: nope", 1), "target skill 'nope'")

    def test_unknown_referenced_skill(self) -> None:
        self.assertRejects(GOOD.replace("forbid: [alpha]", "forbid: [ghost]"), "unknown skill 'ghost'")

    def test_duplicate_ids_across_files(self) -> None:
        errors = self.validate(GOOD, GOOD)
        self.assertTrue(any("duplicate id" in error for error in errors), errors)

    def test_bad_trial_counts(self) -> None:
        for bad in ("0", "6", "-1", "2.5", "'3'", "true"):
            with self.subTest(trials=bad):
                self.assertRejects(GOOD.replace("trials: 3", f"trials: {bad}"), "trials must be")

    def test_expect_forbid_conflict(self) -> None:
        self.assertRejects(GOOD.replace("forbid: []", "forbid: [alpha]"), "both expected and forbidden")

    def test_empty_expect_and_forbid(self) -> None:
        self.assertRejects(GOOD.replace("expect: [alpha]", "expect: []"), "cannot both be empty")

    def test_bad_tags(self) -> None:
        self.assertRejects(GOOD.replace("[positive]", "[bogus]"), "unknown tag 'bogus'")
        self.assertRejects(GOOD.replace("[positive]", "[]"), "tags must be")

    def test_design_tags_follow_exactly_one_kind_tag(self) -> None:
        self.assertEqual(self.validate(GOOD.replace("[positive]", "[positive, symptom-only]")), [])
        self.assertEqual(self.validate(GOOD.replace("[positive]", "[positive, symptom-only, name-lure]")), [])
        self.assertRejects(GOOD.replace("[positive]", "[symptom-only]"), "exactly one kind tag")
        self.assertRejects(GOOD.replace("[positive]", "[name-lure, positive]"), "listed first")
        self.assertRejects(GOOD.replace("[positive]", "[positive, sibling]"), "exactly one kind tag")

    def test_bad_id_and_prompt(self) -> None:
        self.assertRejects(GOOD.replace("alpha-positive-1", "Bad_ID"), "kebab-case")
        self.assertRejects(GOOD.replace("Do the alpha thing.", "'  '"), "prompt must be")

    def test_non_yaml_file_rejected(self) -> None:
        (self.dir / "notes.txt").write_text("x")
        self.assertTrue(any("must use .yaml" in e for e in validator.validate_scenarios(self.dir, SKILLS)))


if __name__ == "__main__":
    unittest.main()
