"""CI agent-selection tests; offline, never uses real keys."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import routing_ci_agents as ci

C, O = "ANTHROPIC_API_KEY", "OPENAI_API_KEY"


class PlanTests(unittest.TestCase):
    def agents(self, env):
        return ci.plan(env)["agents"]

    def test_all_key_combinations(self) -> None:
        self.assertEqual(self.agents({C: "x", O: "y"}), ["claude", "codex"])
        self.assertEqual(self.agents({C: "x"}), ["claude"])
        self.assertEqual(self.agents({O: "y"}), ["codex"])
        self.assertEqual(self.agents({}), [])

    def test_empty_and_whitespace_values_count_as_missing(self) -> None:
        self.assertEqual(self.agents({C: "", O: ""}), [])
        self.assertEqual(self.agents({C: "  \n", O: "y"}), ["codex"])

    def test_messages_name_the_variable_and_never_a_value(self) -> None:
        plan = ci.plan({C: "sk-secret-value"})
        self.assertEqual(plan["messages"], ["codex skipped: OPENAI_API_KEY is not set"])
        self.assertNotIn("sk-secret-value", json.dumps(plan))
        self.assertEqual(plan["summary"], "Agents run: claude; skipped: codex")
        self.assertEqual(ci.plan({})["summary"], "Agents run: none; skipped: claude, codex")
        self.assertEqual(ci.plan({C: "a", O: "b"})["messages"], [])

    def test_cli_plan_reads_the_process_environment(self) -> None:
        out = io.StringIO()
        with mock.patch.dict("os.environ", {C: "", O: "y"}), redirect_stdout(out):
            self.assertEqual(ci.main(["x", "plan"]), 0)
        self.assertEqual(json.loads(out.getvalue())["agents"], ["codex"])


class VerifyTests(unittest.TestCase):
    def test_partial_is_accepted_only_when_explained_by_missing_keys(self) -> None:
        self.assertIsNone(ci.verify({"agents_run": ["claude"], "partial": True}, ["claude"]))
        self.assertIsNone(ci.verify({"agents_run": ["claude", "codex"], "partial": False}, ["claude", "codex"]))

    def test_unexplained_partial_or_scope_fails(self) -> None:
        # both keys present but only one agent ran
        self.assertIsNotNone(ci.verify({"agents_run": ["claude"], "partial": True}, ["claude", "codex"]))
        # a different subset than the keys explain
        self.assertIsNotNone(ci.verify({"agents_run": ["codex"], "partial": True}, ["claude"]))
        # partial flag inconsistent with scope
        self.assertIsNotNone(ci.verify({"agents_run": ["claude"], "partial": False}, ["claude"]))
        self.assertIsNotNone(ci.verify({}, ["claude"]))

    def test_cli_verify_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".tmp") as tmp:
            path = Path(tmp) / "s.json"
            path.write_text(json.dumps({"agents_run": ["claude"], "partial": True}))
            self.assertEqual(ci.main(["x", "verify", str(path), "claude"]), 0)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(ci.main(["x", "verify", str(path), "claude,codex"]), 2)
                self.assertEqual(ci.main(["x", "verify", str(path) + ".missing", "claude"]), 2)
                self.assertEqual(ci.main(["x", "bogus"]), 2)


if __name__ == "__main__":
    unittest.main()
