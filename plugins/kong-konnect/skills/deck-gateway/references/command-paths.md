# Command Paths

Use this file when the main question is which `decK` path matches the user's
intent. Do not load it as a general `decK` command catalog.

## Core Rule

Pick the smallest `decK` path that answers the request. Do not jump from
"inspect drift" to `sync`.

## Intent Map

| Intent | Default path |
|---|---|
| Check syntax or file validity | `deck file` or `deck gateway validate` |
| Compare intended vs live state | `deck gateway diff` |
| Apply intended state | `deck gateway sync` |
| Export live Gateway config | `deck gateway dump` |
| Generate config from OpenAPI | `deck file` generation workflow |

## Decision Rules

- If the repo-owned file, include boundary, or tag boundary is still unclear,
  stop and identify that slice before picking `diff`, `dump`, or `sync`.
- Prefer `diff` before `sync` unless the user explicitly wants immediate
  mutation.
- Prefer scoped generation or scoped edits over full re-dumps.
- Treat `dump` as an inspection tool, not as proof that the repo should be
  overwritten with its output.
- Treat OpenAPI generation as scaffolding. The next step is to fit the result
  back into the repository's existing state shape.

## What To Return

Return:

- which `decK` command path matches the request
- whether the next step is inspect-only or mutating
- whether a different tool skill should take over
