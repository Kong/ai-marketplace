# IdP and Role Model

Use this file when SSO, SCIM, external groups, or additive roles are the main
access boundary.

## Core Rule

Treat externally mastered identity data as read-only from the Konnect side
unless proven otherwise.

## Useful Distinctions

| Branch | Meaning |
|---|---|
| Additive roles | multiple memberships can expand access |
| Resource-scoped roles | access may differ by control plane, portal, or other surface |
| IdP-managed groups | changes may need to happen outside Konnect |
| SCIM-provisioned identity | lifecycle and membership may be externally controlled |

## Decision Rules

- If the user can explain access only by combining multiple roles or teams, do
  not collapse that into one "main" role. State the additive outcome.
- If the requested fix is a group, team, or lifecycle change for an
  IdP-managed identity, route the change to the IdP unless Konnect ownership is
  explicitly confirmed.
- If org-wide roles look correct but one control plane or portal still differs,
  keep resource-scoped grants in focus instead of assuming the org role is
  sufficient.

## What To Return

Return:

- whether the issue is role layering or external identity mastery
- whether the next action belongs in Konnect or the IdP
- whether resource-scoped access differs from org-wide assumptions
