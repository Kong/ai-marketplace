# Other Tools

![Other Tools](https://img.shields.io/badge/Other_Tools-skills-555555?style=for-the-badge&logo=vercel&logoColor=white)

For tools without a first-class plugin or extension wrapper in Kong AI Marketplace, use
the shared skills plus the MCP config.

## Skills

`npx skills` and `gh skill` are both supported install paths for the shared
skills in Kong AI Marketplace.

### `npx skills`

Install all skills:

```bash
npx skills add kong/ai-marketplace
```

<!-- END HEADER SECTION -->

Install a single skill:

```bash
npx skills add kong/ai-marketplace --skill gateway-plugin-datakit
```

Update all globally installed skills:

```bash
npx skills update -g -y
```

Update one installed skill:

```bash
npx skills update -g -y gateway-plugin-datakit
```

`--skill` applies to `npx skills add`. The `update` command takes skill names
positionally.

### `gh skill`

`gh skill` is available in GitHub CLI v2.90.0+ and is currently in public
preview.

Preview a skill before installing it:

```bash
gh skill preview kong/ai-marketplace gateway-plugin-datakit
```

```bash
gh skill install kong/ai-marketplace
```

To install a single skill directly, use:

```bash
gh skill install kong/ai-marketplace gateway-plugin-datakit
```

If `gh skill` does not pick the right host automatically, pass `--agent`.

Pin an install to a reviewed tag or SHA when you need reproducibility:

```bash
gh skill install kong/ai-marketplace gateway-plugin-datakit --pin v1.0.0
```

Update all installed skills:

```bash
gh skill update --all
```

Update one installed skill:

```bash
gh skill update gateway-plugin-datakit
```

These skill-only installs do not require MCP authentication.

To validate GitHub-side publishability without publishing:

```bash
gh skill publish --dry-run
```

## Auto-update caution

Be careful with any automatic update path. It can pull newer skill
instructions without review, which may introduce supply-chain or security risk
if content changes upstream.

If you use auto-update, prefer updating one known skill first:

```bash
npx skills update -g -y gateway-plugin-datakit
```

Or with GitHub CLI:

```bash
gh skill update gateway-plugin-datakit
```

Claude Code has a native plugin update flow. See its install page for the
current recommended approach.

## Remote MCP with OAuth

Use [`plugins/kong-konnect/mcp.json`](../../plugins/kong-konnect/mcp.json) as
the checked-in reference for the global URL and header-free OAuth configuration.
The client flows below follow client documentation; Kong has not recorded
end-to-end OAuth tests for them as of 2026-09-18.

### Claude.ai and Claude Desktop

For individual plans in Claude.ai, go to **Customize → Connectors**, click
**+**, then **Add custom connector**. Enter `kong-konnect` as the name and
`https://global.mcp.konghq.com/` as the URL. Free users are limited to one custom
connector.

For Team and Enterprise plans, an Owner must first add the connector through
**Organization settings → Connectors**, using **Add → Custom → Web**. Members
can then connect to it individually.

Connect the server and complete the browser login when first prompted. No PAT
is needed. Claude Desktop shares the connector once it is added in Claude.ai.
This installs the remote connector, not the repository's skills. See
[Claude's custom connector instructions](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

### Codex CLI

Add the server directly:

```bash
codex mcp add kong-konnect --url https://global.mcp.konghq.com/
```

Complete the browser login when prompted during setup or first use. If login
has not started, run:

```bash
codex mcp login kong-konnect
```

[Codex documents remote MCP OAuth and the login command](https://developers.openai.com/codex/mcp/).
The Codex plugin was removed pending marketplace approval; these commands
configure the MCP server directly and do not install a plugin.

### CI and headless clients

For clients such as the Copilot cloud agent that need non-interactive auth,
use the separate [PAT/SPAT example](./README.md#ci-and-headless-authentication).
Before switching an existing installation, follow the
[migration steps](./README.md#migrating-from-the-old-server).
