#!/usr/bin/env python3
"""Build a reproducible OpenAI submission ZIP from tracked Kong Konnect files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins/kong-konnect"
FIXED_FILES = {".codex-plugin/plugin.json", ".mcp.json", "README.md", "LICENSE", "assets/logo.png"}
SECRET_PATTERN = re.compile(rb"(?:kpat_|spat_)[A-Za-z0-9_-]{16,}|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")


def package_files() -> dict[str, bytes]:
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "plugins/kong-konnect"], cwd=REPO_ROOT
    ).decode().split("\0")
    files: dict[str, bytes] = {}
    for entry in filter(None, tracked):
        path = REPO_ROOT / entry
        name = path.relative_to(PLUGIN_ROOT).as_posix()
        if name not in FIXED_FILES and not name.startswith("skills/"):
            continue
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != REPO_ROOT):
            raise ValueError(f"symlink in package: {name}")
        if not path.is_file() or not path.resolve().is_relative_to(PLUGIN_ROOT.resolve()):
            raise ValueError(f"missing or escaping package file: {name}")
        if name.startswith("skills/") and any(part.startswith(".") for part in PurePosixPath(name).parts):
            raise ValueError(f"hidden skill file: {name}")
        content = path.read_bytes()
        if SECRET_PATTERN.search(content):
            raise ValueError(f"possible credential in package: {name}")
        files[name] = content
    if missing := FIXED_FILES - files.keys():
        raise ValueError(f"required files must exist and be git-tracked: {sorted(missing)}")
    manifest = json.loads(files[".codex-plugin/plugin.json"])
    if manifest.get("skills") != "./skills/" or manifest.get("mcpServers") != "./.mcp.json":
        raise ValueError("unexpected skill or MCP path; update the package allowlist deliberately")
    expected_mcp = {"mcpServers": {"kong-konnect": {"type": "http", "url": "https://global.mcp.konghq.com/"}}}
    if json.loads(files[".mcp.json"]) != expected_mcp:
        raise ValueError("MCP must use the global OAuth endpoint without headers, tokens, or local commands")
    if any(field in manifest for field in ("apps", "hooks")):
        raise ValueError("new component references require an explicit package allowlist update")
    interface = manifest["interface"]
    for field in ("logo", "composerIcon", "logoDark", "composerIconDark", "screenshots"):
        values = interface.get(field, [])
        if isinstance(values, str):
            values = [values]
        for value in values:
            if not value.startswith("./") or ".." in PurePosixPath(value).parts or value[2:] not in files:
                raise ValueError(f"unpackaged interface.{field}: {value}")
    skills = {name for name in files if re.fullmatch(r"skills/[^/]+/SKILL\.md", name)}
    disk_skills = {path.relative_to(PLUGIN_ROOT).as_posix() for path in (PLUGIN_ROOT / "skills").glob("*/SKILL.md")}
    if not skills or skills != disk_skills:
        raise ValueError("every shipped skill must be tracked and packaged")
    return files


def build(output: Path) -> None:
    files = package_files()
    if output.resolve().is_relative_to(PLUGIN_ROOT.resolve()):
        raise ValueError("write the ZIP outside the source plugin directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    print(f"Built {output} ({len(files)} files)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination ZIP (package contents at archive root)")
    args = parser.parse_args()
    try:
        build(args.output)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
