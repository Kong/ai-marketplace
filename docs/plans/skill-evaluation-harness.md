# Skill evaluation harness

Decision and roadmap record. How to use the implemented harness (adding scenarios, running,
credentials, exit codes, CI behavior) lives in [docs/testing.md](../testing.md#routing-evals);
this file does not repeat it.

## Decision

Keep a repo-owned scenario layer on **Promptfoo**, not a custom model runner. Promptfoo's CLI
and native Codex SDK and Claude Agent SDK providers run both locally and in CI. Scenarios,
thresholds, change selection, and result reduction stay in this repository.

The initiative covers regression gating and skill experimentation. The first bounded
implementation evaluates **routing only**; outcome, scope, safety, tool behavior, cost, and
latency evaluation are later branches (see [Roadmap](#roadmap)).

An *agent* is an agent runtime: Claude Code or Codex. The two are independent compatibility
targets, never blended into one score; each is reported separately. A provider or telemetry
failure is `infra_error`, not a routing failure.

## Status

The routing MVP (issues #11-#20, integration PR #21) is implemented:

- Scenarios in `evals/routing/*.yaml`, validated offline; pilot corpus for
  `konnect-platform-router`, `konnect-gateway-triage`, and `kongctl-declarative`.
- Promptfoo, Codex SDK, and Claude Agent SDK pinned in `package.json` / `package-lock.json`;
  models and effort pinned in `evals/promptfoo/settings.js`.
- Per-agent runs reduced to `pass` / `routing_fail` / `infra_error`, with one retry for
  infrastructure errors and token, cost, concurrency, and timeout ceilings.
- Candidate vs merge-base comparison for modified skills; absolute thresholds for new skills
  (at least 90% positive recall and 95% near-miss specificity per agent) with scenario minimums
  (5 positive, 5 near-miss, 2 sibling per adjacent skill, up to 5).
- Gating workflow (`.github/workflows/skill-evals.yml`, merge queue only; advisory until an admin
  requires the check `routing-evals-gate`): skills with a changed routing surface or edited scenarios,
  selected at scenario level with lazy control; manual runs for one skill, changed skills, or the
  full suite.
- Tasks: `eval:routing`, `eval:routing:compare`, `eval:routing:canary`, `eval:routing:config`,
  `eval:routing:coverage`.

### Decisions made during implementation

- **Terminology:** "agent" (not "host") everywhere, including result-document keys.
- **Subset runs:** `--agent claude|codex` runs a subset. Such a run is labelled `partial: true`
  with `agents_run`; it is never presented as a complete both-agent result, and a missing
  agent is still `infra_error` by default.
- **Local overrides:** `ROUTING_{CODEX,CLAUDE}_{MODEL,EFFORT}` allow local experiments, are
  recorded as `overridden: true`, and are never used by CI, which always uses the pins.
- **CI and missing keys:** an agent without its API key is skipped with a warning instead of
  becoming `infra_error`. A partial result is accepted only when `agents_run` is exactly the
  requested agents that had keys; any other partial result fails.
- **Adjacent skills:** compared with control (regression-only), one trial each at first.
- **Exit codes:** 0 pass, 1 `routing_fail`, 2 usage/validation/harness error, 3 `infra_error`,
  so a crash can never look like a routing regression (table in docs/testing.md).
- **Evidence and storage:** raw Promptfoo JSON is the diagnostic transcript, uploaded as a CI
  artifact; credentials, reports, and score baselines are never committed.
- **Deterministic validation** stays in `mise run ci`; routing evals are model-backed and gate
  only through the merge queue (below).

### Gating decisions

Rules and workflow are documented in [docs/testing.md](../testing.md#merge-gate-workflow); the
decisions behind them:

- **Where:** pull request pushes only validate and preview (no spend); the merge queue
  (`merge_group`) runs the relevant evals once and `routing-evals-gate` blocks on failure. The full
  suite is manual only, behind an approval environment, and never part of the gate. The repo does
  not enable the gate; an admin makes `routing-evals-gate` required later.
- **Trigger:** a skill is evaluated only when its routing surface changed (SKILL.md frontmatter
  `name`/`description`, plus any other non-bookkeeping frontmatter key; or the skill is new, renamed
  or deleted), or when its scenarios were added or edited. Body-only and references-only changes
  skip with a notice and the gate passes; harness and pin changes never trigger (a reviewed manual
  run validates them). This replaces running every changed skill.
- **Selection:** scenario level, not file level. For each affected skill: its own file plus every
  scenario elsewhere whose `expect` or `forbid` names it, de-duplicated by id and capped at 60 per
  skill. Adjacent skills no longer run wholesale (this replaces "up to five adjacent skills").
- **Pass criteria:** modified skills are regression-only per agent (a scenario that fails on the
  candidate and passes on control); new skills use the absolute thresholds plus scenario minimums.
  Absolute scores are not gated for existing skills because flake rates are unmeasured.
- **Adaptive trials and lazy control:** the candidate runs each scenario once; the control never
  runs for a scenario that passed. Failures are confirmed on the candidate at `max(scenario trials, 3)`
  (the baseline corpus declares all siblings `trials: 1`, which one flaky trial on each side must not
  turn into a regression; `trials` still sets the new-skill trial
  count, not "run 3 times everywhere"), and the control runs only for those still failing. Failing on both sides is a warning
  (`preexisting_failure`). The full candidate-vs-control comparison with aggregate deltas stays
  available manually (`eval:routing:compare` without `--gate`); the gate path deliberately has no
  deltas or control data for scenarios that passed.
- **Cost visibility:** the no-spend preview prints scenarios, initial and worst-case trials per
  agent and a cost range from stated, rough per-trial assumptions (`scripts/routing_cost.py`).
  Expected effect for one changed description: about $30 down to $3-5 per queue run; a body-only
  change costs nothing. The full suite is unchanged: manual, at the scenarios' own trials,
  informational.
- **Fail closed on infrastructure:** a persistent `infra_error` for an agent that should have run
  blocks (`blocked_infra`); a re-run or admin override resolves it.
- **Keys:** a missing key warns while any agent runs; no runnable agent fails the gate in the
  queue and manual runs.
- **Description sensitivity (live finding, known limitation):** a PR that rewrote
  `konnect-gateway-triage`'s description into off-domain marketing copy passed the queue gate (29
  trials, all passing), because descriptive names let the agent route without the description; the
  canary with real names confirmed it (`canary_missed` 0/5), and with every description removed (the
  `name-only` listing preset) all 43 scenarios of that skill still passed. Description-only
  regressions on skills with descriptive names are **not** reliably detected by the agentic routing
  eval. Kept: every built workspace is verified against its source revision and fingerprinted, and the
  canary (`mode: canary`, `mise run eval:routing:canary`), which notes `canary_missed` as this
  limitation. The same runs exposed a reducer bug: Promptfoo copies an assertion failure into the
  row-level `error` (failureReason 1), which was misclassified as a provider `infra_error`; only
  `response.error` or failureReason 2 (or an error with no failureReason) is infrastructure now.
  Details: docs/testing.md.
- **Aliasing tried and removed:** opaque skill aliases (`s-` plus a hash of the name) were built to
  isolate descriptions from names. A 43-trial live run showed aliasing suppresses Claude's skill
  selection: real names passed 43/43, while with aliases every positive and sibling trial answered
  `NONE` (one turn, no tool call), even for the undamaged skill; the earlier "aliases on => canary
  detected" reading was that suppression. An opaque name gives the agent nothing to route on, so the
  approach cannot separate description from name, and it was removed with its plumbing. A wider
  skill-listing budget (every description listed in full) was also tried and changed nothing, so the
  listing budget is not the cause either; that preset was removed too. The `name-only` listing preset
  stays as the ablation (`mise run eval:routing:ablation`, workflow mode `ablation`): a skill's own
  scenarios run under the default and name-only listings and are classified `description_dependent`,
  `name_solvable` or `failing`. A free lexical check over descriptions (`scripts/check_description_routing.py`,
  in lint) catches gross description damage and near-duplicates without a model.
- **Measured cost:** Claude about $0.058-0.065 per trial on CI (43 trials, 1.07M tokens, $2.49; the
  29-trial gate profile, 682K tokens, $1.88), so `routing_cost.py` plans at $0.065; Codex remains
  the unmeasured old range of $0.05-0.10. Artifacts are kept 10 days, the repository maximum.
- **Approvals** on both environments (`skill-evals` for queue and manual changed/skill runs,
  `skill-evals-full` for the full suite), so no run starts, and no secret is exposed, without a
  reviewer from `skill-eval-maintainers`. Both environments allow deployments from `main` and
  `gh-readonly-queue/main/*`: queue refs are `gh-readonly-queue/main/pr-N-sha` and the pattern
  `gh-readonly-queue/*` does not match two levels (a real queue run was rejected for that).

## Why this fits this repository

Existing validation covers package shape, frontmatter, generated metadata, description overlap,
and publishability. It does not show that the right skill activates for realistic wording, that
a nearby skill stays inactive, that loading a skill improves the outcome, or that behavior is
reliable across samples and agents. The routing MVP addresses the first two by exercising each
agent's real skill-selection path. It does not claim routed skills improve task outcomes.

## Tool assessment (trimmed)

- **Promptfoo (chosen).** Native Agent Skill support for Codex and Claude, `skill-used` /
  `not-skill-used` assertions, repeated trials, and JSON/JUnit/HTML reports avoid building
  provider adapters and report plumbing. It is Node-based: pin exact versions and call the local
  binary through `mise`, never `npx ...@latest`. Skill telemetry differs: Claude has first-class
  skill tool calls; Codex use is inferred from successful `SKILL.md` reads. Agent-native
  invocation evidence is the authoritative routing signal. See
  [Test Agent Skills](https://www.promptfoo.dev/docs/guides/test-agent-skills/) and
  [CI/CD integration](https://www.promptfoo.dev/docs/integrations/ci-cd/).
- **[Inspect AI](https://inspect.aisi.org.uk/).** Strongest future option if the corpus grows
  into long-horizon repository mutation, MCP simulation, or sandboxed security tasks; heavier
  than routing needs and without ready-made skill assertions.
- **[OpenAI Evals / graders](https://developers.openai.com/api/docs/guides/evals).** Useful for
  grader ideas (task-specific evals, human-calibrated graders) but does not provide repo fixture
  lifecycle or cross-agent skill routing.
- **[LangSmith](https://docs.langchain.com/langsmith/evaluation-types).** Viable if Kong
  standardizes on it for production traces; otherwise a hosted control plane that does not solve
  skill installation or fixture isolation.

## Design principles (still binding)

- Keep eval mechanics in the repo so skills, scenarios, and pins form one reviewable contract;
  candidate-vs-`main` comparisons then run in the same job, which controls provider variance
  better than stored scores.
- Python helpers only select skills and materialize workspaces; Promptfoo owns provider
  execution, retries, and reporting.
- Routing oracle: Claude = successful native skill call; Codex = successful read of the exact
  `SKILL.md`. Description matching and final-answer mentions are never evidence.
- Scenario classes: positive routing, near miss, sibling routing (robustness variants are
  roadmap). Source cases from incidents, review corrections, and real operator requests; never
  copy description wording into prompts.
- Pass rule: at least 2/3 trials per scenario. Thresholds are initial values to calibrate from
  observed variance before they become permanent gates.
- Normal review owns scenario quality; no CODEOWNERS or hidden-suite mechanism for the MVP.
  Only Kong contributors write to the repo; provider keys stay in GitHub secrets.

## Roadmap

1. **Enable and calibrate the gate.** The workflow is built; an admin enables it with the checklist
   in docs/testing.md, starting the merge queue in evaluate mode. Collect at least 20 queue runs
   and review flake rate, confirmation-rerun frequency, `blocked_infra` incidents, and spend
   before treating the gate as final; adjust the first-pass and confirmation trial counts, the
   scenario cap and thresholds from observed variance.
2. **Corpus growth.** Cover more skills (see `mise run eval:routing:coverage`); every escaped
   skill failure becomes a minimal scenario before its fix lands. Add robustness variants
   (concise vs conversational wording, product term implied, explicit vs inferred toolchain,
   diagnose vs implement, distractor naming a neighboring product) and a per-skill explicit
   invocation smoke test for package wiring.
3. **Nightly health check** in a separate `skill-evals-nightly.yml`, so the PR contract stays
   unambiguous: full-catalog and bundle-routing suites, five trials per scenario and adjacency
   prompts, trend pass rate, variance, latency, tokens, and cost on the default branch with both
   pinned models; alert on sustained regression, not one noisy run. Model pins are upgraded
   through an explicit A/B run, then changed together.
4. **Behavioral and outcome evals.** Task completion and skill uplift versus a no-skill control;
   scope, safety, tool-use, reference-loading, and handoff checks; live `kong-konnect` and
   mutation scenarios; judge-scored rubrics with human calibration. These need isolated fixtures
   and trajectory inspection, and may justify revisiting Inspect AI.
5. **Later, only if needed:** hidden holdouts, protected scenario ownership, special fork
   workflows, cross-model benchmarking beyond one pinned model per agent.

## Success criteria

The routing MVP is useful when it catches intentionally seeded positive, near-miss, and sibling
regressions on both agents; distinguishes a modified skill from `main` across repeated trials;
explains failures with inspectable invocation evidence; and completes the changed-skill PR suite
in under ten minutes within its configured budget.
