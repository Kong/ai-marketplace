# Live Konnect Ops

Use this file for read-heavy Konnect work: discovery, analytics, debugging, and
triage against live state.

## Defaults

- Prefer the `kong-konnect` MCP server first.
- If MCP is unavailable, say so early and continue with the relevant existing
  skill plus repo or user-provided artifacts.
- Keep this workflow read-only unless the user explicitly asks for changes.

## Primary Skill Sources

- `skills/konnect-gateway-triage/SKILL.md`
- `skills/konnect-observability-triage/SKILL.md`
- `skills/konnect-access-scope/SKILL.md`
- `skills/kongctl-query/SKILL.md`
