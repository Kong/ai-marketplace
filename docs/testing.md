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

Routing evals check that the right skill activates for a request (and the wrong ones do not).
Scenarios live in `evals/routing/`; Promptfoo's native providers run them on each *agent*
(Claude Code and Codex, separate runs and reports; Promptfoo, SDKs, Node, and models are
pinned in `package.json`, `package-lock.json`, and `mise.toml`). Runs make paid model calls. In CI
they can gate merges through the merge queue, but only once an admin makes the check required
(see [Merge gate workflow](#merge-gate-workflow)); until then they are advisory.

### Add evals for a skill

Create `evals/routing/<skill>.yaml` (one file per target skill). A tiny annotated example:

```yaml
skill: my-skill                  # the skill under test
scenarios:
  - id: my-skill-positive-1      # unique across all files, kebab-case
    prompt: "Realistic user request in the user's own words."
    expect: [my-skill]           # skills that must activate
    forbid: []                   # skills that must not activate
    trials: 3                    # 1-5 runs per agent; a scenario passes with >= 2/3 of them
    tags: [positive]             # positive | near-miss | sibling
```

- `positive`: expects the skill. `near-miss`: plausible but out of scope, so it forbids the
  skill. `sibling`: expects a neighbouring skill and forbids this one.
- A **new** skill needs at least 5 positive and 5 near-miss scenarios (`trials: 3`) and at least 2
  sibling scenarios for each adjacent skill (up to 5 adjacent skills). Write prompts as a user
  would, not by copying the skill description's wording (guidance; not machine-checked).
- To extend an **existing** skill, append scenarios to its file; new ids must be unique.
- Validate offline with `mise run lint` (checks every scenario file), or for the new-skill
  minimums:
  `uv run --python 3.12 --cache-dir .tmp/uv-cache python scripts/validate_routing_scenarios.py --new-skill=<skill>`.
- Then do a first run: `mise run eval:routing -- skill <skill>`.

### Run vs compare

| Task | Question it answers | Use when |
| --- | --- | --- |
| `eval:routing` | Does the skill route correctly as it is now? Judged per agent against each scenario's pass rule. | Authoring, or a snapshot of the current checkout |
| `eval:routing:compare` | Did my change move routing? Runs *candidate* (current checkout) and *control* (skills at the merge base) with identical scenarios, agents, models, tools, and trials, and reports per-scenario and aggregate pass-rate deltas per agent. | A modified skill, before a PR |

A skill that is new at the merge base has no control: `compare` skips it and judges each agent
on absolute thresholds (at least 90% positive recall, 95% near-miss specificity) instead of a
delta. `compare` itself reports deltas; the merge gate turns them into a regression-only verdict
(see [Pass criteria](#pass-criteria)). No baselines are committed.

### Examples

```bash
mise run eval:routing -- skill konnect-gateway-triage                 # one skill, both agents
mise run eval:routing -- skill konnect-gateway-triage --agent claude  # one skill, Claude only
mise run eval:routing -- changed --base origin/main                  # skills changed since the base
mise run eval:routing -- all                                          # every skill that has scenarios
mise run eval:routing:compare -- konnect-gateway-triage --base origin/main
mise run eval:routing:compare -- konnect-gateway-triage --agent codex # compare on Codex only
mise run eval:routing:compare -- konnect-gateway-triage --confirm     # also re-run regressed scenarios at 3 trials, as the gate does
mise run eval:routing:config -- --json                               # effective settings, offline
mise run eval:routing:coverage                                        # which skills have scenarios, offline (--json too)
ROUTING_CODEX_MODEL=gpt-5.5 ROUTING_CODEX_EFFORT=high mise run eval:routing -- skill konnect-gateway-triage --agent codex
```

`--agent claude|codex` is repeatable or comma-separated (default both). Only selected agents get
workspaces, runs, retries, ceilings, and reports; an unknown name exits 2. A subset run is never
a complete result: summaries and comparisons record `agents_run` and `partial: true`, the overall
state covers only the agents run, and the console says `pass (partial: claude only)`.
The override variables are for local experiments only; CI always uses the pinned defaults
(see [Model and effort settings](#model-and-effort-settings)).

### Credentials

| Agent | Local | CI |
| --- | --- | --- |
| Claude | `ANTHROPIC_API_KEY` environment variable | `ANTHROPIC_API_KEY` secret |
| Codex | local Codex login, or `OPENAI_API_KEY` | `OPENAI_API_KEY` secret |

With `--agent` you only need the key for the selected agent. Locally, missing credentials give
`infra_error`, never `routing_fail`. In CI the keys are environment secrets of the evaluate job only,
and an agent whose key is missing is skipped (see [Missing keys and infrastructure errors](#missing-keys-and-infrastructure-errors)).
Never commit keys; reports and transcripts stay under `.tmp/` and out of git.

### Is a skill covered?

- `mise run lint` validates the scenario files that exist; it does not require any skill to have them.
- `mise run eval:routing:coverage` lists covered and uncovered skills, tag counts, and whether a
  covered skill currently meets the new-skill minimums. It is informational and exits 0 on gaps.
- The merge queue fails a **new** skill that lacks the minimums (before any model call; a pull
  request only warns). A **modified** skill without scenarios is skipped with a note.

### How agents are judged

- Claude: the agent only has the `Skill` tool; evidence is a successful native skill call, and
  positive scenarios stop once it succeeds.
- Codex: read-only sandbox, no network, never asks for approval. Evidence is a successful command
  that reads `.agents/skills/<name>/SKILL.md` in the eval workspace (Promptfoo's `skillCalls`,
  source `heuristic`); final-answer mentions do not count. Codex cannot be limited to one tool,
  so the prompt confines it to that read.
- Modes: `skill <name>` runs one skill; `all` every skill with scenarios; `changed` the skills
  changed since the base (`scripts/select_changed.py`; default `origin/main`, else `main`), with a
  note for modified skills without scenarios. No selected skills is a no-op success; every
  selected skill runs and the worst exit code wins.
- Reports land in `.tmp/routing/reports/<agent>-<skill>.{json,html,junit.xml}` (per-trial scenario,
  agent, expected/forbidden routes, observed skills, pass/fail reason). Each agent also writes
  `<agent>-<skill>.result.json` (shape in `scripts/routing_results.py`), with a cross-agent
  `<skill>.summary.json`; comparisons write `<agent>-<skill>.comparison.json` (shape in
  `scripts/routing_compare.py`, including the optional `confirmation`); CI adds `<skill>.run.json`
  for the gate (`scripts/routing_ci.py`). Candidate and control runs use isolated workspaces under `.tmp/routing/`.

Each agent reduces to one state:

- `pass`: every scenario met its route (at least 2/3 trials, rounded up).
- `routing_fail`: the agent answered with valid telemetry but routed wrongly.
- `infra_error`: missing credentials, provider failure, malformed telemetry, or a reached ceiling.
  Trials are retried once; a persistent failure leaves the agent incomplete, never `routing_fail`.
  An agent that is incomplete (for example a comparison whose control hit an `infra_error`) is
  `infra_error` even if its candidate passed; `routing_fail` on any agent takes precedence.

Results also record the failure kind (`invocation`, `provider`, `telemetry`, `ceiling`;
`scenario_validation` only from library callers), retries, and per-trial evidence.

#### Exit codes

Every routing script and task (`run_routing_eval.py`, `run_routing_comparison.py`,
`mise run eval:routing`, `eval:routing:compare`) uses one table:

| Code | Meaning |
| --- | --- |
| 0 | `pass` |
| 1 | `routing_fail` |
| 2 | usage, scenario validation (including new-skill minimums), or harness error (unexpected exceptions are caught and exit 2) |
| 3 | `infra_error` (provider, telemetry, ceiling; result incomplete) |

When one task runs several skills, harness error (2) outranks `routing_fail` (1), which
outranks `infra_error` (3). `validate_routing_scenarios.py` and `prepare_routing_workspace.py`
also exit 2 on errors, so `mise run lint` still fails on invalid scenarios.

`scripts/routing_gate.py` reduces CI results to a gate verdict with its own exit codes (the one
place they are defined):

| Verdict | Exit | Meaning |
| --- | --- | --- |
| `pass` | 0 | no confirmed regression, no new-skill threshold failure, nothing blocked |
| `pass_with_warnings` | 0 | as `pass`, with warnings: an agent skipped for a missing key, a regression not reproduced on re-run, or a scenario that also fails on control |
| `fail` | 1 | confirmed routing regression, or a new skill below its thresholds |
| (input error) | 2 | unreadable or malformed gate input; a harness error, not a verdict |
| `blocked_infra` | 3 | an agent that was supposed to run ended `infra_error`, or a result, confirmation, or job is missing or hit a harness error: fail closed |
| `fail_no_agents` | 4 | no requested agent had an API key, so nothing was evaluated |

Precedence is `fail_no_agents` > `fail` > `blocked_infra` > `pass_with_warnings` > `pass`.
`--informational` (the manual full suite) reports `fail` and `blocked_infra` but exits 0.

### Merge gate workflow

`.github/workflows/skill-evals.yml` is separate from `validate.yml`. It has no `paths:` filter, so
its check reports on every pull request and queue entry; the `select` job decides relevance from
the base/head diff (`scripts/routing_targets.py`, built on `select_changed.py`). Orchestration
lives in `scripts/routing_ci.py` (`select`, `evaluate`) and the verdict in `scripts/routing_gate.py`.

| Event | What runs | Paid calls | `routing-evals-gate` |
| --- | --- | --- | --- |
| Pull request push | `validate.yml`, plus a no-spend preview in the Select job summary: changed and adjacent skills, planned trials, estimated cost. A new skill below the scenario minimums only warns. | none, no secrets | passes immediately |
| Merge queue (`merge_group`) | The relevant evals once, for the queued commit (diff `base_sha...head_sha`): changed skills plus at most 5 adjacent skills, each compared with its merge base. A queue entry is never cancelled by a later one. | yes, environment `skill-evals` | applies the policy below; fails the queue entry on `fail`, `blocked_infra`, `fail_no_agents` |
| Manual (`workflow_dispatch`) | `mode` = `skill` (one skill; needs `skill`), `changed` (vs `origin/main`, with adjacent skills), or `all` (full suite); optional `agents` (`claude`, `codex`). `all` runs both agents on every skill with scenarios as snapshots, prints an estimated cost (planned trials x assumed $/trial, plus the hard bound from the cost ceiling), and needs approval (environment `skill-evals-full`). | yes | reports the verdict and fails like the queue, but is not part of any merge gate; `all` is informational |

The full suite is manual only and never part of the gate. A manual `skill` run on a ref with
nothing beyond `main` is a snapshot, not a comparison with itself. Environments restrict where
secrets are used, so manual `skill`/`changed` runs work only from refs allowed by the
`skill-evals` deployment branch rule (`main` and the queue refs).

The gate is not enabled by the repo: until an admin makes `routing-evals-gate` a required check, all
of this is advisory.

#### Pass criteria

- **Modified (existing) skills: regression-only, per agent.** A scenario passes by the usual rule
  (at least `ceil(2/3 x trials)`). A *regression* is a scenario that passes on control (merge base)
  and fails on candidate. A scenario that also fails on control is a warning, not a regression.
- **Adjacent skills:** the same regression-only comparison, with one trial each at first.
- **New skills (absent at the merge base):** absolute thresholds per agent (at least 90% positive
  recall, 95% near-miss specificity) plus the scenario minimums, from the existing trial data.
- **Confirmation re-run:** before failing on a regression, `eval:routing:compare --confirm` re-runs
  just the regressed scenarios at 3 trials on both candidate and control (one shared ledger, so the
  ceilings still bound the spend). The gate fails only if the candidate still fails and the
  control still passes; otherwise it passes with a warning.

#### Missing keys and infrastructure errors

- Keys are the `ANTHROPIC_API_KEY` (Claude) and `OPENAI_API_KEY` (Codex) environment secrets;
  `scripts/routing_ci_agents.py` reads only whether each is non-empty and never prints a value.
  An agent without a key is skipped with `::warning title=agent_skipped::...` and a job-summary
  line; results then carry `partial: true` and `agents_run`, and a partial result is accepted only
  when `agents_run` is exactly the requested agents that had keys.
- If at least one agent runs, a missing key only warns. If **no** agent can run, the gate fails
  (`fail_no_agents`) in the merge queue and manual runs. Pull requests never need keys.
- An agent that is still `infra_error` after the single retry (provider or telemetry failure, a
  ceiling breach, a missing result or confirmation, a harness error) **fails closed**
  (`blocked_infra`, with the reason in the summary). A maintainer re-run or an admin override
  resolves it.

#### Artifacts and limits

- Each evaluate job uploads `routing-reports-<mode>-<skill>-<attempt>`: full Promptfoo JSON (raw responses and
  skill calls are the diagnostic transcript), HTML, JUnit, result, comparison and run documents,
  and logs. HTML and JUnit come from the first full run; `*.result.json` and the comparison reflect
  the state after the single retry (`*.retry.json`) and any confirmation (`<variant>-confirm/`).
  The gate job downloads them and writes the verdict table to its job summary.
- Each evaluate job targets ten minutes (`timeout-minutes: 10`) with the eval deadline below it;
  `max-parallel` bounds paid jobs. Actions are pinned by commit SHA, every job has least-privilege
  permissions, and model/effort overrides are never read in CI.

#### Admin setup checklist

The repo cannot do these itself; until they are done the workflow is advisory and key-less.

1. Create the team `skill-eval-maintainers`.
2. Create environment `skill-evals` (Settings > Environments > New environment): required
   reviewers = `skill-eval-maintainers` (add the team under "Required reviewers"; consider
   "Prevent self-review"); deployment branches limited to the merge queue refs
   `gh-readonly-queue/*` and `main`. Every queue and manual changed/skill run then waits for an
   approval before the job, and so the secrets, starts. A queued PR is blocked until a reviewer
   approves, so keep the team responsive.
3. Create environment `skill-evals-full`: the same required reviewers, with the same branch limits.
   The full suite is manual only and expensive, so use the stricter reviewer list if the two differ.
4. Store `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` as **environment secrets** in both environments
   (not repo secrets), using dedicated keys with provider spend caps.
5. Set the `ROUTING_*` repository variables if the defaults in `scripts/routing_ceilings.py`
   (`mise run eval:routing:config`) do not fit.
6. Main ruleset, in this order: require a pull request; require status checks `validate` and
   `routing-evals-gate`; require the merge queue (start in evaluate mode).
7. On a throwaway PR, verify how the required checks behave on the PR page (the gate passes
   immediately) versus in the queue (the evals run and the gate decides).
8. `release.yml` does not push to `main` (it creates a tag and release with the GitHub App token), so
   the ruleset needs no bypass for it, unless tag rules are added.

### Model and effort settings

The pinned defaults (Codex `gpt-5.5` at `low` effort, Claude `claude-sonnet-5-5` with the
provider's default effort) live in `evals/promptfoo/settings.js`, which both agent configs, the
harness, and the printer read. For local experiments only, override them:

- `ROUTING_CODEX_MODEL`, `ROUTING_CODEX_EFFORT` (becomes `model_reasoning_effort`)
- `ROUTING_CLAUDE_MODEL`, `ROUTING_CLAUDE_EFFORT` (forwarded to the Claude Agent SDK; allowed:
  `low`, `medium`, `high`, `xhigh`, `max`)

Unset or empty means the pin; an invalid value exits 2 before any run. Tool restrictions, sandbox,
permissions, and budgets are fixed. Candidate and control inherit the same environment, so a
comparison applies the same settings to both sides. Every result, summary, and comparison records
`settings` (effective model and effort, each `default` or `override`) and `overridden`; an active
override prints a warning and such results are not comparable with CI. CI unsets these variables.
Changing a pin is a reviewed edit to `settings.js`, supported by `eval:routing:compare` evidence
for the old and new setting.

### Ceilings

`scripts/routing_ceilings.py` enforces limits for every routing run, local or CI. Defaults are in
code (print them with `mise run eval:routing:config`); override with environment variables (in CI,
repository variables of the same name): `ROUTING_MAX_TOKENS` and `ROUTING_MAX_COST_USD` (per agent,
across candidate, control, and retries), `ROUTING_MAX_CONCURRENCY` (Promptfoo `--max-concurrency`),
`ROUTING_RUN_TIMEOUT_SECONDS` (one Promptfoo run; the run is killed), and
`ROUTING_JOB_TIMEOUT_SECONDS` (whole eval; keep it below the CI job timeout). Promptfoo reports
tokens and cost only when a run ends, so those ceilings are checked after each run and before
every later launch: spend stops at the next boundary and can overshoot by at most one run.

A breach makes the agent `infra_error` (kind `ceiling`, incomplete, never `routing_fail`, never
retried). It is recorded in `breaches` in the result, comparison, and summary documents, printed
as `BREACH: ...` in the console, and raised as a warning annotation in CI. Each agent also reports
`usage` (trials, tokens, estimated cost, latency) and retries.

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
