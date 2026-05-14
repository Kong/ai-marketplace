# Linked Service and Enforcement

Use this file when Portal-side configuration seems complete but runtime auth is
not being enforced as intended.

## Core Rule

Application auth only works as intended when the API is linked to the correct
Gateway Service and the strategy can actually be enforced on that path.

## Inspect In Order

- is the API linked to a Gateway Service at all
- is it the right service
- is the publication carrying the intended auth strategy
- is the Gateway-side auth configuration present on the linked path
- is the issue portal-side workflow or runtime Gateway-side enforcement

## Common Misreads

| Symptom | Better interpretation |
|---|---|
| Publication looks correct but calls still bypass auth | linked service or enforcement path issue |
| Strategy exists but no runtime effect | wrong service linkage or wrong publication boundary |
| Credentials were issued but requests still fail | likely Gateway-side enforcement or credential usage mismatch |

## What To Prove

- the exact linked service that the publication targets
- whether the auth strategy is attached to the intended publication
- whether the next owner is still Portal app-auth work or a Gateway config
  skill

## What To Return

Return:

- whether the linked service path is complete
- whether the issue is portal/workflow state or Gateway-side enforcement
- which exact linkage or enforcement assumption is wrong
- whether a tool skill or gateway skill should take over
