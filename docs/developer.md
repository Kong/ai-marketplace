# Developer Guide

This repo keeps authoring simple:

1. choose the owning plugin under `plugins/`
2. add or update a skill under that plugin's `skills/`
3. sync generated metadata
4. run repo validation
5. manually spot-check only the install surfaces you changed
6. prepare release-versioned manifests in git, then publish from GitHub Actions

This repo is optimized for contributors maintaining the shared source package.
Consumers generally see the synced plugin manifests or installed skill content
through their host tool rather than this working tree.

The GitHub Actions workflow is the only publishing path for public releases.
Local tooling prepares and validates release content, but it does not tag or
publish.

For the full release preparation and trigger sequence, see
[docs/release.md](release.md).

## Prerequisites

Install `mise` first:

- `mise`: https://mise.jdx.dev/
- `uv`: https://docs.astral.sh/uv/

Then bootstrap the repo:

```bash
mise trust
mise install
mise run preflight
mise run deps
mise run hooks:install
```

`mise install` provisions the repo-managed Python toolchain from
[mise.toml](../mise.toml). `uv` is still required separately. Additional tools
are only needed for the flows that use them:

- `gh` for `gh skill publish --dry-run`
- `node` and `npx` for shared-installer verification

When a script-backed task takes arguments, prefer `mise run <task> -- --help` to see the
expected positional arguments and flags.

Install hooks during bootstrap unless you have a reason not to. This repo uses
repo-local `pre-commit` and `pre-push` hooks as a convenience layer that runs
`mise run lint` before changes leave your machine.

## Typical Loops

Run this once per checkout before you start editing:

```bash
mise run hooks:install
```

Use the smallest workflow that matches the change:

- Skill text only: `mise run preflight`, `mise run lint`
- New skill or frontmatter change: `mise run preflight`, `mise run lint`, and `gh skill publish --dry-run`
- Packaging or shared MCP/install surface change: `mise run preflight`, `mise run lint`, and the affected manual spot checks
- Release prep: `mise run preflight`, `mise run ci`

For local guardrails, install the repo hooks once:

```bash
mise run hooks:install
```

That enables the checked-in `pre-commit` and `pre-push` hooks, both of which
run `mise run lint`. Treat hooks as convenience, not enforcement. CI is still
the required repo gate.

## Add A Plugin

Use a separate plugin package when the product surface, ownership boundary, or
install identity is meaningfully different.

Scaffold a new plugin package with:

```bash
mise run plugin:new -- kong-mesh
```

If the plugin also needs the shared `kong-konnect` MCP reference shape:

```bash
mise run plugin:new -- kong-mesh --with-mcp
```

That creates:

- `plugins/<plugin-name>/skills/`
- `plugins/<plugin-name>/.claude-plugin/plugin.json`
- optional `plugins/<plugin-name>/mcp.json`

Root marketplace manifests are generated from plugin discovery, so you do not
hand-edit marketplace entries when adding a new package.

## Add A Skill

Contributors will approach skill authoring in different ways:

- some will read this guide and edit files directly
- some will ask an agent to help immediately
- some will use the built-in generic skill creator first and then refine the
  result

All of those paths are fine. For repo-specific authoring guidance:

- use [AGENTS.md](../AGENTS.md) as the canonical policy
- use the shipped `kong-skill-authoring` skill when you want an agent to walk
  the overlap, layering, and trigger-boundary decisions progressively
- use the host tool's built-in generic skill creator only as a helper, then
  review the result against `AGENTS.md`

Scaffold the boilerplate with one command:

```bash
mise run skill:new -- your-skill-name
```

That defaults to the `kong-konnect` plugin. To target a different plugin:

```bash
mise run skill:new -- kong-mesh your-skill-name
```

For task-level help:

```bash
mise run skill:new -- --help
```

That creates:

- `plugins/<plugin-name>/skills/<skill-name>/SKILL.md`

Start with:

```md
---
name: your-skill-name
description: One-line description used for discovery and matching.
license: MIT
metadata:
  product: product-name
  category: workflow-category
  tags:
    - kong
    - example-tag
---
```

Optional companion directories are supported:

- `plugins/<plugin-name>/skills/<skill-name>/references/`
- `plugins/<plugin-name>/skills/<skill-name>/assets/`
- `plugins/<plugin-name>/skills/<skill-name>/scripts/`

Keep `SKILL.md` as the only file at the skill root. Companion content should
stay lightweight, non-hidden, non-executable, and easy to review. Set
`license: MIT` for skills in this repo unless you have an explicit reason to
ship different terms.

This repo does not currently allow per-skill MCP dependency declarations. Keep
shared MCP wiring at the plugin level for v1.

Before you scaffold a new skill, check [docs/skills.md](skills.md) and the
existing plugin-local `skills/` directories for overlap. Prefer extending an
existing skill unless the trigger boundary or ownership boundary is clearly
different.

### Description Budget

`description` is the primary trigger surface for implicit skill activation.
Keep it short, front-loaded, and specific.

- Put the main trigger words and boundary near the start.
- Keep most descriptions under roughly 260 characters.
- Prefer one clear trigger phrase over long lists of near-synonyms.
- If two descriptions start sounding similar, tighten the scope or merge the
  skills.

## Sync And Validate

```bash
mise install
mise run preflight
mise run deps
mise run skill:new -- your-skill-name
mise run gen
mise run lint
gh skill publish --dry-run
```

If `mise` says the repo is not trusted:

```bash
mise trust
```

If you have not already enabled the repo hooks, do that once as well:

```bash
mise run hooks:install
```

`mise run lint` is the main repo guardrail for authoring quality. It now
checks:

- generated metadata drift
- scaffold placeholders
- `SKILL.md` length
- description budget
- high-similarity trigger overlap between skills

## What Generate Updates

- the skill arrays in [`plugins/kong-konnect/.claude-plugin/plugin.json`](../plugins/kong-konnect/.claude-plugin/plugin.json)
- the Claude marketplace keywords in [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json)
- the generated skill inventory in [docs/skills.md](skills.md)
- the plugin-local MCP config in [`plugins/kong-konnect/mcp.json`](../plugins/kong-konnect/mcp.json)

## What Stays Manual

- explanatory docs
- marketplace positioning text
- harness-specific install prose
- decisions about whether a skill needs `references/`, `assets/`, or `scripts/`
- replacing scaffold placeholders with real Kong-specific content
- any rationale for exceptions to the default `license: MIT`
- judgment about whether two skills are still meaningfully distinct after an
  overlap warning

## Conventions

- canonical public repo: `https://github.com/kong/skills`
- canonical marketplace repo name: `kong-skills`
- first shipped plugin package: `kong-konnect`
- canonical MCP server name: `kong-konnect`
- auth variable: `KONNECT_TOKEN`
- keep shared behavior in `SKILL.md`
- keep harness-specific packaging out of skills

For authoring guidance on what makes a good skill, see [AGENTS.md](../AGENTS.md).

## Supported Tools

- Claude Code: https://code.claude.com/docs
- GitHub CLI `gh skill`: https://cli.github.com/
- `npx skills`: https://github.com/vercel-labs/skills

## Manual Verification

This repo intentionally keeps automated testing narrow.

- Keep CI on `mise run ci`.
- Install hooks so `mise run lint` also runs automatically on local commit and
  push.
- Use manual verification when you change install docs, plugin manifests, or
  MCP config surfaces.
- Prefer scratch projects and disposable user profiles over repo-managed
  install automation.
- Run `gh skill publish --dry-run` before release-oriented changes to catch
  Agent Skills spec drift and GitHub-side publishability issues.

## Security Notes

- Prefer `gh skill preview` before `gh skill install` when you are validating
  the public GitHub install path.
- Keep Konnect credentials in host-managed secure settings or environment
  variables, not in checked-in files.
- Treat startup or auto-update features as opt-in convenience, not the default
  recommendation.

See [docs/testing.md](testing.md) for the lightweight verification checklist
per supported tool.

## Release Preparation

Use:

```bash
mise run release:prepare -- 1.0.1
mise run preflight
mise run ci
```

To inspect the accepted release arguments:

```bash
mise run release:prepare -- --help
```

Commit the version bump, get it reviewed, and merge it to `main`.

For how the GitHub Actions release is triggered and what it does, see
[docs/release.md](release.md).
