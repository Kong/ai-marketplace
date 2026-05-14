# Common Failure Signals

Use this file when the operator starts with symptoms instead of a clear failure
domain.

## Symptom Map

| Operator symptom | Start here |
|---|---|
| "My data plane is disconnected" | `connection-bootstrap.md` |
| "Config exists in git but not in Gateway" | `live-vs-declarative-drift.md` |
| "The plane is healthy but traffic is still broken" | `traffic-path-vs-control-plane.md` |
| "Resources look missing but only for this environment" | wrong control plane or label slice first, then drift |
| "Analytics are empty" | likely `konnect-observability-triage`, not gateway rollout first |

## Fast Proving Checks

| First check | What it separates |
|---|---|
| Is the data plane attached right now? | attachment failure versus later config or traffic failure |
| Are you looking at the intended control plane and region? | wrong slice versus real resource absence |
| Does the live control plane contain the expected resource? | rollout drift versus request-path or upstream failure |
| If the resource exists, does the failing request reach the intended route? | traffic-path failure versus deployment failure |

## Fast Classification Prompts

Ask only enough to place the issue:

- Is the data plane attached right now?
- Are you looking at the intended control plane and region?
- Does the live control plane contain the expected resources?
- If yes, is the failing symptom about traffic behavior instead of config
  presence?
- Is the real complaint actually analytics or visibility rather than request
  routing?

## Decision Rules

- If the plane is disconnected, stop before route or plugin analysis.
- If the plane is healthy but the live resource is missing, treat that as drift
  or wrong-environment inspection first.
- If the live resource exists and the request still fails, move to the
  traffic-path branch instead of repeating deploy-state checks.
- If the user only has observability symptoms, hand off early rather than
  stretching gateway rollout triage to cover analytics.

## Return Shape

When the initial report is ambiguous, respond with:

- the most likely failure layer
- the next proving check
- the deeper reference branch or neighboring skill that now owns the problem
