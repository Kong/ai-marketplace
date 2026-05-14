# Scope and Time Window Checks

Use this file when missing data may be explained by the slice being inspected
rather than by broken ingestion.

## Core Rule

Prove that the operator is looking at the intended control plane, entity, and
time range before concluding that telemetry is absent.

## Inspection Order

1. Identify the subject of the claim:
   one control plane, one API, one service or route, one portal slice, or the
   whole organization.
2. Check whether the user expects all traffic or a filtered subset.
3. Align the time window with when the traffic or event actually happened.
4. Compare the selected slice with a wider or neighboring slice before calling
   it ingestion failure.

## Quick Questions

- Which control plane, API, service, route, or portal slice is in scope?
- Is the expectation for all traffic or only a named subset?
- Did traffic happen inside the selected time window?
- Is the user inferring org-wide failure from one narrow view?

## Common Patterns

| Symptom | Likely interpretation |
|---|---|
| Empty dashboard for one plane, data elsewhere | wrong plane or entity scope |
| "It was there yesterday" | time window or traffic recency mismatch first |
| Only some APIs show data | scoped entity mismatch or partial usage pattern |
| Data appears in a broader view but not the filtered one | filter or association mismatch, not global outage |

## Decision Rules

- If a wider slice shows the expected signal, do not call it ingestion
  failure; isolate the narrower filter or entity association instead.
- If the user cannot name the control plane or entity they expect to see, stop
  and resolve scope before deeper diagnosis.
- If the selected window does not include known traffic, treat the empty result
  as valid until proven otherwise.

## Return Shape

Return:

- which scope variable is wrong, if any
- whether the time window itself explains the symptom
- whether the issue can be resolved without treating it as ingestion failure
