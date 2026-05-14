# Gateway Entities Inside Konnect

Use this file when the task mixes Konnect platform resources with Gateway
entities that live inside a Konnect control plane.

## Core Rule

Do not assume that all Konnect-scoped work belongs in one Terraform module.
Gateway entities may share a provider context with platform resources while
still living in a different ownership boundary.

## Useful Distinctions

| Resource type | Typical question |
|---|---|
| Platform resources | control planes, APIs, portals, teams, roles, publications |
| Gateway entities in Konnect | services, routes, plugins, upstreams, certificates inside a control plane |

## Decision Rules

- If the repo already groups Gateway entities separately from platform
  resources, preserve that split.
- If the change is mostly Gateway-entity GitOps, consider whether `deck` would
  have been the better baseline before forcing Terraform.
- If the task spans both resource families, keep the explanation explicit about
  which file/module owns which part.

## Return Shape

Return:

- whether the task is platform-centric, Gateway-entity-centric, or both
- which module owns each part
- whether another tool skill would be a better implementation owner
