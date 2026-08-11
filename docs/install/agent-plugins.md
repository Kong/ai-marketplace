# Agent Plugins

The `kong-konnect` package conforms to the Agent Plugins 1.0.0 working draft
for portable skill distribution. Use
[`plugins/kong-konnect/`](../../plugins/kong-konnect/) as the plugin root; its
[`plugin.json`](../../plugins/kong-konnect/plugin.json) and `skills/` directory
are the open-standard surfaces.

When a client installs from an archive or copied directory, `plugin.json` must
remain at the package root. In this multi-plugin repository, point the client
or marketplace entry at `plugins/kong-konnect/`, not at the repository root.

## Authentication Before Konnect MCP OAuth

Agent Plugins 1.0.0 does not define secret references, install-time variables,
or API-key prompts for remote MCP headers. It also requires clients to treat
remote URLs and header values literally. A checked-in value such as
`${KONNECT_TOKEN}` would therefore be sent literally by a conforming client,
not resolved from the environment.

For that reason the open-standard package currently installs the skills but
does not declare a root `mcp.json`. Choose the authenticated path your client
supports:

- Claude Code: install the Claude plugin, which prompts for the token and stores
  it through Claude's sensitive `userConfig` flow.
- Cursor: install the Cursor plugin, which declares `KONNECT_TOKEN` and the
  regional URL as plugin variables configured in Cursor's plugin dashboard.
- Other Agent Plugins clients: add the Konnect MCP endpoint with the client's
  own secure credential facility. If the client cannot attach a bearer token
  without storing it in the plugin package, install the skills only.

Do not add a real token, a token default, or an environment placeholder to a
root Agent Plugins `mcp.json`.

## OAuth-Ready MCP Shape

Once the Konnect endpoint supports client-managed MCP OAuth, the portable
configuration can be enabled without a packaged header:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "kong-konnect": {
      "type": "streamable-http",
      "url": "https://us.mcp.konghq.com"
    }
  }
}
```

That file belongs at `plugins/kong-konnect/mcp.json`. Keep regional endpoint
selection client-managed unless the portable standard gains a configuration
mechanism.

## Coexistence With Native Plugins

The package deliberately contains three manifests:

- `plugin.json` for Agent Plugins clients
- `.claude-plugin/plugin.json` for Claude's secure token prompt
- `.cursor-plugin/plugin.json` for Cursor variables and marketplace metadata

The native manifests point at native MCP definitions and do not change the
portable skills. Cursor's marketplace catalog selects the Cursor manifest;
clients installing the open standard select the root manifest.

The pinned Agent Plugins 1.0.0 schemas live under
[`schemas/agent-plugins/1.0.0/`](../../schemas/agent-plugins/1.0.0/). Repo
validation checks the root manifest against those snapshots and runs the
official `skills-ref` validator across every shipped skill.

References:

- [Agent Plugins specification](https://agent-plugins.org/specification)
- [Agent Plugins MCP server rules](https://agent-plugins.org/plugin-authors/mcp-servers)
- [Agent Plugins credential configuration proposal](https://github.com/agentplugins/agent-plugins-spec/issues/7)
- [Agent Skills specification](https://agentskills.io/specification)
