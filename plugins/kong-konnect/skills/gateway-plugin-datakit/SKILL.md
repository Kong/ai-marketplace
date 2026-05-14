---
name: gateway-plugin-datakit
description: Use when designing or debugging Kong DataKit plugin flows, including node selection, DAG wiring, jq transforms, cache or vault usage, and phase-specific request or response orchestration. Do not use for generic decK, Terraform, or Konnect workflow questions.
license: MIT
metadata:
  product: datakit
  category: orchestration
  tags:
    - kong
    - datakit
    - gateway-plugin-datakit
    - gateway
---

# Goal

Help the agent turn an orchestration request into a correct DataKit flow, or
debug an existing flow, without drifting into generic Gateway or declarative
tool guidance.

Own DataKit reasoning: phase choice, node selection, DAG structure, connection
shape, cache or vault requirements, and debug strategy.

# Tool Selection

Prefer working from the artifact that already owns the flow:

- If the repo already contains DataKit YAML under `deck`, `kong.yaml`, or other
  declarative config, edit that artifact in place.
- If the request depends on current Konnect state and `kong-konnect` MCP is
  available, use it to inspect the attached plugin instance and confirm whether
  the problem is in the saved config or only in the repo copy.
- If the request is only about DataKit flow behavior, stay in this skill. Hand
  off only when the work becomes mainly about `decK`, `kongctl`, or Terraform
  packaging.

# References To Load

Load only the file that matches the current branch:

- `references/node-reference.md`
  - Load when choosing node types, checking required fields, or confirming what
    a node or implicit object can read or write.
- `references/patterns.md`
  - Load when translating a user workflow into a starter flow shape such as
    fan-out merge, auth injection, caching, XML conversion, dynamic URLs, or
    header mutation.
- `references/resources-and-debugging.md`
  - Load when the problem depends on cache or vault resources, live debug
    traces, deployment topology, or version-gated behavior.

Run `scripts/validate_datakit_flow.py` when a local YAML file already exists
and you need deterministic checks for node naming, references, branch targets,
cycles, implicit-field misuse, or missing cache or vault resources.

# Workflow

1. Classify the request before drafting YAML.
   - Identify whether the flow runs in access or response phase.
   - Confirm whether the plugin should mutate `service_request`, mutate
     `response`, or short-circuit with `exit`.
   - Confirm the attachment boundary: service, route, consumer, consumer group,
     or global.

2. Reduce the task to a small DAG.
   - List the external calls, transforms, gates, and writes that must happen.
   - Prefer the fewest nodes that preserve clarity.
   - Treat independent `call` nodes as concurrent by default unless the output
     of one is required by another.

3. Choose nodes from behavior, not from examples.
   - Use `call` for HTTP work, `jq` for reshaping, `branch` for scheduling
     conditional paths, `cache` for lookup or store, `property` for Kong
     internals, and `exit` only when the flow must terminate early.
   - Load `references/node-reference.md` instead of guessing field names or
     outputs.

4. Encode the flow around references and resources.
   - Reserve explicit node names for actual nodes; never redeclare implicit
     names such as `request` or `response`.
   - Keep connections explicit with `input` or `inputs`.
   - Add `resources.cache` or `resources.vault` only when the chosen nodes
     require them.
   - Prefer vault-backed secrets over hardcoded credentials.

5. Debug from the first broken edge, not from the final symptom.
   - Start with the node whose output feeds the failing downstream node.
   - If the issue is structural, run the validator first.
   - If the issue is live execution, enable DataKit debug mode and inspect the
     trace to find the earliest `NODE_ERROR` or the upstream cause of
     `NODE_CANCELED`.

# DataKit-Specific Gotchas

- Implicit nodes are phase-bound interfaces, not normal nodes:
  `request` and `service_request` belong to access; `service_response` and
  `response` belong to response.
- `branch` controls which named nodes are scheduled. It does not replace normal
  data dependencies, so downstream nodes still need valid `input` or `inputs`
  wiring.
- `cache` and `vault` nodes are incomplete without matching `resources.*`
  configuration.
- Non-2xx `call` responses are usually flow errors. Do not assume a response
  body exists downstream unless the call succeeded or the user explicitly wants
  error-path handling.
- Some capabilities are version-gated, including newer node types and dynamic
  URL overrides. If the request targets an older gateway, verify support before
  leaning on those features.

# Validation Checklist

- Confirm the plugin is attached at the intended scope and phase.
- Confirm every explicit node name is unique and does not shadow an implicit
  node.
- Confirm each reference base exists and each referenced field is valid for that
  node or implicit object.
- Confirm cache and vault resources exist only when required and match the node
  usage.
- Confirm downstream nodes consume the actual output shape produced upstream,
  especially after `jq`, cache lookups, and XML conversion.
- Run
  `python3 plugins/kong-konnect/skills/gateway-plugin-datakit/scripts/validate_datakit_flow.py <yaml-path>`
  for local files before concluding the structure is sound.
- For live debugging, prove the intended node path executed by checking the
  first failing trace event, not just that the request reached Kong.

# Handoffs

- Hand off to `deck-gateway` when the main job becomes declarative Gateway file
  integration, diff, or apply workflow.
- Hand off to `terraform-kong-gateway` or `terraform-konnect` when the repo is
  Terraform-owned and the problem becomes provider schema or state behavior.
- Hand off to `kongctl-declarative` when the repo already uses `kongctl` plan or
  apply workflows for Konnect resources.
