# Claude Code

![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-111111?style=for-the-badge&logo=claude&logoColor=white)

## Install

```bash
/plugin marketplace add kong/ai-marketplace
/plugin install kong-konnect@ai-marketplace
/reload-plugins
```

### What gets installed

- The `kong-konnect` plugin package from [`plugins/kong-konnect/`](../../plugins/kong-konnect/)
- The shared skills from [`plugins/kong-konnect/skills/`](../../plugins/kong-konnect/skills/)
- The `kong-konnect` MCP server entry

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

Skill-only installs do not require MCP authentication.

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

## MCP authentication

The plugin loads the global URL from
[`plugins/kong-konnect/mcp.json`](../../plugins/kong-konnect/mcp.json) and uses
OAuth. On first use Claude Code marks the server as needing authentication.
Run `/mcp`, select the `kong-konnect` server (shown as a plugin server when
installed via the plugin), and follow the browser login. For the direct-add
path you can also run `claude mcp login kong-konnect`.

For the MCP server alone, run this shell command instead of installing the plugin:

```bash
claude mcp add --transport http kong-konnect https://global.mcp.konghq.com/
```

Kong recorded a successful OAuth test of this direct-add flow on 2026-09-18.
That test does not establish an end-to-end test of the plugin install path.
See [Claude Code's MCP documentation](https://code.claude.com/docs/en/mcp)
for authentication steps.

For CI or headless use, see the separate
[PAT/SPAT configuration](./README.md#ci-and-headless-authentication).
Before switching an existing installation, follow the
[migration steps](./README.md#migrating-from-the-old-server).
