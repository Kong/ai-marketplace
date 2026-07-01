---
name: konnect-access-scope
description: Troubleshoot Konnect operator access and visibility. Use when a user cannot authenticate, cannot see or edit a Konnect resource, may be in the wrong region, org, or team, or needs help with scoped roles or IdP-managed access. Not for Dev Portal app auth.
license: MIT
metadata:
  product: konnect
  category: access
  tags:
    - kong
    - konnect
    - access
    - auth
    - permissions
---

# Konnect access and scope troubleshooting

## Goal

Explain why an identity can or cannot reach a Konnect surface, see a
resource, or mutate it, then identify the narrowest next step.

Default to read-first inspection. Do not propose role or team changes until
you have separated resource existence, endpoint selection, authentication, and
authorization.

Use this skill for operator or automation access to Konnect itself. Do not use
it for downstream API consumer auth, Dev Portal application credentials, or
Gateway runtime auth flows.

## Tool Selection

- Use the shared `kong-konnect` MCP server first for live inspection when it
  is available in the session.
- Use `kongctl-query` for read-only checks, identity inspection, and resource
  existence checks from the CLI surface.
- Preserve the repository's chosen declarative toolchain when access-adjacent
  resources need to be codified: prefer `kongctl-declarative` for `kongctl`
  YAML and `terraform-konnect` for HCL-managed Konnect resources.
- If the request depends on live Konnect state and `kong-konnect` MCP is not
  connected, say so early and continue with CLI or user-provided artifacts.

Do not treat declarative config in a repo as proof that a user should be able
to see or edit the live resource. Live access always wins over intended state.

## References To Load

Load only the reference file that matches the active branch:

- `references/region-org-and-team-checks.md`
  - Load when wrong region, org, team, or resource slice is the likely cause.
- `references/visibility-vs-permission.md`
  - Load when the hard question is whether the resource exists, is visible, or
    is writable by this identity.
- `references/idp-and-role-model.md`
  - Load when SSO, SCIM, IdP-managed groups, additive roles, or external
    identity mastering is the real boundary.

## Inspection Order

### 1. Identify the failing surface

Pin down:

- which interface is failing: MCP, `kongctl`, Konnect UI, Konnect API, or
  Portal operator UI
- which operation fails: authenticate, list, get, edit, create, delete
- which resource scope is involved: organization, control plane, portal,
  catalog asset, analytics surface, or Event Gateway resource
- whether the symptom is "cannot see it" or "can see it but cannot change it"
- whether the caller is a human identity or an automation identity acting
  directly against Konnect

Keep the failing operation concrete. Access failures look similar across
surfaces but have different root causes.

If the complaint is really about developer-facing application registration,
issued credentials, or runtime API access, hand off to `konnect-app-auth`
instead of stretching this skill.

### 2. Verify endpoint and identity before permissions

Confirm the caller is pointed at the right Konnect region and organization
before reasoning about roles.

For CLI-based checks, prefer:

```bash
kongctl get organization -o json
kongctl get me -o json
```

If those succeed, authentication is present. If they fail, stop there and fix
auth or endpoint selection first.

Load `references/region-org-and-team-checks.md` when the main ambiguity is
where the caller is pointed rather than what permissions they have.

### 3. Separate resource existence from visibility

Check whether the target resource exists in the organization independently of
the affected user.

- If an operator with broader access can see it, the issue is likely scope or
  role assignment.
- If nobody can see it, the problem is likely name, region, organization, or
  resource lifecycle rather than permissions.
- If the resource exists under a different product surface than expected,
  explain the mismatch instead of calling it a permission failure.

Load `references/visibility-vs-permission.md` when the core question is whether
the resource is absent, hidden, or only non-mutable.

### 4. Evaluate scope and role layering

Interpret access using these defaults:

- Roles are additive. Multiple team memberships can expand what a user can do.
- Resource-scoped roles matter as much as organization-level roles.
- A user may be allowed to read a resource but not mutate it.
- Portal, analytics, gateway, and Event Gateway surfaces can expose different
  subsets of the same organization.
- Organization-wide roles are only a starting clue; verify the narrower
  resource slice that actually governs the target object.

Do not assume a missing mutation permission implies missing read permission, or
the reverse.

### 5. Check for IdP-managed or external identity constraints

When the user mentions Okta, SSO, SCIM, or IdP-managed groups, verify whether
the requested change is blocked because identity membership is mastered outside
Konnect.

Treat externally managed identity data as read-only from the Konnect side
unless you can confirm otherwise.

Load `references/idp-and-role-model.md` when role layering, IdP mastery, or
team/identity mapping is the main decision branch.

### 6. Explain the narrowest root cause

Classify the outcome as one of:

- wrong region or organization
- missing or invalid auth
- resource does not exist where expected
- read access present but write access missing
- scope mismatch between team or role assignment and target resource
- IdP-managed identity constraint
- neighboring product-surface confusion

Then give the minimum next action needed to unblock the user.

If the root cause is outside Konnect operator access, say which neighboring
skill should take over instead of keeping the diagnosis open-ended.

## Konnect-Specific Gotchas

- A valid PAT does not prove the caller is pointed at the intended region.
- Seeing one product surface does not imply access to every Konnect surface.
- Additive roles can make "why can this user do that?" as important as
  "why can't they?"
- IdP-backed users may appear editable in theory but still be effectively
  read-only for team or profile changes.
- "I cannot see the control plane" can mean the control plane exists in a
  different region, belongs to a different team scope, or was never created.

## Validation Checklist

Before answering, verify that you can state:

- the exact failing surface and operation
- whether authentication itself works
- whether the target resource exists
- whether the issue is endpoint, scope, role, or IdP related
- whether read and write permissions differ in this case
- whether another skill should take over for the next step

## Handoffs

- Use `kongctl-query` for exact read-only command selection and output shaping.
- Use `kongctl-declarative` or `terraform-konnect` when the user wants to
  create or update managed Konnect resources after the access issue is
  understood. Match the repository's current toolchain.
- Use `konnect-app-auth` when the real issue is developer registration,
  application credentials, or Dev Portal auth behavior rather than operator
  access to Konnect.
- Use `konnect-gateway-triage`, `konnect-observability-triage`,
  `konnect-api-publish`, or `konnect-event-gateway` when the real problem is
  not access but operator ambiguity inside that surface.
