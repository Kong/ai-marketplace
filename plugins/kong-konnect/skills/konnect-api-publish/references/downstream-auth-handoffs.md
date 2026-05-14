# Downstream Auth Handoffs

Use this file when a publication investigation turns into a developer app,
credential, registration, or approval workflow problem.

## Handoff Boundary

Stay in `konnect-api-publish` only while the missing link is publication or
portal visibility.

Hand off when the real blocker is:

- application registration
- approval workflow
- credential issuance
- DCR versus manual app creation
- OIDC or auth-strategy choice
- developer onboarding after the API is already visible

## Proof Required Before Handoff

Before handing off, confirm as much of this chain as the available evidence
allows:

- the managed API and intended version exist
- the API is published to the intended portal or audience
- the remaining blocker starts after discovery or visibility

## Quick Signals

| Signal | Primary owner |
|---|---|
| API not present in portal at all | `konnect-api-publish` |
| API visible, signup/use blocked | `konnect-app-auth` |
| API likely exists but caller cannot even see admin resources | `konnect-access-scope` |
| Gateway-side auth config missing for the runtime path | declarative tool skill or gateway domain, depending on context |

## What To Return

When handing off, say:

- publication state is complete or sufficiently proven
- the next missing step is consumer auth or registration
- `konnect-app-auth` now owns the next action
- any unresolved visibility or portal-target ambiguity that still needs proof
