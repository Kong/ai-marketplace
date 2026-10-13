"""Ceiling tests with synthetic rows and a fake clock; no model calls."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import routing_ceilings as c
import routing_compare as compare
import routing_results as r
import run_routing_eval as run
from test_routing_results import row


def costly(tokens=100, cost=0.01, **kwargs):
    out = row(**kwargs)
    if out.get("response"):
        out["response"]["tokenUsage"] = {"total": tokens}
    out["cost"] = cost
    return out


def ledger(clock=None, **env):
    base = {"ROUTING_MAX_TOKENS": "1000000", "ROUTING_MAX_COST_USD": "100"}
    return c.Ledger(c.Ceilings.from_env({**base, **{k: str(v) for k, v in env.items()}}), clock or (lambda: 0.0))


class ConfigTests(unittest.TestCase):
    def test_defaults_and_env_override(self) -> None:
        d = c.Ceilings.from_env({})
        self.assertEqual((d.max_concurrency, d.max_tokens), (4, 4000000))
        o = c.Ceilings.from_env({"ROUTING_MAX_CONCURRENCY": "2", "ROUTING_MAX_COST_USD": "0.5", "ROUTING_MAX_TOKENS": ""})
        self.assertEqual((o.max_concurrency, o.max_cost_usd, o.max_tokens), (2, 0.5, 4000000))

    def test_invalid_values_are_rejected(self) -> None:
        for env in ({"ROUTING_MAX_TOKENS": "lots"}, {"ROUTING_MAX_CONCURRENCY": "0"}, {"ROUTING_MAX_COST_USD": "-1"}):
            with self.assertRaises(ValueError):
                c.Ceilings.from_env(env)


class LedgerTests(unittest.TestCase):
    def test_usage_sums_and_ignores_missing_numbers(self) -> None:
        u = c.usage([costly(tokens=10, cost=0.5), row()])
        self.assertEqual((u["trials"], u["tokens"], u["cost_usd"], u["latency_ms"]), (2, 10, 0.5, 10))

    def test_token_and_cost_breach_names_the_ceiling_per_host(self) -> None:
        led = ledger(ROUTING_MAX_TOKENS=150, ROUTING_MAX_COST_USD=0.015)
        led.record("codex", [costly(), costly()])
        self.assertEqual({b["ceiling"] for b in led.breaches("codex")}, {c.TOKENS, c.COST})
        self.assertEqual(led.breaches("claude"), [])

    def test_below_limit_is_fine_and_job_deadline_breaches(self) -> None:
        now = [0.0]
        led = ledger(lambda: now[0], ROUTING_JOB_TIMEOUT_SECONDS=100, ROUTING_RUN_TIMEOUT_SECONDS=60)
        led.record("codex", [costly()])
        self.assertEqual(led.breaches("codex"), [])
        self.assertEqual(led.run_timeout(), 60)
        now[0] = 70
        self.assertEqual(led.run_timeout(), 30)  # capped by remaining job time
        self.assertEqual(led.timeout_breach("codex")["ceiling"], c.JOB_TIMEOUT)
        now[0] = 100
        with self.assertRaises(c.CeilingBreach):
            led.check("codex")


class EvaluateHostTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = Path(__file__).resolve().parents[1] / ".tmp"
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.calls = 0

    def runner(self, *outcomes):
        queue = list(outcomes)

        def fake(host, skill, report, pattern):
            self.calls += 1
            out = queue.pop(0)
            if isinstance(out, Exception):
                raise out
            return "", out

        return fake

    def test_token_breach_after_run_is_infra_error_ceiling_not_routing_fail(self) -> None:
        # The trial is a routing failure, but the run overspent: the result is not trusted.
        h = run.evaluate_host("codex", "alpha", self.runner([costly(calls=[], success=False)]), self.dir,
                              ledger=ledger(ROUTING_MAX_TOKENS=50))
        self.assertEqual((h["state"], h["complete"], h["failure_kinds"]), (r.INFRA_ERROR, False, [r.CEILING, r.INVOCATION]))
        self.assertEqual([b["ceiling"] for b in h["breaches"]], [c.TOKENS])
        self.assertEqual(h["usage"]["tokens"], 100)
        self.assertIn("tokens ceiling", h["reason"])
        self.assertEqual(h["scenarios"][0]["state"], r.ROUTING_FAIL)  # judged trials stay visible

    def test_breach_blocks_the_retry(self) -> None:
        h = run.evaluate_host("codex", "alpha", self.runner([costly(error="503")]), self.dir,
                              ledger=ledger(ROUTING_MAX_COST_USD=0.005))
        self.assertEqual((h["state"], h["retries"]), (r.INFRA_ERROR, 0))
        self.assertEqual(self.calls, 1)

    def test_shared_ledger_stops_later_runs_before_launch(self) -> None:
        led = ledger(ROUTING_MAX_COST_USD=0.005)
        run.evaluate_host("codex", "alpha", self.runner([costly()]), self.dir, ledger=led)
        h = run.evaluate_host("codex", "alpha", self.runner(), self.dir, ledger=led)  # would pop an empty queue
        self.assertEqual((h["state"], h["failure_kinds"], h["scenarios"]), (r.INFRA_ERROR, [r.CEILING], []))
        self.assertEqual(self.calls, 1)
        self.assertEqual(led.breaches("claude"), [])  # other host unaffected

    def test_timeout_raised_by_runner_is_infra_error_ceiling(self) -> None:
        breach = {"ceiling": c.RUN_TIMEOUT, "limit": 240, "observed": 240, "host": "codex"}
        h = run.evaluate_host("codex", "alpha", self.runner(c.CeilingBreach(breach)), self.dir, ledger=ledger())
        self.assertEqual((h["state"], h["complete"], h["failure_kinds"], h["breaches"]), (r.INFRA_ERROR, False, [r.CEILING], [breach]))
        self.assertEqual(self.calls, 1)  # a timeout is not retried

    def test_within_ceilings_reports_usage_and_retries(self) -> None:
        full = [costly(tokens=40, cost=0.1, scenario="s1", trial=1, trials=2), costly(scenario="s1", trial=2, trials=2, error="503")]
        h = run.evaluate_host("codex", "alpha", self.runner(full, [costly(tokens=60, cost=0.2, scenario="s1", trial=2, trials=2)]),
                              self.dir, ledger=ledger())
        self.assertEqual((h["state"], h["retries"], h["breaches"]), (r.PASS, 1, []))
        self.assertEqual((h["usage"]["tokens"], h["usage"]["cost_usd"]), (100, 0.31))
        self.assertIn("tokens=100", run.summarize(h))

    def test_comparison_and_summary_carry_breaches_and_usage(self) -> None:
        ok = run.evaluate_host("codex", "alpha", self.runner([costly()]), self.dir, ledger=ledger())
        over = run.evaluate_host("codex", "alpha", self.runner([costly()]), self.dir, ledger=ledger(ROUTING_MAX_TOKENS=50))
        doc = compare.compare_host(ok, over)
        self.assertEqual((doc["state"], doc["complete"], doc["usage"]["tokens"]), (r.INFRA_ERROR, False, 200))
        self.assertEqual(doc["usage_by_side"]["control"]["tokens"], 100)
        combined = r.combine_hosts([doc])
        self.assertEqual(len(combined["breaches"]), 1)
        self.assertEqual(combined["usage"]["codex"]["tokens"], 200)


class RunPromptfooTests(unittest.TestCase):
    def fake_cli(self, body: str) -> Path:
        scratch = Path(__file__).resolve().parents[1] / ".tmp"
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "promptfoo"
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o755)
        return path

    def test_timeout_kills_the_run_and_raises_a_breach(self) -> None:
        cli = self.fake_cli("sleep 30\n")
        led = ledger(ROUTING_RUN_TIMEOUT_SECONDS=1)
        with mock.patch.object(run, "PROMPTFOO", cli), tempfile.TemporaryDirectory() as out:
            with self.assertRaises(c.CeilingBreach) as ctx:
                run.run_promptfoo("codex", "alpha", Path(out) / "r.json", None, ledger=led)
        self.assertEqual(ctx.exception.breach["ceiling"], c.RUN_TIMEOUT)

    def test_concurrency_ceiling_is_passed_to_promptfoo(self) -> None:
        cli = self.fake_cli('echo "$@" > "$(dirname "$0")/args"; echo \'{"results":{"results":[]}}\' > "$(dirname "$0")/../report.json"\n')
        led = ledger(ROUTING_MAX_CONCURRENCY=2)
        with mock.patch.object(run, "PROMPTFOO", cli):
            report = cli.parent.parent / "report.json"
            _, rows = run.run_promptfoo("codex", "alpha", report, None, ledger=led)
            args = (cli.parent / "args").read_text()
        self.assertIn("--max-concurrency 2", args)
        self.assertEqual(rows, [])
        report.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
