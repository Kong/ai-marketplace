"""Coverage listing tests; offline, no model calls."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import routing_coverage as coverage

SCRATCH = Path(__file__).resolve().parents[1] / ".tmp"


def scenario(i: str, tags: str, expect: str = "[]", forbid: str = "[]", trials: int = 3) -> str:
    return f"  - {{id: {i}, prompt: x, expect: {expect}, forbid: {forbid}, trials: {trials}, tags: [{tags}]}}\n"


class CoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        body = "skill: alpha\nscenarios:\n"
        body += scenario("p1", "positive", expect="[alpha]") + scenario("n1", "near-miss", forbid="[alpha]")
        body += scenario("s1", "sibling", expect="[beta]", forbid="[alpha]", trials=1)
        (self.dir / "alpha.yaml").write_text(body)
        for patcher in (
            mock.patch.object(coverage.scenarios, "SCENARIOS_DIR", self.dir),
            mock.patch.object(coverage.scenarios, "known_skill_names", return_value={"alpha", "beta", "gamma"}),
            mock.patch.object(coverage.scenarios, "adjacent_skills", return_value=["beta"]),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_lists_covered_and_uncovered_with_tag_counts_and_summary(self) -> None:
        report = coverage.collect()
        self.assertEqual((report["summary"], report["covered"], report["total"]), ("1 of 3 skills covered", 1, 3))
        by_name = {e["skill"]: e for e in report["skills"]}
        self.assertEqual(by_name["alpha"]["tags"], {"near-miss": 1, "positive": 1, "sibling": 1})
        self.assertEqual(by_name["alpha"]["scenarios"], 3)
        self.assertEqual(by_name["beta"], {"skill": "beta", "covered": False})

    def test_reports_new_skill_minimums_as_information_only(self) -> None:
        alpha = coverage.collect()["skills"][0]
        self.assertFalse(alpha["meets_new_skill_minimums"])
        self.assertTrue(any("at least 5 positive" in gap for gap in alpha["new_skill_gaps"]))

    def test_text_and_json_output_exit_0_even_with_gaps(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(coverage.main(["x"]), 0)
        self.assertIn("uncovered  gamma", out.getvalue())
        self.assertIn("covered    alpha: 3 scenarios (1 near-miss, 1 positive, 1 sibling); below new-skill minimums", out.getvalue())
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(coverage.main(["x", "--json"]), 0)
        self.assertEqual(json.loads(out.getvalue())["covered"], 1)

    def test_real_errors_exit_2(self) -> None:
        with mock.patch.object(coverage, "collect", side_effect=ValueError("bad plugin")), mock.patch("sys.stderr"):
            self.assertEqual(coverage.main(["x"]), 2)


if __name__ == "__main__":
    unittest.main()
