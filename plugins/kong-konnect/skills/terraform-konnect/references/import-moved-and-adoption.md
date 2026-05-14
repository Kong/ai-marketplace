# Import, Moved, and Adoption

Use this file when Konnect resources already exist and the job is to bring them
under Terraform without unnecessary churn.

## Core Rule

Prefer importing or preserving existing addresses over recreating resources.
State continuity matters more than fast greenfield-looking HCL.

## Inspection Order

1. Prove the resource already exists live or under another Terraform address.
2. Check whether the repo already owns that Konnect slice in a different module
   or state path.
3. Choose import, `moved`, or generated HCL based on ownership continuity, not
   convenience.
4. Verify the next `terraform plan` shows adoption of the intended resource
   rather than a destroy-and-recreate path.

## Common Cases

| Situation | Preferred default |
|---|---|
| Resource exists in Konnect but not in state | import it |
| Resource moved between modules/addresses | preserve history with `moved` blocks where the repo already uses them |
| Gateway entities already exist in `decK` or live state | use `deck file kong2tf` as a starting point, then normalize |
| Repo only partially manages Konnect | import only the intended boundary, do not broaden casually |

## What To Check

- whether the resource already exists live
- whether the repo already tracks it under another module or address
- whether references to that resource would break if recreated
- whether a generated HCL starting point still needs cleanup to match repo
  conventions

## Proof Targets

Before treating adoption as complete, prove:

- the chosen Terraform address matches the intended owner
- imported or moved resources appear under the expected address in state
- the follow-up `terraform plan` no longer proposes unintended replacement

## Return Shape

Return:

- whether import is required
- whether address preservation or `moved` handling is needed
- whether generated HCL is only a starting point
