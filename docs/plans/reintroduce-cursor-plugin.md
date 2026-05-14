# Reintroduce Cursor Plugin Support

## Goal

Restore Cursor as a first-class install target after repository owners approve
shipping and documenting Cursor plugin surfaces again. The implementation needs
to restore not only the manifests, but also the generation, validation, release
prep, and install documentation that were removed when Cursor support was
temporarily taken out.

## Current State

Cursor support was intentionally removed because listing or publishing plugins
for Cursor currently requires approval that this repo has not received yet.
Removal included:

- root Cursor marketplace metadata
- plugin-local Cursor manifest(s)
- repo automation that scaffolded, synced, validated, and versioned Cursor
  manifests
- Cursor-specific install docs and all contributor references to them
- manual verification guidance for Cursor

Do not re-add only the manifest files. The repo used to treat Cursor as a
fully supported host, so the reintroduction needs to restore that whole slice.

## Preconditions

Before making code changes, confirm:

1. Approval to support Cursor plugin listing and distribution has actually been
   granted.
2. The desired distribution shape is still the same:
   - root marketplace file at `.cursor-plugin/marketplace.json`
   - per-plugin manifest at `plugins/<plugin>/.cursor-plugin/plugin.json`
   - optional plugin-local `mcp.json` reference reused via `"mcpServers":
     "mcp.json"`
3. Cursor still expects the same manifest schema and local install shape. If
   the product changed, update the design instead of blindly restoring the old
   files.

## Files To Restore Or Update

### Checked-In Cursor Manifest Files

Restore:

- `.cursor-plugin/marketplace.json`
- `plugins/kong-konnect/.cursor-plugin/plugin.json`

If the repo has additional plugin packages by then, create the corresponding
`plugins/<plugin>/.cursor-plugin/plugin.json` file for each shipped plugin, not
just `kong-konnect`.

Expected responsibilities:

- root marketplace lists each shipped plugin package
- plugin-local manifest points Cursor at the plugin's `skills/` directory
- plugin-local manifest references `mcp.json` when that plugin has MCP wiring
- version numbers stay aligned with the other host manifests
- homepage and repository values stay aligned with the canonical repo URL

### Automation And Validation Code

Restore Cursor handling in:

- `scripts/scaffold_skill.py`
- `scripts/check_repo.py`
- `scripts/release_prepare.py`

Required implementation details:

1. `scripts/scaffold_skill.py`
   - restore a `cursor_manifest_template(...)`
   - make `plugin:new` create `plugins/<plugin>/.cursor-plugin/plugin.json`
   - keep behavior parallel with the other supported host scaffolding
   - if `--with-mcp` is set, include the Cursor manifest's `mcpServers`
     pointer

2. `scripts/check_repo.py`
   - add `Plugin.cursor_manifest`
   - require the Cursor manifest during plugin discovery
   - restore generated sync for:
     - plugin-local Cursor manifest
     - root Cursor marketplace file
   - restore static metadata checks for Cursor:
     - plugin names
     - source paths
     - homepage/repository drift
     - version drift
   - restore text-file assertions for Cursor-facing docs
   - ensure `--fix` rewrites Cursor generated artifacts the same way it does
     for the other supported hosts

3. `scripts/release_prepare.py`
   - add Cursor manifests back into `version_targets()`
   - keep release version checks requiring Cursor and the other supported host
     manifests to stay aligned

### Documentation To Restore

Restore or update these files:

- `README.md`
- `docs/install/README.md`
- `docs/install/cursor.md`
- `docs/release.md`
- `docs/developer.md`
- `docs/testing.md`
- `docs/structure.md`

Required doc content:

1. `README.md`
   - add Cursor back to the supported install targets badge list
   - add Cursor back to the opening supported-host summary if appropriate
   - restore any host-update guidance only if it is still accurate

2. `docs/install/README.md`
   - add the Cursor install badge/link back
   - keep shared MCP guidance aligned with the checked-in `mcp.json` shape

3. `docs/install/cursor.md`
   - recreate the dedicated Cursor installation page
   - document both the native plugin path and the skill-only fallback path
   - reference:
     - `.cursor-plugin/marketplace.json`
     - `plugins/kong-konnect/.cursor-plugin/plugin.json`
     - `plugins/kong-konnect/mcp.json`
   - clearly explain when `KONNECT_TOKEN` is required

4. `docs/release.md`
   - add Cursor manifests back to the list of files versioned by
     `mise run release:prepare`

5. `docs/developer.md`
   - update the "Add A Plugin" section so plugin scaffolding includes Cursor
   - restore Cursor entries under generated outputs
   - restore Cursor in the supported tools list only if it is truly supported
     again

6. `docs/testing.md`
   - restore a Cursor-specific manual spot-check section
   - include install path, expected availability of
     `gateway-plugin-datakit`, MCP visibility expectations, and cleanup notes

7. `docs/structure.md`
   - restore the root Cursor marketplace entry
   - restore the plugin-local Cursor manifest entry

## Suggested Manifest Shapes

Unless Cursor's schema has changed, the plugin-local manifest should match the
previous repository convention:

```json
{
  "name": "kong-konnect",
  "skills": "skills",
  "mcpServers": "mcp.json",
  "description": "Portable Kong Konnect skills plus remote MCP configuration for Cursor.",
  "version": "1.0.0",
  "author": {
    "name": "kong"
  },
  "homepage": "https://github.com/kong/skills",
  "repository": "https://github.com/kong/skills",
  "license": "MIT",
  "keywords": []
}
```

And the root marketplace file should follow the previous repository convention:

```json
{
  "name": "kong-skills",
  "owner": {
    "name": "kong"
  },
  "metadata": {
    "description": "Portable Kong skills plus remote MCP configuration for Cursor.",
    "version": "1.0.0"
  },
  "plugins": [
    {
      "name": "kong-konnect",
      "source": "./plugins/kong-konnect",
      "description": "Portable Kong Konnect skills plus remote MCP configuration for Cursor."
    }
  ]
}
```

Treat those shapes as a starting point, not a guarantee. Revalidate them
against current Cursor expectations before committing.

## Implementation Sequence

1. Confirm approval and current Cursor manifest expectations.
2. Restore the checked-in Cursor manifest files.
3. Restore Cursor support in scaffolding, generation, validation, and release
   prep scripts.
4. Run `mise run gen` so generated Cursor metadata and any dependent docs are
   in sync.
5. Restore the Cursor install doc and all contributor references to it.
6. Run repo validation.
7. Run a manual Cursor spot check only if approval includes actually testing
   the install path.

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

- `scripts/check_repo.py --fix` regenerates Cursor artifacts without drift
- `scripts/check_repo.py` passes without errors
- plugin discovery fails if a shipped plugin is missing its Cursor manifest
- release version updates touch Cursor and the other supported host manifests
  together
- docs link correctly to the restored Cursor files

## Non-Goals

Do not broaden this task into:

- a redesign of all plugin packaging
- changes to the shared MCP server shape unless Cursor now requires them
- migration away from plugin-local manifests
- repo-wide documentation rewrites unrelated to Cursor support

## Handoff Notes For The Implementing Agent

- Preserve the existing toolchain choices in this repo. Cursor support should
  be restored alongside the repo's other supported host flows, not by
  replacing them.
- Keep generated-vs-manual boundaries consistent with the rest of the repo.
  The root and plugin Cursor manifests should be generated or validated by the
  same scripts that manage the other host surfaces.
- If Cursor's manifest format or install mechanics have changed since removal,
  document that clearly in the PR and update this plan after implementation so
  future contributors have the corrected shape.
