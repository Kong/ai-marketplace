"""Candidate/control comparison tests: workspace isolation, deltas, new-skill policy, minimums.

Synthetic results and throwaway git repositories; no model calls.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

import check_repo
import prepare_routing_workspace as prep
import routing_compare as compare
import routing_results as r
import run_routing_comparison as driver
import test_routing_results as fixtures
import validate_routing_scenarios as validator

SCRATCH = Path(__file__).resolve().parents[1] / ".tmp"


def skill_md(name: str, body: str) -> str:
    return (
        f"---\nname: {name}\ndescription: Handle {name} work\nlicense: MIT\n"
        f"metadata:\n  product: konnect\n  category: domain\n  tags:\n    - kong\n---\n{body}\n"
    )


class ThrowawayRepo(unittest.TestCase):
    """A git repo with one plugin, patched in as the repo root for workspace code."""

    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve()
        for patcher in (
            mock.patch.object(check_repo, "REPO_ROOT", self.repo),
            mock.patch.object(check_repo, "PLUGINS_DIR", self.repo / "plugins"),
            mock.patch.object(prep, "TMP_ROOT", self.repo / ".tmp"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        plugin = self.repo / "plugins" / "demo"
        for manifest in (".claude-plugin", ".cursor-plugin", ".codex-plugin"):
            (plugin / manifest).mkdir(parents=True)
            (plugin / manifest / "plugin.json").write_text("{}")
        self.git("init", "-q", "-b", "main")
        self.write_skill("alpha", "control alpha")
        self.write_skill("beta", "control beta")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.repo, check=True, capture_output=True, text=True,
        ).stdout

    def write_skill(self, name: str, body: str) -> None:
        path = self.repo / "plugins" / "demo" / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(skill_md(name, body))


class WorkspaceIsolationTests(ThrowawayRepo):
    def test_control_reads_merge_base_while_candidate_reads_working_tree(self) -> None:
        self.write_skill("alpha", "candidate alpha")  # uncommitted edit to a modified skill
        self.write_skill("gamma", "candidate-only gamma")  # new skill
        root = self.repo / ".tmp" / "routing"
        for host, skills_dir in (("claude", ".claude/skills"), ("codex", ".agents/skills")):
            with self.subTest(host=host):
                cand = prep.prepare_workspace(root / "candidate" / host, host)
                ctrl = prep.prepare_workspace(root / "control" / host, host, self.base)
                self.assertEqual(sorted(cand), ["alpha", "beta", "gamma"])
                self.assertEqual(sorted(ctrl), ["alpha", "beta"])
                read = lambda variant, name: (root / variant / host / skills_dir / name / "SKILL.md").read_text()  # noqa: E731
                self.assertIn("candidate alpha", read("candidate", "alpha"))
                self.assertIn("control alpha", read("control", "alpha"))
                self.assertIn("control beta", read("candidate", "beta"))
                self.assertFalse((root / "control" / host / skills_dir / "gamma").exists())

    def test_control_is_a_copy_not_the_checkout_and_edits_do_not_cross_over(self) -> None:
        root = self.repo / ".tmp" / "routing"
        prep.prepare_workspace(root / "candidate" / "claude", "claude")
        prep.prepare_workspace(root / "control" / "claude", "claude", self.base)
        skill = root / "candidate" / "claude" / ".claude" / "skills" / "alpha"
        self.assertFalse(skill.is_symlink())
        (skill / "SKILL.md").write_text("tampered")
        control = root / "control" / "claude" / ".claude" / "skills" / "alpha" / "SKILL.md"
        self.assertIn("control alpha", control.read_text())
        self.assertIn("control alpha", (self.repo / "plugins/demo/skills/alpha/SKILL.md").read_text())

    def test_control_includes_supporting_files(self) -> None:
        ref_file = self.repo / "plugins/demo/skills/alpha/references/x.md"
        ref_file.parent.mkdir()
        ref_file.write_text("ref")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "refs")
        out = self.repo / ".tmp" / "routing" / "control" / "claude"
        prep.prepare_workspace(out, "claude", "HEAD")
        self.assertEqual((out / ".claude/skills/alpha/references/x.md").read_text(), "ref")

    def test_ref_workspace_still_refuses_destinations_outside_tmp(self) -> None:
        with self.assertRaises(ValueError):
            prep.prepare_workspace(Path("/tmp/routing-elsewhere"), "claude", self.base)


class VariantWiringTests(ThrowawayRepo):
    def test_variants_differ_only_in_workspace_root_and_report_dir(self) -> None:
        calls: list[tuple[str, str, Path, str | None]] = []

        def fake(host: str, skill: str, report: Path, pattern: str | None):
            calls.append((host, skill, report, pattern))
            return "", [fixtures.row(scenario="s1", trials=1)]

        routing = self.repo / ".tmp" / "routing"
        cand = driver.evaluate_variant("candidate", "codex", "alpha", None, [], fake, routing)
        ctrl = driver.evaluate_variant("control", "codex", "alpha", self.base, [], fake, routing)
        self.assertEqual(cand["state"], r.PASS)
        self.assertEqual(ctrl["state"], r.PASS)
        (h1, s1, rep1, p1), (h2, s2, rep2, p2) = calls
        self.assertEqual((h1, s1, p1), (h2, s2, p2))
        self.assertEqual(rep1.name, rep2.name)
        self.assertNotEqual(rep1.parent, rep2.parent)
        self.assertTrue((routing / "candidate" / "codex" / ".agents/skills/alpha").is_dir())
        self.assertTrue((routing / "control" / "codex" / ".agents/skills/beta").is_dir())

    def test_default_runner_passes_workspace_root_env(self) -> None:
        seen: dict[str, str] = {}

        def fake_promptfoo(host, skill, report, pattern, env=None, ledger=None):
            seen.update(env or {})
            return "", [fixtures.row()]

        with mock.patch.object(driver.runner, "run_promptfoo", fake_promptfoo):
            driver.evaluate_variant("control", "claude", "alpha", self.base, [], None, self.repo / ".tmp" / "routing")
        self.assertEqual(seen, {"ROUTING_WORKSPACE_ROOT": str(self.repo / ".tmp" / "routing" / "control")})

    def test_validation_errors_skip_workspace_and_run(self) -> None:
        def boom(*args):
            raise AssertionError("must not run")

        doc = driver.evaluate_variant("candidate", "claude", "alpha", None, ["bad"], boom, self.repo / ".tmp" / "routing")
        self.assertEqual((doc["state"], doc["failure_kinds"]), (r.INFRA_ERROR, [r.SCENARIO_VALIDATION]))
        self.assertFalse((self.repo / ".tmp" / "routing" / "candidate").exists())

    def test_new_skill_detection_uses_merge_base_catalog(self) -> None:
        self.git("checkout", "-q", "-b", "feature")
        self.write_skill("gamma", "new")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "add gamma")
        self.assertEqual(driver.skills_at(driver.merge_base("main")), {"alpha", "beta"})
        self.assertIn("gamma", driver.skills_at("HEAD"))


def host_doc(host="codex", skill="alpha", **scenario_trials):
    """Reduce rows given {scenario: [passed, ...]} into a host result."""
    rows = []
    for scenario, outcomes in scenario_trials.items():
        for index, ok in enumerate(outcomes, start=1):
            rows.append(fixtures.row(scenario=scenario, trial=index, trials=len(outcomes), calls=None if ok else [], success=ok))
    return r.reduce_host(host, skill, [rows])


class DeltaTests(unittest.TestCase):
    def test_seeded_regression_shows_negative_delta_per_scenario_and_aggregate(self) -> None:
        control = host_doc(pos=[True, True, True], near=[True, True, True])
        candidate = host_doc(pos=[True, False, False], near=[True, True, True])
        doc = compare.compare_host(candidate, control)
        by_id = {s["id"]: s for s in doc["scenarios"]}
        self.assertAlmostEqual(by_id["pos"]["delta"], round(1 / 3 - 1, 4))
        self.assertEqual(by_id["near"]["delta"], 0.0)
        self.assertEqual(doc["aggregate"]["candidate"]["passes"], 4)
        self.assertEqual(doc["aggregate"]["control"]["passes"], 6)
        self.assertAlmostEqual(doc["aggregate"]["delta"], round(4 / 6 - 1, 4))
        self.assertEqual((doc["host"], doc["mode"], doc["complete"]), ("codex", "comparison", True))

    def test_improvement_is_positive_and_state_is_candidates_own(self) -> None:
        control = host_doc(pos=[False, False, True])
        candidate = host_doc(pos=[True, True, True])
        doc = compare.compare_host(candidate, control)
        self.assertGreater(doc["aggregate"]["delta"], 0)
        self.assertEqual((doc["state"], doc["control_state"]), (r.PASS, r.ROUTING_FAIL))

    def test_infra_error_side_is_incomplete_and_has_no_delta(self) -> None:
        control = r.host_failure("codex", "alpha", r.PROVIDER, "down")
        doc = compare.compare_host(host_doc(pos=[True]), control)
        self.assertFalse(doc["complete"])
        self.assertIsNone(doc["aggregate"]["delta"])
        self.assertEqual(doc["scenarios"][0]["control"], None)

    def test_hosts_are_compared_independently(self) -> None:
        claude = compare.compare_host(host_doc("claude", pos=[True]), host_doc("claude", pos=[True]))
        codex = compare.compare_host(host_doc("codex", pos=[False]), host_doc("codex", pos=[True]))
        self.assertEqual((claude["host"], claude["aggregate"]["delta"]), ("claude", 0.0))
        self.assertEqual((codex["host"], codex["aggregate"]["delta"]), ("codex", -1.0))
        self.assertEqual(r.combine_hosts([claude, codex])["state"], r.ROUTING_FAIL)

    def test_passing_candidate_with_failed_control_combines_to_incomplete_infra_error(self) -> None:
        claude = compare.compare_host(host_doc("claude", pos=[True]), host_doc("claude", pos=[True]))
        codex = compare.compare_host(host_doc("codex", pos=[True]), r.host_failure("codex", "alpha", r.PROVIDER, "down"))
        self.assertEqual((codex["state"], codex["complete"]), (r.PASS, False))
        combined = r.combine_hosts([claude, codex])
        self.assertEqual((combined["state"], combined["complete"]), (r.INFRA_ERROR, False))
        self.assertEqual(driver.runner.EXIT_CODES[combined["state"]], 3)

    def test_no_stored_baseline_input(self) -> None:
        self.assertEqual(compare.compare_host.__code__.co_argcount, 2)


class NewSkillPolicyTests(unittest.TestCase):
    TAGS = {"pos": ["positive"], "near": ["near-miss"], "sib": ["sibling"]}

    def doc(self, pos, near, sib=(True,)):
        return host_doc(pos=pos, near=near, sib=list(sib))

    def test_thresholds_met_at_the_boundary(self) -> None:
        # 15 positive trials: 14/15 = 93% >= 90%. 20 near-miss trials: 19/20 = 95%.
        doc = compare.evaluate_new_skill(
            self.doc([True] * 14 + [False], [True] * 19 + [False]), self.TAGS
        )
        self.assertEqual(doc["state"], r.PASS)
        self.assertEqual(doc["control"], "skipped")
        self.assertEqual(doc["mode"], "new_skill")
        self.assertEqual(doc["expectations"]["positive_recall"]["passes"], 14)

    def test_below_positive_recall_fails(self) -> None:
        doc = compare.evaluate_new_skill(self.doc([True] * 13 + [False] * 2, [True] * 20), self.TAGS)
        self.assertEqual(doc["state"], r.ROUTING_FAIL)
        self.assertFalse(doc["expectations"]["positive_recall"]["met"])
        self.assertTrue(doc["expectations"]["near_miss_specificity"]["met"])

    def test_below_near_miss_specificity_fails(self) -> None:
        doc = compare.evaluate_new_skill(self.doc([True] * 15, [True] * 18 + [False] * 2), self.TAGS)
        self.assertEqual(doc["state"], r.ROUTING_FAIL)
        self.assertFalse(doc["expectations"]["near_miss_specificity"]["met"])

    def test_absolute_thresholds_replace_the_two_of_three_rule(self) -> None:
        # Each scenario passes 2/3 (host passes), yet recall 67% misses 90%.
        host = host_doc(pos=[True, True, False], near=[True, True, True])
        self.assertEqual(host["state"], r.PASS)
        self.assertEqual(compare.evaluate_new_skill(host, self.TAGS)["state"], r.ROUTING_FAIL)

    def test_incomplete_host_is_infra_error_not_routing_fail(self) -> None:
        failed = r.host_failure("codex", "alpha", r.PROVIDER, "no key")
        doc = compare.evaluate_new_skill(failed, self.TAGS)
        self.assertEqual((doc["state"], doc["complete"]), (r.INFRA_ERROR, False))

    def test_missing_category_is_not_met(self) -> None:
        doc = compare.evaluate_new_skill(host_doc(pos=[True]), self.TAGS)
        self.assertFalse(doc["expectations"]["near_miss_specificity"]["met"])
        self.assertEqual(doc["state"], r.ROUTING_FAIL)

    def test_siblings_are_reported_not_thresholded(self) -> None:
        doc = compare.evaluate_new_skill(self.doc([True] * 3, [True] * 3, sib=[False]), self.TAGS)
        self.assertEqual(doc["state"], r.PASS)
        self.assertEqual((doc["siblings"]["passes"], doc["siblings"]["trials"]), (0, 1))


def scenario_yaml(positives=5, near_misses=5, siblings=None, skill="alpha") -> str:
    siblings = {"beta": 2, "gamma": 2} if siblings is None else siblings
    items = []
    for i in range(positives):
        items.append(f"  - {{id: p-{i}, prompt: x, expect: [{skill}], forbid: [], trials: 3, tags: [positive]}}")
    for i in range(near_misses):
        items.append(f"  - {{id: n-{i}, prompt: x, expect: [], forbid: [{skill}], trials: 3, tags: [near-miss]}}")
    for name, count in siblings.items():
        for i in range(count):
            items.append(f"  - {{id: s-{name}-{i}, prompt: x, expect: [{name}], forbid: [{skill}], trials: 1, tags: [sibling]}}")
    return f"skill: {skill}\nscenarios:\n" + "\n".join(items) + "\n"


class NewSkillMinimumTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)

    def errors(self, content: str, adjacent=("beta", "gamma")) -> list[str]:
        (self.dir / "alpha.yaml").write_text(textwrap.dedent(content))
        return validator.new_skill_minimum_errors(self.dir, "alpha", list(adjacent))

    def test_exact_minimums_pass(self) -> None:
        self.assertEqual(self.errors(scenario_yaml()), [])

    def test_too_few_positives_fails(self) -> None:
        errors = self.errors(scenario_yaml(positives=4))
        self.assertEqual(len(errors), 1)
        self.assertIn("at least 5 positive scenarios, found 4", errors[0])

    def test_too_few_near_misses_fails(self) -> None:
        self.assertIn("at least 5 near-miss scenarios, found 4", self.errors(scenario_yaml(near_misses=4))[0])

    def test_each_adjacent_skill_needs_two_siblings(self) -> None:
        errors = self.errors(scenario_yaml(siblings={"beta": 2, "gamma": 1}))
        self.assertEqual(len(errors), 1)
        self.assertIn("adjacent skill 'gamma', found 1", errors[0])

    def test_positive_and_near_miss_need_three_trials_but_siblings_do_not(self) -> None:
        content = scenario_yaml().replace("trials: 3, tags: [near-miss]", "trials: 1, tags: [near-miss]")
        errors = self.errors(content)
        self.assertEqual(len(errors), 5)
        self.assertTrue(all("needs trials: 3" in e for e in errors))

    def test_max_adjacent_is_shared_with_selection(self) -> None:
        self.assertIs(validator.MAX_ADJACENT, validator.select_changed.MAX_ADJACENT)

    def test_sibling_must_forbid_the_target(self) -> None:
        content = scenario_yaml(siblings={"beta": 2}).replace("forbid: [alpha], trials: 1", "forbid: [], trials: 1")
        self.assertTrue(any("adjacent skill 'beta', found 0" in e for e in self.errors(content, ("beta",))))

    def test_positive_must_expect_target(self) -> None:
        content = scenario_yaml().replace("expect: [alpha], forbid: [], trials: 3", "expect: [beta], forbid: [], trials: 3")
        self.assertTrue(any("positive scenarios, found 0" in e for e in self.errors(content)))

    def test_no_scenarios_fails_every_minimum(self) -> None:
        self.assertEqual(len(validator.new_skill_minimum_errors(self.dir, "alpha", ["beta"])), 3)

    def test_more_than_five_adjacent_skills_fails(self) -> None:
        names = [f"adj-{i}" for i in range(6)]
        errors = self.errors(scenario_yaml(siblings={n: 2 for n in names}), adjacent=names[:5])
        self.assertEqual(len(errors), 1)
        self.assertIn("6 adjacent skills; at most 5", errors[0])

    def test_requirement_is_capped_at_five_adjacent_skills(self) -> None:
        names = [f"adj-{i}" for i in range(7)]
        self.assertEqual(self.errors(scenario_yaml(siblings={n: 2 for n in names[:5]}), adjacent=names), [])

    def test_cli_fails_for_new_skill_without_corpus_and_is_inert_without_flag(self) -> None:
        with mock.patch.object(validator, "SCENARIOS_DIR", self.dir), \
             mock.patch.object(validator, "adjacent_skills", return_value=["beta"]), \
             mock.patch.object(validator, "known_skill_names", return_value={"alpha", "beta"}), \
             mock.patch("sys.argv", ["v", "--new-skill=alpha"]), mock.patch("sys.stderr"):
            self.assertEqual(validator.main(), 2)
        with mock.patch.object(validator, "SCENARIOS_DIR", self.dir), \
             mock.patch.object(validator, "known_skill_names", return_value={"alpha", "beta"}), \
             mock.patch("sys.argv", ["v"]), mock.patch("builtins.print"):
            self.assertEqual(validator.main(), 0)


class DriverPolicyTests(ThrowawayRepo):
    """main() end to end with the Promptfoo runner stubbed."""

    def run_main(self, skill: str, scenario_dir: Path, fake, adjacent=("beta", "gamma"), extra=()) -> tuple[int, list[str]]:
        calls: list[str] = []

        def stub(host, name, report, pattern, env=None, ledger=None):
            calls.append(f"{host}:{Path(env['ROUTING_WORKSPACE_ROOT']).name}")
            return fake()

        patches = [
            mock.patch.object(driver.scenarios, "SCENARIOS_DIR", scenario_dir),
            mock.patch.object(driver.scenarios, "known_skill_names", return_value={"alpha", "beta", "gamma"}),
            mock.patch.object(driver.scenarios, "adjacent_skills", return_value=list(adjacent)),
            mock.patch.object(driver, "ROUTING_DIR", self.repo / ".tmp" / "routing"),
            mock.patch.object(driver.runner, "REPORTS_DIR", self.repo / ".tmp" / "routing" / "reports"),
            mock.patch.object(driver.runner, "run_promptfoo", stub),
            mock.patch("builtins.print"),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.git("checkout", "-q", "-b", "feature")
        self.write_skill("gamma", "new skill")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "gamma")
        return driver.main(["run", skill, "--base", "main", *extra]), calls

    def scenario_dir(self, content: str) -> Path:
        directory = self.repo / "scenarios"
        directory.mkdir()
        (directory / "gamma.yaml").write_text(content)
        return directory

    def test_new_skill_below_minimums_fails_validation_and_runs_nothing(self) -> None:
        directory = self.scenario_dir(scenario_yaml(positives=1, skill="gamma", siblings={"beta": 2, "gamma2": 0}))
        code, calls = self.run_main("gamma", directory, lambda: self.fail("must not run"))
        self.assertEqual((code, calls), (2, []))
        self.assertFalse((self.repo / ".tmp/routing/candidate").exists())

    def test_new_skill_positive_scenarios_need_three_trials(self) -> None:
        content = scenario_yaml(skill="gamma", siblings={"beta": 2, "alpha": 2}).replace(
            "trials: 3, tags: [positive]", "trials: 1, tags: [positive]"
        )
        code, calls = self.run_main("gamma", self.scenario_dir(content), lambda: self.fail("must not run"), adjacent=("beta", "alpha"))
        self.assertEqual((code, calls), (2, []))

    def test_unexpected_exception_is_a_harness_error_not_routing_fail(self) -> None:
        directory = self.scenario_dir(scenario_yaml(skill="alpha"))
        (directory / "gamma.yaml").rename(directory / "alpha.yaml")

        def boom():
            raise RuntimeError("boom")
        with mock.patch("traceback.print_exc"), mock.patch("sys.stderr"):
            code, _ = self.run_main("alpha", directory, boom)
        self.assertEqual(code, 2)

    def test_new_skill_runs_candidate_only_and_reports_absolute_expectations(self) -> None:
        directory = self.scenario_dir(scenario_yaml(skill="gamma", siblings={"beta": 2, "alpha": 2}))

        def fake():
            return "", [
                fixtures.row(scenario=f"{prefix}-{i}", trial=t, trials=3, calls=[], success=False,
                             expected=("gamma",) if prefix == "p" else ())
                for prefix, count in (("p", 5), ("n", 5)) for i in range(count) for t in (1, 2, 3)
            ]
        code, calls = self.run_main("gamma", directory, fake, adjacent=("beta", "alpha"))
        self.assertEqual(set(calls), {"claude:candidate", "codex:candidate"})
        self.assertNotIn("control", " ".join(calls))
        self.assertEqual(code, 1)
        doc = (self.repo / ".tmp/routing/reports/codex-gamma.comparison.json").read_text()
        self.assertIn('"mode": "new_skill"', doc)
        self.assertIn('"control": "skipped"', doc)

    def test_modified_skill_runs_candidate_and_control_with_same_scenarios(self) -> None:
        directory = self.scenario_dir(scenario_yaml(skill="alpha"))
        (directory / "gamma.yaml").rename(directory / "alpha.yaml")
        code, calls = self.run_main("alpha", directory, lambda: ("", [fixtures.row()]))
        self.assertEqual(
            calls, ["claude:candidate", "claude:control", "codex:candidate", "codex:control"]
        )
        self.assertEqual(code, 0)
        self.assertIn('"mode": "comparison"', (self.repo / ".tmp/routing/reports/codex-alpha.comparison.json").read_text())


class ExitCodeTests(unittest.TestCase):
    def test_uncaught_exception_exits_2_for_eval_runner(self) -> None:
        import run_routing_eval as runner

        with mock.patch.object(runner.scenarios, "known_skill_names", side_effect=RuntimeError("boom")), \
             mock.patch("sys.stderr"), mock.patch("traceback.print_exc"):
            self.assertEqual(runner.main(["run", "alpha"]), 2)

    def test_invalid_scenarios_exit_2_before_any_host_runs(self) -> None:
        import run_routing_eval as runner

        with mock.patch.object(runner.scenarios, "known_skill_names", return_value={"alpha"}), \
             mock.patch.object(runner.scenarios, "validate_scenarios", return_value=["bad"]), \
             mock.patch.object(runner, "evaluate_host", side_effect=AssertionError("ran")), \
             mock.patch("sys.stderr"):
            self.assertEqual(runner.main(["run", "alpha"]), 2)

    def test_workspace_errors_exit_2(self) -> None:
        with mock.patch("sys.stderr"):
            self.assertEqual(prep.main(["p", "/tmp/not-under-the-repo-tmp"]), 2)


class AgentSubsetDriverTests(DriverPolicyTests):
    def modified(self, extra):
        directory = self.scenario_dir(scenario_yaml(skill="alpha"))
        (directory / "gamma.yaml").rename(directory / "alpha.yaml")
        return self.run_main("alpha", directory, lambda: ("", [fixtures.row()]), extra=extra)

    def test_subset_runs_only_that_agent_and_is_marked_partial(self) -> None:
        code, calls = self.modified(["--agent", "codex"])
        self.assertEqual((code, calls), (0, ["codex:candidate", "codex:control"]))
        reports = self.repo / ".tmp/routing/reports"
        summary = json.loads((reports / "alpha.comparison-summary.json").read_text())
        self.assertEqual((summary["agents_run"], summary["partial"]), (["codex"], True))
        self.assertEqual(list(summary["hosts"]), ["codex"])
        doc = json.loads((reports / "codex-alpha.comparison.json").read_text())
        self.assertEqual((doc["agents_run"], doc["partial"]), (["codex"], True))
        self.assertFalse((reports / "claude-alpha.comparison.json").exists())
        self.assertFalse((self.repo / ".tmp/routing/candidate/claude").exists())

    def test_comma_separated_and_default_cover_both_agents_and_are_not_partial(self) -> None:
        for extra in ([], ["--agent", "claude,codex"]):
            self.setUp()
            code, calls = self.modified(extra)
            self.assertEqual(len(calls), 4)
            summary = json.loads((self.repo / ".tmp/routing/reports/alpha.comparison-summary.json").read_text())
            self.assertEqual((summary["agents_run"], summary["partial"]), (["claude", "codex"], False))

    def test_unknown_agent_exits_2_before_any_run(self) -> None:
        with mock.patch("sys.stderr"):
            code, calls = self.modified(["--agent", "gemini"])
        self.assertEqual((code, calls), (2, []))


class DescribeTests(unittest.TestCase):
    def test_summary_lines_are_per_host(self) -> None:
        mod = compare.compare_host(host_doc(pos=[True]), host_doc(pos=[True]))
        self.assertIn("delta +0.00", driver.describe(mod))
        new = compare.evaluate_new_skill(host_doc(pos=[True]), {"pos": ["positive"]})
        self.assertIn("control skipped", driver.describe(new))


if __name__ == "__main__":
    unittest.main()
