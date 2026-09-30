# Kong Konnect

This plugin installs skills for configuring and inspecting Kong Gateway and
Konnect, plus the `kong-konnect` MCP server at
`https://global.mcp.konghq.com/`. The MCP connection uses OAuth and the signed-in
user's Konnect permissions. Access to resources and operations depends on those
permissions.

## Included skills

- `deck-gateway`
- `gateway-plugin-datakit`
- `kong-skill-authoring`
- `kongctl-declarative`
- `kongctl-query`
- `konnect-access-scope`
- `konnect-ai-gateway`
- `konnect-api-catalog`
- `konnect-api-publish`
- `konnect-app-auth`
- `konnect-control-plane-bootstrap`
- `konnect-event-gateway`
- `konnect-gateway-triage`
- `konnect-monetization`
- `konnect-observability-triage`
- `konnect-platform-router`
- `portal-branding`
- `portal-page-design`
- `technical-writing`
- `terraform-kong-gateway`
- `terraform-konnect`

## What it runs and sends

The bundled MCP connection sends tool requests only to
`global.mcp.konghq.com`. Requests contain the arguments needed for the selected
Konnect operation; results return to your agent client. The client handles
OAuth login and credentials. The plugin itself reads no credentials and starts
no local MCP server.

Some skills guide the agent to run local CLIs such as decK, kongctl, or
Terraform, or provide CI examples. These use your own existing Konnect
credentials, such as `KONNECT_TOKEN` or credentials established by `kongctl login`.
Those credentials go only to the Konnect or Kong Gateway endpoint you point
the tool at. The plugin itself does not read or forward them. Review the
selected commands and target environment before running them; operations can
read or change resources according to your permissions.

## Install and log in

For Claude Code, follow the [installation guide](https://github.com/Kong/ai-marketplace/blob/main/docs/install/claude-code.md).
Add the marketplace, install `kong-konnect@ai-marketplace`, and reload plugins.
Run `/mcp`, select the plugin server, and complete the browser login. From an
interactive terminal, you can also run
`claude mcp login plugin:kong-konnect:kong-konnect`.

For Cursor, follow the [installation guide](https://github.com/Kong/ai-marketplace/blob/main/docs/install/cursor.md).
Install the plugin, connect its `kong-konnect` server, and complete the OAuth
browser prompt. The guides also cover existing server entries and alternative
installation paths.

## Privacy, support, and license

[Privacy](https://konghq.com/legal/privacy-policy)

[Support](https://github.com/Kong/ai-marketplace/issues)

License: [MIT](LICENSE).
