"""Decide which agents a CI routing eval runs, from which API keys are present.

    python scripts/routing_ci_agents.py plan [--agents claude,codex]  JSON on stdout
    python scripts/routing_ci_agents.py verify SUMMARY.json AGENTS  exit 0 ok, 2 mismatch

Claude needs ANTHROPIC_API_KEY and Codex needs OPENAI_API_KEY (CI has no Codex login). Only
presence is read: a missing, empty, or whitespace-only value counts as absent, and a key value
is never printed (fork PRs get no secrets, so they skip cleanly). `--agents` restricts the plan to
the requested agents (default both); an agent that was not requested is neither run nor "skipped".
`plan` prints {"requested": [...], "agents": [...], "skipped": [{"agent", "env"}], "messages": [...],
"none_runnable": bool, "summary": str}.

Missing keys only ever warn while at least one requested agent can run. `none_runnable` is true when no
requested agent has a key: nothing runs, and the gate (routing_gate.py) fails `fail_no_agents` in the
merge queue and manual runs rather than passing without having evaluated anything.

`verify` is the CI partial-result guard: a summary may be partial only when its `agents_run`
is exactly the agents that had keys (the others were skipped for missing keys). Any other
mismatch fails, so an unexplained partial result is never accepted. No model calls.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

import routing_agents as agents_lib

KEYS = {"claude": "ANTHROPIC_API_KEY", "codex": "OPENAI_API_KEY"}
NO_KEYS_MESSAGE = "no routing eval can run: none of the requested agents has an API key configured"


def plan(env: Mapping[str, str] | None = None, requested: Iterable[str] | None = None) -> dict[str, Any]:
    env = os.environ if env is None else env
    wanted = agents_lib.parse_agents(requested)
    present = [agent for agent in wanted if env.get(KEYS[agent], "").strip()]
    skipped = [{"agent": agent, "env": KEYS[agent]} for agent in wanted if agent not in present]
    messages = [f"{item['agent']} skipped: {item['env']} is not set" for item in skipped]
    summary = f"Agents run: {', '.join(present) or 'none'}; skipped: {', '.join(i['agent'] for i in skipped) or 'none'}"
    return {
        "requested": list(wanted), "agents": present, "skipped": skipped, "messages": messages,
        "none_runnable": not present, "summary": summary,
    }


def verify(summary: Mapping[str, Any], agents: list[str]) -> str | None:
    """Return an error message when the summary's scope is not explained by the agents with keys."""
    ran = sorted(summary.get("agents_run") or [])
    if ran != sorted(agents):
        return f"summary ran agents {ran} but the agents with API keys were {sorted(agents)}"
    if bool(summary.get("partial")) != agents_lib.is_partial(agents):
        return f"summary partial={summary.get('partial')!r} does not match agents {sorted(agents)}"
    return None


def main(argv: list[str]) -> int:
    if len(argv) in (2, 4) and argv[1] == "plan" and (len(argv) == 2 or argv[2] == "--agents"):
        try:
            print(json.dumps(plan(requested=argv[3:] or None)))
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        return 0
    if len(argv) == 4 and argv[1] == "verify":
        try:
            summary = json.loads(Path(argv[2]).read_text())
            agents = agents_lib.parse_agents([argv[3]])
        except (OSError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        error = verify(summary, list(agents))
        if error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
