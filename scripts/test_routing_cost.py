"""Trial and cost estimate tests; pure arithmetic, offline."""
from __future__ import annotations

import unittest

import routing_cost as cost

TRIALS = {"a": 3, "b": 3, "c": 1}


def entry(mode: str, ids: str = "a,b,c", new: bool = False) -> dict:
    return {"skill": "x", "mode": mode, "scenarios": ids, "new": new}


class TrialPlanTests(unittest.TestCase):
    def test_gate_modified_skill_is_one_trial_per_scenario_with_a_confirmed_worst_case(self) -> None:
        plan = cost.entry_trials(entry("gate"), TRIALS, TRIALS)
        # initial 3; worst: 3 + 2 x (3+3+1) (candidate and control re-run at own trials)
        self.assertEqual(plan, {"scenarios": 3, "initial": 3, "worst": 17})

    def test_gate_new_skill_runs_own_trials_without_control(self) -> None:
        self.assertEqual(cost.entry_trials(entry("gate", new=True), TRIALS, TRIALS), {"scenarios": 3, "initial": 7, "worst": 7})

    def test_snapshot_is_the_full_file_at_own_trials(self) -> None:
        self.assertEqual(cost.entry_trials(entry("snapshot"), TRIALS, TRIALS)["initial"], 7)

    def test_full_compare_doubles_for_the_control(self) -> None:
        self.assertEqual(cost.entry_trials(entry("compare"), TRIALS, TRIALS), {"scenarios": 3, "initial": 14, "worst": 28})


class EstimateTests(unittest.TestCase):
    def test_assumptions_are_constants_in_one_place(self) -> None:
        self.assertEqual((cost.CLAUDE_USD_PER_TRIAL, cost.CODEX_USD_PER_TRIAL), (0.04, (0.05, 0.10)))

    def test_ranges_use_per_agent_prices(self) -> None:
        est = cost.estimate([{"scenarios": 20, "initial": 20, "worst": 100}], ["claude", "codex"])
        self.assertEqual(est["agents"]["claude"]["expected_usd"], (0.8, 0.8))
        self.assertEqual(est["agents"]["codex"]["expected_usd"], (1.0, 2.0))
        self.assertEqual(est["expected_usd"], (1.8, 2.8))
        self.assertEqual(est["worst_usd"], (9.0, 14.0))
        self.assertEqual(est["scenarios"], 20)

    def test_single_agent_total_only_counts_that_agent(self) -> None:
        est = cost.estimate([{"scenarios": 10, "initial": 10, "worst": 10}], ["claude"])
        self.assertEqual(est["expected_usd"], (0.4, 0.4))

    def test_summary_lines_state_scenarios_trials_cost_and_that_it_is_rough(self) -> None:
        text = "\n".join(cost.lines([{"scenarios": 20, "initial": 20, "worst": 100}], ["claude", "codex"]))
        for expected in ("20 scenario(s)", "| claude | 20 | 100 | $0.80 | $4.00 |", "| codex | 20 | 100 | $1.00-$2.00 | $5.00-$10.00 |",
                         "Total expected $1.80-$2.80", "rough assumptions, not measurements", "$0.04/trial Claude", "$0.05-$0.10/trial Codex"):
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
