---
name: konnect-app-auth
description: Use when Konnect Dev Portal APIs are published but blocked by application auth strategy, registration, approval, or app-credential flow issues; not for Portal sign-in/SSO or basic API publication.
license: MIT
metadata:
  product: konnect
  category: application-auth
  tags:
    - kong
    - konnect
    - dev-portal
    - authentication
    - application-registration
---

# Konnect application auth workflow

## Goal

Help an operator configure or troubleshoot how developers register applications,
receive credentials, and use APIs through Konnect Dev Portal and Konnect
Application Auth.

Own the application-auth branch only: strategy choice, application
registration, approvals, credentials, and the publication-to-enforcement path.
Do not keep Portal sign-in, SSO, or generic API publication diagnosis in this
skill after the surface is classified.

## Tool Selection

- Use the shared `kong-konnect` MCP server first for live inspection of portals,
  publications, application auth strategies, applications, registrations, and
  related approvals.
- Preserve the repository's chosen declarative toolchain when auth resources
  need to change: use `terraform-konnect` for HCL-managed resources and
  `kongctl-declarative` only when the surrounding repo already uses `kongctl`
  for this Konnect workflow.
- Use `deck-gateway` only when the real change is downstream Gateway-entity
  config rather than Portal app-auth configuration.
- If live Konnect state matters and `kong-konnect` MCP is not connected, say so
  early and continue with user-provided artifacts or repo context.
- If the primary issue is developer sign-in, SSO, or broad org/team access,
  classify that early and stop instead of debugging app credentials here.

## References To Load

Load only the reference file that matches the active branch:

- `references/auth-strategy-selection.md`
  - Load when choosing between key auth, self-managed OIDC, and DCR is the
    main decision.
- `references/registration-and-approval-flows.md`
  - Load when the strategy is plausible but self-service, approvals, or
    registration state still block developers.
- `references/linked-service-and-enforcement.md`
  - Load when the hard question is whether auth can actually be enforced on the
    linked Gateway Service path.

## Inspection Order

### 1. Classify the failing surface before choosing fixes

Clarify whether the problem is:

- developer sign-in or SSO into the Portal
- application creation or registration approval
- API-specific registration
- credential issuance
- runtime authorization at the linked Gateway Service

Do not use one answer path for all of these. If the blocker is mainly Portal
sign-in or non-app-specific access, stop and hand off before investigating app
registrations or credentials.

### 2. Verify the publication-to-enforcement chain

For developer self-service to work as intended, inspect:

- application auth strategy existence
- API linkage to a Gateway Service
- API publication to the intended Portal
- auth strategy selection on that publication

If any link is missing, stop there before debugging credentials.

Load `references/linked-service-and-enforcement.md` when the chain appears
complete on the portal side but runtime enforcement still looks wrong.

### 3. Choose strategy by client-ownership model

Choose based on who creates and owns the client credential material, not on
which option happens to be easiest to name in the UI. Keep the strategy choice
separate from publication state or downstream Gateway enforcement.

Load `references/auth-strategy-selection.md` when the main question is which
strategy model fits the intended developer workflow.

### 4. Inspect approvals, registration state, and consumption gates

If the strategy is correct but access still fails, inspect:

- whether developer approval is required
- whether application approval is required
- whether the registration is pending, approved, revoked, or rejected
- whether team or RBAC assignment is blocking consumption

Treat “published but unusable” as a workflow-state problem until proven
otherwise.

Load `references/registration-and-approval-flows.md` when pending, approved,
rejected, or RBAC-gated state is the likely blocker.

### 5. Prove the linked-service enforcement boundary

Application auth only works the intended way when the API is linked to a
Gateway Service and the auth strategy can be enforced there.

If there is no linked service, or the wrong service is linked, fix that model
before changing strategy details.

### 6. Return the narrowest failure point and next owner

Classify the primary issue as:

- missing auth strategy
- wrong strategy type for the use case
- missing Gateway Service linkage
- missing or mis-scoped publication
- approval / registration state mismatch
- RBAC or team assignment mismatch

## Konnect-Specific Gotchas

- User auth and application auth are different layers.
- Selecting an auth strategy during publication applies it to the linked
  Gateway Service path, not just to Portal presentation.
- A Gateway Service must be linked for auth strategies to be enforced as
  intended.
- One application can use only one auth strategy at a time.
- Published APIs can still be unusable because approvals, registrations, or
  linked-service enforcement are incomplete.

## Validation Checklist

Before answering, verify that you can state:

- which surface is actually failing: Portal sign-in, app auth, registration,
  approval, or runtime enforcement
- whether the publication-to-enforcement chain is complete end to end
- whether the selected strategy type matches the intended developer flow
- whether approvals or RBAC are the real blocker
- what exact object or state proves the diagnosis
- whether another skill should own the next step

## Handoffs

- Use `konnect-api-publish` when the API is not yet published or is published to
  the wrong audience.
- Use `konnect-api-catalog` when the API or implementation model itself is not
  ready.
- Use `konnect-access-scope` when the problem is mainly who can view or
  administer the Portal or auth resources, or when org/team/role scoping is
  broader than one app-auth workflow.
- Treat developer Portal sign-in or SSO problems as Portal identity work, not
  application-auth work.
- Use `terraform-konnect` or `kongctl-declarative` when the operator wants to
  encode or apply the resulting auth changes as config.
