# Event Path Map

Use this file when the operator starts with a symptom instead of a clear Event
Gateway failure hop.

## Core Rule

Follow the event path end to end:

client -> listener -> virtual cluster -> backend cluster -> auth/policy

Do not start with policy or credentials when the listener hop is still
uncertain.

## Questions That Collapse Ambiguity

Clarify these first:

- what endpoint or hostname the client used
- whether the failure was no connect, wrong downstream behavior, or denial
- which virtual cluster and backend cluster were expected
- whether the operator can name the exact control plane in scope

## Symptom Map

| Symptom | Most likely hop | What to disprove next |
|---|---|
| Cannot connect at all | listener and hostname branch | wrong control plane or endpoint assumption |
| Connects but wrong backend behavior | cluster routing branch | listener mismatch masquerading as downstream failure |
| Connects but denied | auth/policy branch | wrong listener or hostname before chasing credentials |
| Objects seem present but nothing lines up | control plane and object-chain verification first | that the resources actually belong to one Event Gateway path |
| Some clients work and others fail | compare listener and hostname mapping first | partial routing or policy attachment only after the path matches |

## What To Return

Return:

- which hop is most likely failing
- which deeper reference branch should be loaded next
- which adjacent hop was ruled out already
- whether this is still Event Gateway-specific or has become a broader access problem
