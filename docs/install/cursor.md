# Cursor

![Cursor](https://img.shields.io/badge/Cursor-plugin-000000?style=for-the-badge&logo=cursor&logoColor=white)

## Local plugin install

For local verification, install the plugin package from Kong AI Marketplace
under Cursor's local plugin directory:

1. Create `~/.cursor/plugins/local/kong-konnect/`.
2. Copy the contents of [`plugins/kong-konnect/`](../../plugins/kong-konnect/) into that path so Cursor sees
   [`.cursor-plugin/plugin.json`](../../plugins/kong-konnect/.cursor-plugin/plugin.json) at the plugin root.
3. Restart Cursor or run `Developer: Reload Window`.
4. Confirm `kong-konnect` appears under installed plugins.
5. Open the plugin's Configure screen and enter the required Konnect access
   token. Change the MCP URL only when the organization is outside the US
   region.

<!-- END HEADER SECTION -->

Use a real copied directory for local testing. A symlinked local plugin
directory does not load reliably, while a copied directory does.

Once Kong AI Marketplace is listed in a Cursor marketplace, the same package
shape can also be installed through Cursor's plugin UI or `/add-plugin`. The
local path above remains the contributor smoke-test flow.

### What gets installed

- The `kong-konnect` plugin package from [`plugins/kong-konnect/`](../../plugins/kong-konnect/)
- The shared skills from [`plugins/kong-konnect/skills/`](../../plugins/kong-konnect/skills/)
- The `kong-konnect` MCP server entry from [`plugins/kong-konnect/mcp.cursor.json`](../../plugins/kong-konnect/mcp.cursor.json)

Cursor uses the plugin manifest in
[`plugins/kong-konnect/.cursor-plugin/plugin.json`](../../plugins/kong-konnect/.cursor-plugin/plugin.json)
and the marketplace catalog in
[`.cursor-plugin/marketplace.json`](../../.cursor-plugin/marketplace.json).

## Skills without the plugin wrapper

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

## MCP Notes

`KONNECT_TOKEN` is only required when Cursor loads or uses the `kong-konnect`
MCP server. The native plugin declares it as a required variable; Cursor asks
an administrator for the value through Plugins → Configure and substitutes it
into the MCP header without putting the value in this repository.

`KONNECT_MCP_URL` defaults to `https://us.mcp.konghq.com`. Set it to the
regional endpoint for the organization when needed.

If you want the MCP server without the full plugin wrapper, create a user-level
Cursor MCP entry and use Cursor's documented environment-variable or secure
configuration support. The checked-in `mcp.cursor.json` is a plugin template;
its placeholders require the declarations in `.cursor-plugin/plugin.json`.

Cursor can also load the root Agent Plugins format, but that path is currently
skills-only because Agent Plugins 1.0.0 cannot portably bind an API key. See
[Agent Plugins](./agent-plugins.md).
