"""Routing-surface detection against throwaway git repositories; offline, no model calls."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import routing_surface as surface

SCRATCH = Path(__file__).resolve().parents[1] / ".tmp"


def skill_md(name: str, description: str, body: str = "body", extra: str = "", meta: str = "  product: konnect\n") -> str:
    return f"---\nname: {name}\ndescription: {description}\nlicense: MIT\n{extra}metadata:\n{meta}---\n{body}\n"


class Repo(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.git("init", "-q", "-b", "main")
        self.write("README.md", "hi")
        self.write_skill("alpha", "Diagnose gateway latency", "alpha")
        self.write_skill("beta", "Apply declarative fixes", "beta")
        self.write_skill("gamma", "Publish an API", "gamma")
        self.commit("base")
        self.git("tag", "base")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.repo, check=True, capture_output=True, text=True,
        ).stdout

    def write(self, rel: str, content: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def write_skill(self, directory: str, description: str, name: str | None = None, **kwargs: str) -> None:
        self.write(f"plugins/p/skills/{directory}/SKILL.md", skill_md(name or directory, description, **kwargs))

    def commit(self, message: str = "change") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def classify(self) -> dict[str, str]:
        return surface.classify(self.repo, "base", "HEAD")


class ClassifyTests(Repo):
    def test_no_change_classifies_nothing(self) -> None:
        self.assertEqual(self.classify(), {})

    def test_description_change_changes_the_surface(self) -> None:
        self.write_skill("alpha", "Diagnose gateway latency and drops", "alpha")
        self.commit()
        self.assertEqual(self.classify(), {"alpha": surface.SURFACE_CHANGED})

    def test_body_only_change_is_skipped_with_the_notice(self) -> None:
        self.write_skill("alpha", "Diagnose gateway latency", body="a much longer body")
        self.commit()
        self.assertEqual(self.classify(), {"alpha": surface.BODY_CHANGED})
        self.assertEqual(surface.NOTICES[surface.BODY_CHANGED], "SKILL.md body changed, routing surface unchanged: skipped")

    def test_references_only_change_is_skipped(self) -> None:
        self.write("plugins/p/skills/alpha/references/more.md", "x")
        self.commit()
        self.assertEqual(self.classify(), {"alpha": surface.FILES_CHANGED})

    def test_license_and_metadata_changes_are_not_routing(self) -> None:
        self.write_skill("alpha", "Diagnose gateway latency", body="alpha", meta="  product: konnect\n  internal: true\n  tags:\n    - x\n")
        self.commit()
        self.assertEqual(self.classify(), {"alpha": surface.BODY_CHANGED})

    def test_unknown_top_level_field_counts_as_routing(self) -> None:
        self.write_skill("alpha", "Diagnose gateway latency", body="alpha", extra="disable-model-invocation: true\n")
        self.commit()
        self.assertEqual(self.classify(), {"alpha": surface.SURFACE_CHANGED})

    def test_yaml_formatting_without_a_value_change_is_not_a_surface_change(self) -> None:
        self.write("plugins/p/skills/alpha/SKILL.md", skill_md("alpha", "'Diagnose gateway latency'", "alpha"))
        self.commit()
        self.assertEqual(self.classify(), {"alpha": surface.BODY_CHANGED})  # text differs, parsed surface does not

    def test_name_change_is_a_rename(self) -> None:
        self.write_skill("alpha", "Diagnose gateway latency", name="alpha-renamed")
        self.commit()
        self.assertEqual(self.classify(), {"alpha-renamed": surface.RENAMED})

    def test_directory_rename_is_a_rename(self) -> None:
        self.git("mv", "plugins/p/skills/alpha", "plugins/p/skills/alpha-v2")
        self.commit()
        self.assertEqual(self.classify(), {"alpha": surface.RENAMED})

    def test_new_skill(self) -> None:
        self.write_skill("delta", "Brand new skill")
        self.commit()
        self.assertEqual(self.classify(), {"delta": surface.NEW})

    def test_deleted_skill_is_not_classified(self) -> None:
        self.git("rm", "-rq", "plugins/p/skills/gamma")
        self.commit()
        self.assertEqual(self.classify(), {})

    def test_merge_base_not_tip_of_base_is_the_comparison_point(self) -> None:
        self.git("checkout", "-q", "-b", "feature")
        self.write_skill("alpha", "Diagnose gateway latency", body="edited on the branch")
        self.commit("feature")
        self.git("checkout", "-q", "main")
        self.write_skill("beta", "Changed on main after the branch point")
        self.commit("main moves")
        self.git("checkout", "-q", "feature")
        self.assertEqual(surface.classify(self.repo, "main", "HEAD"), {"alpha": surface.BODY_CHANGED})

    def test_triggers_are_new_renamed_and_surface_changed_only(self) -> None:
        self.assertEqual(set(surface.TRIGGERS), {surface.NEW, surface.RENAMED, surface.SURFACE_CHANGED})


if __name__ == "__main__":
    unittest.main()
