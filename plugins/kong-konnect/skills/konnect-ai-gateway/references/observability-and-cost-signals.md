# Observability and Cost Signals

Use this file when the operator is asking about token usage, latency, error
concentration, or other AI-specific runtime signals.

## Core Rule

Prefer AI-specific analytics for AI-runtime questions. Generic API analytics
are not the best source for token or model-level interpretation.

## Questions This File Helps With

- are requests reaching AI Gateway at all
- does token usage align with the expected route/provider/model
- is latency concentrated by provider, model, or route
- are AI errors concentrated by one policy layer or runtime path

## Common Misreads

| Symptom | Better interpretation |
|---|---|
| "Gateway is slow" | latency may be concentrated by one provider/model path |
| "Cost looks wrong" | token behavior should be read from AI-specific analytics, not only generic request counts |
| "No AI data" | confirm the question is actually about AI-specific surfaces rather than normal API analytics |

## Return Shape

Return:

- whether the real issue is traffic absence, token behavior, latency
  concentration, or visibility
- which AI runtime slice best explains the symptom
- whether to stay in AI Gateway or hand off to broader observability triage
