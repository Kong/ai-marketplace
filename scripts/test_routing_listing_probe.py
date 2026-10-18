"""Listing probe tests: parsing, similarity, verdict thresholds, report shape, settings and compare; offline fake output."""
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
import routing_listing_probe as probe
import run_routing_eval as runner

SCRATCH = check_repo.REPO_ROOT / ".tmp"
REAL = {
    "alpha": "Use when the user asks about alpha routing and needs a careful, step by step walkthrough of every gateway setting.",
    "beta": "Diagnose beta failures in the control plane; covers certificates, nodes and the status page for each region.",
}


def lines(*pairs: tuple[str, str]) -> str:
    return "\n".join(f"{name} | {text}" for name, text in pairs)


class ParseTests(unittest.TestCase):
    def parse(self, output: str) -> dict:
        return probe.parse_output(output, ["alpha", "beta", "gamma"])

    def test_one_line_per_skill_with_descriptions_and_name_only(self) -> None:
        parsed = self.parse(f"alpha | {REAL['alpha']}\nbeta | NAME ONLY\ngamma | name only (no description)")
        self.assertEqual(parsed["listed"], {"alpha": REAL["alpha"], "beta": None, "gamma": None})
        self.assertEqual((parsed["unknown"], parsed["ignored"]), ([], 0))

    def test_extra_chatter_bullets_backticks_and_tables_are_tolerated(self) -> None:
        output = "\n".join([
            "Sure! Here are the skills:", "",
            "- `alpha` | First one", "1. **beta** | Second one",
            "| name | description |", "| --- | --- |", "| gamma | Third one |",
            "That is all.",
        ])
        parsed = self.parse(output)
        self.assertEqual(parsed["listed"], {"alpha": "First one", "beta": "Second one", "gamma": "Third one"})
        self.assertEqual(parsed["ignored"], 3)  # two chatter lines and the table separator; the header row is skipped
        self.assertEqual(parsed["unknown"], [])

    def test_missing_skills_unknown_names_plugin_prefix_and_first_line_wins(self) -> None:
        parsed = self.parse("plugin:alpha | one\nalpha | two\nupdate-config | built in")
        self.assertEqual(parsed["listed"], {"alpha": "one"})
        self.assertEqual(parsed["unknown"], ["update-config"])

    def test_a_description_may_contain_a_pipe(self) -> None:
        self.assertEqual(self.parse("alpha | use a | b")["listed"], {"alpha": "use a | b"})

    def test_empty_output(self) -> None:
        self.assertEqual(self.parse(""), {"listed": {}, "unknown": [], "ignored": 0})


class SimilarityTests(unittest.TestCase):
    def test_exact_truncated_and_ellipsised_copies_match(self) -> None:
        real = REAL["alpha"]
        self.assertEqual(probe.similarity(real, real), 1.0)
        self.assertEqual(probe.similarity(real[:60] + "...", real), 1.0)
        self.assertEqual(probe.similarity(real[:60] + "…", real), 1.0)
        self.assertEqual(probe.similarity(f'"{real}"', real), 1.0)
        self.assertEqual(probe.similarity("  " + real.upper().replace(" ", "  "), real), 1.0)  # case and whitespace

    def test_unrelated_or_invented_text_does_not_match(self) -> None:
        self.assertLess(probe.similarity("Helps with kongs and also bananas", REAL["alpha"]), probe.MATCH_THRESHOLD)
        self.assertEqual(probe.similarity("", REAL["alpha"]), 0.0)

    def test_a_tiny_prefix_is_not_a_match_by_prefix_alone(self) -> None:
        self.assertLess(probe.similarity("Use when", REAL["alpha"]), probe.MATCH_THRESHOLD)

    def test_a_paraphrase_scores_between(self) -> None:
        score = probe.similarity(REAL["beta"].replace("Diagnose", "Debug").replace("certificates", "certs"), REAL["beta"])
        self.assertTrue(0.8 < score < 1.0, score)


class JudgeTests(unittest.TestCase):
    def real(self, count: int) -> dict[str, str]:
        return {f"s{i:02d}": f"Description number {i} of a skill that is long enough to be compared meaningfully." for i in range(count)}

    def verdict(self, real: dict[str, str], shown: int, listed: int | None = None) -> dict:
        names = sorted(real)
        listed = len(real) if listed is None else listed
        parsed = {"listed": {n: (real[n] if i < shown else None) for i, n in enumerate(names[:listed])}, "unknown": [], "ignored": 0}
        return probe.judge(real, parsed)

    def test_thresholds(self) -> None:
        real = self.real(10)
        for shown, expected in ((10, "descriptions_visible"), (9, "descriptions_visible"), (8, "partial"), (2, "partial"), (1, "partial"), (0, "names_only")):
            with self.subTest(shown=shown):
                self.assertEqual(self.verdict(real, shown)["verdict"], expected)
        real = self.real(20)
        self.assertEqual(self.verdict(real, 2)["verdict"], "partial")  # exactly 10% is not names_only
        self.assertEqual(self.verdict(real, 1)["verdict"], "names_only")
        self.assertEqual(self.verdict(real, 18)["verdict"], "descriptions_visible")  # exactly 90%
        self.assertEqual(self.verdict(real, 17)["verdict"], "partial")

    def test_unlisted_skills_count_against_the_share_and_nothing_listed_is_inconclusive(self) -> None:
        real = self.real(10)
        self.assertEqual(self.verdict(real, 5, listed=5)["verdict"], "partial")
        self.assertEqual(self.verdict(real, 0, listed=0)["verdict"], "inconclusive")

    def test_wrong_descriptions_are_shown_but_do_not_match(self) -> None:
        real = self.real(4)
        parsed = {"listed": {n: "Marketing copy about nothing in particular" for n in real}, "unknown": [], "ignored": 0}
        doc = probe.judge(real, parsed)
        self.assertEqual((doc["verdict"], doc["counts"]["description_shown"], doc["counts"]["matching"]), ("names_only", 4, 0))

    def test_rows_report_listed_shown_similarity_and_lengths(self) -> None:
        parsed = probe.parse_output(f"alpha | {REAL['alpha'][:50]}...\nbeta | NAME ONLY", ["alpha", "beta", "gamma"])
        rows = {r["skill"]: r for r in probe.judge({**REAL, "gamma": "g " * 20}, parsed)["skills"]}
        self.assertEqual((rows["alpha"]["listed"], rows["alpha"]["description_shown"], rows["alpha"]["similarity"], rows["alpha"]["matches"]), (True, True, 1.0, True))
        self.assertEqual(rows["alpha"]["shown_length"], 53)  # the ellipsis is part of what was shown
        self.assertEqual(rows["alpha"]["real_length"], len(REAL["alpha"]))
        self.assertEqual((rows["beta"]["listed"], rows["beta"]["description_shown"], rows["beta"]["similarity"], rows["beta"]["shown_length"]), (True, False, None, 0))
        self.assertEqual((rows["gamma"]["listed"], rows["gamma"]["matches"]), (False, False))


class CompareTests(unittest.TestCase):
    def doc(self, listing: str, matching: int, verdict: str, fingerprint: str = "f") -> dict:
        return {"listing": listing, "fingerprint": fingerprint, "verdict": verdict, "counts": {"skills": 10, "matching": matching}}

    def conclusion(self, default: dict, name_only: dict) -> str:
        return probe.compare(default, name_only)["conclusion"]

    def test_conclusions(self) -> None:
        visible = self.doc("default", 10, "descriptions_visible")
        self.assertEqual(self.conclusion(visible, self.doc("name-only", 0, "names_only")), "honoured")
        self.assertEqual(self.conclusion(visible, self.doc("name-only", 10, "descriptions_visible")), "not_honoured")
        self.assertEqual(self.conclusion(visible, self.doc("name-only", 8, "partial")), "not_honoured")  # a drop under 25% is noise
        self.assertEqual(self.conclusion(visible, self.doc("name-only", 7, "partial")), "partly_honoured")
        self.assertEqual(self.conclusion(visible, self.doc("name-only", 5, "partial")), "partly_honoured")
        self.assertEqual(self.conclusion(self.doc("default", 0, "names_only"), self.doc("name-only", 0, "names_only")), "indeterminate")
        self.assertEqual(self.conclusion(visible, self.doc("name-only", 0, "inconclusive")), "inconclusive")

    def test_reports_from_different_workspaces_or_listings_are_not_comparable(self) -> None:
        visible, name_only = self.doc("default", 10, "descriptions_visible"), self.doc("name-only", 0, "names_only")
        self.assertEqual(self.conclusion(visible, {**name_only, "fingerprint": "other"}), "not_comparable")
        self.assertEqual(self.conclusion(name_only, visible), "not_comparable")


def promptfoo_row(output: str, error: str | None = None) -> dict:
    row = {"success": True, "latencyMs": 5, "cost": 0.07, "response": {"output": output, "tokenUsage": {"total": 10}, "metadata": {"skillCalls": []}}}
    if error:
        row["error"] = error
    return row


class RunProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="probe-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.descriptions = {}
        for plugin in check_repo.discover_plugins():
            for skill in check_repo.discover_skills(plugin):
                self.descriptions[skill.name] = skill.description

    def output(self, show: int | None = None) -> str:
        names = sorted(self.descriptions)
        return "Here are my skills:\n" + "\n".join(
            f"{n} | {self.descriptions[n]}" if show is None or i < show else f"{n} | NAME ONLY" for i, n in enumerate(names)
        )

    def test_default_listing_document_shape_and_settings(self) -> None:
        doc = probe.run_probe("default", fake_output=self.output(), routing_dir=self.dir, settings=None)
        self.assertEqual(doc["verdict"], "descriptions_visible")
        self.assertEqual(doc["listing"], "default")
        self.assertRegex(doc["fingerprint"], r"^[0-9a-f]{12}$")
        self.assertEqual(doc["settings_requested"], {"file": None, "content": None})
        self.assertTrue(doc["offline"] and doc["complete"])
        self.assertEqual((doc["exit_code"], doc["agents_run"], doc["partial"]), (0, ["claude"], True))
        self.assertEqual(doc["prompt"], probe.PROMPT)
        self.assertIn("Here are my skills", doc["raw_output"])
        self.assertIn("cannot by itself prove", doc["note"])
        self.assertEqual(sorted(r["skill"] for r in doc["skills"]), sorted(self.descriptions))
        self.assertEqual(doc["counts"]["skills"], len(self.descriptions))
        json.dumps(doc)  # serialisable

    def test_name_only_listing_records_the_settings_written_into_the_workspace(self) -> None:
        doc = probe.run_probe("name-only", fake_output=self.output(show=0), routing_dir=self.dir)
        self.assertEqual(doc["verdict"], "names_only")
        self.assertEqual(doc["settings_requested"]["file"], ".claude/settings.json")
        self.assertEqual(doc["settings_requested"]["content"], {"skillOverrides": {n: "name-only" for n in sorted(self.descriptions)}})
        on_disk = json.loads((self.dir / "probe-name-only" / "claude" / ".claude" / "settings.json").read_text())
        self.assertEqual(on_disk, doc["settings_requested"]["content"])

    def test_provider_settings_are_recorded(self) -> None:
        settings = {"claude": {"model": {"value": "claude-x", "source": "default"}, "effort": {"value": None, "source": "default"}, "overridden": False}}
        doc = probe.run_probe("default", fake_output=self.output(), routing_dir=self.dir, settings=settings)
        self.assertEqual(doc["provider"], {"model": "claude-x", "effort": None, "overridden": False})

    def test_partial_and_unparseable_outputs(self) -> None:
        half = probe.run_probe("default", fake_output=self.output(show=len(self.descriptions) // 2), routing_dir=self.dir)
        self.assertEqual((half["verdict"], half["exit_code"]), ("partial", 0))
        refusal = probe.run_probe("default", fake_output="I cannot list my skills.", routing_dir=self.dir)
        self.assertEqual((refusal["verdict"], refusal["complete"], refusal["exit_code"]), ("inconclusive", False, 3))
        self.assertEqual(refusal["counts"]["ignored_lines"], 1)

    def test_live_path_runs_the_probe_config_in_the_prepared_workspace_with_the_prompt(self) -> None:
        calls = []

        def fake_run(agent, skill, report, pattern, env=None, ledger=None, config=None):
            calls.append((agent, report, pattern, env, config))
            return "", [promptfoo_row(self.output())]

        with mock.patch.object(runner, "run_promptfoo", fake_run):
            doc = probe.run_probe("name-only", routing_dir=self.dir)
        agent, report, pattern, env, config = calls[0]
        self.assertEqual((agent, pattern, config), ("claude", None, probe.PROBE_CONFIG))
        self.assertEqual(env, {"ROUTING_WORKSPACE_ROOT": str(self.dir / "probe-name-only"), probe.PROMPT_ENV: probe.PROMPT})
        self.assertEqual(report, self.dir / "reports" / "probe-name-only" / "claude-probe.json")
        self.assertEqual((doc["offline"], doc["verdict"], doc["response"]["metadata"], doc["usage"]["tokens"] >= 0), (False, "descriptions_visible", {"skillCalls": []}, True))
        self.assertEqual(doc["response"]["cost"], 0.07)

    def test_provider_error_and_missing_report_are_incomplete(self) -> None:
        for rows in ([promptfoo_row("", error="provider exploded")], None, []):
            with self.subTest(rows=rows), mock.patch.object(runner, "run_promptfoo", lambda *a, **k: ("boom", rows)), redirect_stdout(io.StringIO()):
                doc = probe.run_probe("default", routing_dir=self.dir)
            self.assertEqual((doc["complete"], doc["exit_code"]), (False, 3))
            self.assertTrue(doc["reason"])


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        self.dir = Path(tempfile.mkdtemp(dir=SCRATCH, prefix="probe-cli-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        for patcher in (
            mock.patch.object(runner, "REPORTS_DIR", self.dir / "reports"),
            mock.patch.object(probe.driver, "ROUTING_DIR", self.dir),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        names = [skill.name for plugin in check_repo.discover_plugins() for skill in check_repo.discover_skills(plugin)]
        descriptions = {s.name: s.description for plugin in check_repo.discover_plugins() for s in check_repo.discover_skills(plugin)}
        self.fake = self.dir / "fake.txt"
        self.fake.write_text("\n".join(f"{n} | {descriptions[n]}" for n in names))
        self.nothing = self.dir / "nothing.txt"
        self.nothing.write_text("no")

    def main(self, *args: str, env: dict | None = None) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), mock.patch.dict("os.environ", env or {}, clear=False):
            code = probe.main(["probe", *args])
        return code, out.getvalue(), err.getvalue()

    def test_writes_the_report_and_prints_the_table(self) -> None:
        code, out, _ = self.main("--listing", "default", "--fake-output", str(self.fake))
        self.assertEqual(code, 0)
        self.assertIn("listing probe (claude, listing=default", out)
        self.assertIn("| Skill | Listed | Description shown | Similarity | Shown / real length |", out)
        doc = json.loads((self.dir / "reports" / "probe-default.json").read_text())
        self.assertEqual((doc["listing"], doc["verdict"]), ("default", "descriptions_visible"))

    def test_listing_defaults_to_the_environment_preset_and_rejects_unknown_ones(self) -> None:
        code, _, _ = self.main("--fake-output", str(self.fake), env={"ROUTING_SKILL_LISTING": "name-only"})
        self.assertEqual(code, 0)
        self.assertTrue((self.dir / "reports" / "probe-name-only.json").is_file())
        code, _, err = self.main("--listing", "wide", "--fake-output", str(self.fake))
        self.assertEqual(code, 2)
        self.assertIn("ROUTING_SKILL_LISTING", err)

    def test_incomplete_exits_3_but_still_writes_the_report(self) -> None:
        code, out, _ = self.main("--listing", "default", "--fake-output", str(self.nothing))
        self.assertEqual(code, 3)
        self.assertIn("INCOMPLETE", out)
        self.assertTrue((self.dir / "reports" / "probe-default.json").is_file())

    def test_compare_reads_both_reports(self) -> None:
        code, _, err = self.main("--compare")
        self.assertEqual(code, 2)  # no reports yet
        self.assertIn("need both probe reports", err)
        self.main("--listing", "default", "--fake-output", str(self.fake))
        self.main("--listing", "name-only", "--fake-output", str(self.fake))  # the fake model ignores the preset
        code, out, _ = self.main("--compare")
        self.assertEqual(code, 0)
        self.assertIn("name-only honoured: not_honoured", out)


if __name__ == "__main__":
    unittest.main()
