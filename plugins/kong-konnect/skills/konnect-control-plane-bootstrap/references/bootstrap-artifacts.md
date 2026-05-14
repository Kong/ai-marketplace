# Bootstrap Artifacts

Use this file when the operator needs the bootstrap milestones separated into
concrete stages.

## Core Rule

Control plane creation, data plane attachment, and first Gateway config are
different milestones. Do not call bootstrap complete after only the first one.

## Milestone Split

| Milestone | What it proves |
|---|---|
| Control plane exists | the platform object was created in the intended region |
| Data plane attachment works | the connectivity and hosting path are viable |
| First Gateway config applies | the environment is ready for runtime config workflows |

## Minimum Proof For Each Milestone

- Control plane exists:
  confirm the intended region, name, and ownership slice are correct.
- Data plane attachment works:
  confirm the chosen hosting model matches the plan and the attachment path is
  understood, not just that an object was created.
- First Gateway config applies:
  confirm the next delivery tool is known and that a first config rollout is
  expected to succeed in this environment.

## Common Misreads

| Symptom | Better interpretation |
|---|---|
| Control plane exists | not enough; attachment and config still unproven |
| Quickstart worked once | not enough; durable ownership path may still be undefined |
| First config failed | bootstrap is incomplete, not just a normal Gateway drift issue |

## Branching Rules

- If milestone 1 is missing, stay in control-plane bootstrap.
- If milestone 1 is complete but milestone 2 is failing for an existing
  environment, hand off to `konnect-gateway-triage`.
- If milestone 2 is complete and the remaining task is how to encode the first
  Gateway entities, hand off to `deck-gateway`, `terraform-konnect`, or
  `kongctl-declarative` based on the repo toolchain.

## What To Return

Return:

- which milestone is complete
- which milestone is still missing
- what evidence supports that classification
- whether the next step is bootstrap, gateway triage, or declarative codification
