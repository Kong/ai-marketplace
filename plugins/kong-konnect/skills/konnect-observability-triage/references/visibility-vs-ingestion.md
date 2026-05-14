# Visibility vs Ingestion

Use this file when the main question is whether data truly is missing or merely
not visible to this caller or in this surface yet.

## Core Rule

Keep these separate:

- no underlying traffic/events
- data exists but is permission-limited
- data exists but the user is in the wrong scope
- data is delayed or partial
- data is genuinely absent because configuration or association is wrong

## Proving Order

1. Confirm that underlying traffic or events exist for the claimed slice.
2. Compare what different viewers or roles can see before blaming ingestion.
3. Compare a broader and narrower scope to separate visibility from total
   absence.
4. Check whether the expected analytics or debugging capability is enabled and
   associated with the intended entity.
5. Only after those checks, treat "nothing appears anywhere" as a genuine
   ingestion or configuration-path concern.

## Diagnostic Split

| Signal | Likely branch |
|---|---|
| Some users see it, others do not | permissions or visibility |
| Some datasets have data, others do not | wrong surface or configuration boundary |
| Small delay after known traffic | delay/partial visibility first, not immediate outage claims |
| Nothing appears anywhere for proven traffic | configuration, association, or ingestion path problem |
| Broader scope has data but filtered scope does not | mis-scoped or partially associated resource |

## Decision Rules

- If one principal can see the data and another cannot, hand off toward
  `konnect-access-scope` instead of treating it as telemetry loss.
- If only one dataset is empty, prove the surface choice and entity
  association before escalating to ingestion.
- If the evidence supports delay or partial visibility, say that explicitly
  instead of collapsing it into a binary present-or-absent answer.

## Return Shape

Return one primary explanation:

- no traffic/events
- visibility-limited
- delayed/partial
- mis-scoped
- configuration or association issue
