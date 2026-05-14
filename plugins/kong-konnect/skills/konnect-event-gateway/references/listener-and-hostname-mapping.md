# Listener and Hostname Mapping

Use this file when the likely issue is how clients reach the Event Gateway
listener.

## Core Rule

Treat listener reachability as separate from downstream authorization and
routing correctness.

## Questions To Clarify

- which hostname or endpoint the client uses
- which listener should receive that traffic
- whether protocol/port/TLS expectations match the listener configuration
- whether the listener is attached to the intended virtual cluster path

## Decision Rules

Use these splits:

- no connection or TLS negotiation failure: stay on listener and hostname
  mapping first
- successful connect with wrong downstream behavior: prove the listener path,
  then move to cluster routing
- successful connect with denial: prove the listener path before treating it as
  an auth or policy problem

## Common Misreads

| Symptom | Better interpretation |
|---|---|
| TCP connect succeeds | does not prove auth or policy success |
| Client says auth failed | may still be wrong hostname or wrong listener path |
| TLS error | listener/certificate assumption first, not policy |

## What To Return

Return:

- whether the listener mapping is correct
- whether hostname/protocol/TLS is the blocker
- what evidence shows the request reached the intended listener
- whether the next branch is routing or auth/policy
