# Testing Agent Plugins

Use these checks when changing the portable root `plugin.json`, `mcp.json`, or
shared skills. The package root is `plugins/kong-konnect/`.

## Automated checks

```bash
mise run test
mise run lint
gh skill publish --dry-run
```

`mise run lint` validates the pinned Agent Plugins 1.0.0 schemas plus the
specification's remote URL and credential rules. `gh skill publish --dry-run`
checks Agent Skills only; it is not an Agent Plugins package validator. There
is currently no official standalone CLI validator covering the complete Agent
Plugins package. Codex validates and loads the package as part of installation.

## Real-client smoke test

Codex supports schema-declared root Agent Plugins. With a current Codex CLI,
test through this repo's local marketplace:

```bash
codex plugin marketplace add .
codex plugin list --marketplace ai-marketplace --available --json
codex plugin add kong-konnect@ai-marketplace --json
codex plugin list --json
codex
```

Start a new session with the plugin enabled, confirm the Kong skills are
present, and try:

```text
When should I use the gateway-plugin-datakit skill?
```

The current portable package is intentionally skills-only, so no
`kong-konnect` MCP server should be installed from the root package. Clean up
with:

```bash
codex plugin remove kong-konnect@ai-marketplace
codex plugin marketplace remove ai-marketplace
```

This flow was verified with Codex CLI 0.147.0, which installed version 1.0.0
from the root Agent Plugins manifest. Confirm that `codex plugin list --json`
reports every skill currently listed in `docs/skills.md`; the count will grow as
the marketplace adds skills.

References:

- [Codex portable Agent Plugins support](https://github.com/openai/codex/pull/36544)
- [Codex marketplace commands](https://developers.openai.com/plugins/build/plugins)
