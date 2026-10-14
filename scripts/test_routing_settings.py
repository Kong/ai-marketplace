"""Model/effort override tests; offline, no model calls."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import print_routing_config as printer
import routing_results as r
import routing_settings as settings_lib
import run_routing_comparison as driver
import run_routing_eval as runner

CLEAN = {name: "" for name in settings_lib.OVERRIDE_VARIABLES}


class ResolutionTests(unittest.TestCase):
    def test_defaults_are_the_pins_and_marked_default(self) -> None:
        s = settings_lib.load(CLEAN)
        self.assertEqual(s["codex"]["model"], {"value": "gpt-5.5", "source": "default"})
        self.assertEqual(s["codex"]["effort"], {"value": "low", "source": "default"})
        self.assertEqual(s["claude"]["effort"], {"value": None, "source": "default"})
        self.assertFalse(s["codex"]["overridden"] or s["claude"]["overridden"])
        self.assertIsNone(settings_lib.warning(s))

    def test_overrides_are_marked_and_warned_about(self) -> None:
        s = settings_lib.load({**CLEAN, "ROUTING_CODEX_MODEL": "gpt-x", "ROUTING_CLAUDE_EFFORT": "high"})
        self.assertEqual(s["codex"]["model"], {"value": "gpt-x", "source": "override"})
        self.assertEqual(s["codex"]["effort"]["source"], "default")
        self.assertTrue(s["codex"]["overridden"] and s["claude"]["overridden"])
        self.assertIn("overridden", settings_lib.warning(s))

    def test_invalid_values_fail_fast(self) -> None:
        for name, value in (
            ("ROUTING_CODEX_EFFORT", "bogus"), ("ROUTING_CLAUDE_EFFORT", "minimal"),
            ("ROUTING_CODEX_MODEL", "   "), ("ROUTING_CLAUDE_MODEL", "bad model;rm"),
        ):
            with self.assertRaisesRegex(ValueError, name):
                settings_lib.load({**CLEAN, name: value})

    def test_documents_record_settings_per_host_and_summary_aggregates(self) -> None:
        s = settings_lib.load({**CLEAN, "ROUTING_CODEX_EFFORT": "high"})
        docs = [settings_lib.annotate({"host": h, "state": r.PASS, "complete": True}, s) for h in r.HOSTS]
        self.assertEqual({d["host"]: d["overridden"] for d in docs}, {"claude": False, "codex": True})
        combined = r.combine_hosts(docs)
        self.assertTrue(combined["overridden"])
        self.assertEqual(combined["settings"]["codex"]["effort"], {"value": "high", "source": "override"})
        self.assertFalse(r.combine_hosts([{"host": h, "state": r.PASS} for h in r.HOSTS])["overridden"])


class EntryPointTests(unittest.TestCase):
    def test_invalid_override_exits_2_for_every_entry_point(self) -> None:
        env = {**CLEAN, "ROUTING_CODEX_EFFORT": "bogus"}
        for entry, argv in ((runner.main, ["x", "alpha"]), (driver.main, ["x", "alpha"]), (printer.main, ["x"])):
            with mock.patch.dict("os.environ", env), redirect_stderr(io.StringIO()) as err, redirect_stdout(io.StringIO()):
                self.assertEqual(entry(argv), 2)
            self.assertIn("ROUTING_CODEX_EFFORT", err.getvalue())

    def test_candidate_and_control_runs_see_the_same_overrides(self) -> None:
        envs = []

        class FakeProc:
            pid = 1

            def communicate(self, timeout=None):
                return "", None

        def popen(command, env=None, **kwargs):
            envs.append(env)
            return FakeProc()

        overrides = {**CLEAN, "ROUTING_CODEX_MODEL": "gpt-x", "ROUTING_CODEX_EFFORT": "high"}
        with mock.patch.dict("os.environ", overrides), mock.patch.object(runner.subprocess, "Popen", popen):
            for variant in ("candidate", "control"):
                root = Path("/tmp") / variant
                runner.run_promptfoo("codex", "alpha", Path("/tmp/rr/x.json"), None, env={"ROUTING_WORKSPACE_ROOT": str(root)})
        self.assertEqual(len(envs), 2)
        for env in envs:
            self.assertEqual((env["ROUTING_CODEX_MODEL"], env["ROUTING_CODEX_EFFORT"]), ("gpt-x", "high"))
        self.assertNotEqual(envs[0]["ROUTING_WORKSPACE_ROOT"], envs[1]["ROUTING_WORKSPACE_ROOT"])

    def test_eval_runner_subset_runs_only_selected_agents_and_marks_summary_partial(self) -> None:
        ran = []
        reports = Path(__file__).resolve().parents[1] / ".tmp" / "test-agent-subset"

        def fake(host, skill, **kwargs):
            ran.append(host)
            return r.host_failure(host, skill, r.PROVIDER, "down")

        with mock.patch.dict("os.environ", CLEAN), mock.patch.object(runner, "evaluate_host", fake), \
             mock.patch.object(runner, "REPORTS_DIR", reports), mock.patch.object(runner.scenarios, "validate_scenarios", return_value=[]), \
             mock.patch.object(runner.scenarios, "known_skill_names", return_value={"alpha"}), \
             redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
            code = runner.main(["x", "alpha", "--agent", "claude"])
        self.assertEqual((ran, code), (["claude"], 3))
        summary = json.loads((reports / "alpha.summary.json").read_text())
        self.assertEqual((summary["agents_run"], summary["partial"]), (["claude"], True))
        self.assertIn("overall: infra_error (partial: claude only)", out.getvalue())
        self.assertFalse((reports / "codex-alpha.result.json").exists())

    def test_eval_runner_rejects_unknown_agent(self) -> None:
        with redirect_stderr(io.StringIO()):
            self.assertEqual(runner.main(["x", "alpha", "--agent", "gemini"]), 2)

    def test_summary_lines_show_effective_settings(self) -> None:
        s = settings_lib.load(CLEAN)
        doc = settings_lib.annotate(r.host_failure("codex", "alpha", r.PROVIDER, "down"), s)
        self.assertIn("model=gpt-5.5 (default) effort=low (default)", runner.summarize(doc))


class PrinterTests(unittest.TestCase):
    def test_json_output_is_complete_and_offline(self) -> None:
        out = io.StringIO()
        with mock.patch.dict("os.environ", {**CLEAN, "ROUTING_CLAUDE_MODEL": "claude-x"}), redirect_stdout(out):
            self.assertEqual(printer.main(["x", "--json"]), 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["hosts"]["claude"]["model"], {"value": "claude-x", "source": "override"})
        self.assertTrue(data["overridden"])
        self.assertEqual(data["trials"]["new_skill_trials"], 3)
        self.assertEqual(set(data["ceilings"]["defaults"]), set(printer.ceilings.DEFAULTS))
        self.assertEqual(data["fixed"]["codex"]["sandbox_mode"], "read-only")

    def test_text_output_marks_defaults(self) -> None:
        out = io.StringIO()
        with mock.patch.dict("os.environ", CLEAN), redirect_stdout(out):
            self.assertEqual(printer.main(["x"]), 0)
        self.assertIn("codex: model=gpt-5.5 (default) effort=low (default)", out.getvalue())
        self.assertIn("ROUTING_MAX_TOKENS", out.getvalue())


if __name__ == "__main__":
    unittest.main()
