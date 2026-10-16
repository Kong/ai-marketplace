"""Canary tests: verdicts, the 60% boundary, damaged workspace contents and the CLI; offline fake results."""
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
import prepare_routing_workspace as prep
import routing_canary as canary
import routing_results as r
import run_routing_comparison as driver
import run_routing_eval as runner

SKILL = "konnect-gateway-triage"
SCRATCH = check_repo.REPO_ROOT / ".tmp"


def result(states: dict[str, str], complete: bool = True) -> dict:
    return {
        "complete": complete, "reason": None if complete else "provider error", "fingerprint": "f" * 12,
        "usage": {"trials": len(states), "tokens": 0, "cost_usd": 0.0, "latency_ms": 0},
        "scenarios": [{"id": sid, "state": state} for sid, state in states.items()],
    }


class JudgeTests(unittest.TestCase):
    def ids(self, n: int) -> list[str]:
        return [f"p-{i}" for i in range(n)]

    def states(self, n: int, failed: int) -> dict[str, str]:
        return {sid: (r.ROUTING_FAIL if i < failed else r.PASS) for i, sid in enumerate(self.ids(n))}

    def test_detected_when_most_positives_stop_routing(self) -> None:
        self.assertEqual(canary.judge_agent(result(self.states(5, 5)), self.ids(5))["verdict"], canary.DETECTED)

    def test_missed_when_the_skill_still_routes(self) -> None:
        verdict = canary.judge_agent(result(self.states(5, 0)), self.ids(5))
        self.assertEqual((verdict["verdict"], verdict["failed"]), (canary.MISSED, []))

    def test_boundary_is_exactly_sixty_percent(self) -> None:
        for total, failed, expected in ((5, 3, canary.DETECTED), (5, 2, canary.MISSED), (10, 6, canary.DETECTED), (10, 5, canary.MISSED), (3, 2, canary.DETECTED), (3, 1, canary.MISSED)):
            with self.subTest(total=total, failed=failed):
                self.assertEqual(canary.judge_agent(result(self.states(total, failed)), self.ids(total))["verdict"], expected)

    def test_incomplete_never_counts_as_detected_or_missed(self) -> None:
        self.assertEqual(canary.judge_agent(result(self.states(5, 5), complete=False), self.ids(5))["verdict"], canary.INCOMPLETE)
        infra = self.states(5, 0)
        infra["p-0"] = r.INFRA_ERROR
        self.assertEqual(canary.judge_agent(result(infra), self.ids(5))["verdict"], canary.INCOMPLETE)
        short = self.states(4, 4)  # a scenario never ran
        self.assertEqual(canary.judge_agent(result(short), self.ids(5))["verdict"], canary.INCOMPLETE)

    def test_overall_verdict_precedence(self) -> None:
        agent = lambda v: {"verdict": v}  # noqa: E731
        self.assertEqual(canary.overall({"claude": agent(canary.DETECTED), "codex": agent(canary.DETECTED)}), canary.DETECTED)
        self.assertEqual(canary.overall({"claude": agent(canary.DETECTED), "codex": agent(canary.MISSED)}), canary.MISSED)
        self.assertEqual(canary.overall({"claude": agent(canary.MISSED), "codex": agent(canary.INCOMPLETE)}), canary.MISSED)
        self.assertEqual(canary.overall({"claude": agent(canary.DETECTED), "codex": agent(canary.INCOMPLETE)}), canary.INCOMPLETE)

    def test_exit_codes(self) -> None:
        self.assertEqual(canary.EXIT_CODES, {canary.DETECTED: 0, canary.MISSED: 1, canary.INCOMPLETE: 3})

    def test_canary_text_is_off_domain_and_in_the_real_length_class(self) -> None:
        self.assertTrue(150 <= len(canary.CANARY_DESCRIPTION) <= 400)
        for word in ("kong", "konnect", "gateway", "plugin", "api"):
            self.assertNotRegex(canary.CANARY_DESCRIPTION.lower(), rf"\b{word}\b")


class OfflineRunTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="canary-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.ids = canary.positive_scenarios(SKILL)

    def run_canary(self, routed: dict[str, bool], agents=("claude",)) -> dict:
        return canary.run_canary(SKILL, agents, self.dir, fake={agent: routed for agent in agents})

    def test_skill_has_its_own_positive_scenarios(self) -> None:
        self.assertGreaterEqual(len(self.ids), 5)
        self.assertTrue(all("positive" in s["tags"] for s in canary.scenarios.target_scenarios(canary.scenarios.SCENARIOS_DIR, SKILL) if s["id"] in self.ids))

    def test_detected_when_every_positive_fails_to_route(self) -> None:
        doc = self.run_canary({sid: False for sid in self.ids}, ("claude", "codex"))
        self.assertEqual((doc["verdict"], doc["exit_code"], doc["offline"]), (canary.DETECTED, 0, True))
        self.assertEqual(doc["positives"], self.ids)
        self.assertEqual(doc["agents_run"], ["claude", "codex"])
        self.assertEqual(doc["usage"]["trials"], 2 * len(self.ids))  # one trial per scenario per agent

    def test_none_answers_without_skill_calls_count_as_failed_to_route(self) -> None:
        # the fake runner emits the live shape for an unrouted answer: output NONE, no skillCalls
        rows = canary.fake_runner(self.dir, {"claude": {sid: False for sid in self.ids}}, self.ids)("claude", SKILL, self.dir / "x.json", None)[1]
        self.assertTrue(all(row["response"]["output"] == "NONE" and "skillCalls" not in row["response"]["metadata"] for row in rows))
        doc = self.run_canary({sid: False for sid in self.ids})
        self.assertEqual((doc["verdict"], doc["exit_code"], doc["agents"]["claude"]["failed"]), (canary.DETECTED, 0, sorted(self.ids)))

    def test_missed_when_the_damaged_skill_still_routes(self) -> None:
        doc = self.run_canary({})  # every scenario routed to the skill
        self.assertEqual((doc["verdict"], doc["exit_code"]), (canary.MISSED, 1))

    def test_boundary_over_the_real_scenarios(self) -> None:
        total = len(self.ids)
        needed = -(-total * canary.THRESHOLD_PERCENT // 100)
        fails = lambda n: {sid: False for sid in self.ids[:n]}  # noqa: E731
        self.assertEqual(self.run_canary(fails(needed))["verdict"], canary.DETECTED)
        self.assertEqual(self.run_canary(fails(needed - 1))["verdict"], canary.MISSED)

    def test_only_the_named_skill_is_damaged_and_the_workspace_verified(self) -> None:
        self.run_canary({})
        root = self.dir / "canary" / "claude"
        damaged = check_repo.parse_frontmatter(root / ".claude/skills" / SKILL / "SKILL.md")
        self.assertEqual(damaged["description"], canary.CANARY_DESCRIPTION)
        real = {s.name: s.description for p in check_repo.discover_plugins() for s in check_repo.discover_skills(p)}
        other = next(n for n in real if n != SKILL)
        front = check_repo.parse_frontmatter(root / ".claude/skills" / other / "SKILL.md")
        self.assertEqual(front["description"], real[other])
        prep.verify_workspace(root, "claude", description_overrides={SKILL: canary.CANARY_DESCRIPTION})

    def test_unknown_skill_or_no_positives_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            canary.run_canary("no-such-skill", ("claude",), self.dir, fake={})


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="canary-cli-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        for patcher in (
            mock.patch.object(driver, "ROUTING_DIR", self.dir),
            mock.patch.object(runner, "REPORTS_DIR", self.dir / "reports"),
            mock.patch.dict("os.environ", {}, clear=False),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def main(self, *args: str, fake: dict | None = None) -> tuple[int, str, str]:
        argv = ["routing_canary.py", *args]
        if fake is not None:
            path = self.dir / "fake.json"
            path.write_text(json.dumps(fake))
            argv += ["--fake-results", str(path)]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = canary.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_detected_run_writes_the_document_and_prints_the_cost(self) -> None:
        ids = canary.positive_scenarios(SKILL)
        code, out, _ = self.main(SKILL, "--agent", "claude", fake={"claude": {sid: False for sid in ids}})
        self.assertEqual(code, 0)
        self.assertIn(f"canary {SKILL}: canary_detected (listing: default;", out)
        self.assertIn("measured cost: $0.0000", out)
        doc = json.loads((self.dir / "reports" / f"canary-{SKILL}.canary.json").read_text())
        self.assertEqual((doc["verdict"], doc["partial"], doc["agents_run"]), (canary.DETECTED, True, ["claude"]))
        self.assertEqual(doc["settings"]["claude"]["model"]["source"], "default")
        self.assertFalse(doc["overridden"])

    def test_missed_exits_one_and_prints_the_name_driven_note(self) -> None:
        code, out, _ = self.main(SKILL, "--agent", "claude", fake={})
        self.assertEqual(code, 1)
        self.assertIn("canary_missed", out)
        self.assertIn("name-driven-routing limitation", out)

    def test_unknown_skill_exits_two(self) -> None:
        code, _, err = self.main("no-such-skill", fake={})
        self.assertEqual(code, 2)
        self.assertIn("no-such-skill", err)

    def test_unknown_agent_exits_two(self) -> None:
        self.assertEqual(self.main(SKILL, "--agent", "gemini", fake={})[0], 2)


if __name__ == "__main__":
    unittest.main()
