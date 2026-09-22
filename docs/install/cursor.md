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

<!-- END HEADER SECTION -->

Use a real copied directory for local testing. A symlinked local plugin
directory does not load reliably, while a copied directory does.

Once Kong AI Marketplace is listed in a Cursor marketplace, the same package
shape can also be installed through Cursor's plugin UI or `/add-plugin`. The
local path above remains the contributor smoke-test flow.

### What gets installed

- The `kong-konnect` plugin package from [`plugins/kong-konnect/`](../../plugins/kong-konnect/)
- The shared skills from [`plugins/kong-konnect/skills/`](../../plugins/kong-konnect/skills/)
- The `kong-konnect` MCP server entry from [`plugins/kong-konnect/mcp.json`](../../plugins/kong-konnect/mcp.json)

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

Skill-only installs do not require MCP authentication.

If you installed via `gh skill`, you can also update one installed skill with
`gh skill update gateway-plugin-datakit`.

## MCP authentication

Cursor loads the plugin's
[`mcp.json`](../../plugins/kong-konnect/mcp.json), which uses the global URL
without a bearer header. [Cursor documents OAuth for remote servers in
`mcp.json`](https://cursor.com/docs/context/mcp); the plugin-bundled entry has
not been tested by Kong as of 2026-09-18. On first use, follow the connection
prompt and complete the browser login.

From a checkout of this repository, the local install steps above can be run as:

```bash
mkdir -p ~/.cursor/plugins/local/kong-konnect
cp -R plugins/kong-konnect/. ~/.cursor/plugins/local/kong-konnect/
```

Restart Cursor or run `Developer: Reload Window`, then connect the server.
For MCP alone, copy the shipped MCP entry into your Cursor MCP settings
instead of installing the plugin.

For CI or headless use, see the separate
[PAT/SPAT configuration](./README.md#ci-and-headless-authentication).
Before switching an existing installation, follow the
[migration steps](./README.md#migrating-from-the-old-server).
