# Dataset Map

Use this file when the operator may be asking the right question in the wrong
observability surface.

## Core Rule

Do not treat Konnect observability as one bucket. Map the question to the
dataset first.

## Fast Mapping

| Question type | Best starting surface | What to prove |
|---|---|---|
| Gateway/API runtime traffic | gateway or API-oriented analytics or Explorer views | whether the runtime request path and target entity match the view |
| LLM token, model, or latency behavior | LLM-specific analytics surfaces | whether the operator expects LLM-specific metrics in a generic API surface |
| Request-level debugging | Debugger or trace-oriented surface | whether a trace-level artifact is expected rather than an aggregate trend |
| Platform or admin activity | platform-level operational or audit-like surface | whether the event is operational metadata rather than traffic telemetry |

## Granularity Check

Ask what evidence would satisfy the user:

- a trend or count over time
- a filterable usage record set
- a single request or trace
- an administrative event or lifecycle change

If the evidence type does not match the surface, correct that first. Do not
call it missing data yet.

## Common Misroutes

| Operator expectation | Better interpretation |
|---|---|
| "Analytics is broken" | wrong product surface for the question |
| "I cannot see LLM cost-like behavior in normal API analytics" | use LLM-specific observability |
| "Debugger is empty so analytics must be empty too" | aggregate analytics and request debugging are different surfaces |
| "The API is not published so observability must be broken" | publication or Catalog ownership, not observability first |

## Neighbor Boundaries

Hand off instead of stretching this branch:

- use `konnect-gateway-triage` when the real question is traffic reaching the
  gateway at all
- use `konnect-api-catalog` when the issue is API object readiness, versioning,
  or implementation modeling
- use `konnect-api-publish` when the issue is publication or audience
  visibility rather than runtime telemetry

## Return Shape

Return:

- which surface best matches the question
- why the current surface is the wrong one if applicable
- whether the issue should stay in observability or hand off to gateway health
