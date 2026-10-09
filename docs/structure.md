# Structure

This file maps the install and config surfaces generated or maintained in this
repo.

This is a contributor file map, not an end-user guide. The repo now uses a
plugin-first marketplace layout: root marketplace manifests enumerate plugins,
and each shipped plugin package owns its local skills, manifests, and optional
MCP config.

## Root Marketplace Manifests

- `.agents/plugins/marketplace.json`
  - Codex repo marketplace catalog; generated from shipped plugin packages.

- `server.json`
  - Official MCP Registry listing for the remote Konnect MCP server, published
    with `mcp-publisher` (domain proof on `konghq.com`).
- `.cursor-plugin/marketplace.json`
  - Cursor marketplace registry for all plugin packages in this repo.
- `.claude-plugin/marketplace.json`
  - Claude Code marketplace registry for all plugin packages in this repo.

## Plugin Packages

- `plugins/kong-konnect/`
  - First shipped plugin package. Future product packages should follow the
    same shape.
- `plugins/kong-konnect/README.md`
  - Package contents, data handling, installation, privacy, support, and license.
- `plugins/kong-konnect/LICENSE`
  - Full MIT license text shipped inside the plugin folder.
- `plugins/kong-konnect/skills/`
  - Canonical shared skills shipped by the `kong-konnect` plugin and by
    shared-skill installers.
- `plugins/kong-konnect/.claude-plugin/plugin.json`
  - Claude Code plugin manifest local to the `kong-konnect` package.
- `plugins/kong-konnect/.codex-plugin/plugin.json`
  - Codex-native manifest for local installation and OpenAI submission.
- `plugins/kong-konnect/.cursor-plugin/plugin.json`
  - Cursor plugin manifest local to the `kong-konnect` package.
- `plugins/kong-konnect/assets/logo.png`
  - Cursor and Codex marketplace logo. Codex uses it for both listing and
    composer icons. When `assets/logo.png` exists at a plugin
    root, `sync_cursor_plugin()` in `scripts/check_repo.py` emits the
    `logo` field in that plugin's Cursor manifest.
- `plugins/kong-konnect/.mcp.json`
  - Codex submission MCP configuration, generated identically to `mcp.json`.
- `plugins/kong-konnect/mcp.json`
  - Generated HTTP MCP configuration using the global URL and OAuth.
  - Source: `sync_plugin_mcp()` in `scripts/check_repo.py`.

## Generated Inventory

- `docs/skills.md`
  - Generated inventory of the currently shipped skills, grouped by plugin.

## Contributor Helpers

- `AGENTS.md`
  - Contributor-facing skill authoring guide used in this repo.

## Release And Validation

- `.github/workflows/validate.yml`
  - Validates generated metadata on pull requests and `main`.
- `.github/workflows/release.yml`
  - Canonical publishing workflow for tags and GitHub releases.
- `docs/release.md`
  - Contributor-facing release preparation and trigger process.

## Installation Guides

- `docs/install/README.md`
  - Client index, OAuth default, headless PAT/SPAT example, and migration from
    the archived stdio server or a PAT-configured plugin.
