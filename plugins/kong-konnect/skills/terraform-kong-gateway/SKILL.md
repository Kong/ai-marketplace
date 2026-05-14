---
name: terraform-kong-gateway
description: Use when editing or reviewing Terraform that manages self-managed Kong Gateway Admin API entities with the official `kong/kong-gateway` provider; not for Konnect resources, decK-native Gateway GitOps, or gateway troubleshooting before tool choice.
license: MIT
metadata:
  product: terraform
  category: declarative-gateway
  tags:
    - kong
    - gateway
    - terraform
    - hcl
    - declarative
---

# Terraform for self-managed Kong Gateway

## Goal

Author or revise Terraform-managed self-managed Kong Gateway entities while
preserving the repository's current module layout, provider model, and state
ownership.

Use this skill once Terraform is already the right tool for Admin API-backed
self-managed Gateway work. Do not use it as the default for Konnect platform
resources or for design and troubleshooting work that should happen before
tool-specific HCL changes.

## Tool Positioning

- Use this skill when the repository already uses Terraform for self-managed
  Gateway resources or the user explicitly asks for Terraform.
- This skill owns HCL authoring, import-first adoption, plan review, and
  Terraform-native proof after the Terraform path is chosen.
- Preserve existing Terraform modules, variables, backend settings, and
  workspaces.
- Use the official `kong/kong-gateway` provider for self-managed Gateway
  resources reachable through the Admin API.
- Hand off to `deck-gateway` when the user wants file-based Gateway GitOps,
  dump/diff workflows, or a `decK`-native repository.
- Hand off to `terraform-konnect` when the target resources actually belong to
  Konnect rather than a self-managed Admin API surface.
- Hand off to Gateway or product-specific diagnosis skills when the harder
  problem is gateway health, plugin behavior, or design intent rather than HCL
  ownership.

## References To Load

Load only the reference file that matches the active branch:

- `references/provider-and-import.md`
  - Load when provider inputs, existing live resources, or import-first
    handling is the main question.
- `references/entity-patterns.md`
  - Load when the user is deciding how self-managed Gateway entities should be
    grouped or modeled in the existing HCL layout.
- `references/plan-safety-and-state.md`
  - Load when the main issue is how to inspect plan impact safely before
    applying to a live Admin API surface.
- `references/provider-schema-debugging.md`
  - Load when nested resource shape is unclear, validation reports
    object-vs-string or similar type mismatches, or provider behavior does not
    line up cleanly with docs or example HCL.

## Validation Contract

### Preflight

Before writing HCL or proposing a plan:

- Confirm Terraform is installed and runnable.
- Confirm the target Admin API endpoint and auth method already exist.
- Inspect provider blocks, backend settings, workspace selection, and module
  conventions before adding HCL.
- Keep Admin API tokens and secrets out of committed files.
- Confirm whether existing live Gateway entities must be imported before
  planning.
- Use `terraform providers schema -json` as the default source of truth when
  nested resource shape is unclear before guessing from docs or examples

### Preview

Use Terraform's native preview surface before apply:

- run the repo's normal format and validation checks when they exist
- run `terraform validate`
- run `terraform plan`
- import first when a live Service, Route, plugin, or other entity already
  exists and should be brought under state
- check the exact resource addresses, environment, and create-update-destroy
  shape before considering apply

### Execute

- Describe the intended effect before any mutating command.
- Run `terraform apply` only when the user explicitly asked for live mutation.
- Keep apply scoped to the same directory, workspace, and variable inputs that
  were previewed.

### Prove

After a requested apply:

- confirm the intended resource addresses are now present in Terraform state
- inspect key addresses with `terraform state show <address>` or the repo's
  normal output surface
- when practical, run a follow-up `terraform plan` and expect no remaining
  intended changes for the touched slice
- do not treat apply success by itself as proof that the live Gateway matches
  intent

## Operating Rules

- Preserve existing HCL layout, resource grouping, and variable usage.
- Use `terraform providers schema -json` as the default source of truth for
  unknown nested resource shape before guessing HCL from docs or examples.
- Prefer `terraform plan` before `terraform apply` unless the user explicitly
  asks for direct execution.
- If `terraform providers schema -json`, provider startup, `terraform validate`,
  or `terraform plan` fails in a way that suggests sandbox interference,
  retry outside the sandbox with approval before treating it as a provider,
  auth, or schema problem.
- Prefer importing existing Gateway resources over recreating them.
- Keep the scope limited to the Gateway entities requested by the user.
- Do not mix self-managed Gateway assumptions into Konnect tasks.
- When the repository already uses `decK`, do not switch it to Terraform unless
  migration is the task.
- Do not treat a successful `terraform apply` as proof by itself; follow with
  state or plan-based verification of the touched addresses.

## Workflow

### 1. Classify the ownership boundary

Establish whether the task is actually:

- self-managed Gateway Admin API configuration that this skill should own
- Konnect platform configuration that belongs to `terraform-konnect`
- a `decK`-native Gateway workflow that belongs to `deck-gateway`
- gateway behavior or design diagnosis that should be resolved before
  Terraform-specific implementation

Do not write HCL until that split is clear.

### 2. Inspect the Terraform shape

Identify:

- root and child modules
- provider aliases
- backend or remote state configuration
- variable files and secrets conventions
- existing ownership boundaries for services, routes, plugins, consumers, or
  certificates

### 3. Confirm the target Gateway surface

Pin down:

- which Admin API endpoint is in scope
- which Gateway entities are being managed
- whether the task is create, update, import, or drift correction

Load `references/provider-and-import.md` when provider inputs, import-first
adoption, or Admin API targeting is the real uncertainty.

### 4. Choose the narrow implementation path

Default paths:

- new managed entity: add HCL in the existing module layout
- existing unmanaged entity: import first, then normalize the HCL
- large-scale file-based Gateway GitOps: consider `deck-gateway` instead of
  forcing Terraform if that matches the user's intent better

Load `references/entity-patterns.md` when repo ownership shape is the harder
question. Load `references/provider-schema-debugging.md` when resource shape is
the main uncertainty.

### 5. Author HCL with minimal churn

- reuse existing variables and locals
- keep names and identifiers stable
- avoid broad refactors while making a narrow Gateway change
- add outputs only when another module or pipeline consumes them
- inspect `terraform providers schema -json` before guessing nested block or
  attribute structure

### 6. Preview before any apply path

- run the repo's normal format and validation checks when they exist
- run `terraform validate`
- run `terraform plan`
- import first if the plan would recreate an entity that already exists live
- inspect whether the plan touches only the intended addresses and workspace

Load `references/plan-safety-and-state.md` when the operator needs a safer
inspection-first path before touching a live Gateway.

### 7. Execute only when requested

- Describe the intended live effect before presenting or running
  `terraform apply`.
- Use the same directory, workspace, and variable inputs that produced the
  reviewed plan.
- Run `terraform apply` only when the user explicitly asked to mutate live
  Gateway state.

### 8. Prove the result with Terraform-native checks

After any requested `terraform apply`:

- confirm the touched resource addresses now appear in `terraform state list`
- inspect key addresses with `terraform state show <address>` or the repo's
  normal outputs
- when practical, run a follow-up `terraform plan` and expect no remaining
  intended changes for the affected slice
- call out remaining drift or ownership surprises instead of hiding them behind
  apply success

### 9. Report config and state impact

State:

- which files or modules changed
- which Gateway entities are affected
- whether import is required
- whether the next step is `plan`, `apply`, or external verification

## Kong-Specific Gotchas

- Terraform state is not a substitute for checking what the live Gateway
  already has; import matters.
- Recreating existing plugins, services, or routes can cause avoidable
  identifier churn.
- Provider docs and Gateway examples can describe intent, but the Terraform
  provider schema is the authoritative shape for nested HCL.
- Some teams use Terraform for infrastructure but `decK` for Gateway entities;
  preserve the established split if it already exists.
- A self-managed Admin API workflow is not the same as a Konnect control plane
  workflow even if the resource names look similar.

## Validation Checklist

Before answering, verify that you can state:

- why Terraform is the right tool for this repository or request
- which Admin API-backed Gateway surface is in scope
- which module or file owns the resources
- whether import is required
- which preview commands prove the intended change before mutation
- whether provider schema inspection is needed before guessing nested HCL shape
- whether the task stops at HCL authoring or continues to `plan/apply`
- how the touched resource addresses will be proved after apply
- whether `deck-gateway` would be a better fit for the user's intent

## Handoffs

- Use `deck-gateway` when the user wants `decK`-native Gateway GitOps or live
  Gateway export/diff workflows.
- Use `terraform-konnect` when the resources actually belong to Konnect.
- Use Gateway or product-specific domain skills when the user first needs
  troubleshooting or design help rather than HCL authoring.
