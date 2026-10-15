"""Agent-subset selection tests; offline, no model calls."""
from __future__ import annotations

import unittest

import routing_agents as agents
import routing_results as r


class ParseTests(unittest.TestCase):
    def test_omitted_means_all_in_canonical_order(self) -> None:
        for value in (None, [], [""]):
            self.assertEqual(agents.parse_agents(value), ("claude", "codex"))

    def test_repeatable_comma_separated_and_deduplicated(self) -> None:
        self.assertEqual(agents.parse_agents(["codex"]), ("codex",))
        self.assertEqual(agents.parse_agents(["codex", "claude"]), ("claude", "codex"))
        self.assertEqual(agents.parse_agents(["codex,claude,codex"]), ("claude", "codex"))

    def test_unknown_agent_is_rejected_with_choices(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown agent 'gemini'; choose from claude, codex"):
            agents.parse_agents(["claude", "gemini"])

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(agents.main(["x", "claude"]), 0)
        self.assertEqual(agents.main(["x", "nope"]), 2)

    def test_label_marks_partial_runs(self) -> None:
        self.assertEqual(agents.label("pass", ["claude"]), "pass (partial: claude only)")
        self.assertEqual(agents.label("pass", ["claude", "codex"]), "pass")


class CombineScopeTests(unittest.TestCase):
    def result(self, agent, state=r.PASS):
        return {"agent": agent, "state": state, "complete": True}

    def test_default_still_requires_every_agent(self) -> None:
        combined = r.combine_agents([self.result("claude")])
        self.assertEqual((combined["state"], combined["complete"], combined["partial"]), (r.INFRA_ERROR, False, False))
        self.assertEqual(combined["agents_run"], ["claude", "codex"])

    def test_subset_run_is_partial_and_covers_only_the_agents_run(self) -> None:
        combined = r.combine_agents([self.result("claude")], required=("claude",))
        self.assertEqual((combined["state"], combined["partial"], combined["agents_run"]), (r.PASS, True, ["claude"]))
        failing = r.combine_agents([self.result("codex", r.ROUTING_FAIL)], required=("codex",))
        self.assertEqual((failing["state"], failing["partial"]), (r.ROUTING_FAIL, True))

    def test_both_agents_is_not_partial(self) -> None:
        combined = r.combine_agents([self.result("claude"), self.result("codex")])
        self.assertEqual((combined["partial"], combined["state"]), (False, r.PASS))


if __name__ == "__main__":
    unittest.main()
