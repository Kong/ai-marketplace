# Registration and Approval Flows

Use this file when the strategy is plausible but developers still cannot get
through the self-service workflow.

## Core Rule

Treat "published but unusable" as a workflow-state problem until proven
otherwise.

## Check In Order

- whether the application exists for the intended developer or team
- whether a registration exists for the API/publication in question
- whether approval is required at the developer or application layer
- whether credentials were actually issued after approval
- whether RBAC or team membership blocks consumption after registration

## Common Flow States

| State | Meaning |
|---|---|
| no registration | the developer never reached the API-specific app-registration step |
| pending | approval or manual action is still required |
| approved | the next blocker is usually credential issuance or runtime enforcement |
| revoked/rejected | the workflow failed by policy or admin action |

## Useful Distinctions

- developer approval versus application approval
- registration state versus credential issuance
- RBAC/team gating versus auth-strategy mismatch

## What To Prove

- which object is pending, rejected, revoked, or missing
- whether policy requires a manual approver or a broader role assignment
- whether the workflow is blocked before credentials exist or after they exist

## What To Return

Return:

- which workflow state is blocking consumption
- whether the problem is approvals, registration, or RBAC/team gating
- which exact state transition or approval action is needed next
- whether another skill now owns the next step
