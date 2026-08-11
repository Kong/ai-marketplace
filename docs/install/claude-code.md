# Claude Code

![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-111111?style=for-the-badge&logo=claude&logoColor=white)

## Install

```bash
/plugin marketplace add kong/ai-marketplace
/plugin install kong-konnect@ai-marketplace
/reload-plugins
```

When Claude Code enables the plugin, enter:

- a Konnect personal or system account access token; Claude masks the value and
  stores it in its secure credential store
- the regional MCP URL matching your Konnect resources; the default is
  `https://us.mcp.konghq.com`

Use `https://eu.mcp.konghq.com`, `https://au.mcp.konghq.com`, or
`https://in.mcp.konghq.com` when your resources are in that region. The full
Claude plugin does not require you to export `KONNECT_TOKEN`.

### What gets installed

- The `kong-konnect` plugin package from [`plugins/kong-konnect/`](../../plugins/kong-konnect/)
- The shared skills from [`plugins/kong-konnect/skills/`](../../plugins/kong-konnect/skills/)
- The prompt-configured `kong-konnect` MCP server entry

<!-- END HEADER SECTION -->

Claude Code uses the plugin manifest in
[`plugins/kong-konnect/.claude-plugin/plugin.json`](../../plugins/kong-konnect/.claude-plugin/plugin.json)
and the marketplace catalog in
[`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json).

## Install components instead of the full plugin

Install all skills:

```bash
npx skills add kong/ai-marketplace
```

Install only one skill:

```bash
npx skills add kong/ai-marketplace --skill gateway-plugin-datakit
```

That does not require `KONNECT_TOKEN`.

If you installed via `gh skill`, you can also update one installed skill with
`gh skill update gateway-plugin-datakit`.

## Auto-update

Prefer Claude Code's marketplace auto-update support over a custom shell hook.

In Claude Code:

1. Run `/plugin`.
2. Open the `Marketplaces` tab.
3. Select the `ai-marketplace` marketplace.
4. Enable or disable auto-update there.

If plugins were updated during a session, run `/reload-plugins`.

Be careful with auto-update. It can pull newer skill instructions
automatically, which may introduce supply-chain or security risk if content
changes upstream without review.

If you want the MCP server without the full plugin wrapper, add
`kong-konnect` manually as an HTTP MCP server and attach the Authorization
header through Claude's own MCP configuration. Do not copy a real token into
this repository. Set the regional URL when your resources are outside the US
region.

The native manifest uses `streamable-http`, matching Agent Plugins. This was
verified by loading a session-only plugin in Claude Code 2.1.226 and observing
the server in Claude's MCP inventory; strict manifest validation alone is not
treated as transport evidence. The definition stays inline because Claude's
`${user_config...}` credential expansion is client-specific even though the
transport name is shared.
