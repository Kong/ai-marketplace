# Agent Plugins

The `kong-konnect` package conforms to the Agent Plugins 1.0.0 working draft
for portable skill distribution. Use
[`plugins/kong-konnect/`](../../plugins/kong-konnect/) as the plugin root; its
[`plugin.json`](../../plugins/kong-konnect/plugin.json) and `skills/` directory
are the open-standard surfaces.

When a client installs from an archive or copied directory, `plugin.json` must
remain at the package root. In this multi-plugin repository, point the client
or marketplace entry at `plugins/kong-konnect/`, not at the repository root.

Codex 0.147.0 and newer Codex builds with portable Agent Plugins support can
install this package through the checked-in marketplace:

```bash
codex plugin marketplace add kong/ai-marketplace
codex plugin add kong-konnect@ai-marketplace
```

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
  own secure credential facility. Select the literal regional endpoint
  (`https://us.mcp.konghq.com`, `https://eu.mcp.konghq.com`,
  `https://au.mcp.konghq.com`, or `https://in.mcp.konghq.com`) and store the
  bearer token in the client's credential store, not in this package. If the
  client cannot do both, install the skills only.

Do not add a real token, a token default, or an environment placeholder to a
root Agent Plugins `mcp.json`.

## Enable MCP After OAuth Ships

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

That file belongs at `plugins/kong-konnect/mcp.json`, but the generic package
should not add it while the correct endpoint is region-specific. Agent Plugins
1.0.0 cannot ask the user to choose a region. The concrete options are:

1. Keep the generic package skills-only and let each client own the regional
   MCP connection. This is the recommendation today.
2. Once OAuth is available, publish explicitly region-scoped packages with
   distinct names and one literal HTTPS URL each.
3. If Kong provides one global OAuth-capable MCP endpoint, use that literal URL
   without configured headers in the generic package.

Do not silently make the US endpoint the portable default for users whose
Konnect resources may live elsewhere.

When OAuth is available:

1. Confirm whether Kong exposes one global endpoint or separate regional
   endpoints, and choose the package shape above.
2. Add `plugins/kong-konnect/mcp.json` with `streamable-http`, one literal HTTPS
   URL, and no `headers` entry.
3. Run the automated checks and the Codex smoke test in
   [Testing Agent Plugins](../testing-agent-plugins.md).
4. Verify that a fresh client session discovers `kong-konnect`, completes the
   OAuth flow, and can call a read-only Konnect tool.
5. Remove the skills-only caveats from the install documentation only after
   that end-to-end check passes.

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
repo's existing skill-structure checks. `gh skill publish --dry-run` remains
the external Agent Skills conformance check used by CI; there is no official
standalone Agent Plugins validator in this repo's toolchain.

See [Testing Agent Plugins](../testing-agent-plugins.md) for the focused local
and real-client checks.

References:

- [Agent Plugins specification](https://agent-plugins.org/specification)
- [Agent Plugins MCP server rules](https://agent-plugins.org/plugin-authors/mcp-servers)
- [Agent Plugins compatible clients](https://agent-plugins.org/compatible-clients)
- [Agent Skills specification](https://agentskills.io/specification)
