# Codex

## Plugin install

The repository packages all Kong Konnect skills and the hosted MCP server for
Codex and ChatGPT. This is a repo marketplace install; public directory
approval and publication are separate and are not claimed here.

From a checkout containing the Codex package:

```bash
codex plugin marketplace add .
codex plugin marketplace list
codex plugin add kong-konnect@ai-marketplace
```

After this change is available on the public default branch, the remote form is:

```bash
codex plugin marketplace add Kong/ai-marketplace
```

The CLI install command enables the plugin. Complete its MCP OAuth prompt
when connecting and start a new session. Alternatively, restart the ChatGPT
desktop app, open the Plugins Directory, choose
**Kong AI Marketplace**, and install **Kong Konnect**. Complete the OAuth
browser login when prompted, then start a new chat and check that the Kong
skills and `kong-konnect` MCP tools are available. Client availability varies;
see [OpenAI's package and marketplace guide](https://developers.openai.com/plugins/build/plugins).

The repository marketplace is
[`.agents/plugins/marketplace.json`](../../.agents/plugins/marketplace.json).
It points to the package containing
[`plugins/kong-konnect/.codex-plugin/plugin.json`](../../plugins/kong-konnect/.codex-plugin/plugin.json),
which loads the skill directory and
[`plugins/kong-konnect/.mcp.json`](../../plugins/kong-konnect/.mcp.json).
This generated Codex companion has the same content as the shared
[`plugins/kong-konnect/mcp.json`](../../plugins/kong-konnect/mcp.json).
The MCP configuration uses `https://global.mcp.konghq.com/` without headers or
tokens; the client manages OAuth and dynamic client registration.

## MCP only

To connect the server without installing the plugin or its skills:

```bash
codex mcp add kong-konnect --url https://global.mcp.konghq.com/
codex mcp login kong-konnect
```

Use either the plugin connection or the manual connection. Remove an existing
manual entry with `codex mcp remove kong-konnect` before using the plugin.
See [migration and headless authentication](README.md) for legacy entries and
separate PAT/SPAT configuration for CI. Never add credentials to the package.

## Skills only

```bash
npx skills add kong/ai-marketplace --agent codex
```

This installs skills without MCP wiring or OAuth. See
[shared installers](other-tools.md) for preview, update, and single-skill options.
