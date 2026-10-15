"""Reverse-index scenario selection against throwaway git repositories; offline, no model calls."""
from __future__ import annotations

import textwrap
import unittest

import routing_selection as selection
import test_routing_surface as fixtures


def scenario_file(skill: str, *rows: tuple[str, list[str], list[str], int]) -> str:
    lines = [f"skill: {skill}", "scenarios:"]
    for sid, expect, forbid, trials in rows:
        lines += [
            f"  - id: {sid}", f"    prompt: prompt for {sid}", f"    expect: {expect}", f"    forbid: {forbid}",
            f"    trials: {trials}", "    tags: [positive]",
        ]
    return "\n".join(lines) + "\n"


class SelectionRepo(fixtures.Repo):
    def setUp(self) -> None:
        super().setUp()
        self.git("checkout", "-q", "base")
        self.write("evals/routing/alpha.yaml", scenario_file(
            "alpha",
            ("a-pos", ["alpha"], [], 3),
            ("a-near", [], ["alpha"], 3),
            ("a-sib", ["beta"], ["alpha"], 1),  # sibling in alpha's file naming beta
        ))
        self.write("evals/routing/beta.yaml", scenario_file(
            "beta",
            ("b-pos", ["beta"], [], 3),
            ("b-sib", ["alpha"], ["beta"], 1),  # sibling in beta's file naming alpha
        ))
        self.write("evals/routing/gamma.yaml", scenario_file("gamma", ("g-pos", ["gamma"], [], 3), ("g-near-beta", ["gamma"], ["beta"], 3)))
        self.commit("corpus")
        self.git("tag", "-f", "base")
        self.git("checkout", "-q", "-b", "feature")

    def select(self, **kwargs):
        return selection.select_gate(self.repo, "base", "HEAD", new_skill_errors=lambda name: [], **kwargs)

    def ids(self, result, skill: str) -> list[str]:
        entry = next(e for e in result["entries"] if e["skill"] == skill)
        return entry["scenarios"].split(",")


class ReverseIndexTests(SelectionRepo):
    def test_description_change_runs_own_file_plus_scenarios_naming_the_skill(self) -> None:
        self.write_skill("beta", "Apply declarative fixes to gateways", "beta")
        self.commit()
        result = self.select()
        self.assertEqual([e["skill"] for e in result["entries"]], ["beta"])
        # own file (b-pos, b-sib), then other files naming beta: a-sib (expect), g-near-beta (forbid); a-pos/g-pos do not name it
        self.assertEqual(self.ids(result, "beta"), ["b-pos", "b-sib", "a-sib", "g-near-beta"])
        self.assertEqual(result["entries"][0]["mode"], "gate")
        self.assertFalse(result["entries"][0]["new"])

    def test_adjacent_skills_do_not_run_wholesale(self) -> None:
        self.write_skill("beta", "Apply declarative fixes to gateways", "beta", body="Use `alpha` and `gamma` for diagnosis.")
        self.commit()
        result = self.select()
        self.assertNotIn("g-pos", self.ids(result, "beta"))
        self.assertNotIn("a-pos", self.ids(result, "beta"))
        self.assertEqual([e["skill"] for e in result["entries"]], ["beta"])
        self.assertTrue(result["diff"]["adjacent"])  # adjacency stays available for the preview

    def test_shared_sibling_runs_once_under_its_owner(self) -> None:
        self.write_skill("alpha", "Diagnose gateway latency spikes", "alpha")
        self.write_skill("beta", "Apply declarative fixes to gateways", "beta")
        self.commit()
        result = self.select()
        every = [sid for e in result["entries"] for sid in e["scenarios"].split(",")]
        self.assertEqual(len(every), len(set(every)))
        self.assertIn("a-sib", self.ids(result, "alpha"))  # owner keeps it although beta's index also names it
        self.assertNotIn("a-sib", self.ids(result, "beta"))
        self.assertIn("b-sib", self.ids(result, "beta"))
        self.assertIn("b-sib", self.ids(result, "alpha") + self.ids(result, "beta"))

    def test_scenario_named_by_two_affected_skills_goes_to_its_owning_file_skill(self) -> None:
        self.write_skill("alpha", "Diagnose gateway latency spikes", "alpha")
        self.write_skill("gamma", "Publish an API with a portal", "gamma")
        self.commit()
        result = self.select()
        self.assertEqual(sorted(e["skill"] for e in result["entries"]), ["alpha", "gamma"])
        self.assertEqual(sorted(self.ids(result, "alpha")), ["a-near", "a-pos", "a-sib", "b-sib"])
        self.assertEqual(self.ids(result, "gamma"), ["g-pos", "g-near-beta"])

    def test_body_only_change_selects_nothing_and_says_so(self) -> None:
        self.write_skill("beta", "Apply declarative fixes", body="much more body", name="beta")
        self.commit()
        result = self.select()
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["skipped"], [{"skill": "beta", "reason": "SKILL.md body changed, routing surface unchanged: skipped"}])

    def test_references_only_change_selects_nothing(self) -> None:
        self.write("plugins/p/skills/beta/references/x.md", "x")
        self.commit()
        result = self.select()
        self.assertEqual((result["entries"], len(result["skipped"])), ([], 1))

    def test_nothing_changed_selects_nothing(self) -> None:
        self.assertEqual(self.select()["entries"], [])

    def test_edited_scenario_runs_alone_without_a_description_change(self) -> None:
        self.write("evals/routing/gamma.yaml", scenario_file(
            "gamma", ("g-pos", ["gamma"], [], 3), ("g-near-beta", ["gamma"], ["beta"], 3), ("g-new", ["gamma"], [], 3)))
        self.commit()
        result = self.select()
        self.assertEqual([(e["skill"], e["scenarios"]) for e in result["entries"]], [("gamma", "g-new")])
        self.assertTrue(any("g-new" in note for note in result["notes"]))

    def test_modified_scenario_is_detected_by_content_not_position(self) -> None:
        self.write("evals/routing/beta.yaml", scenario_file("beta", ("b-pos", ["beta"], [], 3), ("b-sib", ["alpha"], ["beta"], 3)))
        self.commit()
        self.assertEqual([(e["skill"], e["scenarios"]) for e in self.select()["entries"]], [("beta", "b-sib")])

    def test_scenario_file_with_no_semantic_change_selects_nothing(self) -> None:
        self.write("evals/routing/beta.yaml", "# reformatted\n" + scenario_file("beta", ("b-pos", ["beta"], [], 3), ("b-sib", ["alpha"], ["beta"], 1)))
        self.commit()
        self.assertEqual(self.select()["entries"], [])

    def test_edited_scenario_joins_the_job_of_a_surface_changed_skill_once(self) -> None:
        self.write_skill("beta", "Apply declarative fixes to gateways", "beta")
        self.write("evals/routing/beta.yaml", scenario_file("beta", ("b-pos", ["beta"], [], 3), ("b-sib", ["alpha"], ["beta"], 3)))
        self.commit()
        self.assertEqual(self.ids(self.select(), "beta"), ["b-pos", "b-sib", "a-sib", "g-near-beta"])

    def test_new_skill_runs_only_its_own_file_with_absolute_thresholds(self) -> None:
        self.write_skill("delta", "Brand new skill")
        self.write("evals/routing/delta.yaml", scenario_file("delta", ("d-pos", ["delta"], [], 3), ("d-near", [], ["delta"], 3)))
        self.write("evals/routing/gamma.yaml", scenario_file(
            "gamma", ("g-pos", ["gamma"], [], 3), ("g-near-beta", ["gamma"], ["beta"], 3), ("g-sib-delta", ["gamma"], ["delta"], 1)))
        self.commit()
        result = self.select()
        delta = next(e for e in result["entries"] if e["skill"] == "delta")
        self.assertEqual((delta["scenarios"], delta["new"]), ("d-pos,d-near", True))
        gamma = next(e for e in result["entries"] if e["skill"] == "gamma")  # the new sibling scenario in an existing file
        self.assertEqual((gamma["scenarios"], gamma["new"]), ("g-sib-delta", False))

    def test_new_skill_below_the_minimums_raises(self) -> None:
        self.write_skill("delta", "Brand new skill")
        self.commit()
        with self.assertRaisesRegex(ValueError, "scenario_validation: needs 5"):
            selection.select_gate(self.repo, "base", "HEAD", new_skill_errors=lambda name: [f"needs 5 for {name}"])

    def test_surface_change_without_any_scenario_is_skipped_not_passed_silently(self) -> None:
        self.git("rm", "-q", "evals/routing/gamma.yaml")
        self.commit("drop gamma corpus")
        self.write_skill("gamma", "Publish an API with a portal", "gamma")
        self.commit()
        result = self.select()
        self.assertEqual(result["entries"], [])
        self.assertIn("no routing scenarios cover it", result["skipped"][0]["reason"])

    def test_deleted_skill_selects_nothing_itself_and_is_noted(self) -> None:
        self.git("rm", "-rq", "plugins/p/skills/gamma", "evals/routing/gamma.yaml")
        self.commit()
        result = self.select()
        self.assertEqual(result["entries"], [])
        self.assertTrue(any("gamma: deleted" in note for note in result["notes"]))


class CapTests(unittest.TestCase):
    def corpus(self, others: int) -> list[selection.Scenario]:
        own = [selection.Scenario(f"own-{i}", "s", ("s",), (), 3, "") for i in range(3)]
        named = [selection.Scenario(f"other-{i}", "t", (), ("s",), 3, "") for i in range(others)]
        return own + named

    def test_cap_keeps_the_own_file_and_drops_the_tail_of_referencing_scenarios(self) -> None:
        ids, dropped = selection.evaluation_set(self.corpus(10), "s", cap=8)
        self.assertEqual((len(ids), dropped), (8, 5))
        self.assertEqual(ids[:3], ["own-0", "own-1", "own-2"])
        self.assertEqual(ids[-1], "other-4")

    def test_own_file_is_never_truncated(self) -> None:
        ids, dropped = selection.evaluation_set(self.corpus(4), "s", cap=2)
        self.assertEqual((len(ids), dropped), (3, 4))

    def test_default_cap_is_documented_and_sane(self) -> None:
        self.assertEqual(selection.MAX_SCENARIOS_PER_SKILL, 60)

    def test_real_corpus_reverse_index_is_deduplicated(self) -> None:
        corpus = selection.load_corpus(selection.Path(__file__).resolve().parents[1] / "evals" / "routing")
        for skill in {s.owner for s in corpus}:
            ids, _ = selection.evaluation_set(corpus, skill)
            self.assertEqual(len(ids), len(set(ids)))
            self.assertTrue({s.id for s in corpus if s.owner == skill} <= set(ids))


class SkillEntryTests(SelectionRepo):
    def test_manual_skill_uses_the_reverse_index_without_the_surface_trigger(self) -> None:
        entry = selection.skill_entry(self.repo, "beta", "base")["entries"][0]
        self.assertEqual((entry["scenarios"], entry["new"]), ("b-pos,b-sib,a-sib,g-near-beta", False))

    def test_manual_skill_without_scenarios_is_an_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "no routing scenarios"):
            selection.skill_entry(self.repo, "nothing-here", "base")


if __name__ == "__main__":
    unittest.main()
