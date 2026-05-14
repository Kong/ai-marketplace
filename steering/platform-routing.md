# Platform Routing

Use this file when a request is broadly about Kong or Konnect and the next
specialist workflow is not obvious yet.

## Default Routing

- Start with `skills/konnect-platform-router/SKILL.md`.
- Treat that skill as the classifier and handoff layer.
- Do not rewrite the downstream specialist workflow here.

## Operating Defaults

- Prefer `kong-konnect` MCP when the request depends on current live Konnect
  state.
- Preserve the existing repo toolchain. Do not switch between `decK`,
  `kongctl`, and Terraform unless the user asks.
- Name one primary downstream skill and explain the handoff briefly.
