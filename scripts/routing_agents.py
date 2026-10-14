"""Select which agent runtimes (Claude Code, Codex) a routing eval run covers.

The spec and result documents call an agent a "host"; identifiers keep that name. A run with
fewer than all agents is partial and must never read as a complete result (routing_results.combine_hosts).

    python scripts/routing_agents.py [claude|codex|claude,codex ...]

Prints the normalized agents (canonical order, one line, space separated); no values means all.
An unknown agent exits 2 with a message. Used by the mise tasks; no model calls.
"""
from __future__ import annotations

import sys
from typing import Iterable

import routing_results as results

AGENTS = results.HOSTS


def parse_agents(values: Iterable[str] | None) -> tuple[str, ...]:
    """Normalize repeatable and comma-separated --agent values; omitted or empty means every agent."""
    names = [part.strip() for value in values or [] for part in value.split(",")]
    if not any(names):
        return AGENTS
    unknown = sorted({name for name in names if name not in AGENTS})
    if unknown:
        raise ValueError(f"unknown agent {', '.join(map(repr, unknown))}; choose from {', '.join(AGENTS)}")
    return tuple(agent for agent in AGENTS if agent in names)


def is_partial(agents: Iterable[str]) -> bool:
    return set(agents) != set(AGENTS)


def scope(agents: Iterable[str]) -> dict[str, object]:
    agents = list(agents)
    return {"agents_run": agents, "partial": is_partial(agents)}


def label(state: str, agents: Iterable[str]) -> str:
    """Console label for an overall state; a partial run says which agents it covers."""
    agents = list(agents)
    return f"{state} (partial: {', '.join(agents)} only)" if is_partial(agents) else state


def main(argv: list[str]) -> int:
    try:
        print(" ".join(parse_agents(argv[1:])))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
