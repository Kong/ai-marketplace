---
name: konnect-api-catalog
description: Diagnose and shape Konnect API Catalog APIs, versions, specs, implementations, and API packages before publication. Use when Catalog readiness is the question, not when the real owner is Dev Portal publication, app auth, or gateway delivery.
license: MIT
metadata:
  product: konnect
  category: api-catalog
  tags:
    - kong
    - konnect
    - catalog
    - api
    - governance
---

# Konnect API catalog workflow

## Goal

Help an operator create, shape, and troubleshoot Catalog APIs and API packages
before they become a Dev Portal publishing or consumer-access problem.

Own Catalog readiness diagnosis and object modeling for APIs, versions, specs,
documentation, implementations, and packages. Do not absorb Dev Portal
publication, app auth, or declarative delivery workflows beyond clear
handoffs.

## Tool Selection

- Use the shared `kong-konnect` MCP server first for live inspection of APIs,
  versions, specs, documents, implementations, packages, and portal
  publications.
- Prefer Catalog-oriented MCP reads before changing config. Useful live
  surfaces include API, version, implementation, package, and publication
  listings.
- Preserve the repository's chosen declarative toolchain when catalog objects
  need to change: use `terraform-konnect` for HCL-managed Catalog resources and
  `kongctl-declarative` only when the repo already manages the surrounding
  Konnect workflow that way.
- Use `deck-gateway` only when the real missing link is Gateway-entity config
  behind an implementation or linked service.
- If live Konnect state matters and `kong-konnect` MCP is not connected, say so
  early and continue with user-provided artifacts or adjacent CLI/config
  sources.
- This skill owns diagnosis of Catalog shape and readiness. It should not turn
  into a mutation playbook for Portal, app auth, or Gateway configuration.

## References To Load

Load only the reference file that matches the active branch:

- `references/managed-api-readiness.md`
  - Load when the main question is whether the API object, version, and
    upstream catalog shape are complete enough before publication.
- `references/spec-version-and-metadata.md`
  - Load when the hard part is versioning model, spec quality, docs, or
    metadata alignment.
- `references/package-and-implementation-boundaries.md`
  - Load when packages, implementations, Gateway Service linkage, or
    package-versus-API modeling is the real issue.

## Workflow

### 1. Classify the operator's real outcome before inspecting objects

First separate whether the user is trying to make the API:

- visible and correct in Catalog
- publishable in Portal
- consumable through registration or app auth
- encoded in the repo's declarative toolchain

If the real outcome is not Catalog readiness, hand off early instead of doing
partial diagnosis in the wrong layer.

### 2. Identify the first Catalog object that is actually missing

Clarify whether the operator is missing:

- the API object itself
- an API version
- a valid specification or generated documentation
- API documents or page structure
- a Gateway implementation link
- an API package
- a portal publication that should happen after the catalog object is ready

Do not jump straight to Portal troubleshooting if the Catalog object model is
incomplete.

Load `references/managed-api-readiness.md` when "missing from catalog" is
really a question about what object in the chain is incomplete.

### 3. Confirm API identity and versioning model

Inspect:

- API name
- current version
- slug or URL identity
- whether the API should be modeled as one API with multiple spec versions or
  distinct APIs for major versions

Load `references/spec-version-and-metadata.md` when the versioning or
documentation model is the main decision branch.

### 4. Check spec and documentation readiness

Verify:

- a spec exists when generated docs are expected
- the spec version matches the intended current version
- validation issues are understood before blaming downstream publishing
- documentation pages, slugs, parent pages, and status match the intended
  structure

Treat invalid-but-accepted specs as degraded inputs, not as healthy state.

### 5. Check implementation and service linkage only when consumption depends on it

If developers should be able to consume the API through registration, inspect:

- whether the API is linked to a Gateway Service or control-plane-backed
  implementation
- whether the implementation shape is 1:1 service linkage or a broader package
  / control plane scenario
- whether the linked service is the right operational surface

Do not call the API consumer-ready until the implementation story is clear.

### 6. Separate packages from individual APIs

When API packages are involved, verify:

- whether the operator should publish an individual API or a package
- which operations belong in the package
- whether the package boundary is business-facing or merely technical

Packages are for grouping and presentation, not for hiding a broken API model.

Load `references/package-and-implementation-boundaries.md` when grouping,
implementation linkage, or package boundaries are the main question.

### 7. Hand off only after Catalog readiness is clear

Once API shape, docs, implementations, and packages are understood, hand off:

- to `konnect-api-publish` for Portal publication and audience-facing issues
- to `konnect-app-auth` when the API exists but developer registration or auth
  behavior is the real blocker
- to `deck-gateway`, `terraform-konnect`, or `kongctl-declarative` when the
  operator wants to codify or change the resulting config

## Konnect-Specific Gotchas

- Catalog readiness and Portal publication are related but not identical.
- API versioning, spec versioning, and slug identity can drift separately; do
  not treat one healthy field as proof that the rest are aligned.
- Developer self-service depends on implementation linkage, not only on the API
  object existing in Catalog.
- Packages can clarify consumption boundaries, but they do not fix a confused
  underlying API model.

## Validation Checklist

Before answering, verify that you can state:

- whether the user's real outcome is Catalog readiness, Portal publication,
  app auth, or declarative delivery
- which Catalog stage fails first
- which Catalog object is missing or malformed
- whether API identity and versioning are correct
- whether spec and documentation readiness are complete
- whether an implementation or linked service exists where needed
- whether the problem belongs in Catalog, Portal publication, or app auth
- which declarative tool skill owns the needed change

## Handoffs

- Use `konnect-api-publish` when the Catalog object is ready and the remaining
  problem is publication to Portal.
- Use `konnect-app-auth` when the issue is developer self-service, application
  registration, or auth strategy behavior.
- Use `deck-gateway`, `terraform-konnect`, or `kongctl-declarative` when the
  operator wants to encode or apply the resulting change as config.
