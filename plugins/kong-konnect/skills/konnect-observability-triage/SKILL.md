---
name: konnect-observability-triage
description: Diagnose missing, partial, delayed, or mis-scoped Konnect observability data across analytics, Explorer, and Debugger. Use when the question is dataset, scope, or telemetry visibility, not pure gateway health or operator-access troubleshooting.
license: MIT
metadata:
  product: konnect
  category: observability
  tags:
    - kong
    - konnect
    - analytics
    - observability
    - debugger
---

# Konnect observability triage

## Goal

Explain why Konnect observability data is missing, partial, delayed, or scoped
unexpectedly, and direct the operator to the right dataset and next action.

Default to proving traffic and scope before concluding that observability is
broken.
This skill owns observability diagnosis, not generic gateway connectivity,
portal publication, or operator-access troubleshooting.

## Tool Selection

- Use the shared `kong-konnect` MCP server for live inspection of the relevant
  Konnect surface when available.
- Use `kongctl-query` for read-only checks on organizations, control planes,
  APIs, and adjacent resources that determine where telemetry should appear.
- Preserve the repository's chosen declarative toolchain if the investigation
  turns into a configuration change rather than an observability diagnosis.
- Use `konnect-access-scope` when the problem is primarily who can see the
  data.
- Use `konnect-gateway-triage` when the real issue is no traffic or unhealthy
  gateway connectivity.
- If live Konnect state matters and `kong-konnect` MCP is not connected, say
  so early and continue with CLI or user-provided artifacts.

## References To Load

Load only the reference file that matches the active branch:

- `references/dataset-map.md`
  - Load when the user may be looking in the wrong observability surface for
    the question they are asking.
- `references/scope-time-window-checks.md`
  - Load when the likely issue is wrong control plane, entity, slice, or time
    range rather than ingestion failure.
- `references/visibility-vs-ingestion.md`
  - Load when data may exist but is delayed, permission-limited, partially
    visible, or confused with total loss.

## Inspection Order

### 1. Classify the expected signal first

Clarify what the user expects to see:

- aggregate analytics or trend data
- Explorer or other queryable usage data
- Debugger traces or request-level details
- API-oriented dataset visibility
- LLM-oriented dataset visibility
- platform or administrative activity data

Do not assume these are interchangeable. Missing data often starts with the
wrong surface selection or the wrong granularity of evidence.

Load `references/dataset-map.md` when the operator is mixing API, LLM, and
platform observability surfaces.

### 2. Verify scope, subject, and time window

Confirm:

- which control plane, API, portal, or service is in scope
- which time range the user is looking at
- whether the expectation is for all traffic or only a subset
- whether the user expects organization-wide visibility or a narrower slice

Many empty dashboards are valid results for the chosen scope or time window.

Load `references/scope-time-window-checks.md` when the likely problem is the
slice being inspected rather than the telemetry itself.

### 3. Prove underlying activity exists

Before diagnosing telemetry ingestion, verify that the thing being observed is
actually receiving traffic or events.

- If traffic is absent, hand off to `konnect-gateway-triage`.
- If the real question is whether an API or portal object exists or is
  published, hand off to `konnect-api-catalog` or `konnect-api-publish`
  instead of staying in observability.
- If activity exists but no data appears, keep following the observability
  path.
- If only some entities show data, keep scope and dataset mismatches in play.

### 4. Match the request to the correct dataset

Use the simplest mapping that fits the symptom:

- API runtime questions belong in API or gateway-oriented observability
  surfaces.
- LLM runtime questions belong in LLM-specific datasets and views.
- Platform-operation questions belong in platform-level datasets or audit-like
  views rather than API traffic analytics.

If the user is looking in the wrong dataset, say so explicitly instead of
calling it missing data.

### 5. Check configuration and visibility boundaries

Investigate whether missing data is caused by:

- analytics or debugging not being enabled where expected
- the wrong control plane or managed entity being inspected
- permissions limiting dataset visibility
- partial rollout or resource association issues

Keep "configuration missing" separate from "viewer cannot see it."
Prefer the narrowest explanation that matches the evidence. Do not jump from
one empty view to a global ingestion claim.

Load `references/visibility-vs-ingestion.md` when the hard question is whether
the data is absent, delayed, hidden, or only partially scoped.

### 6. Return the smallest credible root cause

Classify the issue as:

- no underlying traffic or events
- wrong time window or scope
- wrong dataset or product surface
- permission-limited visibility
- configuration or association issue
- partial data rather than total data loss

## Konnect-Specific Gotchas

- API, LLM, and platform datasets are not interchangeable.
- Empty data for one control plane does not imply global analytics failure.
- Partial visibility can be a permissions outcome, not an ingestion outage.
- Debugging surfaces and aggregate analytics answer different questions; one
  can be empty while the other remains useful.
- Operators often blame ingestion when the real problem is that traffic never
  reached the intended gateway path.

## Validation Checklist

Before answering, verify that you can state:

- which observability surface the user actually needs
- which control plane, API, or entity is in scope
- whether underlying traffic or events exist
- whether the likely issue is scope, dataset selection, permissions, or
  configuration
- which neighboring skill should take over if this is not truly an
  observability problem

## Handoffs

- Use `konnect-gateway-triage` when the root problem is absent or unhealthy
  runtime traffic.
- Use `konnect-access-scope` when the data likely exists but the caller cannot
  see it.
- Use `konnect-api-catalog` or `konnect-api-publish` when the real issue is
  object readiness or publication state rather than telemetry.
- Use `kongctl-query` for exact resource inspection commands that support the
  diagnosis.
