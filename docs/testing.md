# Testing

This repo favors lightweight checks over tool-driven install automation.

## Prerequisites

Start with the contributor bootstrap:

```bash
mise trust
mise install
mise run preflight
mise run deps
mise run hooks:install
```

Baseline local tools:

- `mise`
- `uv`
- `git`

`mise run preflight` checks the repo's baseline tools and can also check
optional flows:

- `mise run preflight -- publish` for `gh skill publish --dry-run`
- `mise run preflight -- shared-installers` for `npx skills` and `gh skill`
- `mise run preflight -- all` for a full local tool sweep

## Default Workflow

1. Run `mise run preflight`.
2. Run `mise run deps`.
3. Run `mise run hooks:install` once per checkout.
4. Run `mise run lint`.
5. Run `gh skill publish --dry-run` when you change skill metadata or prepare a release, or use `mise run ci` to include it in the standard CI path.
6. If you changed install docs, plugin manifests, or MCP config surfaces, manually verify only the affected tools.
7. Use a scratch project or disposable user profile when a tool writes local state.

Use the smallest path that covers the change. Most edits do not require every
check.

`mise run lint` covers more than generated-file drift. It is also the repo's
default authoring guardrail for:

- scaffold placeholders
- `SKILL.md` length
- description budget
- high-similarity trigger overlap between skills

The checked-in `pre-commit` and `pre-push` hooks both run `mise run lint`, but
they only apply after `mise run hooks:install`. CI remains the enforcement path
for pull requests and pushes to `main`.

If a spot check exercises the shared MCP configuration, export `KONNECT_TOKEN`
or use the host tool's secure settings flow before you test it.

The shipped shared-skill payload lives under `plugins/kong-konnect/skills/`,
so install and publish checks should continue to reflect that source tree.

Run the repo tasks through `mise run ...`, not bare `uv ...`, when you want the
checked-in repo defaults. The `mise` config pins `uv` to Python `3.12` and
keeps the uv cache and managed Python installs under `.tmp/` instead of falling
back to user-profile locations.

## Shared Skill Installers

### `npx skills`

- Install path: [docs/install/other-tools.md](./install/other-tools.md)
- Prerequisite: `node` and `npx`
- Command: `npx skills add kong/ai-marketplace`
- Expected result: install completes without errors and the `gateway-plugin-datakit` skill is available in the target host
- Quick prompt: `When should you use the gateway-plugin-datakit skill?`
- Cleanup: remove the installed skill from the scratch project or discard the scratch project

### `gh skill`

- Install path: [docs/install/other-tools.md](./install/other-tools.md)
- Prerequisite: GitHub CLI `v2.90.0+`
- Note: `gh skill` is in public preview
- Command: `gh skill install kong/ai-marketplace`
- Single-skill command: `gh skill install kong/ai-marketplace gateway-plugin-datakit`
- Expected result: install completes without errors and the `gateway-plugin-datakit` skill is available in the target host
- Quick prompt: `When should you use the gateway-plugin-datakit skill?`
- Cleanup: remove the installed skill from the target host or discard the scratch profile

## GitHub Skill Publish Dry Run

- Command: `gh skill publish --dry-run`
- Use when: skill frontmatter changes, you add a new skill, or you are preparing a release
- Expected result: the repo validates against the Agent Skills specification and GitHub's publish checks without publishing anything
- Notes: this catches issues your local validator may not model, such as recommended frontmatter fields and repository publish settings

## Security Notes

- Prefer `gh skill preview` before installing from GitHub.
- Use scratch projects or disposable profiles when a host writes local plugin or extension state.
- Store `KONNECT_TOKEN` in the host tool's secure settings flow when available.

## Tool Spot Checks

### Claude Code

- Install path: [docs/install/claude-code.md](./install/claude-code.md)
- Verify after install: `kong-konnect` appears as installed and `gateway-plugin-datakit` is available in a fresh session
- MCP check when using the plugin path: confirm `kong-konnect` is configured
- Quick prompt: `What Kong-specific skills are available in this environment?`
- Cleanup: uninstall the plugin or discard the scratch profile

### Cursor

- Install path: [docs/install/cursor.md](./install/cursor.md)
- Local plugin path: `~/.cursor/plugins/local/kong-konnect/`
- Use a copied directory for the local plugin smoke test; do not rely on a symlinked plugin directory
- Verify after install: `kong-konnect` appears as installed and `gateway-plugin-datakit` is available in a fresh session
- MCP check when using the plugin path: confirm `kong-konnect` is configured from `plugins/kong-konnect/mcp.json`
- Quick prompt: `What Kong-specific skills are available in this environment?`
- Cleanup: remove `~/.cursor/plugins/local/kong-konnect/` or discard the scratch profile

## When To Stop

You do not need to manually verify every tool for every change.

- Skill text only: `mise run lint` is usually enough.
- Tool-specific manifest or install doc: verify only that tool.
- Shared MCP config changes: verify one plugin-style path and one skill-plus-MCP path.
- Release prep: run `mise run lint` and spot-check the tools affected by the release.
- Release prep: also run `mise run ci` or `gh skill publish --dry-run`.
