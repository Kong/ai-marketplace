---
name: kongctl-query
description: "Use when the user wants read-only `kongctl` queries against Konnect: prove auth or scope, discover the right `get` path, list or fetch resources, or shape JSON/YAML output. Do not use for `kongctl` plan/apply/sync or declarative authoring."
license: MIT
metadata:
  product: kongctl
  category: query
  tags:
    - kongctl
    - konnect
    - read-only
---

# kongctl-query

## Goal

Use read-only `kongctl` commands to inspect live Konnect state and return the
smallest command and result slice that actually proves the answer.

## Tool Positioning

- Use this skill when the user explicitly wants `kongctl`, CLI-shaped proof, or
  read-only verification after another workflow changed Konnect state.
- If the session already has the shared `kong-konnect` MCP server and the user
  needs live inspection more than exact CLI syntax, suggest MCP first and keep
  `kongctl` as the fallback proof path.
- Do not use this skill for declarative YAML authoring, `kongctl`
  `plan`/`apply`/`sync`, CI/CD scaffolding, or repository refactors.
- Preserve the repository's existing delivery toolchain. This skill only owns
  read paths and post-change verification commands.

## References To Load

Load only the branch-specific reference that matches the active problem:

- `references/resource-discovery.md`
  - Load when the main question is which `kongctl get` resource, parent, or
    child path should be queried.
- `references/output-shaping.md`
  - Load when the main question is output mode, `--jq`, summarization shape, or
    formatting surprises from profile or environment defaults.
- `references/auth-and-scope-checks.md`
  - Load when auth, profile, region, org scope, or empty results may be the
    real issue.

## Validation Contract

### Preflight

- Confirm the CLI is installed and runnable: `kongctl version`.
- Prefer `kongctl login` for interactive sessions. Use PAT or SPAT environment
  variables only when the session is non-interactive.
- Never echo, log, or commit token values.
- If the user's org, region, or profile context matters, prove that context
  with one org-scoped read such as `kongctl get organization -o json` before
  reasoning about a missing resource.

### Preview

- Choose the smallest read-only command that proves the answer:
  - `kongctl help` or `kongctl get <resource> --help` for command shape
  - `kongctl get <resource> -o json` for list proof
  - `kongctl get <resource> "<name-or-id>" -o json` for one-object proof
  - parent-child reads only after the parent boundary is confirmed
- Use explicit `-o json` unless the user specifically wants YAML.
- State the expected slice before relying on filtered or nested output.

### Execute

- Do not mutate. This skill never runs `apply`, `sync`, `adopt`, `patch`,
  `create`, or `delete`.
- When another workflow changes state, use this skill only to supply the exact
  read-only verification command that should be rerun afterward.

### Prove

- Rerun the exact `get` command that shows the affected live object now exists
  or now exposes the intended fields.
- Confirm the exact resource slice touched instead of treating org-level auth
  success as proof of the resulting object.
- Distinguish "empty result" from auth, profile, or scope failure.

## Operating Rules

- Prefer live CLI help over guessing resource names or child-resource forms.
- Use explicit output flags on reads so profile or environment defaults do not
  silently change the proof.
- Keep summaries tight: return only the fields needed to answer the question or
  prove the post-change state.
- If the request turns into product diagnosis rather than query-path discovery
  or proof, hand off after proving the relevant live slice.

## Workflow

1. Classify the request as resource discovery, auth/scope diagnosis, output
   shaping, or post-change verification.
2. Run preflight checks and prove org/profile scope before debugging resource
   paths when the context could be wrong.
3. Discover the smallest valid help or `get` path instead of assuming the
   resource family.
4. Run the narrowest read that proves the answer, defaulting to JSON unless
   the user explicitly wants YAML.
5. Summarize the proof with the minimum useful fields and include the exact
   verification command when another workflow owns the mutation.
6. Load the matching reference only when the branch-specific detail is needed.

## Validation Checklist

Before answering, verify that you can state:

- which command proved auth or scope in the intended Konnect context
- which exact `help` or `get` command is the smallest safe proof
- which output mode and result slice were used
- how an empty result was distinguished from a context or access problem
- whether this request stays in `kongctl-query` or should hand off

## Handoffs

- Hand off to `kongctl-declarative` when the user wants `kongctl`
  `plan`/`apply`/`sync`, declarative YAML authoring, or reconciliation.
- Hand off to `deck-gateway`, `terraform-konnect`, or
  `terraform-kong-gateway` when the repository already uses those tools for
  mutation.
- Hand off to the relevant Konnect domain skill when the question shifts from
  "how do I prove this with a read query?" to product-specific diagnosis or
  design.

## Online Documentation

- kongctl docs: https://developer.konghq.com/kongctl/
