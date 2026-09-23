# Installation

Choose the install path that matches the tool you use.

These pages document the generated install surfaces that this source repo
maintains. Most users will follow one tool-specific page and will not need any
contributor context from the rest of the repository.

[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-111111?style=for-the-badge&logo=claude&logoColor=white)](./claude-code.md)
[![Cursor](https://img.shields.io/badge/Cursor-plugin-000000?style=for-the-badge&logo=cursor&logoColor=white)](./cursor.md)
[![AWS Kiro Powers](https://img.shields.io/badge/AWS-Kiro_Powers-232F3E?style=for-the-badge&labelColor=FF9900&logo=amazonaws&logoColor=000000)](./aws.md)
[![Other Tools](https://img.shields.io/badge/Other_Tools-skills-555555?style=for-the-badge&logo=vercel&logoColor=white)](./other-tools.md)

## Server and authentication

- Name: `kong-konnect`
- Default URL: `https://global.mcp.konghq.com/`
- Interactive authentication: OAuth 2.1 with PKCE and dynamic client registration

The shipped [MCP configuration](../../plugins/kong-konnect/mcp.json) has no
`headers` block. OAuth-capable clients register themselves and open a browser
login when you first connect or use the server; no token is pasted.
An unauthenticated request receives a 401 with `WWW-Authenticate` pointing to
`resource_metadata`; Kong Identity publishes OIDC discovery.

The global URL is the [documented default](https://developer.konghq.com/konnect-platform/konnect-mcp/).
Regional hosts also answer at `https://us.mcp.konghq.com/`,
`https://eu.mcp.konghq.com/`, `https://au.mcp.konghq.com/`, and
`https://in.mcp.konghq.com/` for users who want to pin a region.

Follow the [Claude Code](./claude-code.md), [Cursor](./cursor.md), or
[Claude.ai, Claude Desktop, and Codex CLI](./other-tools.md#remote-mcp-with-oauth)
instructions. Tested with Claude Code's direct
`claude mcp add --transport http` OAuth flow on 2026-09-18 and
[Kiro CLI 2.23.1](./aws.md#mcp-authentication) on 2026-09-23 (CLI surface,
explicit `oauthScopes`). The other client instructions are based on client
documentation, not Kong end-to-end tests.

## CI and headless authentication

A Konnect personal access token (`kpat_`) or system account token (`spat_`)
remains supported for CI and headless use, including the Copilot cloud agent.
Create a separate, hand-written `mcp.json` for your client; do not edit the
shipped OAuth configuration. For clients using this JSON shape:

```json
{
  "mcpServers": {
    "kong-konnect": {
      "type": "http",
      "url": "https://global.mcp.konghq.com/",
      "headers": {
        "Authorization": "Bearer <kpat_or_spat_token>"
      }
    }
  }
}
```

Replace the placeholder through your client's secret configuration with a
`kpat_` or `spat_` token. Use that client's supported secret interpolation
syntax; do not commit a populated token file. This example is a bearer-auth
configuration shape, not a Copilot-specific install file.

## Migrating from the old server

1. Inspect user, project, and plugin MCP settings for duplicate `kong-konnect`
   entries. The archived `Kong/mcp-konnect` stdio entry uses that same name,
   `command: node`, args pointing to `mcp-konnect/build/index.js`, and
   `KONNECT_ACCESS_TOKEN` / `KONNECT_REGION` environment variables. An older
   PAT entry uses `headers.Authorization` with `Bearer ...` on
   `https://us.mcp.konghq.com`.
2. Remove the old stdio entry and duplicate manual entries. Choose either the
   current plugin or one manual HTTP entry so the server is configured once.
3. For interactive use, update to the shipped global URL without `headers`,
   then reconnect and complete the OAuth browser login.
4. If you need headless authentication, retain one explicit PAT/SPAT
   configuration for that environment using the example above.

Find and remove the old entry in your client:

- Claude Code: run `claude mcp list`, then
  `claude mcp remove kong-konnect -s <local|user|project>`, replacing the scope
  placeholder with the scope containing the old entry.
- Cursor: check `~/.cursor/mcp.json` and `.cursor/mcp.json`; remove the old
  `kong-konnect` entry from `mcpServers`.
- Claude Desktop: remove the old stdio entry from `claude_desktop_config.json`.
- Codex CLI: run `codex mcp list`, then `codex mcp remove kong-konnect` for the
  old entry.

See the [Konnect MCP documentation](https://developer.konghq.com/konnect-platform/konnect-mcp/)
for the current remote server.

The Codex plugin was removed pending marketplace approval. Use the direct
Codex CLI MCP setup linked above; do not reinstall the removed plugin.

## Skills only

Shared skills installed with `npx skills` or `gh skill` do not require MCP
authentication.

For skill-only installs from GitHub, prefer previewing before install:

```bash
gh skill preview kong/ai-marketplace gateway-plugin-datakit
```
