# Topology Choice

Use this file when the main bootstrap decision is what kind of environment is
being built.

## Core Rule

Separate quick proof-of-life from durable environment design. A local or guided
quickstart is not automatically the right shared operating model.

## Questions To Clarify

- is this a local proof-of-capability or a long-lived team environment
- are data planes self-hosted, Dedicated Cloud Gateways, or another managed
  hosting shape
- is this dev, staging, prod, or a shared platform slice
- does the team need one control plane now or a repeatable pattern for several
  environments soon

## Common Decision Patterns

| Situation | Default interpretation |
|---|---|
| Tutorial or first-time setup | quickstart plus later durable codification |
| Shared team environment | explicit region, ownership, and durable toolchain from the start |
| Production bootstrap | avoid treating quickstart defaults as final architecture |

## Decision Rules

- Prefer a quickstart framing only when the operator mainly needs proof that
  Konnect Gateway can come up at all.
- Prefer a durable environment framing when the same control plane name,
  region, or ownership decision will be reused by a team or pipeline.
- Treat hosted versus self-hosted data planes as an operating-model choice, not
  just a provisioning detail. It changes what must be proven next.
- If the user is already discussing rollout health, attachment failures, or
  config application on an existing control plane, this is no longer a
  topology-choice question. Hand off to `konnect-gateway-triage`.

## What To Check Before Recommending A Shape

- whether the user needs local speed or repeatable team ownership
- whether the region is constrained by org policy or adjacent services
- whether the next step after creation is data plane attachment, managed
  provisioning, or repository codification
- whether the recommendation still works once a second environment is added

## What To Return

Return:

- the intended topology shape
- whether the current path is quickstart-only or durable
- the data plane hosting model that should be assumed next
- which next skill or tool should own codification
