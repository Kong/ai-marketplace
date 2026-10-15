# Issue tracker

GitHub Issues in `Kong/ai-marketplace` is the active tracker.

Always pass `--repo Kong/ai-marketplace` or `-R Kong/ai-marketplace` to `gh`
commands. Never infer the target from the working directory.

## Workflow metadata

Each workflow issue has exactly one kind:

- `bug`
- `feature`
- `task`
- `chore`
- `decision`
- `epic`

Each workflow issue has exactly one triage state:

- `needs-triage`
- `needs-info`
- `ready-for-agent`
- `ready-for-human`
- `wontfix`

Preserve unrelated labels. Pull requests are not a workflow request surface.

## Operations

- Create: `gh issue create -R Kong/ai-marketplace`
- Read: `gh issue view <number-or-url> -R Kong/ai-marketplace`
- List: `gh issue list -R Kong/ai-marketplace`
- Comment: `gh issue comment <number> -R Kong/ai-marketplace`
- Update: `gh issue edit <number> -R Kong/ai-marketplace`
- Close: `gh issue close <number> -R Kong/ai-marketplace`

An issue is published only after creation returns a URL and the issue can be
read back from `Kong/ai-marketplace`.
