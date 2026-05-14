# Guardrails and Policy Intent

Use this file when AI traffic succeeds technically but still violates the
operator's intended policy, prompt behavior, or governance model.

## Core Rule

Do not confuse "provider returned a response" with "the policy worked." Policy
intent sits above baseline proxy success.

## Useful Distinctions

| Branch | Meaning |
|---|---|
| Baseline proxy success | request reached the provider and returned |
| Prompt shaping issue | prompt decoration/template behavior is wrong |
| Guardrail issue | the control should have allowed/blocked/rewritten differently |
| Model behavior issue | the provider/model output itself is not what the operator wants |

## Decision Rules

- If the request never reached the provider, stay below the guardrail layer.
- If the request reached the provider but the output violates policy intent,
  keep the diagnosis on prompt/guardrail behavior before calling it a model
  bug.
- If the provider behaved unexpectedly despite correct prompt shaping, say that
  not every bad response is a Kong defect.

## Return Shape

Return one primary explanation:

- prompt shaping error
- guardrail policy mismatch
- model/provider behavior outside Kong-side control
