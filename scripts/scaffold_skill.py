#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = REPO_ROOT / "plugins"
MCP_NAME = "kong-konnect"
MCP_URL = "https://us.mcp.konghq.com"
TOKEN_ENV = "KONNECT_TOKEN"
REPO_URL = "https://github.com/kong/skills"
DEFAULT_PLUGIN = "kong-konnect"


def normalize_name(value: str, label: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        raise ValueError(f"{label} must contain at least one lowercase letter or digit")
    return normalized


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: object) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=True) + "\n")


def ensure_missing(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"{path.relative_to(REPO_ROOT)} already exists")


def ensure_plugin_exists(plugin_name: str) -> Path:
    plugin_dir = PLUGINS_DIR / plugin_name
    if not plugin_dir.exists():
        raise ValueError(
            f"plugin {plugin_name!r} does not exist; create plugins/{plugin_name} first with `mise run plugin:new -- {plugin_name}`"
        )
    return plugin_dir


def skill_usage_error() -> ValueError:
    return ValueError(
        "missing skill name.\n"
        "Use `mise run skill:new -- <skill-name>` to scaffold into the default "
        f"plugin `{DEFAULT_PLUGIN}`.\n"
        "Use `mise run skill:new -- <plugin-name> <skill-name>` to target a "
        "different plugin.\n"
        f"Example: `mise run skill:new -- {DEFAULT_PLUGIN} gateway-plugin-datakit`"
    )


def parse_skill_args(values: list[str]) -> tuple[str, str]:
    if len(values) == 1:
        return DEFAULT_PLUGIN, values[0]
    if len(values) == 2:
        return values[0], values[1]
    raise skill_usage_error()


def skill_template(skill_name: str) -> str:
    title = skill_name.replace("-", " ")
    return textwrap.dedent(
        f"""\
        ---
        name: {skill_name}
        description: One-line Kong-specific description used for discovery and matching. Replace this with a real summary.
        license: MIT
        metadata:
          product: kong
          category: workflow
          tags:
            - kong
            - {skill_name}
        ---

        # {title}

        ## When To Use

        Use this skill when:

        - replace this bullet with the request pattern that should trigger the skill
        - keep the trigger scope Kong-specific and operational

        ## Workflow

        1. Identify the Kong-specific goal, system, or resource involved.
        2. Prefer the source-of-truth artifacts and commands for this workflow.
        3. Call out the key edge cases, failure modes, and validation checks.
        4. Return a concise result with concrete next steps.

        ## Guardrails

        - Replace this section with the real do/do-not guidance for the workflow.
        - Remove generic filler before committing the skill.
        """
    )


def claude_manifest_template(plugin_name: str, with_mcp: bool) -> dict[str, object]:
    data: dict[str, object] = {
        "name": plugin_name,
        "version": "0.1.0",
        "description": f"Portable Kong skills packaged as the {plugin_name} Claude Code plugin.",
        "author": {"name": "kong"},
        "skills": [],
    }
    if with_mcp:
        data["mcpServers"] = "./mcp.json"
    return data


def mcp_template() -> dict[str, object]:
    return {
        "mcpServers": {
            MCP_NAME: {
                "type": "http",
                "url": MCP_URL,
                "headers": {"Authorization": f"Bearer ${{{TOKEN_ENV}}}"},
            }
        }
    }


def scaffold_skill(args: argparse.Namespace) -> int:
    plugin_value, skill_value = parse_skill_args(args.args)
    plugin_name = normalize_name(plugin_value, "plugin name")
    skill_name = normalize_name(skill_value, "skill name")
    plugin_dir = ensure_plugin_exists(plugin_name)
    skill_dir = plugin_dir / "skills" / skill_name
    skill_md = skill_dir / "SKILL.md"
    ensure_missing(skill_dir)
    write_text(skill_md, skill_template(skill_name))
    print(skill_md.relative_to(REPO_ROOT))
    return 0


def scaffold_plugin(args: argparse.Namespace) -> int:
    plugin_name = normalize_name(args.name, "plugin name")
    plugin_dir = PLUGINS_DIR / plugin_name
    ensure_missing(plugin_dir)

    write_json(plugin_dir / ".claude-plugin" / "plugin.json", claude_manifest_template(plugin_name, args.with_mcp))
    (plugin_dir / "skills").mkdir(parents=True, exist_ok=False)
    if args.with_mcp:
        write_json(plugin_dir / "mcp.json", mcp_template())

    print(plugin_dir.relative_to(REPO_ROOT))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scaffold Kong plugin and skill files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plugin_parser = subparsers.add_parser(
        "plugin",
        help="Create a new plugin package with host manifests and an empty skills directory.",
    )
    plugin_parser.add_argument("name", help="Plugin name. This becomes plugins/<name>/ and the manifest package name.")
    plugin_parser.add_argument(
        "--with-mcp",
        action="store_true",
        help="Also create plugins/<name>/mcp.json with the shared kong-konnect MCP reference shape.",
    )
    plugin_parser.set_defaults(handler=scaffold_plugin)

    skill_parser = subparsers.add_parser(
        "skill",
        help="Create a new skill directory with SKILL.md boilerplate inside an existing plugin.",
    )
    skill_parser.add_argument(
        "args",
        nargs="*",
        metavar="plugin-or-skill",
        help=(
            "Pass `<skill-name>` to use the default plugin `kong-konnect`, or "
            "`<plugin-name> <skill-name>` to target a different plugin."
        ),
    )
    skill_parser.set_defaults(handler=scaffold_skill)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (FileExistsError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
