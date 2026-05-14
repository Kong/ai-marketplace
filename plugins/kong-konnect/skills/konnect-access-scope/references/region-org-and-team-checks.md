# Region, Org, and Team Checks

Use this file when the access symptom may really be the wrong Konnect slice.

## Core Rule

Prove the caller is pointed at the intended region and organization before
reasoning about roles or permissions.

## Quick Checks

- `kongctl get organization -o json`
- `kongctl get me -o json`
- inspect the active `kongctl` profile and any `KONGCTL_*` endpoint overrides
- compare the expected team, control plane, or portal slice with what the
  caller is actually querying

## Common Misroutes

| Symptom | Likely interpretation |
|---|---|
| "Resource does not exist" | wrong region or org |
| "My teammate can see it, I cannot" | wrong org/team context or real permission difference |
| Similar control planes appear missing | wrong environment or ownership slice |

## Decision Rules

- If auth works but the organization or user identity is not the expected one,
  stop on endpoint or profile correction before analyzing permissions.
- If the resource exists in the organization but only some teams can see it,
  keep team scope and resource-scoped roles in play.
- If multiple near-identical resources exist, verify ownership slice and region
  before calling the symptom a permission failure.

## What To Return

Return:

- whether the caller is in the right region and org
- whether team or environment slicing explains the symptom
- whether permission analysis should continue after that
