# Output Shaping

Use this file when the main problem is how to return read results cleanly.

## Core Rule

Prefer structured output for inspection, then summarize only the fields the
user actually needs.

## Defaults

- use JSON unless YAML is explicitly requested
- use explicit `-o json` or `-o yaml` to avoid profile/env surprises
- summarize IDs, names, states, timestamps, and the minimum fields needed to
  answer the question

Use `text` output only when the user explicitly wants it and no `--jq` filter
is involved.

## Decision Rules

- If the user wants machine-shaped results, preserve structure.
- If the user wants a concise explanation, summarize after inspection instead
  of switching to text-mode guessing.
- If the result is large, filter conceptually in the response even if the CLI
  output is structured and verbose.

## `--jq` Use

- Use `--jq <expression>` on `get` queries when shaping the response is cheaper
  than post-processing in prose.
- Keep `-o json` or `-o yaml` explicit when `--jq` is present.
- Quote the expression with single quotes to avoid shell parsing surprises.
- If `kongctl` reports that `--jq` only works with JSON or YAML output, rerun
  the same command with `-o json` before changing anything else.

Minimal examples:

```bash
kongctl get portals -o json --jq 'map({id, name, display_name})'
kongctl get me -o json --jq '{id, email}'
```

## Profile and Environment Overrides

- Profile config and `KONGCTL_*` environment variables can change default
  output behavior.
- When formatting is surprising, inspect only the relevant overrides instead of
  assuming the command shape is wrong.

Useful checks:

```bash
env | grep '^KONGCTL_.*OUTPUT'
env | grep '^KONGCTL_PROFILE'
```

## What To Return

Return:

- the output format used
- the key fields that answer the question
- any profile/env caveat that may have affected formatting
