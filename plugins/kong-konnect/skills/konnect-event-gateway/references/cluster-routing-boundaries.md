# Cluster Routing Boundaries

Use this file when the main ambiguity is how a listener path maps through
virtual and backend clusters.

## Core Rule

Once listener reachability is sound, verify that the virtual cluster points to
the intended backend cluster before blaming policy.

## Decision Rules

| Symptom | Likely interpretation | What to check next |
|---|---|
| Right listener, wrong downstream behavior | wrong virtual/backend cluster relationship | whether the virtual cluster actually targets the expected backend cluster |
| Listener looks healthy but nothing useful happens | missing backend association | whether the object chain is complete beyond the listener |
| Some routes behave, others do not | partial cluster mapping or object-chain mismatch | whether only one listener or hostname path points at the intended backend |

## What To Prove

Prove each of these in order:

- the client entered the intended listener path
- the listener is attached to the intended virtual cluster
- the virtual cluster resolves to the backend cluster the operator expected

Only escalate to policy after the cluster chain is proven.

## What To Return

Return:

- whether the virtual cluster is correct
- whether the backend target is the intended one
- what proved policy is not the first failing hop
- whether policy should still be evaluated after routing is proven
