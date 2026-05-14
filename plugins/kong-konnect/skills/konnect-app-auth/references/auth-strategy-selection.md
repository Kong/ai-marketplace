# Auth Strategy Selection

Use this file when the main decision is which application-auth strategy model
fits the use case.

## Core Rule

Choose the strategy from client ownership and provisioning flow, not from what
is easiest to name in the UI.

## Strategy Map

| Strategy | Choose when | Avoid when |
|---|---|
| `key-auth` | the Gateway should accept built-in API keys and the Portal should issue them through the app workflow | the real requirement is OIDC client management or external IdP ownership |
| self-managed OIDC | developers already have pre-registered clients and should bring their own client credentials | the Portal is expected to create or rotate IdP clients for them |
| DCR | the Portal should create and manage IdP clients dynamically during app registration | the IdP or governance model does not allow dynamic client registration |

## Quick Checks

- who creates the client credential material: developer, Portal, or Gateway
- whether the identity provider allows dynamic client registration
- whether the same application must consume multiple APIs with one strategy
- whether the real blocker is publication, approval state, or Gateway
  enforcement instead of strategy type

## Important Constraints

- strategies are reusable across APIs and Portals
- one application can use only one auth strategy at a time
- strategy choice is separate from whether the API is published at all

## What To Return

Return:

- which strategy best fits the intended self-service model
- why the alternatives are worse for this workflow
- which prerequisite is still missing if strategy choice is not the real
  blocker
- whether the next issue is publication, registration, or enforcement
