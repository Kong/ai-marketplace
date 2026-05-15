# Reintroduce Codex Plugin Support

## Goal

Restore Codex as a first-class plugin and marketplace install target after the
required approval to list on the Codex marketplace has been granted again.
Reintroduction must restore the checked-in manifests, sync and validation
automation, release versioning, and the contributor docs that explain the
Codex-specific install path.

## Current State

Codex marketplace support was intentionally removed because this repo does not
yet have approval to list plugins on the Codex marketplace. Removal included:

- the root Codex marketplace registry file
- the plugin-local Codex manifest(s)
- scaffolding, generated sync, validation, and release-prep code for Codex
- the dedicated Codex install guide
- contributor/testing docs that treated Codex as a supported plugin host

Shared skill installers such as `npx skills` and `gh skill` may still exist in
the repo independently. Do not assume restoring Codex marketplace support means
changing those flows.

## Preconditions

Before restoring anything, confirm:

1. Marketplace approval for Codex has been granted.
2. The desired install shape is still a root marketplace file plus per-plugin
   `.codex-plugin/plugin.json` manifests.
3. The current Codex plugin and marketplace schema still match the previous
   repository design. If the product changed, update the implementation rather
   than restoring stale shapes.

## Files To Restore Or Update

### Checked-In Codex Manifest Files

Restore:

- `.agents/plugins/marketplace.json`
- `plugins/kong-konnect/.codex-plugin/plugin.json`

If the repo has additional shipped plugin packages by then, restore
`plugins/<plugin>/.codex-plugin/plugin.json` for each relevant plugin.

Expected responsibilities:

- the root marketplace file lists all shipped plugins
- each plugin-local Codex manifest declares the local skills it ships
- `mcpServers` references the shared `kong-konnect` MCP entry when the plugin
  has MCP wiring
- manifest versions stay aligned with the other supported host manifests
- homepage and repository fields stay aligned with the canonical repo URL
- generated keywords and capabilities stay derived from shipped skills

### Automation And Validation Code

Restore Codex handling in:

- `scripts/scaffold_skill.py`
- `scripts/check_repo.py`
- `scripts/release_prepare.py`

Required implementation details:

1. `scripts/scaffold_skill.py`
   - restore `codex_manifest_template(...)`
   - make `plugin:new` create `plugins/<plugin>/.codex-plugin/plugin.json`
   - preserve the current manifest shape conventions:
     - `skills` list
     - `keywords`
     - `interface.displayName`
     - `interface.shortDescription`
     - `interface.category`
     - `interface.capabilities`
   - if `--with-mcp` is set, wire `mcpServers` to the shared MCP server name

2. `scripts/check_repo.py`
   - restore `Plugin.codex_manifest`
   - require the Codex manifest during plugin discovery
   - restore `sync_codex_marketplace(...)`
   - restore `sync_codex_plugin(...)`
   - restore derived capability generation if it is not already present
   - restore static validation for:
     - plugin names
     - source paths
     - homepage/repository drift
     - release version alignment
     - marketplace listing integrity
   - restore text-file checks for Codex-facing docs
   - ensure `--fix` rewrites Codex generated artifacts alongside the other
     supported host surfaces

3. `scripts/release_prepare.py`
   - add Codex manifests back to `version_targets()`
   - keep release version updates aligned across Codex and the other supported
     host manifests

### Documentation To Restore

Restore or update these files:

- `README.md`
- `docs/install/README.md`
- `docs/install/codex.md`
- `docs/release.md`
- `docs/developer.md`
- `docs/testing.md`
- `docs/structure.md`

Required doc content:

1. `README.md`
   - add Codex back to the supported install target badges
   - restore the opening summary only if Codex is actually supported again

2. `docs/install/README.md`
   - add the Codex install badge/link back

3. `docs/install/codex.md`
   - restore the dedicated Codex page
   - cover both:
     - skill-only install via `npx skills`
     - personal or team marketplace/plugin install, if still supported
   - reference:
     - `.agents/plugins/marketplace.json`
     - `plugins/kong-konnect/.codex-plugin/plugin.json`
     - `plugins/kong-konnect/mcp.json`
   - explain when `KONNECT_TOKEN` is required
   - clearly separate skill-only install from marketplace/plugin install

4. `docs/release.md`
   - add Codex manifests back to the `release:prepare` manifest list

5. `docs/developer.md`
   - restore Codex under "Add A Plugin"
   - restore Codex under generated outputs
   - restore Codex in the supported tools list only if it is again a supported
     host surface

6. `docs/testing.md`
   - restore a Codex-specific spot-check section
   - decide whether the shared-installer section should again include a
     host-specific `gh skill install ... --agent codex` example
   - include expected skill visibility and MCP expectations for the plugin path

7. `docs/structure.md`
   - restore the root Codex marketplace manifest entry
   - restore the plugin-local Codex manifest entry

## Suggested Manifest Shapes

Unless Codex's format changed, the root marketplace file should follow the
previous repository convention:

```json
{
  "name": "ai-marketplace",
  "interface": {
    "displayName": "Kong AI Marketplace"
  },
  "plugins": [
    {
      "name": "kong-konnect",
      "source": {
        "source": "local",
        "path": "./plugins/kong-konnect"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity",
      "keywords": []
    }
  ]
}
```

And the plugin-local manifest should follow the previous repository convention:

```json
{
  "name": "kong-konnect",
  "version": "1.0.0",
  "description": "Portable Kong Konnect skills plus remote MCP configuration for Codex.",
  "author": "kong",
  "homepage": "https://github.com/kong/ai-marketplace",
  "repository": "https://github.com/kong/ai-marketplace",
  "license": "MIT",
  "keywords": [],
  "skills": [],
  "mcpServers": [
    "kong-konnect"
  ],
  "interface": {
    "displayName": "Kong Konnect",
    "shortDescription": "Portable Kong Konnect skills and remote MCP wiring.",
    "category": "development",
    "capabilities": []
  }
}
```

Treat those as a starting point only. Validate them against current Codex
plugin and marketplace expectations before committing.

## Implementation Sequence

1. Confirm marketplace approval and current Codex schema expectations.
2. Restore the root marketplace file and plugin-local Codex manifest(s).
3. Restore Codex support in scaffolding, generated sync, validation, and
   release prep.
4. Run `mise run gen` so generated Codex artifacts are in sync.
5. Restore the Codex install doc and contributor references.
6. Run validation.
7. If approval includes actual host testing, run a manual Codex spot check.

## Validation Checklist

Run:

```bash
mise run preflight
mise run deps
mise run gen
mise run lint
```

If the change is release-oriented, also run:

```bash
gh skill publish --dry-run
mise run release:prepare -- 1.0.1
```

Then verify:

- `.agents/plugins/marketplace.json` regenerates cleanly
- plugin-local Codex manifests regenerate cleanly
- `scripts/check_repo.py` passes without drift
- plugin discovery fails if a shipped plugin is missing its Codex manifest
- release version updates touch Codex and the other supported host manifests
  together
- restored docs link to the correct Codex files

## Non-Goals

Do not broaden this task into:

- a redesign of shared skill installers
- changes to the shared MCP server shape unless Codex now requires them
- migration away from plugin-local manifests
- unrelated repo-wide documentation rewrites

## Handoff Notes For The Implementing Agent

- Preserve the repo's existing generated-versus-manual boundaries. Codex
  marketplace data and plugin manifests should be managed by the same
  generation and validation flow as the other supported hosts.
- If Codex's marketplace or plugin schema changed, document the delta in the
  implementing change and update this plan afterward so the checked-in
  restoration plan stays current.
