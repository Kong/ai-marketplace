# Kong AI Marketplace

[![Status](https://img.shields.io/badge/status-tech_preview-ffb020?style=for-the-badge)](#tech-preview)
[![Maintenance](https://img.shields.io/badge/maintenance-actively_updated-0a7f5a?style=for-the-badge)](#tech-preview)

Portable Kong skills plus `kong-konnect` MCP configuration for Cursor, Claude
Code, Agent Plugins clients, and shared skill installers.

This repo is the contributor-facing source of truth for the packaged skills and
install metadata. End users normally consume these assets through marketplace
catalogs, plugin bundles, or shared-skill installers rather than by reading
this repo directly.

## Tech Preview

This repository is currently in tech preview. It is actively maintained and
updated as the shipped skills, install surfaces, and packaging workflows
evolve.

Public issues are welcome during tech preview. Pull requests are currently
limited to Kong employees while the preview is in progress.

The repo now uses a plugin-first layout. Root marketplace manifests advertise
installable plugin packages, and the first shipped package is
`plugins/kong-konnect/`.

## Getting Started

- Installation docs: [docs/install/README.md](docs/install/README.md)
- Available skills: [docs/skills.md](docs/skills.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
- Developer guide: [docs/developer.md](docs/developer.md)
- Release process: [docs/release.md](docs/release.md)
- Testing guide: [docs/testing.md](docs/testing.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Repo structure: [docs/structure.md](docs/structure.md)

## Contributing

Contributor bootstrap and maintenance guidance lives in
[CONTRIBUTING.md](CONTRIBUTING.md).

Recommended local validation path for contributors:

```bash
mise trust
mise install
mise run preflight
mise run deps
mise run hooks:install
mise run lint
```

The repo hooks are an opt-in local guardrail. GitHub Actions remains the
enforcement path on pull requests and pushes to `main`.

## Install Targets

[![Cursor](https://img.shields.io/badge/Cursor-plugin-000000?style=for-the-badge&logo=cursor&logoColor=white)](docs/install/cursor.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-111111?style=for-the-badge&logo=anthropic&logoColor=white)](docs/install/claude-code.md)
[![Agent Plugins](https://img.shields.io/badge/Agent_Plugins-open_standard-4B32C3?style=for-the-badge)](docs/install/agent-plugins.md)
[![Other Tools](https://img.shields.io/badge/Other_Tools-skills-555555?style=for-the-badge&logo=vercel&logoColor=white)](docs/install/other-tools.md)

## Authentication

All MCP install surfaces use the same bearer token model, but credential input
is host-specific:

```text
Authorization: Bearer <Konnect access token>
```

- Claude Code's full plugin prompts for the token, masks it, and stores it in
  Claude's secure credential store. It also prompts for the regional MCP URL
  and defaults to the US endpoint.
- Cursor's native plugin declares `KONNECT_TOKEN` and the regional endpoint as
  dashboard-configured plugin variables.
- Agent Plugins 1.0.0 does not define API-key prompts or secret references, so
  its package remains skills-only until Konnect MCP supports client-managed
  OAuth. Other clients must use their own secure MCP credential setup.
- Skill-only installs through Agent Plugins, `npx skills`, or `gh skill`
  require no MCP authentication.

## Skill Install Notes

- Install the whole repo with `npx skills add kong/ai-marketplace`.
- Install one skill with `npx skills add kong/ai-marketplace --skill gateway-plugin-datakit`.
- Update one installed skill with `npx skills update -g -y gateway-plugin-datakit` or `gh skill update gateway-plugin-datakit`.
- Prefer native plugin update flows in supported host tools over custom startup hooks.
- Be careful with any automatic update path: it can pull newer skill instructions automatically and may introduce supply-chain or security risk.
- For `gh skill`, preview before install with `gh skill preview kong/ai-marketplace gateway-plugin-datakit`.

Cursor's native MCP template is
[`plugins/kong-konnect/mcp.cursor.json`](plugins/kong-konnect/mcp.cursor.json).
Claude's prompt-backed MCP configuration is generated inline in its plugin
manifest. See [Agent Plugins](docs/install/agent-plugins.md) for why the open
standard package does not yet declare authenticated MCP.
