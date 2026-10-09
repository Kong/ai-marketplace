"""Regression checks for the submission file boundary and Codex integration."""
from __future__ import annotations

import json
import copy
import struct
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import build_openai_plugin as package
import check_repo
import release_prepare
import scaffold_skill


class OpenAIPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = Path(__file__).resolve().parents[1] / ".tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plugin = self.root / "plugins/kong-konnect"
        self.files = {
            ".codex-plugin/plugin.json": json.dumps({
                "skills": "./skills/", "mcpServers": "./.mcp.json",
                "interface": {"logo": "./assets/logo.png", "composerIcon": "./assets/logo.png"},
            }),
            ".mcp.json": json.dumps(check_repo.sync_plugin_mcp()),
            "README.md": "Package documentation", "LICENSE": "MIT",
            "assets/logo.png": "fixture", "skills/sample/SKILL.md": "fixture",
            "skills/sample/references/example.md": "reference",
            ".claude-plugin/plugin.json": "{}", "mcp.json": "{}",
        }
        for name, content in self.files.items():
            path = self.plugin / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        tracked = "\0".join(f"plugins/kong-konnect/{name}" for name in self.files).encode()
        for target, value in (("REPO_ROOT", self.root), ("PLUGIN_ROOT", self.plugin)):
            self.enterContext(patch.object(package, target, value))
        self.enterContext(patch.object(package.subprocess, "check_output", return_value=tracked))

    def test_archive_boundary_and_reproducibility(self) -> None:
        (self.plugin / ".env").write_text("untracked secret")
        output = self.root / "plugin.zip"
        package.build(output)
        first = output.read_bytes()
        package.build(output)
        self.assertEqual(first, output.read_bytes())
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()), package.FIXED_FILES | {
                "skills/sample/SKILL.md", "skills/sample/references/example.md",
            })
            self.assertIsNone(archive.testzip())

    def test_rejects_credentials_in_mcp(self) -> None:
        path = self.plugin / ".mcp.json"
        data = json.loads(path.read_text())
        data["mcpServers"]["kong-konnect"]["headers"] = {"Authorization": "Bearer secret"}
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "without headers"):
            package.package_files()

    def test_rejects_symlinks(self) -> None:
        path = self.plugin / "skills/sample/references/example.md"
        path.unlink()
        path.symlink_to(self.plugin / "README.md")
        with self.assertRaisesRegex(ValueError, "symlink"):
            package.package_files()

    def test_rejects_missing_referenced_asset(self) -> None:
        path = self.plugin / ".codex-plugin/plugin.json"
        data = json.loads(path.read_text())
        data["interface"]["screenshots"] = ["./assets/missing.png"]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "unpackaged"):
            package.package_files()

    def test_rejects_untracked_skill(self) -> None:
        path = self.plugin / "skills/new/SKILL.md"
        path.parent.mkdir()
        path.write_text("new skill")
        with self.assertRaisesRegex(ValueError, "every shipped skill"):
            package.package_files()

    def test_rejects_recognizable_token(self) -> None:
        (self.plugin / "README.md").write_text("kpat_" + "a" * 32)
        with self.assertRaisesRegex(ValueError, "possible credential"):
            package.package_files()

    def test_codex_discovery_and_release_ownership(self) -> None:
        with patch.object(check_repo, "REPO_ROOT", self.root), patch.object(check_repo, "PLUGINS_DIR", self.root / "plugins"):
            (self.plugin / ".cursor-plugin").mkdir()
            (self.plugin / ".cursor-plugin/plugin.json").write_text('{}')
            self.assertEqual(len(check_repo.discover_plugins()), 1)
            (self.plugin / ".codex-plugin/plugin.json").unlink()
            with self.assertRaisesRegex(ValueError, "codex-plugin"):
                check_repo.discover_plugins()
        with patch.object(release_prepare, "REPO_ROOT", self.root):
            self.assertIn(self.plugin / ".codex-plugin/plugin.json", release_prepare.version_targets())

    def test_scaffold_mcp_is_optional(self) -> None:
        self.assertNotIn("mcpServers", scaffold_skill.codex_manifest_template("kong-test", False))
        self.assertEqual(scaffold_skill.codex_manifest_template("kong-test", True)["mcpServers"], "./.mcp.json")


class CodexListingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = [(plugin, check_repo.discover_skills(plugin)) for plugin in check_repo.discover_plugins()]
        self.plugin, self.skills = next(item for item in self.catalog if item[0].name == "kong-konnect")
        self.manifest = check_repo.load_json(self.plugin.codex_manifest)

    def errors_for(self, manifest: dict) -> list[str]:
        original = check_repo.load_json
        with patch.object(check_repo, "load_json", side_effect=lambda path: copy.deepcopy(manifest) if path == self.plugin.codex_manifest else original(path)):
            return check_repo.validate_static_metadata(self.catalog)

    def test_generation_preserves_curated_and_review_metadata(self) -> None:
        generated = check_repo.sync_codex_plugin(self.plugin, self.skills)
        self.assertEqual(generated["extensions"], self.manifest["extensions"])
        self.assertEqual(generated["interface"]["capabilities"], self.manifest["interface"]["capabilities"])
        review = generated["extensions"]["com.openai"]["review"]
        self.assertEqual(len(review["test_cases"]["positive"]), 5)
        self.assertEqual(len(review["test_cases"]["negative"]), 3)
        self.assertIs(review["commerce"], False)

    def test_capability_limits_reject_instead_of_truncate(self) -> None:
        for values in (["Label"] * 21, ["x" * 121]):
            manifest = copy.deepcopy(self.manifest)
            manifest["interface"]["capabilities"] = values
            self.assertTrue(any("invalid interface.capabilities" in error for error in self.errors_for(manifest)))
        manifest["interface"]["capabilities"] = ["x" * 120] * 20
        self.assertFalse(any("invalid interface.capabilities" in error for error in self.errors_for(manifest)))

    def test_identity_limits(self) -> None:
        for name in ("Uppercase", "double--hyphen", "a" * 65):
            manifest = copy.deepcopy(self.manifest)
            manifest["name"] = name
            self.assertTrue(any("invalid name" in error for error in self.errors_for(manifest)))
        manifest = copy.deepcopy(self.manifest)
        manifest["author"]["name"] = "x" * 121
        self.assertTrue(any("invalid author.name" in error for error in self.errors_for(manifest)))

    def test_requires_both_icons(self) -> None:
        for field in ("logo", "composerIcon"):
            for missing in (True, False):
                with self.subTest(field=field, missing=missing):
                    manifest = copy.deepcopy(self.manifest)
                    if missing:
                        del manifest["interface"][field]
                    else:
                        manifest["interface"][field] = None
                    self.assertTrue(any(
                        f"invalid interface.{field} path" in error
                        for error in self.errors_for(manifest)
                    ))

    def test_scaffold_icons_report_missing_asset(self) -> None:
        for with_mcp in (False, True):
            with self.subTest(with_mcp=with_mcp):
                manifest = scaffold_skill.codex_manifest_template("kong-test", with_mcp)
                for field in ("logo", "composerIcon"):
                    self.assertEqual(manifest["interface"][field], "./assets/logo.png")
                with patch.object(Path, "is_file", return_value=False):
                    errors = self.errors_for(manifest)
                for field in ("logo", "composerIcon"):
                    self.assertTrue(any(
                        f"invalid interface.{field} path: './assets/logo.png'" in error
                        for error in errors
                    ))

    def test_icon_dimensions_and_size(self) -> None:
        with tempfile.TemporaryDirectory(dir=check_repo.REPO_ROOT / ".tmp") as temp:
            path = Path(temp) / "icon.png"
            for width, height, valid in ((48, 48, True), (800, 400, False), (47, 47, False), (4097, 4097, False)):
                path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height))
                self.assertEqual(check_repo.validate_codex_icon(path) is None, valid)
            with path.open("wb") as stream:
                stream.truncate(5 * 1024 * 1024 + 1)
            self.assertIn("5 MiB", check_repo.validate_codex_icon(path))


if __name__ == "__main__":
    unittest.main()
