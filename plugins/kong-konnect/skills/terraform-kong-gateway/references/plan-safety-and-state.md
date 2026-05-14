# Plan Safety and State

Use this file when the main issue is how to inspect Terraform impact safely on
a live self-managed Gateway.

## Core Rule

Prefer understanding plan and state impact before `apply`, especially when the
Gateway already has live resources that may not all be tracked.

## Safety Defaults

- prefer `terraform plan` before `terraform apply`
- confirm workspace/environment selection explicitly
- confirm import needs before assuming a recreate is acceptable
- keep the change narrow when the live Admin API surface is shared

## Common Risks

| Risk | Why it matters |
|---|---|
| Recreating an existing route/plugin/service | avoidable identifier churn and behavior disruption |
| Wrong workspace or endpoint | plan touches the wrong Gateway surface |
| Broad refactor during narrow fix | state confusion and noisy review |

## What To Return

Return:

- the safest next Terraform step
- the main state or workspace boundary to verify
- whether the task should stop at HCL authoring or proceed to execution
