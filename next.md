# Agent Plugins handoff

## Current state

- Branch: `feat/agent-plugins-standard`
- Base: `ac6eb98` on `feat/claude-plugin-user-config` (the branch for PR #4)
- This is intentionally a stacked follow-up; it is not based directly on
  `main` yet.

The branch adds Agent Plugins 1.0.0 support while preserving secure,
client-specific bearer-token handling:

- `plugins/kong-konnect/plugin.json` is the portable Agent Plugins manifest.
- The Agent Plugins package is skills-only for now. The standard does not
  define API-key prompts or secret references, and conforming clients treat
  remote MCP URL and header strings literally.
- Claude keeps its sensitive `userConfig` token prompt and inline MCP
  definition. Its transport is now `streamable-http`.
- Cursor uses `mcp.cursor.json` plus declared `KONNECT_TOKEN` and
  `KONNECT_MCP_URL` variables. The URL defaults to the US endpoint.
- All Agent Skills metadata values are strings. `metadata.tags` is a single
  comma-separated string and is split only when deriving marketplace keywords.
- Agent Plugins 1.0.0 manifest and MCP schemas are pinned byte-for-byte under
  `schemas/agent-plugins/1.0.0/`, including recorded SHA-256 checksums.
- Repo validation checks Agent Plugins manifests against the pinned schemas,
  rejects remote `${...}` placeholders in portable `mcp.json` files, and runs
  the pinned `skills-ref` validator over every shipped skill.
- Install, distribution, testing, release, Kiro, structure, and contributor
  documentation describe the client boundaries and the future OAuth path.

## Credential decision

Until Konnect MCP OAuth is released, keep authentication in native client
configuration:

- Claude: sensitive `userConfig`
- Cursor: plugin variables configured through Plugins → Configure
- Other clients: their own secure user-level MCP credential mechanism

Do not add a bearer token, token default, or `${KONNECT_TOKEN}` placeholder to
an Agent Plugins root `mcp.json`. The portable root MCP file should be added
only when client-managed OAuth is available or the standard adopts a portable
secret-reference mechanism.

The relevant upstream credential proposal is:
<https://github.com/agentplugins/agent-plugins-spec/issues/7>.

## Verification completed

- `mise run lint`
- `mise run ci`
- `gh skill publish --dry-run`
- `claude plugin validate ./plugins/kong-konnect --strict`
- Claude Code 2.1.226 disposable-plugin load test: `$schema` plus
  `streamable-http` appeared in Claude's MCP inventory
- `python3 -m py_compile` for the changed Python scripts
- release manifest version check for `1.0.0`
- scaffold output assertions
- `git diff --check`
- pinned schema files matched the official versioned URLs byte-for-byte

Not yet verified end-to-end:

- installing the root Agent Plugins package in each advertised compatible
  client
- Cursor's Plugins → Configure flow with a real token and live Konnect MCP
- live authenticated Konnect MCP behavior through Claude
- OAuth-based portable MCP configuration, because Konnect MCP OAuth is not yet
  released

## Next steps

1. Review the branch diff, especially the skills-only Agent Plugins boundary
   and the rename from `mcp.json` to `mcp.cursor.json`.
2. While PR #4 remains open, either open a stacked PR with
   `feat/claude-plugin-user-config` as the base or wait for PR #4 to merge.
3. After PR #4 merges, rebase this branch onto `main`, rerun `mise run ci`, and
   open or retarget the Agent Plugins PR.
4. Smoke-test a local Cursor plugin copy with dashboard variables using a
   disposable profile. Confirm the token is not written into the checked-in or
   cached plugin package.
5. Smoke-test `plugins/kong-konnect/` as an Agent Plugins package in at least
   one client other than Cursor, confirming all skills are discovered.
6. Track Agent Plugins credential issue #7 and Konnect MCP OAuth. When OAuth is
   released, add a schema-pinned root `mcp.json` using `streamable-http` with no
   packaged Authorization header, then test client-managed login and regional
   endpoint behavior.
