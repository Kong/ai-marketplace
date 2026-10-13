"""Selection tests against throwaway git repositories; no model calls."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import select_changed as selector


def skill_md(name: str, description: str, category: str = "domain", body: str = "") -> str:
    return (
        f"---\nname: {name}\ndescription: {description}\nlicense: MIT\n"
        f"metadata:\n  product: konnect\n  category: {category}\n  tags:\n    - kong\n---\n{body}\n"
    )


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = Path(__file__).resolve().parents[1] / ".tmp"
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.git("init", "-q", "-b", "main")
        self.write("README.md", "hi")
        self.write_skill("router", "Route ambiguous requests", category="routing")
        self.write_skill("alpha", "Diagnose gateway latency spikes", body="Use `beta` for fixes. Use `ghost-skill` too.")
        self.write_skill("beta", "Apply declarative fixes")
        self.write_skill("gamma", "Diagnose gateway latency spikes quickly")
        self.commit("base")
        self.git("tag", "base")

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.repo, check=True, capture_output=True,
        )

    def write(self, rel: str, content: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def write_skill(self, name: str, description: str, **kwargs: str) -> None:
        self.write(f"plugins/p/skills/{name}/SKILL.md", skill_md(name, description, **kwargs))

    def commit(self, message: str = "change") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def select(self) -> dict[str, object]:
        return selector.select(self.repo, "base")

    def test_empty_diff_selects_nothing(self) -> None:
        self.assertEqual(self.select()["selected"], [])

    def test_docs_and_non_skill_paths_select_nothing(self) -> None:
        self.write("docs/skills.md", "x")
        self.write("plugins/p/.codex-plugin/plugin.json", "{}")
        self.write("plugins/p/skills/README.md", "x")
        self.write("scripts/anything.py", "x")
        self.commit()
        self.assertEqual(self.select()["selected"], [])

    def test_changed_skill_adds_router_named_sibling_and_neighbour(self) -> None:
        self.write("plugins/p/skills/alpha/references/more.md", "x")
        self.commit()
        result = self.select()
        self.assertEqual(result["changed"], ["alpha"])
        self.assertEqual(result["adjacent"], ["router", "beta", "gamma"])
        self.assertIn("alpha: references unknown skill 'ghost-skill'", result["ignored"])

    def test_deleted_skill_is_reported_not_selected(self) -> None:
        self.git("rm", "-rq", "plugins/p/skills/beta")
        self.commit()
        result = self.select()
        self.assertEqual(result["selected"], [])
        self.assertEqual(result["removed"], ["beta"])

    def test_renamed_skill_selects_new_directory(self) -> None:
        self.git("mv", "plugins/p/skills/gamma", "plugins/p/skills/delta")
        self.write_skill("delta", "Diagnose gateway latency spikes quickly")
        (self.repo / "plugins/p/skills/delta/SKILL.md").write_text(skill_md("delta", "Diagnose gateway latency spikes quickly"))
        self.commit()
        result = self.select()
        self.assertEqual(result["changed"], ["delta"])
        self.assertEqual(result["renamed"], [{"from": "gamma", "to": "delta"}])
        self.assertEqual(result["removed"], [])

    def test_adjacent_cap_and_never_full_catalog(self) -> None:
        for index in range(8):
            self.write_skill(f"extra{index}", "Diagnose gateway latency spikes")
        self.commit("more skills")
        self.git("tag", "base2")
        self.write("plugins/p/skills/alpha/references/more.md", "y")
        self.commit()
        result = selector.select(self.repo, "base2")
        self.assertEqual(len(result["adjacent"]), selector.MAX_ADJACENT)
        self.assertEqual(result["adjacent"][:2], ["router", "beta"])
        self.assertLess(len(result["selected"]), 12)

    def test_cap_is_shared_across_changed_skills(self) -> None:
        self.write("plugins/p/skills/alpha/references/more.md", "x")
        self.write("plugins/p/skills/beta/references/more.md", "x")
        self.commit()
        result = self.select()
        self.assertEqual(result["changed"], ["alpha", "beta"])
        self.assertLessEqual(len(result["adjacent"]), selector.MAX_ADJACENT)
        self.assertNotIn("alpha", result["adjacent"])

    def test_diff_is_from_merge_base(self) -> None:
        self.git("checkout", "-q", "-b", "feature")
        self.write("plugins/p/skills/beta/references/more.md", "x")
        self.commit()
        self.git("checkout", "-q", "main")
        self.write("plugins/p/skills/gamma/references/more.md", "x")
        self.commit("main moves on")
        self.assertEqual(selector.select(self.repo, "main", "feature")["changed"], ["beta"])

    def test_refuses_full_catalog(self) -> None:
        for index in range(3):
            self.write_skill(f"extra{index}", "Unrelated topic")
        self.commit("more skills")
        self.git("tag", "base2")
        for path in (self.repo / "plugins/p/skills").iterdir():
            (path / "references").mkdir()
            (path / "references/x.md").write_text("x")
        self.commit()
        with self.assertRaises(selector.SelectionError):
            selector.select(self.repo, "base2")

    def test_invalid_ref_raises(self) -> None:
        with self.assertRaises(selector.SelectionError):
            selector.select(self.repo, "no-such-ref")


if __name__ == "__main__":
    unittest.main()
