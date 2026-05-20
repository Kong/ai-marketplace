# Cursor

![Cursor](https://img.shields.io/badge/Cursor-plugin-000000?style=for-the-badge&logo=cursor&logoColor=white)

## Local Plugin Install

For local verification, install the checked-in plugin package from this repo
under Cursor's local plugin directory:

1. Create `~/.cursor/plugins/local/kong-konnect/`.
2. Copy the contents of [`plugins/kong-konnect/`](../../plugins/kong-konnect/) into that path so Cursor sees
   [`.cursor-plugin/plugin.json`](../../plugins/kong-konnect/.cursor-plugin/plugin.json) at the plugin root.
3. Restart Cursor or run `Developer: Reload Window`.
4. Confirm `kong-konnect` appears under installed plugins.

<!-- END HEADER SECTION -->

Use a real copied directory for local testing. In this repo, a symlinked local
plugin directory did not load reliably, while a copied directory did.

Once this repo is listed in a Cursor marketplace, the same package shape can
also be installed through Cursor's plugin UI or `/add-plugin`. The local path
above remains the contributor smoke-test flow.

## What Gets Installed

- the `kong-konnect` plugin package from [`plugins/kong-konnect/`](../../plugins/kong-konnect/)
- the shared skills from [`plugins/kong-konnect/skills/`](../../plugins/kong-konnect/skills/)
- the `kong-konnect` MCP server entry from [`plugins/kong-konnect/mcp.json`](../../plugins/kong-konnect/mcp.json)

Cursor uses the plugin manifest in
[`plugins/kong-konnect/.cursor-plugin/plugin.json`](../../plugins/kong-konnect/.cursor-plugin/plugin.json)
and the repo marketplace catalog in
[`.cursor-plugin/marketplace.json`](../../.cursor-plugin/marketplace.json).

## Skills Without The Plugin Wrapper

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

## MCP Notes

`KONNECT_TOKEN` is only required when Cursor loads or uses the
`kong-konnect` MCP server. If you only want the shared skills, use the
skill-only install path instead.

If you want the MCP server without the full plugin wrapper, use
[`plugins/kong-konnect/mcp.json`](../../plugins/kong-konnect/mcp.json) as the
checked-in reference shape.
