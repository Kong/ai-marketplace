# Provider Routing

Use this file when the main issue is where AI traffic is being sent and why.

## Core Rule

Separate provider routing from higher-level governance. If traffic is hitting
the wrong model or provider, fix that layer before reasoning about guardrails
or prompt policy.

## Prove First

- the request is reaching the intended service and route
- the intended provider and model target are explicit, not inferred from the
  symptom
- any fallback or alternate routing behavior is an intentional design choice
- provider authentication failure is not being misread as routing drift

## Fast Classification

| Symptom | Prove next | Likely branch |
|---|---|
| Wrong model/provider receives traffic | intended route target and provider selection inputs | route targeting, plugin config, or fallback assumptions |
| Requests never reach provider | service/route path and provider auth | baseline proxy or auth problem, not policy |
| Only some model families misbehave | whether the failing requests share one provider path | provider-specific routing branch, not universal AI Gateway failure |
| One route works and another does not | whether the plugin stack differs by route | route-local AI Gateway config, not global outage |

## Decision Rules

- If the request never reaches the intended route or service, leave AI
  provider reasoning and hand off to generic gateway health if needed.
- If the provider is correct but auth fails, classify it as auth or secret
  management, not route targeting.
- If the provider/model changes only under specific conditions, explain the
  fallback rule or alternate path instead of calling it random behavior.
- If only one provider path is unhealthy, keep the diagnosis on that path
  rather than generalizing to all AI Gateway traffic.

## Return Shape

Return:

- whether the issue is route targeting, provider selection, fallback intent, or
  provider auth
- the next proving check that separates Kong-side routing from provider-side
  failure
- whether fallback behavior is expected or accidental
- whether the next step stays in AI Gateway or moves to generic gateway health
