---
name: "ai-marketplace"
displayName: "Kong AI Marketplace"
description: "Portable Kong skills for Kiro with client-managed Konnect MCP setup"
version: "1.0.0"
license: "MIT"
author: "Kong"
repository: "https://github.com/kong/ai-marketplace"
keywords:
  - kong
  - konnect
  - mcp
  - deck
  - kongctl
  - terraform
  - gateway
  - apiops
  - observability
  - ai-gateway
  - dev-portal
  - event-gateway
---

# Kong AI Marketplace

This power makes the Kong AI Marketplace repo directly installable in
Kiro. It reuses the skills under `plugins/kong-konnect/skills/` as the
canonical source of domain guidance. The power does not package a bearer token
or an unauthenticated remote MCP declaration.

Use this power when the user is working on Kong Gateway or Konnect workflows
and needs one of:

- live Konnect inspection, analytics, or troubleshooting via MCP
- Gateway declarative config work with `decK`
- broader Konnect infrastructure management with Terraform
- `kongctl` query or declarative workflows
- routing to the correct Kong specialist workflow when the request is broad

## Onboarding

1. When live Konnect state is needed, use a `kong-konnect` MCP server configured
   through Kiro's user-level MCP settings with a securely supplied bearer token.
2. Verify MCP access before relying on live state. If MCP is absent or auth
   fails, say so early and continue with repo artifacts, the relevant skill
   guidance, or user-provided state.
3. Preserve the user's current toolchain. Do not convert between `decK`,
   `kongctl`, and Terraform unless the user asks or there is a clear blocker.
4. Use `plugins/kong-konnect/skills/` for the substantive Kong workflow guidance.
   The Kiro steering files in this repo are only routing and safety layers.

## Tool Choice

- Prefer `kong-konnect` MCP for live Konnect reads, analytics, and
  troubleshooting.
- Prefer `decK` for declarative Gateway entity changes and diff or sync flows.
- Prefer Terraform for broader Konnect infrastructure lifecycle management.
- Use `kongctl` when the user explicitly wants it or the existing repo already
  centers its workflow on `kongctl`.

## When To Load Steering Files

- Broad Konnect or Kong requests with unclear ownership ->
  `steering/platform-routing.md`
- Live Konnect inspection, analytics, debugging, or read-heavy triage ->
  `steering/live-konnect-ops.md`
- Declarative or tool-specific implementation work ->
  `steering/tool-choice-and-safety.md`

## Skill Inventory

This power uses the existing skill set under `skills/` as the canonical
workflow docs, including:

- `konnect-platform-router`
- `konnect-gateway-triage`
- `konnect-observability-triage`
- `konnect-access-scope`
- `deck-gateway`
- `terraform-konnect`
- `terraform-kong-gateway`
- `kongctl-query`
- `kongctl-declarative`
- product-specific Konnect skills such as AI Gateway, API Catalog, API
  publication, app auth, Event Gateway, and control plane bootstrap

## License And Support

This power mirrors the Kong AI Marketplace repo and integrates with the
`kong-konnect` MCP server.

- License: MIT
- Privacy Policy: https://konghq.com/legal/privacy-policy
- Support: https://github.com/kong/ai-marketplace/issues
