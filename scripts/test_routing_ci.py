"""select/evaluate orchestration tests with a fake runner and fake documents; offline, no real keys."""
from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import routing_ci as ci
import routing_gate as gate
import select_changed
import test_routing_gate as fixtures

C, O = "ANTHROPIC_API_KEY", "OPENAI_API_KEY"
HEAD = "a" * 40
DIFF = {"changed": ["konnect-gateway-triage"], "adjacent": ["konnect-platform-router"], "selected": [], "removed": [], "renamed": [], "ignored": []}


class SelectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out, self.summary = Path(self.tmp.name, "out"), Path(self.tmp.name, "summary")
        self.resolved = {"changed": (["konnect-gateway-triage"], []), "adjacent": (["konnect-platform-router"], []),
                         "all": (["a", "konnect-gateway-triage"], []), "skill": (["konnect-gateway-triage"], [])}
        self.ancestor = False
        for patcher in (
            mock.patch.object(ci.targets, "resolve", lambda mode, name, base, covered, repo: self.resolved[mode]),
            mock.patch.object(ci.targets, "default_base", return_value="origin/main"),
            mock.patch.object(ci.select_changed, "select", return_value=DIFF),
            mock.patch.object(ci, "head_sha", return_value=HEAD),
            mock.patch.object(ci, "_git_ok", lambda *a: self.ancestor),
            mock.patch.object(ci.targets, "covered_skills", return_value={"konnect-gateway-triage", "konnect-platform-router", "a"}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_select(self, **env) -> tuple[int, dict[str, str]]:
        env = {"GITHUB_OUTPUT": str(self.out), "GITHUB_STEP_SUMMARY": str(self.summary), **env}
        with redirect_stdout(io.StringIO()):
            code = ci.select_main(env)
        outputs = dict(line.split("=", 1) for line in self.out.read_text().splitlines()) if self.out.exists() else {}
        return code, outputs

    def matrix(self, outputs) -> list[dict]:
        return json.loads(outputs["skills"])

    def test_pull_request_selects_changed_and_adjacent_and_previews_without_spend(self) -> None:
        code, out = self.run_select(EVENT_NAME="pull_request", BASE_SHA="b" * 40, HEAD_SHA=HEAD)
        self.assertEqual(code, 0)
        self.assertEqual(self.matrix(out), [{"skill": "konnect-gateway-triage", "mode": "compare"}, {"skill": "konnect-platform-router", "mode": "adjacent"}])
        self.assertEqual((out["has_skills"], out["agents"]), ("true", "claude,codex"))
        text = self.summary.read_text()
        self.assertIn("no provider calls were made", text)
        self.assertIn("relevant evals run once in the merge queue", text)
        self.assertIn("konnect-platform-router | adjacent", text)

    def test_merge_group_uses_the_queue_shas(self) -> None:
        with mock.patch.object(ci.select_changed, "select", return_value=DIFF) as select:
            code, out = self.run_select(EVENT_NAME="merge_group", BASE_SHA="b" * 40, HEAD_SHA=HEAD)
        self.assertEqual((code, out["has_skills"]), (0, "true"))
        self.assertEqual(select.call_args.args[1], "b" * 40)

    def test_nothing_relevant_selects_nothing_and_adjacent_never_runs_alone(self) -> None:
        self.resolved["changed"] = ([], ["x: changed but has no routing scenarios, skipped"])
        code, out = self.run_select(EVENT_NAME="merge_group", BASE_SHA="b" * 40, HEAD_SHA=HEAD)
        self.assertEqual((code, out["has_skills"], self.matrix(out)), (0, "false", []))
        self.assertIn("nothing to evaluate", self.summary.read_text())

    def test_selection_problem_warns_on_pull_request_and_fails_in_the_queue(self) -> None:
        def broken(mode, name, base, covered, repo):
            raise ValueError("scenario_validation: new skill needs 5 positive scenarios")
        with mock.patch.object(ci.targets, "resolve", broken):
            code, out = self.run_select(EVENT_NAME="pull_request", BASE_SHA="b" * 40, HEAD_SHA=HEAD)
            self.assertEqual((code, out["has_skills"]), (0, "false"))
            self.assertIn("advisory here", self.summary.read_text())
            code, _ = self.run_select(EVENT_NAME="merge_group", BASE_SHA="b" * 40, HEAD_SHA=HEAD)
            self.assertEqual(code, 2)

    def test_head_must_match_the_event_sha(self) -> None:
        with mock.patch.object(ci, "head_sha", return_value="c" * 40):
            self.assertEqual(self.run_select(EVENT_NAME="merge_group", BASE_SHA="b" * 40, HEAD_SHA=HEAD)[0], 2)

    def test_dispatch_skill_compares_unless_the_ref_has_nothing_beyond_main(self) -> None:
        code, out = self.run_select(EVENT_NAME="workflow_dispatch", MODE_INPUT="skill", SKILL_INPUT="konnect-gateway-triage")
        self.assertEqual((code, self.matrix(out)), (0, [{"skill": "konnect-gateway-triage", "mode": "compare"}]))
        self.ancestor = True
        _, out = self.run_select(EVENT_NAME="workflow_dispatch", MODE_INPUT="skill", SKILL_INPUT="konnect-gateway-triage")
        self.assertEqual(self.matrix(out)[0]["mode"], "snapshot")

    def test_dispatch_changed_uses_origin_main_with_adjacent(self) -> None:
        with mock.patch.object(ci.select_changed, "select", return_value=DIFF) as select:
            _, out = self.run_select(EVENT_NAME="workflow_dispatch", MODE_INPUT="changed", AGENTS_INPUT="codex")
        self.assertEqual([e["mode"] for e in self.matrix(out)], ["compare", "adjacent"])
        self.assertEqual((select.call_args.args[1], out["agents"]), ("origin/main", "codex"))

    def test_dispatch_all_is_every_covered_skill_as_snapshots_with_a_cost_estimate(self) -> None:
        with mock.patch.object(ci, "trial_count", return_value=27):
            code, out = self.run_select(EVENT_NAME="workflow_dispatch", MODE_INPUT="all", ROUTING_MAX_COST_USD="6")
        self.assertEqual((code, [e["mode"] for e in self.matrix(out)]), (0, ["snapshot", "snapshot"]))
        text = self.summary.read_text()
        self.assertIn("Planned trials: 108", text)  # 2 skills x 27 trials x 2 agents
        self.assertIn("$5.40 at an assumed $0.05/trial", text)
        self.assertIn("$24.00", text)  # 2 runs x 2 agents x $6 ceiling
        self.assertIn("never part of the merge gate", text)

    def test_dispatch_input_validation(self) -> None:
        for env in (
            {"MODE_INPUT": "skill"},  # skill required
            {"MODE_INPUT": "changed", "SKILL_INPUT": "x"},  # skill not accepted
            {"MODE_INPUT": "skill", "SKILL_INPUT": "x; rm -rf /"},  # not a skill name
            {"MODE_INPUT": "everything"},
            {"MODE_INPUT": "all", "AGENTS_INPUT": "gemini"},
        ):
            with self.subTest(env=env):
                self.assertEqual(self.run_select(EVENT_NAME="workflow_dispatch", **env)[0], 2)

    def test_unsupported_event_fails(self) -> None:
        self.assertEqual(self.run_select(EVENT_NAME="push")[0], 2)


class TrialCountTests(unittest.TestCase):
    def test_modes_scale_trials_by_control_and_cap(self) -> None:
        scenarios = [{"trials": 3}, {"trials": 3}, {"trials": 1}]
        with mock.patch.object(ci.scenarios, "target_scenarios", return_value=scenarios):
            self.assertEqual(ci.trial_count("x", "snapshot"), 7)
            self.assertEqual(ci.trial_count("x", "compare"), 14)
            self.assertEqual(ci.trial_count("x", "adjacent"), 6)  # one trial each, candidate and control

    def test_real_corpus_is_countable(self) -> None:
        self.assertGreater(ci.trial_count("konnect-gateway-triage", "compare"), 0)


class EvaluateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.reports = self.repo / ".tmp" / "routing" / "reports"
        self.summary = self.repo / "summary.md"
        self.calls: list[tuple[list[str], dict]] = []
        self.rc = 0
        self.write_docs = True

    def fake_run(self, command, env, cwd, check):
        self.calls.append((command, env))
        agents = command[command.index("--agent") + 1].split(",")
        if self.write_docs:
            skill = "alpha"
            for agent in agents:
                doc = fixtures.comparison(agent, {"s1": (3, 3)}, {"s1": (3, 3)})
                (self.reports / f"{agent}-{skill}.comparison.json").write_text(json.dumps(doc))
            summary = {"agents_run": agents, "partial": len(agents) < 2, "breaches": []}
            (self.reports / f"{skill}.comparison-summary.json").write_text(json.dumps(summary))
        return SimpleNamespace(returncode=self.rc)

    def evaluate(self, mode="compare", **env) -> tuple[int, str]:
        env = {"SKILL": "alpha", "MODE": mode, "BASE_REF": "b" * 40, "GITHUB_STEP_SUMMARY": str(self.summary), **env}
        out = io.StringIO()
        with redirect_stdout(out):
            code = ci.evaluate_main(env, run=self.fake_run, repo=self.repo)
        return code, out.getvalue()

    def record(self) -> dict:
        return json.loads((self.reports / "alpha.run.json").read_text())

    def test_both_keys_run_both_agents_with_confirmation(self) -> None:
        code, out = self.evaluate(**{C: "sk-ant-secret", O: "sk-secret"})
        self.assertEqual(code, 0)
        command, env = self.calls[0]
        self.assertEqual(command, ["mise", "run", "eval:routing:compare", "--", "alpha", "--base", "b" * 40, "--agent", "claude,codex", "--confirm"])
        self.assertNotIn("warning", out)
        self.assertEqual((self.record()["agents"], self.record()["skipped"], self.record()["exit_code"]), (["claude", "codex"], [], 0))
        for secret in ("sk-ant-secret", "sk-secret"):
            self.assertNotIn(secret, out + self.summary.read_text() + json.dumps(self.record()))

    def test_one_key_warns_but_does_not_fail(self) -> None:
        code, out = self.evaluate(**{C: "x"})
        self.assertEqual(code, 0)
        self.assertIn("::warning title=agent_skipped::codex skipped: OPENAI_API_KEY is not set", out)
        self.assertEqual((self.calls[0][0][-2:], self.record()["skipped"]), (["claude", "--confirm"], [{"agent": "codex", "env": O}]))
        self.assertIn("Agents run: claude; skipped: codex", self.summary.read_text())

    def test_no_keys_runs_nothing_and_records_it_for_the_gate(self) -> None:
        code, out = self.evaluate()
        self.assertEqual((code, self.calls), (0, []))
        self.assertIn("title=agent_skipped::no routing eval can run", out)
        self.assertEqual((self.record()["agents"], self.record()["exit_code"]), ([], 0))
        # an adjacent entry with a requested agent that has no key behaves the same
        code, _ = self.evaluate("adjacent", REQUESTED_AGENTS="codex", **{C: "x"})
        self.assertEqual((code, self.calls), (0, []))

    def test_requested_agents_restrict_the_run(self) -> None:
        self.evaluate(REQUESTED_AGENTS="codex", **{C: "x", O: "y"})
        self.assertIn("codex", self.calls[0][0])
        self.assertNotIn("claude,codex", self.calls[0][0])

    def test_child_environment_is_pinned_and_adjacent_runs_one_trial(self) -> None:
        env = {C: "x", "ROUTING_CLAUDE_MODEL": "m", "ROUTING_CODEX_EFFORT": "high", "ROUTING_FORCE_TRIALS": "9", "ROUTING_MAX_TRIALS": "5", "ROUTING_MAX_COST_USD": "3"}
        self.evaluate("compare", **env)
        child = self.calls[-1][1]
        for name in ("ROUTING_CLAUDE_MODEL", "ROUTING_CODEX_EFFORT", "ROUTING_FORCE_TRIALS", "ROUTING_MAX_TRIALS"):
            self.assertNotIn(name, child)
        self.assertEqual(child["ROUTING_MAX_COST_USD"], "3")  # ceilings still pass through
        self.evaluate("adjacent", **env)
        self.assertEqual(self.calls[-1][1]["ROUTING_MAX_TRIALS"], "1")

    def test_snapshot_uses_the_plain_eval_task(self) -> None:
        self.write_docs = False
        self.evaluate("snapshot", **{C: "x"})
        self.assertEqual(self.calls[0][0], ["mise", "run", "eval:routing", "--", "skill", "alpha", "--agent", "claude"])

    def test_routing_fail_and_infra_error_are_recorded_not_job_failures(self) -> None:
        for rc, title in ((1, "routing_fail"), (3, "infra_error")):
            self.rc = rc
            code, out = self.evaluate(**{C: "x"})
            self.assertEqual(code, 0)
            self.assertIn(f"title={title}", out)
            self.assertEqual(self.record()["exit_code"], rc)

    def test_harness_error_fails_the_job_and_is_recorded(self) -> None:
        self.rc = 2
        code, out = self.evaluate(**{C: "x"})
        self.assertEqual(code, 2)
        self.assertIn("title=harness_error", out)
        self.assertEqual(self.record()["exit_code"], 2)

    def test_unexplained_partial_result_fails(self) -> None:
        def lying(command, env, cwd, check):
            (self.reports / "alpha.comparison-summary.json").write_text(json.dumps({"agents_run": ["claude"], "partial": True}))
            return SimpleNamespace(returncode=0)
        out = io.StringIO()
        env = {"SKILL": "alpha", "MODE": "compare", C: "x", O: "y"}
        with redirect_stdout(out):
            self.assertEqual(ci.evaluate_main(env, run=lying, repo=self.repo), 2)
        self.assertIn("title=partial", out.getvalue())

    def test_ceiling_breach_is_surfaced(self) -> None:
        def breach(command, env, cwd, check):
            doc = {"agents_run": ["claude"], "partial": True, "breaches": [{"agent": "claude", "ceiling": "cost_usd", "limit": 6, "observed": 6.1}]}
            (self.reports / "alpha.comparison-summary.json").write_text(json.dumps(doc))
            return SimpleNamespace(returncode=3)
        out = io.StringIO()
        with redirect_stdout(out):
            ci.evaluate_main({"SKILL": "alpha", "MODE": "compare", C: "x"}, run=breach, repo=self.repo)
        self.assertIn("title=ceiling", out.getvalue())

    def test_invalid_inputs_are_harness_errors(self) -> None:
        self.assertEqual(self.evaluate("bogus")[0], 2)
        self.assertEqual(self.evaluate(SKILL="Bad Name")[0], 2)
        self.assertEqual(self.evaluate(REQUESTED_AGENTS="gemini")[0], 2)

    def test_records_feed_the_gate_end_to_end(self) -> None:
        self.evaluate(**{C: "x"})
        doc = gate.judge([{"skill": "alpha", "mode": "compare"}], gate.load_runs(self.repo))
        self.assertEqual((doc["verdict"], doc["agents_run"], doc["agents_skipped"]), ("pass_with_warnings", ["claude"], ["codex"]))
        self.evaluate()
        doc = gate.judge([{"skill": "alpha", "mode": "compare"}], gate.load_runs(self.repo))
        self.assertEqual(doc["verdict"], "fail_no_agents")


if __name__ == "__main__":
    unittest.main()
