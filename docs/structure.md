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
- `plugins/kong-konnect/plugin.json`
  - Agent Plugins 1.0.0 manifest. The standard package is skills-only until
    Konnect MCP supports client-managed OAuth or the standard adds portable
    secret references.
- `plugins/kong-konnect/.claude-plugin/plugin.json`
  - Claude Code plugin manifest local to the `kong-konnect` package. It declares
    prompt-backed user configuration and an inline MCP definition so secrets use
    Claude's secure credential store.
- `plugins/kong-konnect/.cursor-plugin/plugin.json`
  - Cursor plugin manifest local to the `kong-konnect` package. It declares
    user configuration variables for the token and regional endpoint.
- `plugins/kong-konnect/mcp.cursor.json`
  - Cursor-native MCP template. Claude does not consume this file through the
    full plugin, and it is not an Agent Plugins `mcp.json`.

## Pinned Standards

- `schemas/agent-plugins/1.0.0/plugin.schema.json`
  - Pinned upstream schema used to validate each root Agent Plugins manifest.
- `schemas/agent-plugins/1.0.0/mcp.schema.json`
  - Pinned upstream schema used when a portable root `mcp.json` is present.

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
