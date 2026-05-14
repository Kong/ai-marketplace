# Module Boundaries

Use this file when the main problem is where a Konnect resource belongs in an
existing Terraform repository.

## Core Rule

Match the repo's current ownership model before adding new files. The right
resource in the wrong module still creates drift and review confusion.

## Inspection Order

1. Identify whether the repo partitions Konnect by environment, team, control
   plane, product surface, or a mixed infra boundary.
2. Find the module or root that already owns the nearest related Konnect
   resources.
3. Prefer the smallest edit inside that boundary before inventing a new module
   or directory.
4. Only propose broader refactors when the current boundary clearly blocks the
   requested Konnect change.

## Boundary Questions

Ask:

- is the repo split by environment, team, control plane, or product surface
- are platform resources and Gateway entities already separated
- does one module own publication/portal resources while another owns gateway
  runtime config
- does the change belong in an existing module even if the naming is imperfect

## Common Patterns

| Pattern | Implication |
|---|---|
| Split by environment | keep new resources in the environment-owned module path |
| Split by product surface | keep APIs/portals/teams separate from gateway runtime where the repo already does so |
| Monolithic root module | prefer narrow edits over opportunistic refactors |
| Mixed Konnect and cloud infra | keep Kong-specific boundaries understandable inside the broader infra repo |

## Proof Targets

Before you settle on a module path, be able to explain:

- why this boundary matches the repo's existing ownership model
- which nearby modules were considered and rejected
- whether any follow-up refactor is optional rather than required for the
  current task

## Return Shape

Return:

- which module or file should own the resource
- why that boundary matches the existing repo
- whether a follow-up refactor is optional instead of required for this task
