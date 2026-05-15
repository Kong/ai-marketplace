# Kong AI Marketplace

[![Status](https://img.shields.io/badge/status-tech_preview-ffb020?style=for-the-badge)](#tech-preview)
[![Maintenance](https://img.shields.io/badge/maintenance-actively_updated-0a7f5a?style=for-the-badge)](#tech-preview)

Portable Kong skills plus `kong-konnect` MCP configuration for Claude Code and
shared skill installers.

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

[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-111111?style=for-the-badge&logo=anthropic&logoColor=white)](docs/install/claude-code.md)
[![Other Tools](https://img.shields.io/badge/Other_Tools-skills-555555?style=for-the-badge&logo=vercel&logoColor=white)](docs/install/other-tools.md)

## Authentication

All install surfaces use the same bearer token model:

```text
Authorization: Bearer ${KONNECT_TOKEN}
```

`KONNECT_TOKEN` is only needed when you install or use the `kong-konnect` MCP
server. A skill-only install via `npx skills` or `gh skill` does not require
it.

## Skill Install Notes

- Install the whole repo with `npx skills add kong/ai-marketplace`.
- Install one skill with `npx skills add kong/ai-marketplace --skill gateway-plugin-datakit`.
- Update one installed skill with `npx skills update -g -y gateway-plugin-datakit` or `gh skill update gateway-plugin-datakit`.
- Prefer native plugin update flows in supported host tools over custom startup hooks.
- Be careful with any automatic update path: it can pull newer skill instructions automatically and may introduce supply-chain or security risk.
- For `gh skill`, preview before install with `gh skill preview kong/ai-marketplace gateway-plugin-datakit`.

Use [`plugins/kong-konnect/mcp.json`](plugins/kong-konnect/mcp.json) as the
shared checked-in reference shape for the `kong-konnect` MCP server.
