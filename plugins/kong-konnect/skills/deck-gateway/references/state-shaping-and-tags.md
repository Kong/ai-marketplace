# State Shaping and Tags

Use this file when the hard part is how `decK` state is partitioned, tagged, or
scoped in the repository.

## Core Rule

Preserve the repository's existing state shape unless migration is the task.
Ownership boundaries are part of the config, not just presentation.

## Common Patterns

| Pattern | Implication |
|---|---|
| Split by environment | keep new entities in the environment-owned file set |
| Split by service or domain | add only the entities needed for that boundary |
| Tags used for ownership | preserve tag scoping in diff/sync paths |
| CI wrapper scripts present | match the wrapper flow instead of inventing direct commands |

## Decision Rules

- Prefer additive narrow edits over broad regrouping.
- If tags determine selective sync, treat them as operational boundaries, not
  decorative metadata.
- Treat include files and wrapper scripts as ownership boundaries too. Match
  the existing entrypoint instead of bypassing it with a broader command.
- If the existing split is imperfect but stable, avoid opportunistic
  restructuring during a narrow task.

## What To Return

Return:

- which file or slice should own the new change
- whether tag scoping affects the apply path
- whether a repo refactor is optional rather than required
