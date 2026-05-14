# Live vs Declarative Drift

Use this file when repository config, Terraform, `decK`, or `kongctl` intent
does not match what the operator sees in Konnect or on the data plane.

## Core Rule

Treat checked-in config as intended state, not proof of deployed state.
Treat live state as observed behavior, not proof that the repository is wrong.
The job is to identify which source of truth currently owns the mismatch.

## Drift Questions

Ask:

- which toolchain owns the resource: `decK`, Terraform, `kongctl`, or manual
  changes
- whether the live control plane has the expected services, routes, plugins,
  or upstreams
- whether the data plane is actually receiving the control-plane state
- whether the repo diff is narrow drift or evidence of the wrong environment

## Proving Order

1. Identify the one resource slice the symptom depends on.
2. Compare the live control-plane state for that slice with the intended source
   of truth.
3. Confirm whether the data plane behavior matches the live slice or lags it.
4. Only then decide whether the mismatch is apply drift, manual drift, or a
   wrong-environment inspection.

## Common Mismatch Patterns

| Pattern | Likely interpretation |
|---|---|
| Repo has entity, live control plane does not | apply/sync not run, wrong environment, failed rollout |
| Live entity exists, repo does not | manual UI/API drift, wrong repo boundary, missing import/adoption |
| Control plane looks right, data plane behavior does not | rollout lag, unhealthy plane, traffic-path issue |
| Labels/tags differ more than entities | wrong slice, ownership mismatch, environment confusion |

## Decision Rules

- If the wrong toolchain owns the resource, hand off to that tool skill.
- If live state is missing but the repo is correct, call it rollout or apply
  drift, not design drift.
- If live state is present but behavior is still wrong, switch to traffic-path
  diagnosis rather than repeating diff logic.
- If a manual change fixed the symptom but broke the repo contract, call that
  hidden drift explicitly.

## What Proves The Branch

Anchor the diagnosis with:

- one intended-state artifact such as the owning repo file, Terraform state, or
  `kongctl` resource definition
- one live-state artifact showing the same resource missing, changed, or placed
  in the wrong environment

## What To Return

Return:

- the intended source of truth
- the observed live mismatch
- whether the issue is apply/rollout drift, manual drift, or wrong-environment
  inspection
- which tool skill owns the correction
