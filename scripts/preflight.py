#!/usr/bin/env python3
"""Check local tool prerequisites for common contributor workflows."""
from __future__ import annotations

import argparse
import shutil
import sys


PROFILE_TOOLS: dict[str, list[tuple[str, str]]] = {
    "core": [
        ("git", "required for working in the repository"),
        ("uv", "required for `mise run deps` and repo validation tasks"),
    ],
    "publish": [
        ("gh", "required for `gh skill publish --dry-run`"),
    ],
    "shared-installers": [
        ("node", "required for `npx skills ...` verification"),
        ("npx", "required for `npx skills ...` verification"),
        ("gh", "required for `gh skill ...` verification"),
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local prerequisites for contributor workflows.")
    parser.add_argument(
        "profiles",
        nargs="*",
        default=None,
        choices=["core", "publish", "shared-installers", "all"],
        help="Profiles to check. Default: core",
    )
    return parser.parse_args()


def selected_profiles(values: list[str]) -> list[str]:
    if "all" in values:
        return ["core", "publish", "shared-installers"]
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def main() -> int:
    args = parse_args()
    missing: list[str] = []

    profiles = args.profiles or ["core"]
    for profile in selected_profiles(profiles):
        print(f"[{profile}]")
        for command, reason in PROFILE_TOOLS[profile]:
            found = shutil.which(command)
            if found is None:
                missing.append(command)
                print(f"  missing: {command:<8} {reason}")
            else:
                print(f"  ok:      {command:<8} {found}")

    if missing:
        unique = ", ".join(sorted(set(missing)))
        print(f"\nmissing required tools: {unique}", file=sys.stderr)
        return 1

    print("\npreflight-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
