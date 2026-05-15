#!/usr/bin/env python3
from __future__ import annotations

import json
import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def version_targets() -> list[Path]:
    targets: list[Path] = [
        REPO_ROOT / ".cursor-plugin" / "marketplace.json",
    ]
    plugins_dir = REPO_ROOT / "plugins"
    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
            continue
        targets.extend(
            [
                plugin_dir / ".claude-plugin" / "plugin.json",
                plugin_dir / ".cursor-plugin" / "plugin.json",
            ]
        )
    return targets


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def update_version(path: Path, version: str) -> None:
    data = load_json(path)
    if "version" in data:
        data["version"] = version
    elif isinstance(data.get("metadata"), dict) and "version" in data["metadata"]:
        data["metadata"]["version"] = version
    write_json(path, data)


def manifest_version(path: Path) -> str | None:
    data = load_json(path)
    value = data.get("version")
    if value is None and isinstance(data.get("metadata"), dict):
        value = data["metadata"].get("version")
    return value if isinstance(value, str) else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare or verify versioned release manifests.")
    parser.add_argument("version", help="Semver version like 1.2.3")
    parser.add_argument("--check", action="store_true", help="Verify manifests already match the supplied version.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    version = args.version.strip()
    if not VERSION_RE.match(version):
        print(f"invalid version: {version!r} (expected semver like 1.2.3)", file=sys.stderr)
        return 1

    if args.check:
        mismatches: list[str] = []
        for target in version_targets():
            actual = manifest_version(target)
            if actual != version:
                mismatches.append(f"{target.relative_to(REPO_ROOT)}={actual!r}")
        if mismatches:
            print(
                "checked-in manifest versions do not match the requested release version: "
                + ", ".join(mismatches),
                file=sys.stderr,
            )
            return 1
        print(f"release manifests already match {version}")
        return 0

    for target in version_targets():
        update_version(target, version)

    print(f"prepared release {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
