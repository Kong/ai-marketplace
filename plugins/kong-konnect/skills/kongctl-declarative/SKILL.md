---
name: kongctl-declarative
description: "Use for `kongctl`-managed Konnect declarative repos: author YAML, model APIs from OpenAPI, and run plan/diff/apply/sync/delete/adopt workflows or CI/CD. Do not use for read-only inspection, exact `get` syntax, or non-`kongctl` toolchains."
license: MIT
metadata:
  product: kongctl
  category: declarative
  tags:
    - kongctl
    - konnect
    - apiops
---

# kongctl declarative workflows

## Goal

Author, update, review, and execute `kongctl` declarative configuration for
Konnect without drifting into read-only query work or a different declarative
toolchain.

## Tool Positioning

- Use this skill when the repository already manages Konnect resources through
  `kongctl` YAML, `_defaults.kongctl`, or `kongctl` plan/apply workflows, or
  when the user explicitly asks for `kongctl`.
- Use the shared `kong-konnect` MCP server first when the task depends on live
  Konnect state and MCP is available.
- Use `kongctl-query` for read-only inspection, exact `get` syntax, output
  shaping, or CLI-shaped proof that should not mutate state.
- Preserve the repository's existing declarative toolchain. Do not convert
  `decK` or Terraform repositories to `kongctl` unless the user explicitly asks.
- Choose execution style from user intent:
  - User-run mode: explain the path and give commands.
  - Agent-run mode: execute the commands and report results.

## References To Load

Load only the branch that matches the task:

- `references/commands.md`
  - Load for command selection, saved-plan versus inline execution, adopt/dump
    command shape, output mode behavior, and guardrail flags.
- `references/resources.md`
  - Load for ownership layout, `_defaults`, parent versus child metadata,
    `!file`, `!ref`, and schema discovery.
- `references/apiops-openapi.md`
  - Load when the task generates or updates `apis` resources from OpenAPI.
- `references/cicd-github-actions.md`
  - Load for GitHub Actions validation or deployment workflows.
- `references/troubleshooting.md`
  - Load when preview or execution fails, or when drift and namespace behavior
    are unclear.

This skill must stay portable across repositories. Do not assume the upstream
`kongctl` repo layout or a local `docs/` tree.

## Validation Contract

### Preflight

Before editing manifests or proposing execution:

- Confirm the repository already owns the target Konnect slice through
  `kongctl` rather than `decK` or Terraform.
- Confirm the CLI is available and authentication works with a small read
  command such as `kongctl get organization -o json`.
- Confirm namespace, profile, file scope, and whether `!file` usage will
  require `--base-dir`.
- If exact syntax is uncertain, check local help instead of guessing.

### Preview

Use the smallest preview surface that matches intent:

- review or CI path: generate a saved plan or a scoped diff artifact
- immediate execution path: run a scoped `diff` or inline `--dry-run`
- inspect unexpected deletes, wrong namespace ownership, unresolved `!ref`
  values, and `!file` boundary issues before mutation

### Execute

- Mutate live state only when the user explicitly asked for it.
- State the intended effect in plain language before any mutating command.
- Keep execution aligned with the previewed path instead of switching tools or
  widening scope mid-task.

### Prove

After a requested mutation:

- rerun the matching preview path and expect no remaining intended drift
- confirm the exact namespace and resource slice now reflect the intended state
- for adopt or dump workflows, prove the integrated declarative config is clean
  instead of stopping at a successful command

## Operating Rules

- If live Konnect state matters and MCP is unavailable, say so early and
  continue with `kongctl`-based inspection as the fallback.
- Prefer explicit namespace, profile, and output flags when environment or
  profile defaults could obscure behavior.
- Treat `sync` and `delete` as destructive. Preview them first unless the user
  explicitly asks for direct execution.
- Use `adopt` only for existing unmanaged parent resources. `adopt` labels the
  resource for namespace ownership; it does not rewrite the resource fields.
- Keep OpenAPI files in their existing repository locations. Prefer `!file`
  extraction and `!ref` links over copied literals or hard-coded UUIDs.
- Do not place non-resource YAML inside a `--recursive` declarative tree. If a
  directory mixes resource YAML with specs or docs, target specific files
  instead of the whole tree.
- When scope is unclear, inspect existing manifests or live state. Do not
  invent a default starter bundle of Konnect resources.
- If a required `kongctl` command appears blocked by the agent sandbox rather
  than by Konnect or the CLI, request an unsandboxed retry before diagnosing
  the command itself as broken.

## Workflow

1. Identify the owned declarative root and target file scope.
   If the path is not provided, search for existing `_defaults.kongctl`,
   `apis`, `portals`, `control_planes`, or related `kongctl` resource keys
   instead of assuming `konnect/resources/`.
2. Classify the branch before editing:
   - general manifest authoring or repair: load `references/resources.md`
   - OpenAPI-driven API modeling: also load `references/apiops-openapi.md`
   - adopt or dump integration: also load `references/commands.md`
   - CI/CD workflow work: also load `references/cicd-github-actions.md`
3. Update manifests in place, preserving the repository's file layout,
   ownership boundaries, and existing reference patterns.
4. Run the validation gates in order: Preflight, Preview, Execute if requested,
   then Prove.
5. Report the files changed, the exact command path used, and the proof of the
   resulting state or remaining drift.

## Validation Checklist

Before answering, verify that you can state:

- why `kongctl` is the correct implementation owner for this request
- which namespace, profile, and file scope the change owns
- which preview path proves the change safely
- whether the user asked only for authoring or for live mutation
- how post-change proof will confirm the exact resource slice
- whether `kongctl-query` should provide read-only follow-up proof

## Handoffs

- Hand off to `kongctl-query` when the real task is read-only inspection, auth
  checking, exact `get` syntax, or output formatting.
- Hand off to `deck-gateway`, `terraform-konnect`, or
  `terraform-kong-gateway` when the repository already uses those tools for the
  target resources.
- Hand off to the relevant Konnect domain skill, or to
  `konnect-platform-router` when the workflow owner is unclear, if the user
  first needs diagnosis or classification rather than declarative
  implementation.
