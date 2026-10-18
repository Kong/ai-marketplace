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
- the free lexical description-routing check (`scripts/check_description_routing.py`, see
  [Description-routing check](#description-routing-check))

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
    trials: 3                    # 1-5; confirmation and new-skill trials per agent (the gate's first pass runs it once); passes with >= 2/3
    tags: [positive]             # positive | near-miss | sibling, optionally + symptom-only | name-lure
```

- `positive`: expects the skill. `near-miss`: plausible but out of scope, so it forbids the
  skill. `sibling`: expects a neighbouring skill and forbids this one. Exactly one of these kind
  tags is required and must be listed first.
- Optional design tags say how the prompt was written, so reports (and the ablation) can break them
  out: `symptom-only` describes the situation or symptom without the skill's domain words, and
  `name-lure` contains words from another skill's name while the intent belongs elsewhere, so the
  name alone cannot decide it. Example: `tags: [positive, name-lure]`.
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
| `eval:routing:compare --gate` | Would the merge gate pass? The candidate runs each selected scenario once; only scenarios that fail are confirmed, and only those that still fail run on the control. Cheap, no aggregate deltas (see [Cost and selection](#cost-and-selection)). | Previewing the queue's verdict on a modified skill |

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
mise run eval:routing:compare -- konnect-gateway-triage --confirm     # full compare, then re-run regressed scenarios at 3 trials
mise run eval:routing:compare -- konnect-gateway-triage --gate        # lazy control, as the merge gate runs it (add --scenarios id,id to narrow)
mise run eval:routing:canary -- konnect-gateway-triage --agent claude # eval of the eval: damage one description, see if the harness notices
mise run eval:routing:ablation -- konnect-gateway-triage             # name-only ablation: which scenarios depend on the description? (Claude only, paid)
ROUTING_SKILL_LISTING=name-only mise run eval:routing -- skill konnect-gateway-triage --agent claude  # experimental skill-listing preset (Claude only)
mise run eval:routing:config -- --json                               # effective settings (including the listing preset), offline
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

> **Known limitation:** the gate cannot reliably catch a description-only regression on a skill with a
> descriptive name; routing is name-driven (see [Known limitation: routing is name-driven](#known-limitation-routing-is-name-driven)).
> It did pass a skill whose description was replaced by marketing copy, and the real-name canary was
> `canary_missed` 0/5.

`.github/workflows/skill-evals.yml` is separate from `validate.yml`. It has no `paths:` filter, so
its check reports on every pull request and queue entry; the `select` job decides relevance from
the base/head diff (`scripts/routing_targets.py`, built on `select_changed.py`). Orchestration
lives in `scripts/routing_ci.py` (`select`, `evaluate`) and the verdict in `scripts/routing_gate.py`.

| Event | What runs | Paid calls | `routing-evals-gate` |
| --- | --- | --- | --- |
| Pull request push | `validate.yml`, plus a no-spend preview in the Select job summary: the selected scenarios, initial and worst-case trials per agent, a rough cost range, and the skills skipped because their routing surface did not change. A new skill below the scenario minimums only warns. | none, no secrets | passes immediately |
| Merge queue (`merge_group`) | Only skills whose routing surface changed, or whose scenarios were edited, once for the queued commit (diff `base_sha...head_sha`), at scenario level with lazy control (see [Cost and selection](#cost-and-selection)). A queue entry is never cancelled by a later one. | yes, environment `skill-evals` | applies the policy below; fails the queue entry on `fail`, `blocked_infra`, `fail_no_agents` |
| Manual (`workflow_dispatch`) | `mode` = `skill` (one skill; needs `skill`; no surface trigger, an explicit request runs), `changed` (vs `origin/main`, same selection as the queue), `all` (full suite), `canary` (needs `skill`; see [Canary](#canary-eval-of-the-eval)), or `ablation` (needs `skill`, Claude only, environment `skill-evals`; see [Scenario design](#scenario-design-description-dependence)); optional `agents` (`claude`, `codex`); and `listing` (`default`, `name-only`; Claude only, see [Skill listing presets](#skill-listing-presets-experiment)). `skill` and `changed` use the gate's lazy control. `all` runs both agents on every skill with scenarios as snapshots at the scenarios' own trials, prints the same cost estimate and the hard bound from the cost ceiling, and needs approval (environment `skill-evals-full`). | yes | reports the verdict and fails like the queue, but is not part of any merge gate; `all` is informational; `canary` and `ablation` are diagnostics (the gate job passes without applying a policy) |

The full suite is manual only and never part of the gate. A manual `skill` run on a ref with
nothing beyond `main` is a snapshot, not a comparison with itself. Environments restrict where
secrets are used, so manual `skill`/`changed` runs work only from refs allowed by the
`skill-evals` deployment branch rule (`main` and `gh-readonly-queue/main/*`; see the
[admin checklist](#admin-setup-checklist)).

The gate is not enabled by the repo: until an admin makes `routing-evals-gate` a required check, all
of this is advisory.

#### Cost and selection

A queue run for one changed skill used to cost about $30 on both agents (every scenario three times
on candidate and control, plus up to five adjacent skills' whole files). Four rules cut that to
roughly $3-5, and the preview prints the estimate before anything is spent.

- **Routing-surface trigger.** A skill is evaluated only when what an agent sees when choosing it
  changed: the SKILL.md frontmatter `name` or `description`, or the skill is new, renamed (name or
  directory) or deleted. Frontmatter is parsed at the merge base and at head and compared as data
  (`scripts/routing_surface.py`), so quoting and key order do not count. Everything except `license`
  and `metadata` is part of the surface, so a routing-relevant key such as `disable-model-invocation`
  can never be assumed inert; `metadata.internal` and the other `metadata` keys are read by no agent
  or script here and are inert. A body-only or references-only change prints
  `SKILL.md body changed, routing surface unchanged: skipped` (or its references counterpart) in the
  preview and summary, and the gate passes. Added or edited scenarios (compared by id with the merge
  base) are always evaluated, so new scenarios are validated even when no description changed.
  Harness and pin changes (`settings.js`, scripts) never trigger evals; validate them with a manual
  run. A deleted skill has nothing left to run; scenarios that named it must be edited (the validator
  insists), and those edits run.
- **Scenario-level selection.** For each affected skill the set is every scenario in its own file
  plus every scenario in any file whose `expect` or `forbid` names it, de-duplicated by id
  (`scripts/routing_selection.py`). Adjacent skills no longer run wholesale; `select_changed.py` still
  lists them as preview context. A scenario shared by two affected skills runs once, under the skill
  whose file holds it. A new skill runs only its own file. At most 60 scenarios run per skill (the
  own file always, then referencing scenarios in file order; the preview notes anything dropped, run
  it manually).
- **Adaptive trials and lazy control.** The candidate runs each selected scenario once. A scenario
  that passes cannot be a regression, so it never runs on the control. A scenario that fails is
  confirmed on the candidate at `max(its trials, 3)`, so a `trials: 1` sibling is never confirmed (or
  cleared) by a single flaky trial; if it still fails (fewer than `ceil(2/3 x trials)` passes at
  that count, 2 of 3) the control runs it at the same count. The first pass stays at one trial. New skills keep the full absolute-threshold run at
  the scenarios' own trials and have no control.
- **Cost visibility.** The Select summary lists the evaluation set size, initial trials per agent,
  worst-case trials (every scenario fails and is confirmed on both sides) and a cost range from
  `scripts/routing_cost.py`: $0.065 per Claude trial, measured on CI ($0.058-$0.065; 43 trials of a
  manual run were 1.07M tokens and $2.49, and the 29-trial gate profile 682K tokens and $1.88), and
  $0.05-$0.10 per Codex trial, which is **unmeasured** (the old planning range). The hard bound is
  still the per-run cost ceiling, which this change does not touch.

Differences from the full comparison: `eval:routing:compare` without `--gate` keeps its complete
candidate-vs-control run and its per-scenario and aggregate deltas. The gate path has no aggregate
delta and no control result for scenarios that passed first time (the deliberate cost saving);
control sides appear only in the confirmation of failed scenarios. A candidate's first-pass state is
what the run exits with, and `routing_gate.py` renders the verdict.

#### Pass criteria

- **Modified (existing) skills: regression-only, per agent.** A scenario passes by the usual rule
  (at least `ceil(2/3 x trials)`). A *regression* is a scenario that fails on the candidate and
  passes on control (merge base). A scenario that also fails on control is a `preexisting_failure`
  warning, not a regression.
- **Lazy control (gate and manual CI runs):** the first pass is one candidate trial per scenario.
  Only failed scenarios are re-run on the candidate at `max(their trials, 3)`, and only those still
  failing run on the control. The gate fails only if the candidate still fails and the control
  passes; a candidate that passes the re-run is a `regression_not_confirmed` warning. The full
  `eval:routing:compare --confirm` keeps its older behaviour: the whole comparison first, then a
  3-trial re-run of regressed scenarios on both sides.
- **New skills (absent at the merge base):** absolute thresholds per agent (at least 90% positive
  recall, 95% near-miss specificity) plus the scenario minimums, at the scenarios' own trials, with
  no control.
- All runs share one ledger, so the ceilings still bound spend.

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

- Each evaluate job uploads `routing-reports-<mode>-<skill>-<attempt>` (`mode` is `gate`, `compare`, `snapshot` or `canary`), kept 10 days (`retention-days: 10`, the repository maximum): full Promptfoo JSON (raw responses and
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
   "Prevent self-review"); deployment branches limited to `main` and `gh-readonly-queue/main/*`.
   Queue refs have two levels (`gh-readonly-queue/main/pr-N-sha`) and `*` does not cross `/`, so the
   pattern `gh-readonly-queue/*` does **not** match them: a real queue run was rejected with "Branch ...
   is not allowed to deploy to skill-evals". Every queue and manual changed/skill/canary run then
   waits for an approval before the job, and so the secrets, starts. A queued PR is blocked until a
   reviewer approves, so keep the team responsive.
3. Create environment `skill-evals-full`: the same required reviewers (`skill-eval-maintainers`) and
   the same two branch patterns, `main` and `gh-readonly-queue/main/*`.
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

### Known limitation: routing is name-driven

The agentic routing eval does **not** reliably detect a description-only regression on a skill with a
descriptive name. A descriptive skill name (`konnect-gateway-triage`) lets an agent route without
reading the description. Live evidence: a merge-queue run passed the gate for a PR that rewrote a skill's
description into off-domain marketing copy (29 trials, all passing); the canary with real names on
`konnect-gateway-triage` was `canary_missed` (all five positives still routed by name); and with every
description removed (the `name-only` listing preset) all 43 scenarios of that skill still passed. Treat a
passing gate as evidence about routing behavior with the current names, not as proof the descriptions
are good; review description changes by hand. Two tools address this: the free
[description-routing check](#description-routing-check) runs in lint and catches gross description
damage and near-duplicate descriptions without a model, and the name-only ablation shows which
scenarios depend on the description at all.

Opaque skill aliases were tried to isolate descriptions and removed: with aliases the agent cannot
connect a request to an opaque name, so Claude answers `NONE` without calling the Skill tool for every
positive and sibling, even for the undamaged skill. That measures nothing about descriptions. The
name-only listing preset (below) is the supported way to measure how much routing depends on
descriptions.

### Description-routing check

`scripts/check_description_routing.py` (part of `mise run lint`, so of CI `validate`; offline,
deterministic, pure Python plus the PyYAML the repo already uses, under a second) asks a narrow question
without a model: does each skill's description still share vocabulary with the scenarios that expect that
skill? It builds a stemmed TF-IDF vector per skill from the **description only** (never the name, so it
measures the description, not the name) and ranks all skills by cosine similarity to every scenario
prompt in `evals/routing/`. For each skill, over the positive and sibling scenarios that expect it, it
reports **hit@1** and **hit@3**: the share where that skill ranks first or in the top three. It also
compares every pair of descriptions.

| Result | Rule | Measured on the 22-skill corpus (330 expected-skill rows) |
| --- | --- | --- |
| error: collision | two descriptions with cosine similarity >= 0.70 | highest pair 0.51 (`konnect-api-catalog` / `konnect-api-publish`) |
| error: collapse | a skill (at least 5 scenarios) with hit@3 < 20%, about chance (3 of 22 is 14%) | lowest 38% (`konnect-platform-router`) |
| error: collapse | corpus hit@3 < 55% | 78% (hit@1 52%) |
| warning: weak | a skill with hit@3 < 50%, named in the output | only `konnect-platform-router` (38%, a router is vague by design) |

Thresholds are constants at the top of the script, set from those numbers with margin and pinned by a
test that fails if the margin shrinks. The signal is real but weak: scenario prompts deliberately avoid
the descriptions' wording (no shared 4-grams), so overlap is a coarse proxy, hit@1 per skill ranges from
19% to 100%, and per-skill hit@3 from 38% to 100% (median 89%). That is why a weak skill only warns and
only a collapse to chance errors. The test suite proves the separation on the real corpus: replacing
`konnect-gateway-triage`'s description with the canary's brand-voice marketing copy drops its hit@3
from 77% to 8% and fails the check, while the real description passes. Sibling-owner-outranks-target
(73%) and near-miss-leak (19%) rates are printed as informational only; they are too noisy to gate
because those prompts are lexically close to the target by design.

Read it with `mise run eval:routing:descriptions -- --report` (or `python scripts/check_description_routing.py --report`):
the per-skill table with `ok` / `weak` / `COLLAPSE`, hit rates by scenario tag, the rank distribution,
the weakest skills and the most similar description pairs. To tune, edit the constants and re-run with
`--report`: after adding scenarios or rewording descriptions the margins move, and a new skill with no
scenarios is simply not judged yet. The check cannot tell whether a description makes a model route
correctly, whether the description is good prose, or whether sibling skills are separable; it
complements the model-based routing eval and does not replace it.

### `NONE` telemetry (Claude)

When Claude selects no skill it can omit `metadata.skillCalls` entirely. That is valid "no skill used"
only if the output, stripped and case-insensitive, is `NONE` and there is no error: a positive then is
`routing_fail`, a near-miss passes. Missing `skillCalls` with any other output stays a `telemetry`
infra_error (it could be a lost Skill call). A present empty list is valid.

### Skill listing presets (experiment)

Claude is shown each skill's name and description up front. The `name-only` preset lists names without
descriptions, to measure how much routing depends on the descriptions: a scenario that still passes
under `name-only` says nothing about description quality. A wider listing budget (every description
listed in full) was tried and changed nothing, so the listing budget is not the cause of name-driven
routing and that preset was removed. The preset is for diagnosis, not the gate: off by default, Claude
only, and never read in `merge_group` or `pull_request` runs.

| `ROUTING_SKILL_LISTING` | Written to `<workspace>/.claude/settings.json` |
| --- | --- |
| `default` (unset) | nothing: current behaviour |
| `name-only` | `skillOverrides` with every workspace skill set to `"name-only"` |

Presets are constants in `scripts/routing_listing.py`; nothing else can be written, so an input can
never inject settings such as hooks. `prepare_routing_workspace.py` writes the file (it fails if one
exists, and rejects a non-default preset for Codex with exit 2), workspace integrity re-checks it, and
every result, summary, comparison and canary document records `listing`, as do the console summary,
the workspace fingerprint line and `mise run eval:routing:config`. Run, for example:

```bash
ROUTING_SKILL_LISTING=name-only mise run eval:routing -- skill konnect-gateway-triage --agent claude
gh workflow run skill-evals.yml -f mode=skill -f skill=konnect-gateway-triage -f agents=claude -f listing=name-only
```

The workflow input `listing` applies to modes `skill`, `changed` and `canary` and needs `agents=claude`;
`all` ignores it with a notice. It is part of the dispatch concurrency group, so experiments differing
only in `listing` do not cancel each other.

### Workspace integrity

After building each workspace the harness asserts, for every skill, that the workspace SKILL.md
frontmatter is derived exactly from the source revision (the working tree, or the merge base for the
control): the description and the name, the directory set, and the skill-listing settings file. Any mismatch exits 2 with the list, before any
provider call, so a stale or wrong workspace can never silently feed an eval. Workspaces that were
built earlier are re-checked before they are reused (the standalone eval, the gate's confirmation
runs). The log and every result document carry a fingerprint, a hash of all descriptions in the
workspace, so two runs can be shown to have measured the same descriptions.

### Canary (eval of the eval)

The canary asks whether the harness can notice a destroyed description at all.
`mise run eval:routing:canary -- <skill> [--agent ...]` (or the manual
workflow with `mode: canary`, `skill` and optional `agents`; environment `skill-evals`) builds
a candidate workspace in which only that skill's description is replaced by a fixed off-domain text
(`CANARY_DESCRIPTION` in `scripts/routing_canary.py`, brand-voice marketing copy of about the same
length as a real description), runs the skill's own positive scenarios at one trial each, candidate
only, and decides per agent:

| Verdict | Meaning | Exit |
| --- | --- | --- |
| `canary_detected` | at least 60% of the positive scenarios failed to route to the skill: the harness noticed | 0 |
| `canary_missed` | fewer did: a blind spot, the eval cannot see description regressions | 1 |
| `canary_incomplete` | infrastructure error or ceiling breach; unknown | 3 |
| (harness error) | usage, unknown skill or no positive scenarios, workspace integrity | 2 |

Overall, any missed agent makes it `canary_missed`, then any incomplete agent `canary_incomplete`.
In CI `canary_missed` and `canary_incomplete` fail the evaluate job; the canary never affects
`routing-evals-gate`. The result is `canary-<skill>.canary.json` (verdict per agent, `listing`,
the damaged workspace's fingerprint, usage) and the measured cost is printed. A canary costs one trial
per positive scenario per agent (about $0.33 for five on Claude at the measured price).

Run it after changing models, pins or the harness, and after enabling the gate. The canary always uses
real skill names, so `canary_missed` is expected for skills with descriptive names: it is the known
name-driven-routing limitation, and the output says so. The canary counts an assertion failure
(including a `NONE` answer) as failed to route. Offline tests drive the same code with fake results
(`--fake-results`).

### Scenario design: description-dependence

A scenario that passes with **no descriptions at all** says nothing about descriptions: the skill name
alone was enough. On `konnect-gateway-triage` every scenario passed with the `name-only` listing, so the
scenarios, and the merge gate built on them, could not see a description regression. The ablation
measures this for one skill instead of guessing:

```bash
mise run eval:routing:ablation -- konnect-gateway-triage [--agent claude]
gh workflow run skill-evals.yml -f mode=ablation -f skill=konnect-gateway-triage   # Claude only; environment skill-evals
```

It runs the skill's **own** scenarios (every tag) on Claude at one trial each, twice and candidate only:
under the `default` listing and under the `name-only` listing, in separate workspaces and report
directories (`.tmp/routing/ablation-default`, `.tmp/routing/ablation-name-only`), through the same runner,
ceilings and reducer as every other eval. Each scenario is classified:

| Class | Meaning |
| --- | --- |
| `description_dependent` | passes with the default listing, fails name-only: the description carries it |
| `name_solvable` | passes both: the name alone suffices, so it says nothing about the description |
| `failing` | fails with the default listing; fix the routing first |
| `incomplete` | an infrastructure error or ceiling breach left it undecided (exit 3) |

The result is `ablation-<skill>.ablation.json` (per-scenario classes and states, counts and percentages
overall and per tag `positive` / `near-miss` / `sibling`, per-listing fingerprint and usage, model and
effort) plus a table in the console and the job summary. In CI the manual `ablation` mode uses the
`skill-evals` environment, needs `agents` empty or `claude` (Codex has no name-only listing; the
`listing` input is ignored), uploads the reports as artifacts, previews the cost in the select summary
(twice the skill's scenarios at the measured Claude price; about $2.7 for 21 scenarios) and the
measured cost afterwards, and never affects the merge gate: `routing-evals-gate` passes without applying
a policy, and `merge_group` and `pull_request` never run it. Exit codes: 0 complete, 2 harness or usage
error (including a non-Claude agent), 3 incomplete.

Design guidance (not enforced; the ablation reports, it does not gate):

- Treat a high `name_solvable` share among `positive` scenarios as a gap in the scenario set, not as
  evidence that the descriptions are good.
- Add positive prompts that avoid the skill's own vocabulary (its name, product nouns and the words in
  its description): describe the symptom or goal the way a user who has never seen the skill would.
- Add sibling pairs whose skill names do not separate them: the right owner is only decidable from the
  description (what each skill covers and excludes), not from a name that resembles the prompt.
- After adding or rewording scenarios, re-run the ablation and check that the new scenarios land in
  `description_dependent`. The [description-routing check](#description-routing-check) is the free
  complement for gross description damage.

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

The defaults are sized for the gate's profile (about 20-40 scenarios, one trial each, confirmation
only for failures): a typical agent spends under $1, so `ROUTING_MAX_COST_USD` defaults to 3 and
`ROUTING_MAX_TOKENS` to 2500000. That is about 3x the expected spend, and a confirmation storm
(everything failing) stops sooner and fails closed. The full suite (`mode: all`) needs higher values:
set the `ROUTING_*` repository variables (or the environment's variables) before running it. Leave
concurrency and the timeouts alone until the queue has produced real timings.

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
