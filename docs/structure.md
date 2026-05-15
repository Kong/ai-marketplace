# Structure

This file maps the install and config surfaces generated or maintained in this
repo.

This is a contributor file map, not an end-user guide. The repo now uses a
plugin-first marketplace layout: root marketplace manifests enumerate plugins,
and each shipped plugin package owns its local skills, manifests, and optional
MCP config.

## Root Marketplace Manifests

- `.cursor-plugin/marketplace.json`
  - Cursor marketplace registry for all plugin packages in this repo.
- `.claude-plugin/marketplace.json`
  - Claude Code marketplace registry for all plugin packages in this repo.

## Plugin Packages

- `plugins/kong-konnect/`
  - First shipped plugin package. Future product packages should follow the
    same shape.
- `plugins/kong-konnect/skills/`
  - Canonical shared skills shipped by the `kong-konnect` plugin and by
    shared-skill installers.
- `plugins/kong-konnect/.claude-plugin/plugin.json`
  - Claude Code plugin manifest local to the `kong-konnect` package.
- `plugins/kong-konnect/.cursor-plugin/plugin.json`
  - Cursor plugin manifest local to the `kong-konnect` package.
- `plugins/kong-konnect/mcp.json`
  - Shared checked-in MCP reference shape for the `kong-konnect` plugin.

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
