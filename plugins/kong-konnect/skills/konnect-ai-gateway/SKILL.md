---
name: konnect-ai-gateway
description: Operate Konnect AI Gateway request flow, provider/model routing, AI Proxy behavior, prompt/response controls, and LLM analytics. Use when the issue is inside AI Gateway, not generic prompt engineering, provider SDK debugging, or non-AI Gateway rollout.
license: MIT
metadata:
  product: konnect
  category: ai-gateway
  tags:
    - kong
    - konnect
    - ai-gateway
    - llm
    - ai
---

# Konnect AI Gateway triage

## Goal

Diagnose the narrowest Konnect AI Gateway failure layer across request path,
provider targeting, AI policy, and AI-runtime visibility.

Use this skill for AI Gateway operator workflows, not for generic
prompt-engineering, provider SDK debugging, or model-quality evaluation.

## Tool Selection

- Use the shared `kong-konnect` MCP server first for live inspection of control
  planes, Gateway entities, and LLM analytics surfaces.
- Prefer LLM-specific analytics when the user is asking about token usage,
  latency, or AI request health. Use the LLM analytics MCP/query surface when
  AI-runtime data is the real question rather than generic API analytics.
- Preserve the repository's chosen declarative toolchain for implementation:
  `deck-gateway` for Gateway-entity GitOps, `terraform-konnect` for HCL-managed
  Konnect AI Gateway resources, `terraform-kong-gateway` for self-managed HCL,
  and `kongctl-declarative` only when the surrounding Konnect repo already uses
  that path.
- If live Konnect state matters and `kong-konnect` MCP is not connected, say so
  early and continue with repo config or user-provided artifacts.
- Hand off early to `konnect-gateway-triage` when the blocker is generic
  gateway reachability, rollout, or route/service health rather than an
  AI-specific layer.

## References To Load

Load the first matching reference. Do not load all three by default:

- `references/provider-routing.md`
  - Load when the main question is model/provider selection, route targeting,
    fallback, or provider-specific request behavior.
- `references/guardrails-and-policy-intent.md`
  - Load when traffic works technically but policy intent, prompt shaping, or
    governance behavior looks wrong.
- `references/observability-and-cost-signals.md`
  - Load when the question is about tokens, latency, AI-specific analytics, or
    operational visibility rather than request construction.

## Inspection Order

### 1. Classify the report before choosing a layer

Place the first symptom in one branch:

- provider routing or model targeting
- service / route setup for AI traffic
- AI Proxy or AI Proxy Advanced behavior
- prompt or response guardrails
- prompt decoration or template behavior
- semantic cache behavior
- LLM usage, latency, or token visibility
- generic gateway reachability or config rollout that only happens to affect AI
  traffic

Do not flatten all AI Gateway issues into “the plugin is broken.”

If the complaint is fundamentally about ordinary route or service health, hand
off to `konnect-gateway-triage` before diagnosing AI controls.

### 2. Prove the baseline AI traffic path

First prove:

- the AI request reaches the expected service and route
- the AI proxy layer is attached where the operator expects
- provider authentication expectations are clear
- the intended provider and model target are known, not assumed

Only then reason about higher-level AI policies such as prompt guards or
templates.

If the request never reaches the provider path cleanly, stay below the
guardrail layer and keep provider-routing or gateway-health branches in play.

### 3. Resolve provider or model targeting before policy

For governed LLM traffic, inspect the stack in this order:

- base AI proxying
- routing and model/provider selection
- authentication and access controls
- prompt decoration or template injection
- prompt / response guardrails
- semantic caching or other acceleration layers

This prevents chasing a guardrail symptom when the route or provider layer is
wrong.

Load `references/provider-routing.md` when the operator is asking where traffic
went, whether fallback occurred, or whether the wrong model/provider answered.

### 4. Evaluate policy layers only after proxying is proven

Once baseline proxying and targeting are credible, separate:

- prompt decoration or template injection errors
- prompt or response guardrail mismatches
- semantic cache behavior
- provider/model behavior outside Kong-side control

Load `references/guardrails-and-policy-intent.md` when the operator needs to
separate technically valid traffic from policy-valid traffic.

### 5. Use LLM analytics for AI-specific runtime questions

If the question is about usage, tokens, latency, or cost-like behavior, prefer
the LLM analytics surface over generic API analytics.

Use AI-specific observability to answer:

- whether requests are reaching the AI Gateway
- whether token usage aligns with expectations
- whether latency or error rates are concentrated by route, provider, or model

Load `references/observability-and-cost-signals.md` when the real problem is
runtime visibility, token behavior, or latency concentration.

### 6. Distinguish Kong-side governance from provider behavior

When a request reaches the provider but still behaves incorrectly, separate:

- Kong-side routing and policy intent
- provider-side model behavior
- prompt construction effects
- authorization or key-management assumptions

Do not promise that every bad model response is a Gateway bug.

### 7. Return the narrowest AI failure domain

Classify the issue as:

- route or service setup problem
- AI proxy / provider configuration problem
- auth or secret-management problem
- prompt decoration / template problem
- guardrail policy problem
- semantic cache or acceleration problem
- analytics / visibility problem rather than traffic failure
- generic gateway health problem that should leave this skill

## Konnect-Specific Gotchas

- AI Gateway is still a Gateway surface first: route, service, and plugin
  placement still matter.
- Prompt and response guardrails extend a working AI proxy path; they do not
  replace it.
- LLM analytics should be treated as a distinct runtime surface from generic API
  analytics.
- A technically successful provider response can still violate policy intent.
- Provider-side refusals, quotas, or model behavior can pass through a healthy
  AI Gateway path; prove the Kong-side intent before calling them Gateway
  defects.
- Quickstarts are useful for proving baseline capability, but they are not a
  substitute for a durable AI Gateway operating model.

## Validation Checklist

Before answering, verify that you can state:

- which AI Gateway layer is failing
- whether baseline proxying works before higher-level AI controls
- which service/route and provider/model target the request is supposed to hit
- whether fallback or alternate provider selection is intended or accidental
- whether the issue is Kong-side routing, auth, guardrails, prompt shaping,
  caching, provider behavior, or analytics
- whether LLM analytics or another observability surface is the right next
  step
- which declarative tool skill should own the resulting change

## Handoffs

- Use `konnect-observability-triage` when the main issue is dataset visibility
  rather than AI Gateway behavior itself.
- Use `konnect-gateway-triage` when the real blocker is generic Gateway
  connectivity or config rollout rather than an AI-specific layer.
- Use `deck-gateway`, `terraform-konnect`, `terraform-kong-gateway`, or
  `kongctl-declarative` when the operator wants to encode or apply the AI
  Gateway change as config.
