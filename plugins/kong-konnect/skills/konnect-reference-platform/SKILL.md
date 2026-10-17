---
name: konnect-reference-platform
description: Design or modernize a federated Konnect reference platform. Use for cross-repo ownership and promotion; not isolated resource operation.
license: MIT
metadata:
  product: konnect
  category: reference-architecture
  tags:
    - kong
    - konnect
    - reference-platform
    - platform-engineering
    - apiops
---

# Konnect reference platform

## Goal

Design, implement, or review a maintained Konnect reference architecture and a
working example that teams can read, copy, and adapt.

Keep the platform declarative and federated. Do not invent a registry, wrapper
CLI, or second configuration format over supported Kong tooling.

## Tool Selection

- Treat the repository manifests as intended state. Use live Konnect state to
  inspect or prove deployment, not as a replacement source of truth.
- Use `kongctl-declarative` for Konnect platform resources such as teams,
  access, control planes, Catalog APIs, versions, specs, implementations,
  publications, Portals, and application auth strategies.
- Use `deck-gateway` for Gateway Services, Routes, and plugins. Prefer
  OpenAPI-driven generation when a service contract is the starting point.
- Preserve an existing Terraform architecture if the target repository already
  owns these resources in Terraform. This skill describes the ownership model;
  it does not require a tool migration.
- Use the shared `kong-konnect` MCP server when current live state matters. If
  it is unavailable, continue from checked-in manifests and clearly separate
  intended architecture from live proof.

## References To Load

- Load `references/ownership-and-promotion.md` when defining repository
  boundaries, CI identities, development ownership, or production promotion.

For the maintained public implementation, consult the official Reference
Platform documentation and the KongAirlines repositories. Prefer their current
checked-in manifests over historical prose or examples that use unsupported
tools.

## Workflow

### 1. Establish the sources of truth

Find the checked-in `kongctl` manifests, decK files, OpenAPI contracts, and CI
workflows before proposing structure.

Require these properties unless the user deliberately chooses another model:

- no custom registry or generated orchestration format
- one default branch with distinct development and production resources
- a root beta OpenAPI contract that advances for every contract change, plus
  immutable, stable versioned files
- an explicit current-production version in the production Catalog manifest
- generated decK files committed so reviewers can inspect exact Gateway state
- append-only Catalog API versions, created with a separate `kongctl apply`
  manifest and omitted from manifests reconciled with `kongctl sync`

### 2. Draw the ownership boundary

Separate organization-wide foundations from service-owned delivery:

- The platform repository owns teams, RBAC, automation identities, control
  planes, Portals, shared Gateway Consumers and verification credentials, and
  the production Gateway configuration.
- Service repositories own their APIs, versions, specs, implementations,
  publications, and development Gateway configuration.
- Service teams may write their owned development Gateway slice. Production
  Gateway changes move through platform review without transferring Catalog
  ownership to the platform team.

Load `references/ownership-and-promotion.md` before encoding this boundary in
repositories or CI.

### 3. Model development and production explicitly

Keep both stages on the default branch as different named resources. Do not use
branches as environments.

Until a generally available environment-aware Catalog model is deliberately
adopted, model development and production as separate API resources when each
must link to a different control plane. A Portal can aggregate the intended
stage's APIs according to audience and governance needs.

Resolve parent resources by declarative references such as `!ref`, `!lookup`,
or `_external` instead of copying UUIDs. If an intended lookup is not supported
by the installed `kongctl` version, retain the target architecture and report
the exact compatibility dependency; do not replace it with a custom registry.

### 4. Keep Catalog and Gateway concerns connected but independent

- The OpenAPI contract drives the Catalog API version and generated Gateway
  configuration.
- Treat Catalog API versions as append-only. Advance `info.version` for every
  contract change, apply the new child before selecting it, and omit the
  versions collection from the API manifest reconciled with `kongctl sync`.
- Link each Catalog API to its runtime implementation.
- Keep routing configuration in decK. Keep APIs, specs, implementations, and
  Portal publications in `kongctl` manifests.
- Scope shared-control-plane Gateway ownership with tags and narrow CI file
  boundaries. Treat tags as an operational ownership aid, not an RBAC boundary.
- Keep global Gateway plugins out of service-owned production manifests unless
  the platform contract explicitly permits them.

### 5. Model consumer authorization end to end

Keep publication visibility, Gateway authentication, and Portal application
access control separate.

- The platform team owns shared Consumers and asymmetric JWT verification
  credentials. Private signing keys remain in a secret manager.
- Service teams configure JWT only on protected Gateway Services and declare
  bearer authentication in their OpenAPI contracts.
- Protected publications omit `auth_strategy_ids` when JWT is the only client
  credential. Selecting a Portal application strategy would add a second,
  independent credential requirement.
- Public services omit authentication plugins and remain callable without
  Portal registration, API keys, or JWTs.
- If ACE is global, validate its behavior separately from JWT. A required
  operation match must not be mistaken for application authentication.
- Verify the authentication plugin replaces client-supplied identity headers
  with the authenticated Consumer identity before proxying upstream.

Hand off a deliberately chosen Portal registration flow to `konnect-app-auth`,
and Gateway plugin configuration to `deck-gateway`.

### 6. Validate the architecture as a working example

Validate more than YAML syntax:

- regenerate committed decK from the OpenAPI source and require a clean diff
- verify development creates the new Catalog version before selecting it, and
  that sync-managed manifests cannot delete prior version children
- verify release automation opens a reviewed service PR, advances the root
  beta, and derives production generation from the manifest's stable selector
- reject modification or deletion of stable release files already on the
  target branch
- validate every decK file and every `kongctl` manifest supported by the
  installed CLI
- check that each CI identity and manifest is limited to its intended repo,
  stage, namespace, and resource slice
- trace one public and one protected API from OpenAPI through Catalog,
  publication, implementation linkage, Gateway routing, and auth behavior
- verify production uses the exact reviewed artifact promoted from the service
  repository, with source commit and checksum provenance
- search docs and examples for obsolete tools, registry concepts, hard-coded
  resource IDs, and branch-as-environment guidance

When a future CLI capability blocks execution, distinguish a valid intended
manifest from a current implementation gap and identify the issue or release
that must land before the pipeline can pass.

## Konnect-Specific Gotchas

- Namespaces express declarative ownership; they do not replace Konnect RBAC.
- Tags can scope decK operations and conflict risk; they do not grant access.
- Catalog implementation linkage and Gateway routing answer different
  questions. Keep both explicit.
- Portal application auth settings, ACE operation enforcement, and Gateway
  runtime authentication are distinct layers. Add each only when its client
  requirement is intentional.
- A service-owned Catalog does not imply service-owned production data-path
  configuration.
- Catalog API versions need a different reconciliation policy from mutable API
  state: use additive apply for version children and sync for the remaining
  authoritative state.
- An unreleased environment or workspace feature should be a documented future
  option, not a hidden dependency of the current working path.

## Validation Checklist

Before answering, verify that you can state:

- which repository owns every resource class
- which declarative file is the source of truth for that class
- how one default branch represents development and production
- how service-owned development Gateway changes are isolated
- how an exact production artifact reaches platform governance
- how Catalog implementation linkage, Portal publication, and runtime auth
  connect end to end
- which failures are architecture defects versus known CLI coverage gaps
- how a reader can inspect and copy the working example

## Handoffs

- Use `kongctl-declarative` to author and validate Konnect YAML and CI apply
  workflows.
- Use `deck-gateway` to generate, tag, validate, diff, or apply Gateway state.
- Use `konnect-api-catalog`, `konnect-api-publish`, or `konnect-app-auth` when
  one product link needs focused diagnosis.
- Use `konnect-access-scope` when the remaining question is the least-privilege
  role or automation identity needed for a resource slice.
