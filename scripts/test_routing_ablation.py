"""Name-only ablation tests: classification, per-tag report, workspaces and the CLI; offline fake results."""
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
import routing_ablation as ablation
import routing_results as r
import run_routing_comparison as driver
import run_routing_eval as runner

SKILL = "konnect-gateway-triage"
SCRATCH = check_repo.REPO_ROOT / ".tmp"
PASS, FAIL, INFRA = r.PASS, r.ROUTING_FAIL, r.INFRA_ERROR


def agent_result(states: dict[str, str], complete: bool = True) -> dict:
    return {"complete": complete, "reason": None if complete else "provider error", "scenarios": [{"id": i, "state": s} for i, s in states.items()]}


class ClassifyTests(unittest.TestCase):
    def test_the_four_classes(self) -> None:
        self.assertEqual(ablation.classify(PASS, FAIL), ablation.DESCRIPTION_DEPENDENT)
        self.assertEqual(ablation.classify(PASS, PASS), ablation.NAME_SOLVABLE)
        self.assertEqual(ablation.classify(FAIL, PASS), ablation.FAILING)
        self.assertEqual(ablation.classify(FAIL, FAIL), ablation.FAILING)

    def test_an_unjudged_side_is_incomplete_unless_the_default_already_failed(self) -> None:
        for default, name_only in ((INFRA, PASS), (PASS, INFRA), (None, PASS), (PASS, None), (INFRA, FAIL)):
            with self.subTest(default=default, name_only=name_only):
                self.assertEqual(ablation.classify(default, name_only), ablation.INCOMPLETE)
        self.assertEqual(ablation.classify(FAIL, INFRA), ablation.FAILING)  # fails default whatever name-only did


class JudgeTests(unittest.TestCase):
    ROWS = [{"id": f"s{i}"} for i in range(1, 7)]
    TAGS = {"s1": ["positive"], "s2": ["positive"], "s3": ["positive"], "s4": ["near-miss"], "s5": ["sibling"], "s6": ["sibling"]}

    def judge(self, default: dict[str, str], name_only: dict[str, str], complete: bool = True) -> dict:
        return ablation.judge(self.ROWS, self.TAGS, {"default": agent_result(default, complete), "name-only": agent_result(name_only, complete)})

    def test_counts_and_percentages_overall_and_per_tag(self) -> None:
        default = {"s1": PASS, "s2": PASS, "s3": FAIL, "s4": PASS, "s5": PASS, "s6": PASS}
        name_only = {"s1": FAIL, "s2": PASS, "s3": PASS, "s4": PASS, "s5": FAIL, "s6": PASS}
        doc = self.judge(default, name_only)
        self.assertEqual([x["class"] for x in doc["scenarios"]], ["description_dependent", "name_solvable", "failing", "name_solvable", "description_dependent", "name_solvable"])
        total = doc["counts"]
        self.assertEqual((total["total"], total["description_dependent"], total["name_solvable"], total["failing"], total["incomplete"]), (6, 2, 3, 1, 0))
        self.assertEqual(total["percent"], {"description_dependent": 33.3, "name_solvable": 50.0, "failing": 16.7})
        positive = doc["by_tag"]["positive"]
        self.assertEqual((positive["total"], positive["description_dependent"], positive["name_solvable"], positive["failing"]), (3, 1, 1, 1))
        self.assertEqual(positive["percent"]["description_dependent"], 33.3)
        self.assertEqual(doc["by_tag"]["near-miss"]["percent"], {"description_dependent": 0.0, "name_solvable": 100.0, "failing": 0.0})
        self.assertEqual(doc["by_tag"]["sibling"]["description_dependent"], 1)
        self.assertEqual(sorted(doc["by_tag"]), ["near-miss", "positive", "sibling"])
        self.assertTrue(doc["complete"])

    def test_an_infrastructure_error_makes_it_incomplete(self) -> None:
        states = {f"s{i}": PASS for i in range(1, 7)}
        doc = self.judge(states, {**states, "s2": INFRA})
        self.assertFalse(doc["complete"])
        self.assertEqual(doc["counts"]["incomplete"], 1)
        self.assertFalse(self.judge(states, states, complete=False)["complete"])

    def test_a_scenario_that_never_ran_is_incomplete(self) -> None:
        states = {f"s{i}": PASS for i in range(1, 6)}  # s6 missing
        doc = self.judge(states, states)
        self.assertFalse(doc["complete"])
        self.assertEqual(doc["scenarios"][-1]["class"], ablation.INCOMPLETE)

    def test_empty_tag_percentages_are_none(self) -> None:
        self.assertEqual(ablation._counts([])["percent"], {"description_dependent": None, "name_solvable": None, "failing": None})


class OfflineRunTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="ablation-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.rows = ablation.own_scenarios(SKILL)
        self.ids = [s["id"] for s in self.rows]

    def run_ablation(self, fake: dict) -> dict:
        return ablation.run_ablation(SKILL, ("claude",), self.dir, fake=fake)

    def test_own_scenarios_cover_every_tag(self) -> None:
        tags = {t for s in self.rows for t in s["tags"]}
        self.assertEqual(tags, {"positive", "near-miss", "sibling"})
        self.assertTrue(all(s["id"].startswith("gateway-triage-") for s in self.rows))

    def test_classification_end_to_end_with_fake_runner_results(self) -> None:
        dependent, failing = self.ids[0], self.ids[1]
        fake = {"default": {failing: False}, "name-only": {dependent: False, failing: False, self.ids[2]: False}}
        doc = self.run_ablation(fake)
        by_id = {s["id"]: s for s in doc["scenarios"]}
        self.assertEqual(by_id[dependent]["class"], ablation.DESCRIPTION_DEPENDENT)
        self.assertEqual(by_id[failing]["class"], ablation.FAILING)
        self.assertEqual(by_id[self.ids[2]]["class"], ablation.DESCRIPTION_DEPENDENT)
        self.assertEqual(by_id[self.ids[3]]["class"], ablation.NAME_SOLVABLE)
        self.assertEqual(doc["counts"]["total"], len(self.ids))
        self.assertEqual((doc["mode"], doc["agent"], doc["complete"], doc["exit_code"], doc["offline"]), ("ablation", "claude", True, 0, True))
        self.assertEqual((doc["agents_run"], doc["partial"], doc["trials_per_scenario"]), (["claude"], True, 1))
        self.assertEqual(doc["usage"]["trials"], 2 * len(self.ids))  # one trial per scenario under each listing
        self.assertEqual(set(doc["listings"]), {"default", "name-only"})

    def test_every_scenario_passing_both_is_name_solvable(self) -> None:
        doc = self.run_ablation({})
        self.assertEqual((doc["counts"]["name_solvable"], doc["counts"]["description_dependent"], doc["counts"]["failing"]), (len(self.ids), 0, 0))
        self.assertEqual(doc["counts"]["percent"]["name_solvable"], 100.0)

    def test_failing_near_miss_is_a_routing_fail_not_a_description_effect(self) -> None:
        near_miss = next(s["id"] for s in self.rows if "near-miss" in s["tags"])
        doc = self.run_ablation({"default": {near_miss: False}})
        self.assertEqual({s["id"]: s["class"] for s in doc["scenarios"]}[near_miss], ablation.FAILING)

    def test_each_listing_has_its_own_workspace_report_dir_and_settings(self) -> None:
        reports: dict[str, Path] = {}
        original = ablation.fake_runner

        def spying(fake, listing, rows):
            run = original(fake, listing, rows)

            def inner(agent, skill, report, pattern):
                reports[listing] = report
                return run(agent, skill, report, pattern)
            return inner

        with mock.patch.object(ablation, "fake_runner", spying):
            self.run_ablation({})
        self.assertEqual(reports["default"].parent, self.dir / "reports" / "ablation-default")
        self.assertEqual(reports["name-only"].parent, self.dir / "reports" / "ablation-name-only")
        default_ws, name_only_ws = (self.dir / f"ablation-{name}" / "claude" for name in ("default", "name-only"))
        self.assertFalse((default_ws / ".claude/settings.json").exists())
        settings = json.loads((name_only_ws / ".claude/settings.json").read_text())
        self.assertEqual(set(settings["skillOverrides"]), {p.name for p in (name_only_ws / ".claude/skills").iterdir()})
        # descriptions are untouched in both: only the listing differs
        for ws in (default_ws, name_only_ws):
            front = check_repo.parse_frontmatter(ws / ".claude/skills" / SKILL / "SKILL.md")
            self.assertEqual(front["description"], next(s.description for p in check_repo.discover_plugins() for s in check_repo.discover_skills(p) if s.name == SKILL))

    def test_ambient_listing_variable_is_not_used(self) -> None:
        with mock.patch.dict("os.environ", {"ROUTING_SKILL_LISTING": "name-only"}):
            doc = self.run_ablation({})
        self.assertFalse((self.dir / "ablation-default" / "claude" / ".claude/settings.json").exists())
        self.assertEqual(doc["counts"]["name_solvable"], len(self.ids))

    def test_unknown_skill_codex_and_missing_scenarios_are_errors(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown skill"):
            ablation.run_ablation("no-such-skill", ("claude",), self.dir, fake={})
        with self.assertRaisesRegex(ValueError, "claude agent only"):
            ablation.run_ablation(SKILL, ("claude", "codex"), self.dir, fake={})
        with mock.patch.object(ablation, "own_scenarios", return_value=[]), self.assertRaisesRegex(ValueError, "no scenarios"):
            ablation.run_ablation(SKILL, ("claude",), self.dir, fake={})


class RenderTests(unittest.TestCase):
    def test_table_lists_counts_percentages_per_tag_and_the_dependent_scenarios(self) -> None:
        rows = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        tags = {"a": ["positive"], "b": ["positive"], "c": ["near-miss"]}
        doc = ablation.judge(rows, tags, {"default": agent_result({"a": PASS, "b": FAIL, "c": PASS}), "name-only": agent_result({"a": FAIL, "b": FAIL, "c": PASS})})
        doc.update({"skill": "alpha", "agent": "claude", "usage": {"cost_usd": 0.13, "trials": 6, "tokens": 6}, "listings": {
            "default": {"complete": True, "reason": None}, "name-only": {"complete": True, "reason": None}}})
        text = "\n".join(ablation.render(doc))
        for fragment in (
            "ablation alpha (claude, 1 trial per scenario, default vs name-only listing): complete",
            "| all | 3 | 1 (33%) | 1 (33%) | 1 (33%) | 0 |",
            "| positive | 2 | 1 (50%) | 0 (0%) | 1 (50%) | 0 |",
            "| near-miss | 1 | 0 (0%) | 1 (100%) | 0 (0%) | 0 |",
            "description_dependent: a", "failing: b", "measured cost: $0.1300 (6 trials, 6 tokens)",
        ):
            self.assertIn(fragment, text)

    def test_incomplete_listing_is_explained(self) -> None:
        rows = [{"id": "a"}]
        doc = ablation.judge(rows, {"a": ["positive"]}, {"default": agent_result({"a": PASS}), "name-only": agent_result({"a": INFRA}, complete=False)})
        doc.update({"skill": "alpha", "agent": "claude", "usage": {"cost_usd": 0, "trials": 2, "tokens": 0}, "listings": {
            "default": {"complete": True, "reason": None}, "name-only": {"complete": False, "reason": "provider error"}}})
        text = "\n".join(ablation.render(doc))
        self.assertIn("INCOMPLETE", text)
        self.assertIn("name-only listing incomplete: provider error", text)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="ablation-cli-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        for patcher in (
            mock.patch.object(driver, "ROUTING_DIR", self.dir),
            mock.patch.object(runner, "REPORTS_DIR", self.dir / "reports"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def main(self, *args: str, fake: dict | None = None) -> tuple[int, str, str]:
        argv = ["routing_ablation.py", *args]
        if fake is not None:
            path = self.dir / "fake.json"
            path.write_text(json.dumps(fake))
            argv += ["--fake-results", str(path)]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = ablation.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_run_writes_the_json_document_and_prints_the_table_and_cost(self) -> None:
        dependent = ablation.own_scenarios(SKILL)[0]["id"]
        code, out, _ = self.main(SKILL, fake={"name-only": {dependent: False}})
        self.assertEqual(code, 0)
        self.assertIn(f"ablation {SKILL} (claude", out)
        self.assertIn("| Tag | Scenarios | description_dependent | name_solvable | failing | incomplete |", out)
        self.assertIn(f"description_dependent: {dependent}", out)
        self.assertIn("measured cost: $0.0000", out)
        doc = json.loads((self.dir / "reports" / f"ablation-{SKILL}.ablation.json").read_text())
        self.assertEqual(doc["counts"]["description_dependent"], 1)
        self.assertEqual((doc["settings"]["claude"]["model"]["source"], doc["overridden"]), ("default", False))

    def test_codex_unknown_skill_and_unknown_agent_exit_two(self) -> None:
        for args in ((SKILL, "--agent", "codex"), (SKILL, "--agent", "claude,codex"), ("no-such-skill",), (SKILL, "--agent", "gemini")):
            with self.subTest(args=args):
                code, _, err = self.main(*args, fake={})
                self.assertEqual(code, 2)
                self.assertIn("ERROR", err)

    def test_incomplete_exits_three(self) -> None:
        # drive the incomplete path through the reducer: an infrastructure error row from the fake runner
        original = ablation.fake_runner

        def failing(fake, listing, rows):
            run = original(fake, listing, rows)

            def inner(agent, skill, report, pattern):
                _, out = run(agent, skill, report, pattern)
                out[0]["error"] = "provider exploded"
                out[0]["failureReason"] = 2
                out[0]["success"] = False
                return "", out
            return inner

        with mock.patch.object(ablation, "fake_runner", failing):
            code, out, _ = self.main(SKILL, fake={})
        self.assertEqual(code, 3)
        self.assertIn("INCOMPLETE", out)


if __name__ == "__main__":
    unittest.main()
