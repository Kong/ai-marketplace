# Provider Selection

Use this file when the main question is whether to use `kong/konnect` or
`kong/konnect-beta`.

## Default Rule

Prefer `kong/konnect`. Treat `kong/konnect-beta` as an explicit exception for
beta-only coverage the user actually needs.

## Inspection Order

1. Inspect the existing provider blocks, aliases, and version constraints.
2. Identify whether the target Konnect resource is already managed by the
   supported provider in this repo.
3. Treat the official provider as sufficient unless the task is blocked by a
   missing resource, attribute, or behavior.
4. If beta coverage is truly required, keep the exception as narrow as the repo
   layout allows.

## Decision Rules

- If the repository already standardizes on `kong/konnect`, keep it unless the
  task is blocked by missing coverage.
- If the repo already uses both providers, preserve the existing alias and
  module pattern rather than collapsing them casually.
- If only one resource family needs beta coverage, avoid broad repo-wide
  provider churn just to solve one module.
- Keep the repo's existing secure auth path and endpoint handling; provider
  choice is not a reason to introduce checked-in credentials or duplicate
  secret wiring.

## Proof Targets

Before recommending `kong/konnect-beta`, be able to point to:

- the specific missing coverage or blocked behavior
- the narrowest module or provider alias that needs the exception
- whether the rest of the repo can stay on `kong/konnect`

## Return Shape

Return:

- which provider should own the change
- why the supported provider is sufficient or insufficient
- whether the exception affects only one module or the broader repo shape
