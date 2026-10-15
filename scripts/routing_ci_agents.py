"""Decide which agents a CI routing eval runs, from which API keys are present.

    python scripts/routing_ci_agents.py plan                       JSON on stdout
    python scripts/routing_ci_agents.py verify SUMMARY.json AGENTS  exit 0 ok, 2 mismatch

Claude needs ANTHROPIC_API_KEY and Codex needs OPENAI_API_KEY (CI has no Codex login). Only
presence is read: a missing, empty, or whitespace-only value counts as absent, and a key value
is never printed (fork PRs get no secrets, so they skip cleanly). `plan` prints
{"agents": [...], "skipped": [{"agent", "env"}], "messages": [...], "summary": str}.

`verify` is the CI partial-result guard: a summary may be partial only when its `agents_run`
is exactly the agents that had keys (the others were skipped for missing keys). Any other
mismatch fails, so an unexplained partial result is never accepted. No model calls.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

import routing_agents as agents_lib

KEYS = {"claude": "ANTHROPIC_API_KEY", "codex": "OPENAI_API_KEY"}
NO_KEYS_MESSAGE = "skipping routing evals: no API keys are configured"


def plan(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if env is None else env
    present = [agent for agent in agents_lib.AGENTS if env.get(KEYS[agent], "").strip()]
    skipped = [{"agent": agent, "env": KEYS[agent]} for agent in agents_lib.AGENTS if agent not in present]
    messages = [f"{item['agent']} skipped: {item['env']} is not set" for item in skipped]
    summary = f"Agents run: {', '.join(present) or 'none'}; skipped: {', '.join(i['agent'] for i in skipped) or 'none'}"
    return {"agents": present, "skipped": skipped, "messages": messages, "summary": summary}


def verify(summary: Mapping[str, Any], agents: list[str]) -> str | None:
    """Return an error message when the summary's scope is not explained by the agents with keys."""
    ran = sorted(summary.get("agents_run") or [])
    if ran != sorted(agents):
        return f"summary ran agents {ran} but the agents with API keys were {sorted(agents)}"
    if bool(summary.get("partial")) != agents_lib.is_partial(agents):
        return f"summary partial={summary.get('partial')!r} does not match agents {sorted(agents)}"
    return None


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "plan":
        print(json.dumps(plan()))
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
