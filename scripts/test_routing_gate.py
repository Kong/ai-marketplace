"""Gate verdict tests over fake result documents; offline, no model calls."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import routing_compare as compare
import routing_gate as gate
import routing_results as r
import test_routing_results as fixtures

SKILL = "alpha"


def agent_result(agent: str, scenarios: dict[str, tuple[int, int]], skill: str = SKILL, infra: str | None = None, breaches=None):
    """Reduced agent result: {scenario id: (passing trials, trials)}; `infra` errors the first scenario."""
    rows = []
    for sid, (passes, trials) in scenarios.items():
        for trial in range(1, trials + 1):
            if infra and sid == next(iter(scenarios)):
                rows.append(fixtures.row(scenario=sid, trial=trial, trials=trials, error=infra))
            else:
                rows.append(fixtures.row(scenario=sid, trial=trial, trials=trials, success=trial <= passes, calls=None if trial <= passes else []))
    return r.reduce_agent(agent, skill, [rows], breaches)


def comparison(agent: str, candidate: dict, control: dict, confirm: tuple[dict, dict] | None = None, **kwargs):
    doc = compare.compare_agent(agent_result(agent, candidate, **kwargs), agent_result(agent, control))
    if confirm:
        doc = compare.with_confirmation(doc, agent_result(agent, confirm[0]), agent_result(agent, confirm[1]))
    return doc


def new_skill(agent: str, positive_passes: int, near_miss_passes: int):
    result = agent_result(agent, {"p": (positive_passes, 10), "n": (near_miss_passes, 20)})
    return compare.evaluate_new_skill(result, {"p": ["positive"], "n": ["near-miss"]})


class Reports:
    """A throwaway reports directory with run records and documents."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def add(self, skill: str, mode: str, docs: dict[str, dict], agents=None, skipped=(), exit_code: int | None = 0, kind: str = "comparison"):
        folder = self.root / f"routing-reports-{mode}-{skill}"
        folder.mkdir(parents=True, exist_ok=True)
        agents = list(docs) if agents is None else agents
        for agent, doc in docs.items():
            (folder / f"{agent}-{skill}.{kind}.json").write_text(json.dumps(doc))
        record = {"skill": skill, "mode": mode, "agents": agents, "skipped": [{"agent": a, "env": f"{a.upper()}_KEY"} for a in skipped], "exit_code": exit_code}
        (folder / f"{skill}.run.json").write_text(json.dumps(record))

    def judge(self, matrix):
        return gate.judge(matrix, gate.load_runs(self.root))


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reports = Reports()
        self.addCleanup(self.reports.tmp.cleanup)

    def verdict(self, mode="compare", skill=SKILL):
        doc = self.reports.judge([{"skill": skill, "mode": mode}])
        return doc["verdict"], doc

    def codes(self, doc):
        return sorted({x["code"] for x in doc["reasons"]})

    def test_nothing_selected_passes(self) -> None:
        self.assertEqual(self.reports.judge([])["verdict"], "pass")

    def test_no_regression_passes_even_when_trials_differ(self) -> None:
        both = {"s1": (3, 3), "s2": (2, 3)}
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", both, both), "codex": comparison("codex", {"s1": (3, 3), "s2": (3, 3)}, both)})
        verdict, doc = self.verdict()
        self.assertEqual((verdict, doc["exit_code"], doc["reasons"]), ("pass", 0, []))
        self.assertEqual(doc["agents_run"], ["claude", "codex"])

    def test_confirmed_regression_fails(self) -> None:
        doc = comparison("claude", {"s1": (0, 3)}, {"s1": (3, 3)}, confirm=({"s1": (1, 3)}, {"s1": (3, 3)}))
        self.assertEqual([x["confirmed"] for x in doc["confirmation"]["scenarios"]], [True])
        self.reports.add(SKILL, "compare", {"claude": doc})
        verdict, out = self.verdict()
        self.assertEqual((verdict, out["exit_code"], self.codes(out)), ("fail", 1, ["routing_regression"]))
        self.assertIn("s1 (candidate 1/3, control 3/3)", out["reasons"][0]["detail"])

    def test_regression_not_reproduced_on_rerun_passes_with_warning(self) -> None:
        doc = comparison("claude", {"s1": (0, 3)}, {"s1": (3, 3)}, confirm=({"s1": (3, 3)}, {"s1": (3, 3)}))
        self.reports.add(SKILL, "compare", {"claude": doc})
        verdict, out = self.verdict()
        self.assertEqual((verdict, out["exit_code"], self.codes(out)), ("pass_with_warnings", 0, ["regression_not_confirmed"]))

    def test_regression_cleared_when_control_also_fails_on_rerun(self) -> None:
        doc = comparison("claude", {"s1": (0, 3)}, {"s1": (3, 3)}, confirm=({"s1": (0, 3)}, {"s1": (1, 3)}))
        self.reports.add(SKILL, "compare", {"claude": doc})
        self.assertEqual(self.verdict()[0], "pass_with_warnings")

    def test_failure_on_both_sides_is_not_a_regression(self) -> None:
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", {"s1": (0, 3), "s2": (3, 3)}, {"s1": (1, 3), "s2": (3, 3)})})
        verdict, out = self.verdict()
        self.assertEqual((verdict, self.codes(out)), ("pass_with_warnings", ["preexisting_failure"]))

    def test_candidate_improvement_passes(self) -> None:
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", {"s1": (3, 3)}, {"s1": (0, 3)})})
        self.assertEqual(self.verdict()[0], "pass")

    def test_regression_without_confirmation_fails_closed(self) -> None:
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", {"s1": (0, 3)}, {"s1": (3, 3)})})
        verdict, out = self.verdict()
        self.assertEqual((verdict, out["exit_code"], self.codes(out)), ("blocked_infra", 3, ["confirmation_missing"]))

    def test_confirmation_infra_error_or_ceiling_fails_closed(self) -> None:
        confirm = ({"s1": (0, 3)}, {"s1": (3, 3)})
        broken = comparison("claude", {"s1": (0, 3)}, {"s1": (3, 3)}, confirm=({"s1": (0, 3)}, {"s1": (3, 3)}))
        broken["confirmation"].update(complete=False, state="infra_error", reason="provider error")
        self.reports.add(SKILL, "compare", {"claude": broken})
        self.assertEqual(self.verdict()[0], "blocked_infra")
        breach = {"ceiling": "cost_usd", "limit": 6, "observed": 6.5, "agent": "claude"}
        doc = compare.with_confirmation(
            compare.compare_agent(agent_result("claude", {"s1": (0, 3)}), agent_result("claude", {"s1": (3, 3)})),
            agent_result("claude", confirm[0], breaches=[breach]), agent_result("claude", confirm[1]),
        )
        self.assertEqual((doc["state"], doc["complete"]), ("infra_error", False))
        self.reports.add("beta", "compare", {"claude": doc})
        self.assertEqual(self.verdict(skill="beta")[0], "blocked_infra")

    def test_persistent_infra_error_fails_closed_and_names_the_reason(self) -> None:
        doc = comparison("codex", {"s1": (3, 3), "s2": (3, 3)}, {"s1": (3, 3), "s2": (3, 3)}, infra="provider 500")
        self.assertFalse(doc["complete"])
        self.reports.add(SKILL, "compare", {"codex": doc}, exit_code=3)
        verdict, out = self.verdict()
        self.assertEqual((verdict, out["exit_code"], self.codes(out)), ("blocked_infra", 3, ["infra_error"]))
        self.assertIn("provider", out["reasons"][0]["detail"])

    def test_new_skill_thresholds(self) -> None:
        self.reports.add(SKILL, "compare", {"claude": new_skill("claude", 9, 20)})
        self.assertEqual(self.verdict()[0], "pass")
        self.reports.add(SKILL, "compare", {"claude": new_skill("claude", 8, 20), "codex": new_skill("codex", 10, 18)})
        verdict, out = self.verdict()
        self.assertEqual((verdict, self.codes(out)), ("fail", ["new_skill_threshold"]))
        self.assertEqual(len(out["reasons"]), 2)  # each agent reported separately

    def test_new_skill_infra_error_fails_closed(self) -> None:
        doc = compare.evaluate_new_skill(agent_result("claude", {"p": (9, 10)}, infra="x"), {"p": ["positive"]})
        self.reports.add(SKILL, "compare", {"claude": doc})
        self.assertEqual(self.verdict()[0], "blocked_infra")

    def test_adjacent_skill_regression_is_gated_like_a_modified_skill(self) -> None:
        doc = comparison("claude", {"s1": (0, 1)}, {"s1": (1, 1)}, confirm=({"s1": (0, 3)}, {"s1": (3, 3)}))
        self.reports.add("beta", "adjacent", {"claude": doc})
        self.assertEqual(self.verdict("adjacent", "beta")[0], "fail")

    def test_snapshot_judges_the_agent_state(self) -> None:
        self.reports.add(SKILL, "snapshot", {"claude": agent_result("claude", {"s1": (3, 3)})}, kind="result")
        self.assertEqual(self.verdict("snapshot")[0], "pass")
        self.reports.add(SKILL, "snapshot", {"claude": agent_result("claude", {"s1": (0, 3)})}, kind="result")
        self.assertEqual(self.verdict("snapshot")[0], "fail")

    def test_one_key_missing_only_warns_when_the_other_agent_ran(self) -> None:
        both = {"s1": (3, 3)}
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", both, both)}, agents=["claude"], skipped=["codex"])
        verdict, out = self.verdict()
        self.assertEqual((verdict, out["exit_code"], self.codes(out)), ("pass_with_warnings", 0, ["agent_skipped"]))
        self.assertEqual((out["agents_run"], out["agents_skipped"]), (["claude"], ["codex"]))

    def test_no_agents_fails_with_a_clear_reason(self) -> None:
        self.reports.add(SKILL, "compare", {}, agents=[], skipped=["claude", "codex"])
        self.reports.add("beta", "adjacent", {}, agents=[], skipped=["claude", "codex"])
        out = self.reports.judge([{"skill": SKILL, "mode": "compare"}, {"skill": "beta", "mode": "adjacent"}])
        self.assertEqual((out["verdict"], out["exit_code"]), ("fail_no_agents", 4))
        self.assertIn("Configure", gate.markdown(out) .replace("configure", "Configure"))

    def test_job_without_a_record_or_with_a_harness_exit_fails_closed(self) -> None:
        self.assertEqual(self.verdict()[1]["reasons"][0]["code"], "missing_result")
        self.assertEqual(self.verdict()[0], "blocked_infra")
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", {"s1": (3, 3)}, {"s1": (3, 3)})}, exit_code=2)
        verdict, out = self.verdict()
        self.assertEqual((verdict, self.codes(out)), ("blocked_infra", ["harness_error"]))
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", {"s1": (3, 3)}, {"s1": (3, 3)})}, exit_code=None)
        self.assertEqual(self.verdict()[0], "blocked_infra")

    def test_rerun_attempt_supersedes_the_blocked_first_attempt(self) -> None:
        broken = comparison("claude", {"s1": (3, 3)}, {"s1": (3, 3)}, infra="x")
        self.reports.add(SKILL, "compare", {"claude": broken}, exit_code=3)
        first = self.reports.root / f"routing-reports-compare-{SKILL}"
        first.rename(self.reports.root / "routing-reports-compare-alpha-1")
        for path in (self.reports.root / "routing-reports-compare-alpha-1").glob("*.run.json"):
            path.write_text(json.dumps({**json.loads(path.read_text()), "attempt": 1}))
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", {"s1": (3, 3)}, {"s1": (3, 3)})}, exit_code=0)
        (self.reports.root / f"routing-reports-compare-{SKILL}").rename(self.reports.root / "routing-reports-compare-alpha-2")
        for path in (self.reports.root / "routing-reports-compare-alpha-2").glob("*.run.json"):
            path.write_text(json.dumps({**json.loads(path.read_text()), "attempt": 2}))
        self.assertEqual(self.verdict()[0], "pass")

    def test_missing_agent_document_fails_closed(self) -> None:
        self.reports.add(SKILL, "compare", {}, agents=["claude"])
        self.assertEqual(self.verdict()[1]["reasons"][0]["code"], "missing_result")

    def test_fail_outranks_blocked_and_blocked_outranks_warnings(self) -> None:
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", {"s1": (0, 3)}, {"s1": (3, 3)}, confirm=({"s1": (0, 3)}, {"s1": (3, 3)}))})
        self.reports.add("beta", "compare", {"claude": comparison("claude", {"s1": (3, 3)}, {"s1": (3, 3)}, skill="beta", infra="x")})
        out = self.reports.judge([{"skill": SKILL, "mode": "compare"}, {"skill": "beta", "mode": "compare"}])
        self.assertEqual(out["verdict"], "fail")
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", {"s1": (3, 3)}, {"s1": (3, 3)})}, agents=["claude"], skipped=["codex"])
        out = self.reports.judge([{"skill": SKILL, "mode": "compare"}, {"skill": "beta", "mode": "compare"}])
        self.assertEqual(out["verdict"], "blocked_infra")

    def test_markdown_table_lists_every_agent(self) -> None:
        both = {"s1": (3, 3)}
        self.reports.add(SKILL, "compare", {"claude": comparison("claude", both, both)}, agents=["claude"], skipped=["codex"])
        text = gate.markdown(self.reports.judge([{"skill": SKILL, "mode": "compare"}]))
        self.assertIn("| alpha | compare | claude | pass |", text)
        self.assertIn("| alpha | compare | codex | skipped |", text)
        self.assertIn("pass_with_warnings", text)


class CliTests(unittest.TestCase):
    def run_cli(self, reports: Reports, matrix, *flags):
        path = reports.root / "matrix.json"
        path.write_text(json.dumps(matrix))
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = gate.main([str(reports.root), str(path), *flags])
        return code, out.getvalue()

    def test_exit_codes_and_outputs(self) -> None:
        reports = Reports()
        self.addCleanup(reports.tmp.cleanup)
        matrix = [{"skill": SKILL, "mode": "compare"}]
        self.assertEqual(self.run_cli(reports, matrix)[0], 3)  # missing record
        self.assertEqual(self.run_cli(reports, matrix, "--informational")[0], 0)
        self.assertEqual(self.run_cli(reports, [])[0], 0)
        reports.add(SKILL, "compare", {}, agents=[], skipped=["claude", "codex"])
        summary, verdict = reports.root / "s.md", reports.root / "v.json"
        code, text = self.run_cli(reports, matrix, "--informational", "--summary", str(summary), "--json", str(verdict))
        self.assertEqual(code, 4)  # no agents is never informational
        self.assertIn("verdict: fail_no_agents", text)
        self.assertEqual(json.loads(verdict.read_text())["verdict"], "fail_no_agents")
        self.assertIn("routing-evals-gate", summary.read_text())

    def test_malformed_input_is_a_harness_error(self) -> None:
        reports = Reports()
        self.addCleanup(reports.tmp.cleanup)
        (reports.root / "alpha.run.json").write_text("not json")
        self.assertEqual(self.run_cli(reports, [{"skill": SKILL, "mode": "compare"}])[0], 2)
        (reports.root / "alpha.run.json").unlink()
        self.assertEqual(self.run_cli(reports, {"skill": "x"})[0], 2)


class ConfirmationTests(unittest.TestCase):
    def test_only_judged_regressions_are_confirmed_and_usage_accumulates(self) -> None:
        doc = comparison("claude", {"s1": (0, 3), "s2": (0, 3), "s3": (3, 3)}, {"s1": (3, 3), "s2": (0, 3), "s3": (3, 3)})
        self.assertEqual(compare.regressions(doc), ["s1"])
        self.assertEqual(compare.preexisting_failures(doc), ["s2"])
        out = compare.with_confirmation(doc, agent_result("claude", {"s1": (0, 3)}), agent_result("claude", {"s1": (3, 3)}))
        self.assertEqual((out["confirmation"]["state"], out["confirmation"]["trials"]), ("routing_fail", 3))
        self.assertEqual(out["usage"]["trials"], doc["usage"]["trials"] + 6)
        self.assertNotIn("confirmation", doc)  # the input document is not mutated

    def test_missing_rerun_scenario_is_incomplete(self) -> None:
        doc = comparison("claude", {"s1": (0, 3)}, {"s1": (3, 3)})
        out = compare.with_confirmation(doc, agent_result("claude", {"other": (3, 3)}), agent_result("claude", {"s1": (3, 3)}))
        self.assertEqual((out["confirmation"]["complete"], out["confirmation"]["state"]), (False, "infra_error"))


if __name__ == "__main__":
    unittest.main()
