"""Reducer and retry tests with synthetic Promptfoo rows; no model calls."""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import routing_results as r
import run_routing_eval as run


def row(scenario="s1", trial=1, trials=1, expected=("alpha",), forbidden=(), calls=None, success=True,
        error=None, output="alpha", metadata_ok=True):
    response = {"output": output, "metadata": {"skillCalls": [{"name": n} for n in (calls if calls is not None else expected)]}}
    if not metadata_ok:
        response["metadata"] = {"skillCalls": "alpha"}
    out = {
        "success": success and not error,
        "failureReason": 2 if error else (0 if success else 1),
        "latencyMs": 5,
        "gradingResult": {"pass": success, "reason": "ok" if success else "Missing required skill(s): alpha. Actual skills: (none)"},
        "response": None if error else response,
        "testCase": {
            "description": f"{scenario} | codex | trial {trial}/{trials} [x]",
            "metadata": {"scenario": scenario, "trial": trial, "trials": trials,
                         "expected": list(expected), "forbidden": list(forbidden)},
        },
    }
    if error:
        out["error"] = error
    return out


class TrialTests(unittest.TestCase):
    def test_pass_and_routing_fail_are_invocation_evidence(self) -> None:
        ok = r.reduce_trial(row(), "codex")
        self.assertEqual((ok["state"], ok["kind"], ok["observed"]), (r.PASS, None, ["alpha"]))
        bad = r.reduce_trial(row(calls=[], success=False), "codex")
        self.assertEqual((bad["state"], bad["kind"]), (r.ROUTING_FAIL, r.INVOCATION))
        self.assertIn("Missing required", bad["reason"])

    def test_provider_error_is_infra_error_not_routing_fail(self) -> None:
        t = r.reduce_trial(row(error="Error: Anthropic API key is not set.\n  at stack"), "claude")
        self.assertEqual((t["state"], t["kind"]), (r.INFRA_ERROR, r.PROVIDER))
        self.assertEqual(t["evidence"]["error"], "Error: Anthropic API key is not set.")

    def test_malformed_telemetry_is_infra_error(self) -> None:
        t = r.reduce_trial(row(metadata_ok=False, success=False), "codex")
        self.assertEqual((t["state"], t["kind"]), (r.INFRA_ERROR, r.TELEMETRY))
        missing = row(success=False)
        missing["response"] = {"output": "x", "metadata": {}}
        self.assertEqual(r.reduce_trial(missing, "claude")["kind"], r.TELEMETRY)
        no_output = row(success=False)
        no_output["response"] = {"metadata": {}}
        self.assertEqual(r.reduce_trial(no_output, "codex")["kind"], r.TELEMETRY)
        no_response = row(success=False)
        no_response["response"] = None
        self.assertEqual(r.reduce_trial(no_response, "codex")["kind"], r.TELEMETRY)

    def test_codex_without_skill_calls_is_valid_non_activation(self) -> None:
        negative = row(expected=(), forbidden=("alpha",))
        negative["response"] = {"output": "NONE"}
        t = r.reduce_trial(negative, "codex")
        self.assertEqual((t["state"], t["observed"]), (r.PASS, []))


def none_row(output="NONE", expected=("alpha",), forbidden=(), success=False, scenario="s1"):
    """The observed Claude shape when no skill is selected: no skillCalls in metadata at all."""
    out = row(scenario=scenario, expected=expected, forbidden=forbidden, success=success)
    out["response"] = {
        "output": output,
        "metadata": {"sessionId": "x"},
        "raw": '{"stop_reason":"end_turn","result":"NONE"}',
    }
    return out


class NoneTelemetryTests(unittest.TestCase):
    def test_none_without_skill_calls_is_routing_fail_on_a_positive(self) -> None:
        t = r.reduce_trial(none_row(), "claude")
        self.assertEqual((t["state"], t["kind"], t["observed"]), (r.ROUTING_FAIL, r.INVOCATION, []))

    def test_none_without_skill_calls_passes_a_near_miss(self) -> None:
        t = r.reduce_trial(none_row(expected=(), forbidden=("alpha",), success=True), "claude")
        self.assertEqual((t["state"], t["observed"]), (r.PASS, []))

    def test_none_is_stripped_and_case_insensitive(self) -> None:
        for output in (" none\n", "None", "NONE "):
            self.assertIsNone(r.telemetry_problem(none_row(output=output)["response"], "claude"), output)

    def test_other_output_without_skill_calls_is_telemetry(self) -> None:
        for output in ("alpha", "s-abc123", "", "   ", "NONE of these", "garbage"):
            with self.subTest(output=output):
                t = r.reduce_trial(none_row(output=output), "claude")
                self.assertEqual((t["state"], t["kind"]), (r.INFRA_ERROR, r.TELEMETRY))

    def test_missing_output_without_skill_calls_is_telemetry(self) -> None:
        bad = none_row()
        del bad["response"]["output"]
        self.assertEqual(r.reduce_trial(bad, "claude")["kind"], r.TELEMETRY)

    def test_none_with_an_error_is_not_valid_telemetry(self) -> None:
        response = none_row()["response"]
        self.assertIsNotNone(r.telemetry_problem({**response, "error": "boom"}, "claude"))

    def test_present_empty_list_stays_valid(self) -> None:
        response = {"output": "", "metadata": {"skillCalls": []}}
        self.assertIsNone(r.telemetry_problem(response, "claude"))

    def test_agent_with_every_positive_answering_none_is_routing_fail(self) -> None:
        doc = r.reduce_agent("claude", "alpha", [[none_row(scenario=f"p-{i}") for i in range(5)]])
        self.assertEqual((doc["state"], doc["complete"], doc["failure_kinds"]), (r.ROUTING_FAIL, True, ["invocation"]))


class AgentTests(unittest.TestCase):
    def test_all_pass(self) -> None:
        h = r.reduce_agent("codex", "alpha", [[row(trial=i, trials=3) for i in (1, 2, 3)]])
        self.assertEqual((h["state"], h["complete"], h["retries"]), (r.PASS, True, 0))
        self.assertEqual(h["scenarios"][0]["required_passes"], 2)

    def test_two_of_three_passes_a_scenario(self) -> None:
        rows = [row(trial=1, trials=3), row(trial=2, trials=3, calls=[], success=False), row(trial=3, trials=3)]
        self.assertEqual(r.reduce_agent("codex", "a", [rows])["state"], r.PASS)
        rows[2] = row(trial=3, trials=3, calls=[], success=False)
        h = r.reduce_agent("codex", "a", [rows])
        self.assertEqual((h["state"], h["failure_kinds"], h["complete"]), (r.ROUTING_FAIL, [r.INVOCATION], True))

    def test_infra_error_makes_agent_incomplete_but_keeps_scenario_states(self) -> None:
        rows = [row("s1", error="boom"), row("s2", calls=[], success=False)]
        h = r.reduce_agent("claude", "alpha", [rows])
        self.assertEqual((h["state"], h["complete"]), (r.INFRA_ERROR, False))
        self.assertEqual([s["state"] for s in h["scenarios"]], [r.INFRA_ERROR, r.ROUTING_FAIL])
        self.assertEqual(h["counts"], {r.PASS: 0, r.ROUTING_FAIL: 1, r.INFRA_ERROR: 1})

    def test_retry_replaces_only_the_retried_trial(self) -> None:
        first = [row("s1", trial=1, trials=3), row("s1", trial=2, trials=3, error="timeout"), row("s1", trial=3, trials=3)]
        h = r.reduce_agent("codex", "alpha", [first, [row("s1", trial=2, trials=3)]])
        self.assertEqual((h["state"], h["retries"]), (r.PASS, 1))
        self.assertEqual([t["attempts"] for t in h["scenarios"][0]["trials"]], [1, 2, 1])

    def test_persistent_failure_after_retry_stays_infra_error(self) -> None:
        first = [row(error="timeout")]
        h = r.reduce_agent("codex", "alpha", [first, [row(error="timeout")]])
        self.assertEqual((h["state"], h["complete"], h["retries"]), (r.INFRA_ERROR, False, 1))

    def test_empty_results_are_infra_error(self) -> None:
        h = r.reduce_agent("codex", "alpha", [[]])
        self.assertEqual((h["state"], h["failure_kinds"]), (r.INFRA_ERROR, [r.PROVIDER]))

    def test_agent_failure_kinds(self) -> None:
        f = r.agent_failure("codex", "alpha", r.SCENARIO_VALIDATION, "duplicate id")
        self.assertEqual((f["state"], f["failure_kinds"], f["complete"]), (r.INFRA_ERROR, [r.SCENARIO_VALIDATION], False))
        with self.assertRaises(ValueError):
            r.agent_failure("codex", "alpha", r.INVOCATION, "no")


class CombineTests(unittest.TestCase):
    def result(self, agent, state):
        return {"agent": agent, "state": state}

    def test_pass_on_one_agent_cannot_offset_another(self) -> None:
        for bad in (r.ROUTING_FAIL, r.INFRA_ERROR):
            c = r.combine_agents([self.result("claude", r.PASS), self.result("codex", bad)])
            self.assertEqual(c["state"], bad)
            self.assertEqual(c["agents"], {"claude": r.PASS, "codex": bad})

    def test_routing_fail_outranks_infra_error_and_missing_agent_is_incomplete(self) -> None:
        both = r.combine_agents([self.result("claude", r.INFRA_ERROR), self.result("codex", r.ROUTING_FAIL)])
        self.assertEqual((both["state"], both["complete"]), (r.ROUTING_FAIL, False))
        missing = r.combine_agents([self.result("codex", r.PASS)])
        self.assertEqual((missing["state"], missing["agents"]["claude"]), (r.INFRA_ERROR, r.INFRA_ERROR))

    def test_incomplete_passing_agent_is_infra_error(self) -> None:
        c = r.combine_agents([{"agent": "claude", "state": r.PASS, "complete": False}, self.result("codex", r.PASS)])
        self.assertEqual((c["state"], c["complete"]), (r.INFRA_ERROR, False))
        self.assertEqual(c["agents"], {"claude": r.INFRA_ERROR, "codex": r.PASS})

    def test_routing_fail_still_outranks_an_incomplete_pass(self) -> None:
        incomplete_pass = {"agent": "claude", "state": r.PASS, "complete": False}
        c = r.combine_agents([incomplete_pass, self.result("codex", r.ROUTING_FAIL)])
        self.assertEqual(c["state"], r.ROUTING_FAIL)

    def test_all_pass(self) -> None:
        c = r.combine_agents([self.result("claude", r.PASS), self.result("codex", r.PASS)])
        self.assertEqual((c["state"], c["complete"]), (r.PASS, True))


class RetryTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = Path(__file__).resolve().parents[1] / ".tmp"
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.calls: list[str | None] = []

    def runner(self, *outcomes):
        queue = list(outcomes)

        def fake(agent, skill, report, pattern):
            self.calls.append(pattern)
            return "", queue.pop(0)

        return fake

    def test_transient_provider_error_is_retried_once_and_recovers(self) -> None:
        full = [row("s1", trial=1, trials=2), row("s1", trial=2, trials=2, error="503")]
        h = run.evaluate_agent("codex", "alpha", self.runner(full, [row("s1", trial=2, trials=2)]), self.dir)
        self.assertEqual((h["state"], h["retries"]), (r.PASS, 1))
        self.assertEqual(len(self.calls), 2)
        pattern = re.compile(self.calls[1])
        self.assertTrue(pattern.search(full[1]["testCase"]["description"]))
        self.assertFalse(pattern.search(full[0]["testCase"]["description"]))

    def test_persistent_error_is_retried_once_then_incomplete(self) -> None:
        h = run.evaluate_agent("claude", "alpha", self.runner([row(error="no key")], [row(error="no key")]), self.dir)
        self.assertEqual((h["state"], h["complete"], h["retries"]), (r.INFRA_ERROR, False, 1))
        self.assertEqual(len(self.calls), 2)

    def test_routing_fail_is_not_retried(self) -> None:
        h = run.evaluate_agent("codex", "alpha", self.runner([row(calls=[], success=False)]), self.dir)
        self.assertEqual((h["state"], h["retries"]), (r.ROUTING_FAIL, 0))
        self.assertEqual(len(self.calls), 1)

    def test_missing_report_retries_whole_run_then_reports_provider_failure(self) -> None:
        h = run.evaluate_agent("codex", "alpha", self.runner(None, None), self.dir)
        self.assertEqual((h["state"], h["failure_kinds"], h["retries"]), (r.INFRA_ERROR, [r.PROVIDER], 1))
        self.assertEqual(self.calls, [None, None])

    def test_scenario_validation_failure_runs_nothing_and_is_not_retried(self) -> None:
        h = run.evaluate_agent("codex", "alpha", self.runner(), self.dir, validation_errors=["dup id"])
        self.assertEqual((h["state"], h["failure_kinds"], h["retries"]), (r.INFRA_ERROR, [r.SCENARIO_VALIDATION], 0))
        self.assertEqual(self.calls, [])

    def test_aliased_workspace_maps_names_back_and_records_aliased_and_fingerprint_on_every_outcome(self) -> None:
        import prepare_routing_workspace as prep

        ws = prep.Workspace(["alpha"], {"alpha": "s-aaaaaa"}, "abc123def456")
        ok = run.evaluate_agent("codex", "alpha", self.runner([row(expected=("s-aaaaaa",), calls=["s-aaaaaa"])]), self.dir, workspace=ws)
        self.assertEqual((ok["aliased"], ok["fingerprint"]), (True, "abc123def456"))
        self.assertEqual(ok["scenarios"][0]["trials"][0]["observed"], ["alpha"])
        for failure in (
            run.evaluate_agent("codex", "alpha", self.runner(None, None), self.dir, workspace=ws),
            run.evaluate_agent("codex", "alpha", self.runner(), self.dir, validation_errors=["x"], workspace=ws),
        ):
            self.assertEqual((failure["aliased"], failure["fingerprint"]), (True, "abc123def456"))
        plain = run.evaluate_agent("codex", "alpha", self.runner([row()]), self.dir)
        self.assertEqual((plain["aliased"], plain["fingerprint"]), (False, None))

    def test_retry_pattern_escapes_regex_metacharacters(self) -> None:
        desc = "s1 | codex | trial 1/3 | expect [a] forbid [b.c]"
        self.assertTrue(re.search(run.retry_pattern([desc]), desc))
        self.assertFalse(re.search(run.retry_pattern([desc]), desc.replace("b.c", "bxc")))


if __name__ == "__main__":
    unittest.main()
