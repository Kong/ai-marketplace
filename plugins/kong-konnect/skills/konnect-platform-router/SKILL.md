---
name: konnect-platform-router
description: Route broad or ambiguous Konnect requests to the first owning specialist skill. Use when multiple Konnect surfaces are involved or the right owner is unclear, not when the user already named a specific workflow, toolchain, or non-Konnect task.
license: MIT
metadata:
  product: konnect
  category: routing
  tags:
    - kong
    - konnect
    - routing
    - triage
---

# Konnect platform router

## Goal

Turn broad Konnect requests into one primary downstream skill with a clear next
step and one concrete thing that skill should prove next.

Use this skill as a classifier and handoff layer. Do not turn it into a
product guide or a second copy of specialist workflows.

## Shared Operating Defaults

- Prefer the shared `kong-konnect` MCP server when the request depends on live
  Konnect state.
- If `kong-konnect` MCP is unavailable, say so early and continue with
  `kongctl-query`, repository artifacts, logs, or user-provided state.
- Preserve the repository's existing declarative toolchain. Do not convert the
  user between `decK`, `kongctl`, and Terraform unless they ask.
- Prefer current live state and current product docs over stale assumptions
  when behavior, product coverage, or limits may have changed.
- When a downstream CLI appears blocked by the agent environment, let the
  specialist tool skill handle sandbox retry guidance instead of classifying it
  as a product failure here.

These defaults are intentionally short. Specialist skills may restate the same
guidance because they can trigger directly without this router.

## Classification Order

### 1. Decide whether routing is needed at all

Bypass this router when the request already has one obvious owner.

Hand off directly when the user already named:

- a specialist workflow such as gateway triage, API publication, Event Gateway,
  or AI Gateway
- a declarative toolchain such as `kongctl`, Terraform, or `decK`
- a repo-authoring task that belongs to `kong-skill-authoring` rather than a
  Konnect product workflow

Use this router only when the request is broad, cross-surface, or still
ambiguous after the first read.

### 2. Decide whether this is diagnosis, inspection, or implementation

Classify the user's immediate need first:

- diagnosing current Konnect behavior
- asking for exact read-only inspection
- planning or authoring declarative changes
- asking which domain owns the problem

If the request is already a direct declarative-tool request, hand off to the
tool skill after checking whether a domain skill should diagnose first.

### 3. Route broad Konnect domain requests

Use one primary destination:

- `konnect-access-scope`
  - auth failures, missing permissions, wrong region, wrong org, role or team
    issues, resources that likely exist but cannot be seen or edited
- `konnect-control-plane-bootstrap`
  - creating a control plane, first-run topology, hosted versus self-hosted
    data plane choices, early ownership boundaries
- `konnect-gateway-triage`
  - disconnected data planes, config rollout problems, wrong control plane,
    live gateway drift, traffic failures that may be control-plane or
    data-plane related
- `konnect-observability-triage`
  - missing analytics, Explorer, Debugger, dataset visibility, observability
    gaps after traffic already exists
- `konnect-api-catalog`
  - managed APIs, versions, specs, packages, catalog readiness, governance
    state before publication
- `konnect-api-publish`
  - API publication from managed API through Catalog and Dev Portal,
    visibility gaps, published-but-not-discoverable problems
- `konnect-app-auth`
  - developer app registration, credentials, approval flows, auth strategies,
    published APIs that developers still cannot use
- `konnect-ai-gateway`
  - provider routing, AI Proxy setup, guardrails, prompt controls, token or
    latency issues, governance around LLM traffic
- `konnect-event-gateway`
  - listeners, clusters, auth setup, hostname mapping, routing or policy
    issues in Event Gateway

### 4. Route direct read-only inspection

Use `kongctl-query` when the user mainly needs:

- exact read-only command syntax
- list/get verification
- formatted CLI output
- auth verification without declarative changes

### 5. Route declarative implementation

After domain classification, preserve the toolchain already present in the repo:

- `kongctl-declarative`
  - `kongctl` YAML repos, plan/apply workflows, Konnect APIOps, adoption into
    `kongctl`
- `terraform-konnect`
  - HCL-managed Konnect resources, Terraform plan/apply/import workflows
- `deck-gateway`
  - Gateway entity config in `decK` state files, diff/sync/dump, Gateway-side
    config generation
- `terraform-kong-gateway`
  - self-managed Gateway entities managed through the official Terraform
    provider

If the user asks for config changes but the failure domain is still ambiguous,
route to the domain skill first and let it hand off to the tool skill once the
missing link is known.

## Routing Rules

- Do not send Portal visibility problems straight to `konnect-app-auth` if the
  API may not be published yet. Publication comes before consumer auth.
- Do not send managed-API governance or package questions straight to
  `konnect-api-publish` when the issue is upstream catalog readiness.
- Do not send disconnected data planes to declarative tool skills before
  gateway health is understood.
- Do not treat missing analytics as a gateway rollout problem until control
  plane, data plane, and traffic presence are reasonably confirmed.
- Do not assume access problems are product-state problems when the caller may
  simply be in the wrong org, region, or team scope.
- Do not keep repo skill-review or skill-authoring work in this router just
  because the word "Konnect" appears in the skill package path.

## Validation Checklist

Before handing off, verify that you can state:

- whether the request is broad enough to need routing at all
- whether the request is diagnosis, read-only inspection, implementation, or
  broad triage
- which Konnect domain or tool owns the problem first, and which nearest
  adjacent skill you ruled out
- whether live state inspection or repository state is the first source of
  truth
- whether an existing repo toolchain should be preserved
- which one downstream skill should own the next step and what fact it should
  prove first

## Output Style

When responding from this router:

- name the primary downstream skill explicitly
- explain the routing reason in one short paragraph
- mention `kong-konnect` MCP only when live state matters
- if routing confidence is low, name the missing fact that would separate the
  top two candidates instead of guessing
- avoid giving long step-by-step instructions that belong in the downstream
  skill
