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

These skill-only installs do not require `KONNECT_TOKEN`.

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

## MCP config reference

Use [`plugins/kong-konnect/mcp.json`](../../plugins/kong-konnect/mcp.json) as
the checked-in reference shape for the `kong-konnect` MCP server.

`KONNECT_TOKEN` is only required if you add and use the MCP server.
