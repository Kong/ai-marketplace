# Auth and Scope Checks

Use this file when a read-only query problem may actually be auth, profile,
region, or scope related.

## Core Rule

Do not assume a failed query means the resource path is wrong. Prove auth and
scope first.

## Quick Checks

- `kongctl version`
- `kongctl get organization -o json`
- `kongctl get me -o json`
- inspect `--profile` use and relevant `KONGCTL_*` overrides

Authentication defaults:

- Prefer `kongctl login` for interactive sessions.
- Use PAT or SPAT environment variables for non-interactive sessions only.
- Never echo or paste token values back into logs or responses.

Scope checks:

- Confirm whether a non-default `--profile <name>` is required.
- Treat org, region, and parent-resource boundaries as separate proof steps.
- If one read works and another is empty, do not assume the second path is
  invalid until the target scope is proven.

## Common Misreads

| Symptom | Likely interpretation |
|---|---|
| Empty results unexpectedly | wrong profile, region, or org slice |
| Query fails broadly | auth or endpoint problem |
| One resource family is visible, another is not | scope/product-surface issue, not always CLI syntax |

## Useful Narrow Follow-Ups

Use the smallest follow-up that isolates the context problem:

```bash
kongctl get organization -o json
kongctl get me -o json
```

If output defaults or profile behavior may be hiding the real problem, inspect:

```bash
env | grep '^KONGCTL_'
```

## What To Return

Return:

- whether auth/scope is proven
- whether the query issue is environmental rather than structural
- whether another skill should take over once access is understood
