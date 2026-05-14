# Auth and Policy Order

Use this file when clients can reach the listener but fail afterward due to
auth or policy behavior.

## Core Rule

Do not debug policy before proving the path is correct, and do not treat a
denial as a listener failure once reachability is known.

## Decision Rules

| Branch | Meaning | Fast proving check |
|---|---|
| Auth mismatch | credentials or identity do not match expectations | the client reached the right listener and the identity assumptions are explicit |
| Policy attachment issue | policy is bound to the wrong listener/hostname/path | the denial changes when the request enters through a different listener or hostname |
| Policy evaluation issue | the right policy is attached but the outcome is still wrong | attachment looks correct and the remaining ambiguity is rule ordering or rule intent |

## What To Separate

Separate these before suggesting fixes:

- identity or credential mismatch versus policy denial
- wrong listener or hostname path versus correct path with wrong policy outcome
- Event Gateway policy behavior versus broader Konnect operator-access problems

## What To Return

Return:

- whether the failure is auth or policy first
- whether attachment order or evaluation order is the likely cause
- what proved the listener and routing path were already correct
- whether `konnect-access-scope` should own the next step
