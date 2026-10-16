"""Offline tests for the lexical description-routing check: tokenizer, ranking, collisions, thresholds, collapse."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

import check_description_routing as check
import routing_canary as canary

TRIAGE = "konnect-gateway-triage"


def scenario(sid: str, prompt: str, expect: tuple[str, ...], tag: str = "positive", forbid: tuple[str, ...] = ()) -> check.Scenario:
    return check.Scenario(sid, prompt, expect, forbid, tag)


DESCRIPTIONS = {
    "alpha": "Debug disconnected data plane nodes and config sync failures in a control plane.",
    "beta": "Write declarative state files and preview a sync of services and routes.",
    "gamma": "Design portal landing pages with brand colors, typography and layout.",
}


class TokenizerTests(unittest.TestCase):
    def test_tokenize_is_deterministic_lowercase_and_drops_stopwords(self) -> None:
        text = "The Gateway's routes are Routing, and the ROUTE   is-here"
        self.assertEqual(check.tokenize(text), check.tokenize(text))
        self.assertEqual(check.tokenize(text), ["gateway", "rout", "rout", "rout", "her"])  # `here` loses its final e too

    def test_stemmer_conflates_inflections_and_keeps_short_words(self) -> None:
        for word in ("route", "routes", "routing", "routed"):
            self.assertEqual(check.stem(word), "rout")
        self.assertEqual(check.stem("policies"), "policy")
        self.assertEqual(check.stem("is"), "is")
        self.assertEqual(check.stem("bus"), "bus")  # nothing is stripped below three characters
        self.assertEqual(check.stem("kongctl"), "kongctl")

    def test_single_characters_are_dropped_and_digits_kept(self) -> None:
        self.assertEqual(check.tokenize("a b 3.4 x v3 3x"), ["v3", "3x"])


class RankingTests(unittest.TestCase):
    def test_description_vocabulary_ranks_its_owner_first(self) -> None:
        index = check.Index(DESCRIPTIONS)
        self.assertEqual(index.ranking("our data plane nodes are disconnected")[0], "alpha")
        self.assertEqual(index.ranking("preview the sync of declarative state")[0], "beta")
        self.assertEqual(index.ranking("pick brand colors for the landing page")[0], "gamma")

    def test_ties_break_by_name_and_unknown_words_are_ignored(self) -> None:
        index = check.Index(DESCRIPTIONS)
        self.assertEqual(index.ranking("zzz qqq"), ["alpha", "beta", "gamma"])

    def test_the_name_is_not_part_of_the_vector(self) -> None:
        index = check.Index({"deck-gateway": "Write declarative state files.", "other": "Design portal pages."})
        self.assertEqual(index.similarities("deck")["deck-gateway"], 0.0)

    def test_analysis_records_ranks_per_expected_skill(self) -> None:
        scenarios = [
            scenario("a1", "data plane nodes are disconnected", ("alpha",)),
            scenario("a2", "preview the sync of declarative state", ("alpha",)),  # beta's vocabulary
            scenario("s1", "preview the sync of declarative state", ("beta",), "sibling", ("alpha",)),
            scenario("n1", "disconnected data plane nodes", (), "near-miss", ("alpha",)),
        ]
        analysis = check.analyze(DESCRIPTIONS, scenarios)
        self.assertEqual(analysis.skills["alpha"].ranks[0], 1)
        self.assertGreater(analysis.skills["alpha"].ranks[1], 1)
        self.assertEqual(analysis.skills["beta"].ranks, [1])
        self.assertEqual((analysis.skills["alpha"].hit(1), analysis.skills["alpha"].hit(3)), (0.5, 1.0))
        self.assertEqual(analysis.owner_beats_target, (1, 1))
        self.assertEqual(analysis.near_miss_leak, (1, 1))
        self.assertEqual(set(analysis.by_tag), {"positive", "sibling"})
        self.assertNotIn("gamma", analysis.skills)  # no scenario expects it

    def test_unknown_expected_skill_is_skipped(self) -> None:
        analysis = check.analyze(DESCRIPTIONS, [scenario("x", "anything", ("nope",))])
        self.assertEqual(analysis.skills, {})


class ThresholdTests(unittest.TestCase):
    def stats(self, ranks: list[int]) -> check.SkillStats:
        return check.SkillStats(ranks)

    def analysis(self, skills: dict[str, list[int]], collisions: list[tuple[float, str, str]] | None = None) -> check.Analysis:
        return check.Analysis({n: self.stats(r) for n, r in skills.items()}, {}, (0, 0), (0, 0), collisions or [])

    def test_collision_is_an_error_naming_both_skills(self) -> None:
        errors, _ = check.judge(self.analysis({}, [(0.8, "a", "b"), (0.69, "c", "d")]))
        self.assertEqual(len(errors), 1)
        self.assertIn("a and b", errors[0])
        self.assertEqual(check.judge(self.analysis({}, [(check.COLLISION_ERROR, "a", "b")]))[0][0][:21], "description collision")

    def test_collapse_is_an_error_and_weak_is_a_warning_that_names_the_skill(self) -> None:
        healthy = [1, 1, 2, 3, 3]
        errors, warnings = check.judge(self.analysis({"good": healthy, "good2": healthy * 3, "weak": [1, 2, 9, 9, 9, 9], "dead": [9] * 5}))
        self.assertEqual([e.split(":")[0] for e in errors], ["description collapse"])
        self.assertIn("dead", errors[0])
        self.assertEqual(len(warnings), 1)
        self.assertIn("weak", warnings[0])

    def test_boundaries(self) -> None:
        n = 10
        at_collapse = [1] * round(n * check.COLLAPSE_HIT3) + [9] * (n - round(n * check.COLLAPSE_HIT3))
        self.assertEqual(check.judge(self.analysis({"s": at_collapse, "t": [1] * n}))[0], [])  # exactly the floor passes
        below = [1] * (round(n * check.COLLAPSE_HIT3) - 1) + [9] * (n - round(n * check.COLLAPSE_HIT3) + 1)
        self.assertEqual(len(check.judge(self.analysis({"s": below, "t": [1] * n}))[0]), 1)

    def test_few_scenarios_are_not_judged(self) -> None:
        errors, warnings = check.judge(self.analysis({"tiny": [9] * (check.MIN_JUDGED - 1), "ok": [1] * 10}))
        self.assertEqual((errors, warnings), ([], []))

    def test_corpus_floor(self) -> None:
        # every skill sits just above the collapse floor but the corpus is poor
        ranks = [1, 9, 9, 9, 9]
        errors, _ = check.judge(self.analysis({f"s{i}": ranks for i in range(4)}))
        self.assertTrue(any("corpus" in e for e in errors))


class RealCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.descriptions = check.load_descriptions()
        cls.scenarios = check.load_scenarios()
        cls.analysis = check.analyze(cls.descriptions, cls.scenarios)

    def test_the_current_repo_passes_and_the_corpus_has_signal(self) -> None:
        errors, _ = check.judge(self.analysis)
        self.assertEqual(errors, [])
        chance = check.TOP_K / len(self.descriptions)
        self.assertGreater(self.analysis.corpus.hit(check.TOP_K), 4 * chance)
        self.assertGreater(len(self.analysis.skills), 20)

    def test_thresholds_keep_margin_over_the_measured_corpus(self) -> None:
        judged = [s.hit(check.TOP_K) for s in self.analysis.skills.values() if s.total >= check.MIN_JUDGED]
        self.assertGreaterEqual(min(judged), check.COLLAPSE_HIT3 + 0.15)
        self.assertGreaterEqual(self.analysis.corpus.hit(check.TOP_K), check.CORPUS_HIT3 + 0.15)
        self.assertLessEqual(self.analysis.collisions[0][0], check.COLLISION_ERROR - 0.15)

    def test_marketing_copy_collapses_the_skills_positives(self) -> None:
        real = self.analysis.skills[TRIAGE]
        damaged_descriptions = {**self.descriptions, TRIAGE: canary.CANARY_DESCRIPTION}
        damaged = check.analyze(damaged_descriptions, self.scenarios)
        self.assertGreaterEqual(real.hit(check.TOP_K), 0.6)
        self.assertLessEqual(damaged.skills[TRIAGE].hit(check.TOP_K), 0.1)
        self.assertLess(damaged.skills[TRIAGE].hit(check.TOP_K), real.hit(check.TOP_K) - 0.5)
        self.assertEqual(real.total, damaged.skills[TRIAGE].total)
        errors, _ = check.judge(damaged)
        self.assertEqual(len(errors), 1)
        self.assertIn(TRIAGE, errors[0])
        self.assertIn("description collapse", errors[0])

    def test_a_copied_description_is_a_collision(self) -> None:
        other = "konnect-api-publish"
        errors, _ = check.judge(check.analyze({**self.descriptions, other: self.descriptions[TRIAGE]}, self.scenarios))
        self.assertTrue(any("description collision" in e and TRIAGE in e and other in e for e in errors))


class CliTests(unittest.TestCase):
    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = check.main(["check_description_routing.py", *args])
        return code, out.getvalue(), err.getvalue()

    def test_default_run_passes_quietly(self) -> None:
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("description-routing-ok", out)
        self.assertNotIn("hit@1", out)

    def test_report_prints_the_table_distribution_and_weakest_skills(self) -> None:
        code, out, _ = self.run_main("--report")
        self.assertEqual(code, 0)
        for text in ("hit@1", "hit@3", TRIAGE, "rank distribution", "weakest skills by hit@3", "informational only"):
            self.assertIn(text, out)


if __name__ == "__main__":
    unittest.main()
