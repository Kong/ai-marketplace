# Reintroduce Codex Plugin Support

## Goal

Restore Codex repo installation and prepare the package used to request public
directory approval. Public listing is a later, separately approved step.
Reintroduction must restore the checked-in manifests, sync and validation
automation, release versioning, and the contributor docs that explain the
Codex-specific install path.

## Implementation Status (2026-10-06)

Codex repo installation and submission packaging are restored to seek directory
approval. Approval is not a prerequisite for preparing the ZIP or testing a
local marketplace; public listing still requires review and approval.

Verified against current OpenAI documentation:

- [Package your plugin](https://developers.openai.com/plugins/build/plugins):
  `.codex-plugin/plugin.json` remains supported. Repo catalogs live at
  `.agents/plugins/marketplace.json`; local source paths resolve from the repo
  root. Installation/authentication policy and category belong on each entry.
- [Submission format and fields](https://developers.openai.com/plugins/deploy/submission):
  the directory accepts the Codex format as well as Agent Plugins. Codex uses
  an author object, `skills` directory path or path array, and an MCP config
  file reference. Listing links use `interface.websiteURL`, `supportURL`,
  `privacyPolicyURL`, and `termsOfServiceURL`. Both icon fields are supplied;
  screenshots are optional. MCP must ship in the initial ZIP.
- [MCP review requirements](https://developers.openai.com/plugins/deploy/app-review):
  tool annotations and their justifications must match actual behavior;
  successful local packaging does not replace server and submission review.

Deltas from the original design below:

- Use `skills: "./skills/"` to include the full inventory, rather than an empty
  or per-skill array. The array form remains supported.
- Use `mcpServers: "./.mcp.json"`, a plugin-relative configuration file path,
  rather than `["kong-konnect"]`. The Codex companion `.mcp.json` is generated with the same HTTP configuration
  as `mcp.json`, without changing Claude or Cursor wiring. This uses the
  submission guide's filename and passes the local helper's path constraint.
  The helper predates the documented `interface.supportURL`; retain that
  field because the current submission reference requires a support URL.
- Use the publisher object from Claude metadata and preserve its product
  homepage and canonical repository URL, rather than forcing both to the repo.
- Use `Developer Tools` for the listing category, a short subtitle within the
  30-character limit, and curated human-readable capability labels within the 20-label limit.
  Keep capabilities in the manifest; lint checks their count and length.
- Keep the Codex manifest separate; no root Agent Plugins manifest is added.

The remaining sections preserve the restoration scope. Use the linked
checked-in manifests as the current format.

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
- `mcpServers` references the generated `.mcp.json` file when the plugin
  has MCP wiring
- manifest versions stay aligned with the other supported host manifests
- homepage and repository fields stay aligned with the canonical repo URL
- keywords stay derived from shipped skills; curated capability labels remain in the manifest

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
     - `skills` directory path
     - `keywords`
     - `interface.displayName`
     - `interface.shortDescription`
     - `interface.category`
     - `interface.capabilities`
   - if `--with-mcp` is set, wire `mcpServers` to the generated `.mcp.json` file

2. `scripts/check_repo.py`
   - restore `Plugin.codex_manifest`
   - require the Codex manifest during plugin discovery
   - restore `sync_codex_marketplace(...)`
   - restore `sync_codex_plugin(...)`
   - preserve curated capabilities and validate their listing limits
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
   - default interactive MCP connections to OAuth; reserve PAT/SPAT bearer
     authentication for CI and headless use
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

## Current Manifest Files

Use the checked-in files rather than copying a sample:

- [Codex repo marketplace](../../.agents/plugins/marketplace.json)
- [Kong Konnect Codex manifest](../../plugins/kong-konnect/.codex-plugin/plugin.json)
- [Codex MCP configuration](../../plugins/kong-konnect/.mcp.json)

`mise run gen` maintains the catalog and derived manifest fields. Listing
capabilities and `extensions.com.openai.review` are maintained in the manifest
and preserved by generation. Review cases require execution against the demo
organization before submission. The supplied demo recording URL is included as
`extensions.com.openai.review.demo_recording_url`, as specified in the
[submission field reference](https://developers.openai.com/plugins/deploy/submission).

## Implementation Sequence

1. Confirm current Codex schema expectations; prepare the submission to seek approval.
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
