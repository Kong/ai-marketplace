# Claude Code

![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-111111?style=for-the-badge&logo=anthropic&logoColor=white)

Claude Code uses the plugin manifest in
[`plugins/kong-konnect/.claude-plugin/plugin.json`](../../plugins/kong-konnect/.claude-plugin/plugin.json)
and the marketplace catalog in
[`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json).

## Install

```bash
/plugin marketplace add kong/ai-marketplace
/plugin install ai-marketplace@kong-konnect
/reload-plugins
```

## What Gets Installed

- the `kong-konnect` plugin package from `plugins/kong-konnect/`
- the shared skills from `plugins/kong-konnect/skills/`
- the `kong-konnect` MCP server entry

## Components Instead Of The Full Plugin

Skill-only install:

```bash
npx skills add kong/ai-marketplace
```

Install only one skill from this repo:

```bash
npx skills add kong/ai-marketplace --skill gateway-plugin-datakit
```

That does not require `KONNECT_TOKEN`.

If you installed via `gh skill`, you can also update one installed skill with
`gh skill update gateway-plugin-datakit`.

## Auto-Update

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
`kong-konnect` manually using
[`plugins/kong-konnect/mcp.json`](../../plugins/kong-konnect/mcp.json) as the
reference shape. That is when `KONNECT_TOKEN` is required.
