---
name: konnect-event-gateway
description: Use when diagnosing Konnect Event Gateway request flow across listeners, hostname mapping, virtual/backend clusters, auth, and policy evaluation. Exclude generic gateway health, org access control, and declarative implementation after the failing hop is known.
license: MIT
metadata:
  product: konnect
  category: event-gateway
  tags:
    - kong
    - konnect
    - event-gateway
    - listeners
    - policies
---

# Event Gateway operator workflow

## Goal

Troubleshoot Event Gateway using its own entity model instead of forcing it
into standard gateway assumptions.

Default to following the request path end to end:
client -> listener -> virtual cluster -> backend cluster -> policy and auth

Own the diagnosis of the failing Event Gateway hop. Hand off implementation or
non-Event-Gateway platform problems once that hop is clear.

## Tool Selection

- Use the shared `kong-konnect` MCP server first for live Event Gateway
  inspection.
- Use `kongctl-query` for read-only resource checks and concise summaries where
  the CLI surface is available.
- Preserve the repository's chosen declarative toolchain when Event Gateway
  resources need to change. Prefer `kongctl-declarative` for `kongctl` YAML
  and `terraform-konnect` when the required Event Gateway resources are already
  managed in HCL.
- Hand off early to `konnect-gateway-triage` when the blocker is generic
  control-plane, data-plane, or rollout health rather than Event Gateway path
  semantics.
- If live Konnect state matters and `kong-konnect` MCP is not connected, say
  so early and continue with CLI or user-provided artifacts.

Do not reuse generic gateway triage blindly. Event Gateway deserves a dedicated
inspection order because the operator objects differ.

## References To Load

Load only the reference file that matches the active branch:

- `references/event-path-map.md`
  - Load when the operator only has a symptom and you need to map the failing
    hop across listener, virtual cluster, backend cluster, auth, and policy.
- `references/listener-and-hostname-mapping.md`
  - Load when the likely issue is listener reachability, hostname mapping, TLS,
    or protocol assumptions.
- `references/cluster-routing-boundaries.md`
  - Load when virtual-cluster to backend-cluster routing intent is the hard
    part.
- `references/auth-and-policy-order.md`
  - Load when clients connect but get denied, rewritten, or otherwise fail
    after reachability is already proven.

## Inspection Order

### 1. Identify the failing event path

Clarify:

- which Event Gateway control plane is in scope
- which listener the client reaches
- which hostname or endpoint the client uses
- which virtual cluster and backend cluster should receive the traffic
- whether the failure is connection, routing, auth, or policy related
- what exact observed symptom proves the failure

Keep the path concrete before inspecting objects.

Load `references/event-path-map.md` when the symptom is still too vague to pick
the right Event Gateway hop.

### 2. Confirm control plane and object presence

Verify the required objects exist in the same intended environment:

- Event Gateway control plane
- backend cluster
- virtual cluster
- listener
- policy objects
- auth-related objects or bindings

If these objects do not line up in the same scope, stop there and call out the
broken chain.

### 3. Validate listener reachability and mapping

For connection-oriented symptoms, inspect:

- listener hostname or endpoint mapping
- protocol or port assumptions
- TLS or certificate expectations
- whether the listener is attached to the expected virtual cluster path

Do not treat a TCP or protocol-level connect as proof that the request is
authorized or routed correctly.

Load `references/listener-and-hostname-mapping.md` when the real question is
whether the listener path itself is the wrong one.

### 4. Check cluster routing intent

Once the listener is correct, verify that the virtual cluster points at the
intended backend cluster and that the backend target is the one the operator
expects.

Use this step to separate:

- wrong-cluster routing
- missing backend associations
- healthy reachability with broken policy enforcement

Load `references/cluster-routing-boundaries.md` when the routing chain from
virtual to backend cluster is the main ambiguity.

### 5. Evaluate auth and policy separately from connectivity

If clients can reach the listener but fail afterward, inspect:

- auth setup and credential expectations
- policy bindings and evaluation order
- hostname- or listener-specific policy attachment
- whether the client identity matches the policy assumptions

This is the default path for "connects but gets denied" reports.

Load `references/auth-and-policy-order.md` when reachability is proven and the
remaining issue is auth or policy evaluation.

### 6. Return a single failure domain with proof

Diagnose one primary operator break:

- wrong control plane or environment
- missing object in the Event Gateway chain
- listener or hostname mapping problem
- backend or virtual cluster routing problem
- auth mismatch
- policy attachment or evaluation problem

State the evidence that ruled out the neighboring hops. Avoid reporting
multiple equally-weighted guesses.

## Konnect-Specific Gotchas

- Successful connection to a listener does not prove policy success.
- Hostname and listener mismatches can look like auth failures from the client
  side.
- Virtual cluster and backend cluster confusion can produce correct-looking
  listeners with wrong downstream routing.
- Generic gateway debugging often misses Event Gateway-specific object
  relationships and leads to noisy advice.
- The right operator question is often "which hop failed?" rather than
  "is Event Gateway up?"

## Validation Checklist

Before answering, verify that you can state:

- the full intended event path
- which Event Gateway objects are present
- whether the listener mapping is correct
- whether the failure is routing, auth, or policy related
- what evidence rules out the adjacent hops
- whether the next action belongs in `kongctl-declarative`,
  `terraform-konnect`, `konnect-access-scope`, or
  `konnect-gateway-triage`

## Handoffs

- Use `konnect-access-scope` when the issue is who can view or administer Event
  Gateway resources.
- Use `konnect-gateway-triage` when the real problem is generic Konnect Gateway
  health, rollout, or connectivity outside Event Gateway object relationships.
- Use `kongctl-declarative` or `terraform-konnect` when the operator wants to
  encode or apply the Event Gateway fix declaratively. Match the repository's
  current toolchain.
- Use `kongctl-query` for exact read-only command selection while inspecting
  Event Gateway resources.
