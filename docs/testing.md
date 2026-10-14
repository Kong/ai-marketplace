# Testing

This repo favors lightweight checks over tool-driven install automation.

## Prerequisites

Start with the contributor bootstrap:

```bash
mise trust
mise install
mise run preflight
mise run deps
mise run hooks:install
```

Baseline local tools:

- `mise`
- `uv`
- `git`
- `node` and `npm` (routing evals and their tests; `mise install` provides the pinned Node)

`mise run preflight` checks the repo's baseline tools and can also check
optional flows:

- `mise run preflight -- publish` for `gh skill publish --dry-run`
- `mise run preflight -- shared-installers` for `npx skills` and `gh skill`
- `mise run preflight -- all` for a full local tool sweep

## Default Workflow

1. Run `mise run preflight`.
2. Run `mise run deps`.
3. Run `mise run hooks:install` once per checkout.
4. Run `mise run lint`.
5. Run `gh skill publish --dry-run` when you change skill metadata or prepare a release, or use `mise run ci` to include it in the standard CI path.
6. If you changed install docs, plugin manifests, or MCP config surfaces, manually verify only the affected tools.
7. Use a scratch project or disposable user profile when a tool writes local state.

Use the smallest path that covers the change. Most edits do not require every
check.

`mise run ci` also runs the submission packaging regression checks in
`scripts/test_openai_package.py`: archive boundaries, reproducibility, unsafe
paths, credentials, missing assets, discovery, and release ownership, plus the
routing eval unit tests (Python `scripts/test_routing_*.py` and
`scripts/test_select_changed.py`, and Node `evals/promptfoo/*.test.js`). None make model calls.

`mise run lint` covers more than generated-file drift. It is also the repo's
default authoring guardrail for:

- scaffold placeholders
- `SKILL.md` length
- description budget
- high-similarity trigger overlap between skills
- routing scenario validation (`scripts/validate_routing_scenarios.py`)

The checked-in `pre-commit` and `pre-push` hooks both run `mise run lint`, but
they only apply after `mise run hooks:install`. CI remains the enforcement path
for pull requests and pushes to `main`.

If a spot check exercises the shared MCP configuration, complete the host's
OAuth browser login. For a separate headless bearer-auth configuration, supply
the PAT/SPAT secret through the host's supported secret settings. Record which
client and install path were actually tested.

The shipped shared-skill payload lives under `plugins/kong-konnect/skills/`,
so install and publish checks should continue to reflect that source tree.

Run the repo tasks through `mise run ...`, not bare `uv ...`, when you want the
checked-in repo defaults. The `mise` config pins `uv` to Python `3.12` and
keeps the uv cache and managed Python installs under `.tmp/` instead of falling
back to user-profile locations.

## Routing Evals

`mise run eval:routing -- changed | skill <name> | all` runs the scenarios in
`evals/routing/` on each host through Promptfoo's native providers (Promptfoo,
SDKs, Node, and models are pinned in `package.json`, `package-lock.json`, and
`mise.toml`). It makes paid model calls. Claude and Codex are separate runs with
separate reports; one host failing never affects the other's result, and the
task exits non-zero if either failed.

- Modes: `skill <name>` runs one skill; `all` runs every skill that has
  scenarios; `changed [--base <ref>]` runs skills changed since the base
  (`scripts/select_changed.py`; default `origin/main`, else `main`) and skips,
  with a note, modified changed skills that have no scenarios (a changed skill that is
  new at the merge base and lacks the minimums is a validation failure instead, see below).
  No selected skills is a no-op success. Every selected skill runs; the worst
  exit code wins (see [Exit codes](#exit-codes)). The pilot corpus covers
  `konnect-platform-router`, `konnect-gateway-triage`, and `kongctl-declarative`.
- Adjacent skills (`select_changed.py`: routers, skills named in a changed `SKILL.md`, nearest
  descriptions; at most 5 and never the full catalog) are run by the workflow in addition to
  changed skills: only those that have scenarios, candidate-only (no control comparison), with
  `ROUTING_MAX_TRIALS=1` capping every scenario at one trial. They check that each adjacent
  skill's own expected/forbidden routes still hold; changed skills keep their scenario trials.
  Adjacent skills without scenarios are skipped with a note, and adjacent skills never run
  without a changed skill that has scenarios. `routing_targets.py adjacent` lists them.
- Agents: an *agent* is the agent runtime (Claude Code or Codex) that the spec and the result
  documents call a *host*; document keys and code identifiers keep the name `host`. Add
  `--agent claude|codex` (repeatable or comma-separated; default both) to `eval:routing` or
  `eval:routing:compare` to run a subset. Only the selected agents get workspaces, runs,
  retries, ceilings, and reports; an unknown name exits 2. A subset run is never a complete
  result: summaries and comparisons record `agents_run` and `partial: true`, the overall
  state covers only the agents run, and the console says `pass (partial: claude only)`.
  Without the flag a missing agent is still `infra_error`. CI never passes `--agent` and
  fails if a summary is partial. `mise run eval:routing:config` lists the selectable agents.
- Claude (`ANTHROPIC_API_KEY`): the agent only has the `Skill` tool. Evidence is
  a successful native skill call. Positives stop once it succeeds.
- Codex (local Codex login or `OPENAI_API_KEY`): read-only sandbox, no network,
  never asks for approval. Evidence is a successful command that reads
  `.agents/skills/<name>/SKILL.md` in the eval workspace (Promptfoo's
  `skillCalls`, source `heuristic`); final-answer mentions do not count. Codex
  cannot be limited to one tool, so the prompt confines it to that read.
- Reports land in `.tmp/routing/reports/<host>-<skill>.{json,html,junit.xml}`: per-trial
  scenario, host, expected/forbidden routes, observed skills (with path for
  Codex), and pass/fail reason.

### Host result states

Each host reduces to one state (`scripts/routing_results.py` documents the
output shape), written to `.tmp/routing/reports/<host>-<skill>.result.json`,
with a cross-host `<skill>.summary.json`:

- `pass`: every scenario met its route (at least 2/3 trials, rounded up).
- `routing_fail`: the host answered with valid telemetry but routed wrongly.
- `infra_error`: missing credentials, provider failure, malformed telemetry,
  or a reached ceiling (invalid scenarios exit 2 before any run). Trials are retried once; a persistent failure leaves the
  host incomplete, never `routing_fail`.

Results record the failure kind (`invocation`, `provider`, `telemetry`,
`ceiling`; `scenario_validation` only from library callers), retries per host, and per-trial evidence. A passing
host never offsets the other, and a host that is incomplete (for example a comparison
whose control run hit an `infra_error`) is `infra_error` even if its candidate passed;
`routing_fail` on any host still takes precedence.

### Exit codes

Every routing script and task (`run_routing_eval.py`, `run_routing_comparison.py`,
`mise run eval:routing`, `eval:routing:compare`) uses one table:

| Code | Meaning |
| --- | --- |
| 0 | `pass` |
| 1 | `routing_fail` |
| 2 | usage, scenario validation (including new-skill minimums), or harness error (unexpected exceptions are caught and exit 2) |
| 3 | `infra_error` (provider, telemetry, ceiling; result incomplete) |

When one task runs several skills, harness error (2) outranks `routing_fail` (1), which
outranks `infra_error` (3). `validate_routing_scenarios.py` and
`prepare_routing_workspace.py` also exit 2 on errors, so `mise run lint` still fails.

### Candidate vs merge-base comparison

`mise run eval:routing:compare -- <name> [--base <ref>]` (default `origin/main`)
evaluates the same scenarios, host configs, models, tools, and trial counts
against two isolated workspaces under `.tmp/routing/`: `candidate` (working-tree
skills) and `control` (skills at `git merge-base <ref> HEAD`). Only the
workspace differs. Each host gets `.tmp/routing/reports/<host>-<skill>.comparison.json`
with per-scenario and aggregate pass-rate deltas (candidate minus control;
shape in `scripts/routing_compare.py`). Deltas are reported, not gated, and no
score baseline is stored; the exit code reflects the candidate's own host state.

A skill absent at the merge base is new: control is skipped and each host is
judged on absolute thresholds (at least 90% positive recall, 95% near-miss
specificity) instead of a delta. New skills must also ship at least 5
positive, 5 near-miss, and 2 sibling scenarios per adjacent skill (at most 5
adjacent skills); violations are scenario validation failures before any model
call, exit 2. Their positive and near-miss scenarios must use `trials: 3`. Changed mode
(`routing_targets.py changed`) and the comparison driver enforce this, so a new skill
without a corpus cannot pass silently. Check them offline with
`uv run --python 3.12 --cache-dir .tmp/uv-cache python scripts/validate_routing_scenarios.py --new-skill=<name>`.

### Advisory workflow

`.github/workflows/skill-evals.yml` is separate from `validate.yml` and advisory:
do not make it a required check. It runs on pull requests only when a path under
`plugins/*/skills/**` changes. The `select` job then re-checks the base/head diff with
`scripts/routing_targets.py changed` (built on `select_changed.py`) and ends with no
provider call unless a changed skill has routing scenarios. It never selects the full
catalog, and changes to evals, docs, manifests, steering, or scripts never match the
path filter. `workflow_dispatch` takes one required `skill` name and compares it with
`origin/main`.

Each changed skill runs `mise run eval:routing:compare` in its own job; each adjacent
skill with scenarios runs `mise run eval:routing -- skill <name>` with one trial,
candidate-only. A `routing_fail` or `infra_error` becomes a warning annotation, not a
red job; exit 2 and any other code (harness or validation errors) fail the job. Provider keys come from the `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`
secrets, only in that step. The artifact `routing-reports-<mode>-<skill>` holds the full Promptfoo JSON
(`reports/{candidate,control}/<host>-<skill>.json` or `reports/<host>-<skill>.json`), whose
raw model responses and skill calls are the diagnostic transcript (no extra transcript
capture is enabled), plus HTML, JUnit, result and comparison documents, and Promptfoo logs; none are
committed. HTML and JUnit come from the first full run, while `*.result.json` and the
comparison reflect the state after the single retry (retried trials are in `*.retry.json`).
The job targets ten minutes (`timeout-minutes: 10`); jobs for one PR share a
concurrency group and `max-parallel` bounds paid jobs. Ceilings are described under
[Ceilings](#ceilings). Actions are pinned by commit SHA.

### Model and effort settings

The pinned defaults (Codex `gpt-5.5` at `low` effort, Claude `claude-sonnet-5-5` with the
provider's default effort) live in one file, `evals/promptfoo/settings.js`, which both host
configs, the harness, and the printer read. For local experiments only, override them:

- `ROUTING_CODEX_MODEL`, `ROUTING_CODEX_EFFORT` (becomes `model_reasoning_effort`)
- `ROUTING_CLAUDE_MODEL`, `ROUTING_CLAUDE_EFFORT` (Promptfoo's `anthropic:claude-agent-sdk`
  provider forwards `effort` to the Agent SDK; allowed: `low`, `medium`, `high`, `xhigh`, `max`)

Unset or empty means the pin. A malformed model id or an effort outside the provider's set
exits 2 before any run. Tool restrictions, sandbox, permissions, and budgets are fixed and not
configurable. Candidate and control inherit the same environment, so a comparison always
applies the same effective settings to both sides.

Every result, summary, and comparison document records `settings` (effective model and effort,
each marked `default` or `override`) and `overridden`, and the console summary shows them. Any
active override prints a warning and sets `overridden: true`; such results are not comparable
with CI. `mise run eval:routing:config -- [--json]` prints the effective settings per host, the
fixed discovery settings, trial policy, and ceilings with their variable names, offline and
without credentials.

CI always uses the pins: `skill-evals.yml` passes none of these variables and unsets them in
the eval step. Changing a pin is a reviewed edit to `settings.js`, supported by
`eval:routing:compare` evidence for the old and new setting.

### Ceilings

`scripts/routing_ceilings.py` enforces limits for every routing run, local or CI.
Defaults are in code; override with environment variables (in CI, repository
variables of the same name): `ROUTING_MAX_TOKENS` and `ROUTING_MAX_COST_USD`
(per host, across candidate, control, and retries), `ROUTING_MAX_CONCURRENCY`
(Promptfoo `--max-concurrency`), `ROUTING_RUN_TIMEOUT_SECONDS` (one Promptfoo run;
the run is killed), and `ROUTING_JOB_TIMEOUT_SECONDS` (whole eval; keep it below the
CI job timeout). Promptfoo reports tokens and cost only when a run ends, so those
ceilings are checked after each run and before every later launch: spend stops at
the next boundary and can overshoot by at most one run.

A breach makes the host `infra_error` (kind `ceiling`, incomplete, never
`routing_fail`, never retried). It is recorded in `breaches` in the result,
comparison, and summary documents, printed as `BREACH: ...` in the console, and
raised as a warning annotation in CI. Judged trials stay in the report but the
host result is not trusted. Each host reports `usage` (trials, tokens, estimated
cost, latency) and retries.

## Shared Skill Installers

### `npx skills`

- Install path: [docs/install/other-tools.md](./install/other-tools.md)
- Prerequisite: `node` and `npx`
- Command: `npx skills add kong/ai-marketplace`
- Expected result: install completes without errors and the `gateway-plugin-datakit` skill is available in the target host
- Quick prompt: `When should you use the gateway-plugin-datakit skill?`
- Cleanup: remove the installed skill from the scratch project or discard the scratch project

### `gh skill`

- Install path: [docs/install/other-tools.md](./install/other-tools.md)
- Prerequisite: GitHub CLI `v2.90.0+`
- Note: `gh skill` is in public preview
- Command: `gh skill install kong/ai-marketplace`
- Single-skill command: `gh skill install kong/ai-marketplace gateway-plugin-datakit`
- Expected result: install completes without errors and the `gateway-plugin-datakit` skill is available in the target host
- Quick prompt: `When should you use the gateway-plugin-datakit skill?`
- Cleanup: remove the installed skill from the target host or discard the scratch profile

## GitHub Skill Publish Dry Run

- Command: `gh skill publish --dry-run`
- Use when: skill frontmatter changes, you add a new skill, or you are preparing a release
- Expected result: the repo validates against the Agent Skills specification and GitHub's publish checks without publishing anything
- Notes: this catches issues your local validator may not model, such as recommended frontmatter fields and repository publish settings

## Security Notes

- Prefer `gh skill preview` before installing from GitHub.
- Use scratch projects or disposable profiles when a host writes local plugin or extension state.
- Store the PAT/SPAT secret in the host tool's secure settings flow when available.

## Tool Spot Checks

### Codex

- Install path: [docs/install/codex.md](./install/codex.md)
- Use a scratch project or disposable profile; add this checkout with `codex plugin marketplace add .`
- Install Kong Konnect from the repo marketplace in the desktop app and start a new chat
- Verify all shipped skills are visible and `gateway-plugin-datakit` can be invoked
- Connect the bundled `kong-konnect` server with OAuth; verify a catalog lookup without changing resources
- Confirm there is no duplicate manually configured MCP connection
- Cleanup: uninstall the plugin and remove the scratch marketplace/profile
- Packaging: run `mise run package:openai -- .tmp/kong-konnect-openai-plugin.zip` after staging package files; inspect `unzip -l` for all skills and referenced assets
- A local validation pass does not prove that OpenAI's submission portal accepts the ZIP

### Claude Code

- Install path: [docs/install/claude-code.md](./install/claude-code.md)
- Verify after install: `kong-konnect` appears as installed and `gateway-plugin-datakit` is available in a fresh session
- MCP check when using the plugin path: confirm `kong-konnect` is configured
- Quick prompt: `What Kong-specific skills are available in this environment?`
- Cleanup: uninstall the plugin or discard the scratch profile

### Cursor

- Install path: [docs/install/cursor.md](./install/cursor.md)
- Local plugin path: `~/.cursor/plugins/local/kong-konnect/`
- Use a copied directory for the local plugin smoke test; do not rely on a symlinked plugin directory
- Verify after install: `kong-konnect` appears as installed and `gateway-plugin-datakit` is available in a fresh session
- MCP check when using the plugin path: confirm `kong-konnect` is configured from `plugins/kong-konnect/mcp.json`
- Quick prompt: `What Kong-specific skills are available in this environment?`
- Cleanup: remove `~/.cursor/plugins/local/kong-konnect/` or discard the scratch profile

## When To Stop

You do not need to manually verify every tool for every change.

- Skill text only: `mise run lint` is usually enough.
- Tool-specific manifest or install doc: verify only that tool.
- Shared MCP config changes: verify one plugin-style path and one skill-plus-MCP path.
- Release prep: run `mise run lint` and spot-check the tools affected by the release.
- Release prep: also run `mise run ci` or `gh skill publish --dry-run`.
