"""Effective per-host model and effort for routing evals, resolved by evals/promptfoo/settings.js.

The Node module is the single source of the pinned defaults and of the validation rules;
this module only runs it (`node evals/promptfoo/settings.js`) so the harness records exactly
what the host configs will use. Offline; no credentials or model calls.

Settings document, per host
    {"model": {"value", "source": "default|override"},
     "effort": {"value": str|null, "source": "default|override"},
     "overridden": bool}
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Mapping

import check_repo

SETTINGS_JS = check_repo.REPO_ROOT / "evals" / "promptfoo" / "settings.js"
OVERRIDE_VARIABLES = (
    "ROUTING_CODEX_MODEL", "ROUTING_CODEX_EFFORT", "ROUTING_CLAUDE_MODEL", "ROUTING_CLAUDE_EFFORT",
)


def load_all(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return {"settings": {host: settings doc}, "fixed": {host: ...}}; ValueError when a variable is invalid."""
    merged = {**os.environ, **(env or {})} if env is not None else dict(os.environ)
    out = subprocess.run(["node", str(SETTINGS_JS)], capture_output=True, text=True, env=merged, check=False)
    if out.returncode != 0:
        raise ValueError((out.stderr.strip() or "invalid routing settings").removeprefix("ERROR: "))
    return json.loads(out.stdout)


def load(env: Mapping[str, str] | None = None) -> dict[str, dict[str, Any]]:
    return load_all(env)["settings"]


def describe(settings: dict[str, Any]) -> str:
    effort = settings["effort"]
    return (
        f"model={settings['model']['value']} ({settings['model']['source']}) "
        f"effort={effort['value'] or 'provider default'} ({effort['source']})"
    )


def warning(settings: dict[str, dict[str, Any]]) -> str | None:
    """Console warning when any override is active; None when every host uses the pins."""
    active = [f"{host}: {describe(doc)}" for host, doc in settings.items() if doc["overridden"]]
    if not active:
        return None
    return (
        "WARNING: routing settings overridden (" + "; ".join(active) + "). Results are marked overridden: true "
        "and are not comparable with CI, which always uses the pinned defaults."
    )


def annotate(doc: dict[str, Any], settings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Record the host's effective settings in a result or comparison document."""
    host_settings = settings[doc["host"]]
    doc["settings"] = {"model": host_settings["model"], "effort": host_settings["effort"]}
    doc["overridden"] = host_settings["overridden"]
    return doc
