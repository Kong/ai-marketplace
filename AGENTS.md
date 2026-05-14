# Skill Authoring Guide

This repo is for high-signal Kong skills. If you are using an LLM to add a new skill here, the main job is not to create more text. The job is to create a skill that helps an agent do Kong-specific work better than general model knowledge already would.

If your host environment exposes a built-in skill-authoring helper or skill such as `skill-creator`, `build-a-skill`, or similar, consult it before drafting or revising a skill. Use it to improve structure and calibration, then apply this repo's Kong-specific rules as the final authority. If the helper conflicts with this file, follow this file.

## What Belongs Here

A skill in this repo should do at least one of these well:

- encode Kong-specific workflows that are easy to get wrong without guidance
- capture product or platform conventions that are not obvious from generic reasoning
- turn a broad request into a repeatable operating procedure
- point agents toward the right artifacts, constraints, or failure modes

Good examples:

- designing or debugging DataKit flows
- working with Konnect concepts, APIs, or configuration patterns
- handling Kong-specific deployment, gateway, plugin, or control-plane workflows

Weak examples:

- generic web research
- generic coding advice
- generic debugging advice that is not Kong-specific

If the skill would be equally useful in any repo, it probably does not belong here.

## Before You Create A Skill

Before creating a new skill, check whether the repo already has one that should
be extended instead.

- inspect `docs/skills.md` and the existing `plugins/<plugin>/skills/` trees before adding a new folder
- extend an existing skill when the new request fits the same trigger class,
  same layer, and same operating procedure
- create a new skill only when the workflow, ownership boundary, or trigger
  surface is meaningfully different
- avoid near-duplicates with slightly different names or product wording

Useful decision rule:

- if the main difference is product surface, operator workflow, or diagnosis
  order, extend or create a domain skill
- if the main difference is config tool, file format, plan/apply workflow, or
  import/adoption path, extend or create a tool skill
- if both apply, keep diagnosis in the domain skill and hand off
  implementation to the tool skill

## What A Good Skill Does

A strong skill is narrow, operational, and reusable.

It should:

- trigger on a clear class of user requests
- reduce ambiguity about how to approach the task
- give the agent a reliable workflow, not just background information
- highlight key constraints, edge cases, and common mistakes
- help the agent produce better outputs with less guesswork

It should not:

- try to document an entire product surface
- read like marketing copy
- duplicate large amounts of reference material inline
- prescribe steps that are too vague to change model behavior

Review for signal, not just correctness.

- a strong skill activates on the right requests and avoids nearby ones
- it steers the agent toward the right Kong-specific workflow
- it teaches inspection order, decision rules, defaults, validation, and
  handoffs
- it preserves enough freedom for the agent to adapt to repo state and live
  facts
- it keeps detail in the cheapest place that still changes behavior

Common weak-skill failure modes:

- it becomes a mini manual
- it encodes one narrow task recipe as a default truth
- it hardcodes volatile CLI or product details in always-loaded content
- it duplicates the same rule across root and references
- it tells the agent exactly what to type more often than it teaches how to
  reason

## Layered Skill Design

Prefer orthogonal Kong skills over repeating the same tool instructions across
many domain skills.

- use domain or product skills for Kong-specific workflows, inspection order,
  failure modes, and decision-making
- use tool skills for Kong-specific config authoring and execution in `decK`,
  `kongctl`, or Terraform
- keep only short tool-selection and handoff guidance in domain skills
- avoid turning every domain skill into a partial `decK`, `kongctl`, or
  Terraform tutorial
- do not create generic tool skills with no Kong-specific value
- keep shared execution-policy defaults in steering docs so the repo has one
  canonical source of truth
- when a specialist tool skill runs external CLIs or providers and can trigger
  directly, restate only the minimum local sandbox or escalation rule there
- do not duplicate the full shared sandbox policy in every skill
- when recommending CLI execution, name concrete escalation triggers instead of
  vague "check permissions" language

Use thin router skills only when broad discovery is a real problem.

- a router skill should classify and hand off, not absorb specialist workflows
- keep router skills light on product facts and references
- do not build a company-wide umbrella docs tree under a router skill
- put shared platform defaults in the router only when specialist skills also
  keep a concise local version, because specialists may trigger directly
- do not try to force the router to trigger before a more specific skill
- assume specialist skills may trigger directly and repeat the minimum shared
  defaults locally when they matter

Examples:

- `konnect-gateway-triage` owns diagnosis of Gateway Manager problems;
  `deck-gateway` or Terraform skills own the declarative implementation
- `konnect-api-publish` owns publication workflow diagnosis;
  `terraform-konnect` or `kongctl-declarative` own the resulting config changes
- `gateway-plugin-datakit` owns DataKit flow design;
  `deck-gateway` or a Terraform skill own repository integration if the user
  needs the plugin config encoded in an existing delivery workflow
- `konnect-platform-router` should classify broad or ambiguous Konnect
  requests, not act as a mandatory first hop before specialist skills

For declarative workflows, preserve the user's existing toolchain when one is
already present in the repository.

- if the repo already uses `*.tf`, stay in Terraform unless the user asks to
  change tools
- if the repo already uses `kong.yaml`, `_format_version`, or `deck gateway`
  workflows, stay in `decK`
- if the repo already uses `konnect/resources`, `_defaults.kongctl`, or
  `kongctl` plan/apply workflows, stay in `kongctl`
- do not convert users between `decK`, `kongctl`, and Terraform unless they
  ask for that migration

## Scope Before Writing

Before drafting the skill, decide:

- what user requests should activate it
- what the agent should actually do once it activates
- what Kong-specific knowledge is essential
- what should remain outside the skill because it is generic or unstable

Prefer one clearly-scoped skill over one large umbrella skill.

If you find yourself writing "this skill can also help with..." many times, the scope is probably too broad.

Also decide whether the task should become a skill at all. Prefer a skill when:

- you keep repeating the same playbook, checklist, or multi-step procedure
- the useful part is procedural, not just factual
- the agent needs Kong-specific defaults, gotchas, or validation steps

Do not create a skill just to restate generic best practices.

## Source Material First

Start from real Kong-specific source material whenever possible, not only from generic model knowledge.

Prefer inputs such as:

- existing runbooks, design docs, and internal conventions
- API specs, config files, and checked-in examples
- issue history, review comments, and bug fixes
- real failure cases and the steps that resolved them

The strongest skills are extracted from real execution traces, corrections, and repeated review feedback.

## How To Structure The Skill

Each skill should start with frontmatter:

```md
---
name: skill-name
description: One-line description used for discovery and matching.
license: MIT
metadata:
  product: product-name
  category: workflow-category
  tags:
    - kong
    - example-tag
---
```

Use these fields consistently in this repo:

- `name`
- `description`
- `license`
- `metadata.product`
- `metadata.category`
- `metadata.tags`

Treat `description` as the primary trigger surface for the skill.

- write it so an agent can recognize when to activate the skill
- include the main job the skill does and the kinds of requests that should
  trigger it
- prefer explicit "Use when..." phrasing
- front-load the key trigger words and main boundary early in the sentence
- include important adjacent exclusions when they prevent accidental triggering
- do not make `description` a short label or marketing summary

Budget the description tightly.

- keep individual descriptions concise enough to survive shortening in large
  skill sets
- as a repo default, keep most descriptions under roughly 260 characters
- avoid long trailing lists of examples when a shorter trigger phrase is enough
- if a detail is not needed for matching, move it into the skill body

Set `license` to `MIT` unless the skill is intentionally shipped under different terms and that exception has been reviewed.

Optional companion directories are allowed when they support the skill:

- `references/` for supporting reference material
- `assets/` for lightweight images or other bundled assets
- `scripts/` for helper scripts an agent may inspect or run explicitly

Use `scripts/` only when a checked-in helper is materially better than restating
the logic inline.

- prefer scripts for fragile, repetitive, or deterministic transformations
- prefer a skill-local validator or inspector script when the repeated failure
  modes are mostly static structure problems that can be checked mechanically
- tell the agent exactly when to run the script and what it validates
- keep scripts lightweight and reviewable
- do not rely on hidden wrappers or special packaging behavior
- do not add executable files or permission-dependent setup just to make a skill
  work

When you use `references/`, make them progressively discoverable.

- keep `SKILL.md` as the stable workflow and decision layer
- use `references/` for conditional depth, not for always-needed instructions
- split references by decision branch or failure domain, not by vague topic
  buckets like `overview.md` or `more.md`
- name reference files so the load condition is obvious from the filename
- add a `References To Load` section in `SKILL.md` that says when each file
  should be loaded
- avoid placing critical common guidance only in references

Treat each package layer as having one job.

- `SKILL.md` is the decision layer and should hold the trigger boundary,
  ownership boundary, workflow or inspection order, key defaults and
  constraints, validation loop, and handoffs to neighboring skills
- `SKILL.md` should not hold large command catalogs, schema inventories unless
  they are essential to avoid repeated errors, branch-specific recipes unless
  the task is fragile and repeatedly wrong, or volatile CLI or product detail
  that can drift without changing the workflow
- each file under `references/` should have one clear load condition and
  support one branch, failure domain, or execution mode
- references should help the agent choose, validate, or recover within that
  branch, not restate the root workflow in longer form or collect adjacent
  facts "just in case"
- scripts are for deterministic leverage when repeated logic is fragile,
  validation can be checked mechanically, or a transformation is cheaper and
  safer in code than in prompt text
- do not keep a script only to preserve a one-off recipe that should instead
  be removed or simplified

### Section Heading Conventions

Standardize equivalent concepts across skills. Do not let headings drift when
the section is serving the same purpose.

Prefer these section templates by skill type:

- domain or product skill:
  - `Goal`
  - `Tool Selection`
  - `References To Load`
  - `Workflow` or `Inspection Order`
  - `Konnect-Specific Gotchas` or another equally explicit product-specific
    gotchas heading when the skill is not Konnect-focused
  - `Validation Checklist`
  - `Handoffs`
- tool skill:
  - `Goal`
  - `Tool Positioning`
  - `References To Load`
  - `Validation Contract`
  - `Operating Rules`
  - `Workflow`
  - `Validation Checklist`
  - `Handoffs`
- router skill:
  - `Goal`
  - `Shared Operating Defaults`
  - `Classification Order`
  - `Routing Rules`
  - `Validation Checklist`
  - `Output Style`

Use the exact heading names for shared concepts:

- use `Tool Selection` for domain skills that explain preferred live
  inspection paths and downstream tool handoffs
- use `Tool Positioning` for tool skills that explain when the tool should or
  should not own the task
- use `Shared Operating Defaults` only in router skills for defaults that may
  also be repeated concisely in specialist skills
- use `Workflow` when the agent needs a general operating procedure
- use `Inspection Order` when the diagnosis sequence is itself a guardrail

Variation is acceptable only when it changes agent behavior or keeps the skill
narrow. Cosmetic synonym drift such as `Preferred Tools` versus `Tool
Selection` is not useful and should be cleaned up.

### Tool And MCP Boundaries

This repo does not currently allow per-skill MCP dependency declarations such
as `agents/openai.yaml`. Keep MCP wiring shared at the repo level so skills stay
portable.

For Konnect-oriented skills:

- treat the shared `kong-konnect` MCP server as the preferred path for live
  inspection when it is available
- prefer MCP guidance at the workflow level, not as a hard dependency
- do not hardcode long or brittle MCP tool inventories in `SKILL.md`
- mention exact MCP tool names only when they are stable and materially reduce
  ambiguity
- tell the agent to suggest connecting `kong-konnect` when the request depends
  on live Konnect state and MCP is not available
- preserve a fallback path through `kongctl`, declarative config, logs, or
  user-provided artifacts
- keep MCP setup and auth instructions in shared install docs unless a skill
  truly needs a narrow workflow-specific reminder

For domain skills:

- make the preferred live inspection path clear, usually `kong-konnect` MCP
  for Konnect work
- keep tool guidance short
- hand off implementation to the appropriate declarative tool skill when needed
- explain how to preserve the user's existing toolchain rather than forcing one
  preferred format
- follow the domain section template unless there is a task-specific reason to
  diverge

For tool skills:

- make the covered Kong product or resource surface explicit
- say when another domain skill should own diagnosis first
- say which neighboring tools the skill should not replace
- include an explicit validation contract with these gates:
  - `Preflight`: confirm tool install, auth, repo or toolchain ownership, and
    target environment, workspace, namespace, or profile
  - `Preview`: use the smallest safe inspect-only command, state the expected
    preview artifact or output shape, and say what must be checked before
    mutation
  - `Execute`: describe the intended effect first and only present mutating
    commands when the user requested mutation
  - `Prove`: use tool-native post-change verification, confirm the exact
    resource slice touched, and distinguish command success from intended state
- keep domain skills focused on diagnosis quality and handoff expectations
  rather than absorbing full mutation playbooks
- follow the tool section template unless a concrete workflow branch needs an
  extra section

For declarative tool selection, use these defaults unless the repo or the user
already chose another path:

- prefer `decK` for Kong Gateway entity configuration, file-based GitOps,
  dump/diff/sync workflows, and OpenAPI-driven gateway config generation
- prefer `kongctl` for Konnect platform YAML workflows and stateless
  plan-based reconciliation
- prefer Terraform when the user already uses HCL or Terraform state, or wants
  Kong and Konnect managed alongside other infrastructure
- use the official `kong/konnect` provider for Konnect resources
- use the official `kong/kong-gateway` provider for self-managed Gateway
  resources reachable through the Admin API
- use beta providers only when the user explicitly needs beta-only coverage

Keep the package shape simple:

- keep `SKILL.md` as the only file at the skill root
- do not add hidden files or directories
- do not add symlinks
- do not add executable files
- keep companion files lightweight and reviewable

After that, write for agent behavior, not human browsing.

Keep `SKILL.md` tight. As a rule of thumb, keep the main file under roughly 500 lines and move bulk reference material into companion files.

Useful sections usually look like:

- when to use this skill
- how to approach the task
- what to prefer or avoid
- what to validate before answering
- how to present the result

Not every skill needs the same headings, but every skill should make those concerns clear.

## Writing Style

Use direct instructions.

Prefer:

- "Use this skill when..."
- "First identify..."
- "Prefer..."
- "Do not..."
- "If X is unclear, ask or verify..."

Avoid:

- long product overviews
- unnecessary historical context
- aspirational language
- repeating the same idea in multiple forms

The skill should change agent behavior quickly. Dense, generic prose weakens that.

Prefer concrete defaults over menus. If several tools or approaches could work, tell the agent which one to use by default and mention alternatives only as escape hatches.

Prefer reusable procedures over one-off answers. Teach the agent how to approach a class of Kong problems, not just the output for one example.

## Focus On Workflow, Not Reference Dumps

A skill is most useful when it tells the agent how to proceed.

For example, instead of only listing concepts, tell the agent:

- what order to inspect things in
- which artifacts matter most
- what common failure modes to check first
- what output shape is expected

Reference material is useful, but it should support the workflow, not replace it.

If large reference content is needed, keep it in companion files under the skill directory and let the skill point to them selectively.

When you point to a companion file, tell the agent exactly when to load it. Prefer:

- "Load `references/troubleshooting.md` if the request is about auth or region errors."
- "Load `references/commands.md` when you need exact command syntax."

Avoid vague directions like "see references for more."

## Encode Judgment

The best skills carry judgment, not just facts.

Include guidance like:

- when to choose one Kong approach over another
- what tradeoffs matter
- which sources of truth are more reliable
- which mistakes are common in real usage

This is often the difference between a skill that is merely informative and a skill that is operationally valuable.

Make sure the skill captures the Kong-specific corrections an agent would not infer on its own. These often belong in short "gotchas", "prefer", or "do not" sections.

## Prefer Stable Guidance

Skills should avoid depending on details that change often unless the change is the point of the skill.

Prefer:

- patterns
- workflows
- naming and configuration conventions
- common debugging sequences

Be careful with:

- volatile version-specific claims
- UI click paths
- fast-changing product matrices

If a detail is likely to drift, either omit it, frame it as version-specific, or place it in a reference file that can be updated cleanly.

Prefer stable operating patterns in `SKILL.md` and push volatile details into references.

For common cross-skill guidance, use this placement rule:

- put platform-wide defaults in a thin router skill when one exists
- repeat a concise local version in specialist skills that can trigger
  directly
- do not rely on references as the only place for core defaults like
  "prefer live MCP state when available" or "preserve the existing toolchain"

For MCP-backed skills, prefer stable capability language such as "use
`kong-konnect` MCP for live inspection of current Konnect state" over rapidly
changing tool catalogs. The skill should describe when MCP is the right choice,
not try to mirror the full remote tool surface inline.

Also preserve discovery budget across the whole repo.

- Codex initially sees only each skill's name, description, and file path
- large skill sets may shorten descriptions first
- prefer compact, front-loaded descriptions so matching still works when the
  inventory grows
- when two skills start sounding too similar, tighten the trigger boundary or
  merge them

## Progressive Disclosure

Use the skill root for the always-needed instructions and companion files for conditional detail.

- Keep activation-critical instructions in `SKILL.md`
- Put bulky examples, command references, and troubleshooting detail in `references/`
- Put templates or structured output examples in `assets/` when they are only needed for certain tasks
- Put helper code in `scripts/` only when running it is materially better than restating the logic inline

Only include a companion file if the main skill tells the agent when and why to load it.

Use these fast self-review tests before calling the skill done:

- overfitting test: remove content that assumes one repo layout, one starter
  bundle of resources, one exact command path, one exact auth check, one
  current UI or provider behavior, or one canonical naming scheme unless that
  specificity is safety-critical
- minutiae test: trim content when the model is more likely to copy it than
  reason from it, especially long field lists, many exact flags, examples that
  outnumber rules, or low-value syntax caveats
- progressive disclosure test: move detail down a layer when metadata, root,
  references, or scripts can carry it more cheaply without harming behavior

For final self-review, ask:

- trigger quality: does the description activate on the right class of
  requests and explicitly exclude nearby ones
- boundary discipline: does the skill stay in its domain, tool, or router lane
- reasoning quality: does the root teach the agent how to think through the
  task rather than list syntax
- root bloat: does `SKILL.md` stay focused on ownership, flow, and validation
- reference discipline: does each reference file have a narrow, useful job
- reference bloat: do references stay operationally dense instead of turning
  into partial manuals

## Instruction Patterns

Useful patterns for this repo include:

- short gotchas sections for non-obvious Kong constraints
- checklists for multi-step workflows
- validation loops that tell the agent what to verify before answering
- output templates when response shape matters

Prefer one clear default path with validation over a long menu of possibilities.

## Fit The Skill To This Repo

This repo already has shared installation wrappers for multiple harnesses. The skill itself should stay portable.

That means:

- put reusable behavior in `SKILL.md`
- keep harness-specific packaging out of the skill body
- avoid writing the skill as if it belongs only to one client

The repo tooling will sync the shared skill inventory into the relevant plugin manifests and generated documentation.
Keep that workflow plugin-aware: choose the owning plugin package first, then place the skill under that plugin's `skills/` tree.

Treat this repo as the contributor-facing source package, not the end-user product surface.

- keep reusable skill behavior in `plugins/<plugin>/skills/`
- keep checked-in install metadata and context files aligned with the skills that actually ship
- prefer pointing docs at checked-in reference files over duplicating large inline config snippets that can drift

If you touch harness-specific install snippets under `docs/install/`, verify that they only mention current skills and current checked-in config shapes.

## Quality Bar For Submission

Before considering the skill done, check:

- is the scope clear
- is the trigger condition obvious
- does the skill prescribe a real workflow
- does it contain Kong-specific value
- does it avoid generic filler
- does the description make activation likely for the right requests and unlikely for the wrong ones
- does the skill choose defaults clearly instead of presenting equal-option menus
- does it tell the agent what to validate before answering
- were all scaffold placeholders replaced with real content
- would an agent using this skill likely perform better than without it
- does `SKILL.md` read like a decision layer rather than a condensed manual
- does each reference file have one clear load condition and one clear job
- did you run the overfitting, minutiae, and progressive-disclosure tests

If the answer to the last question is not clearly yes, the skill probably needs to be narrowed or rewritten.

## Practical Authoring Heuristics

- Prefer concrete verbs over abstract nouns.
- Prefer decision rules over encyclopedic explanation.
- Prefer a few strong constraints over many soft suggestions.
- Prefer examples when they clarify a pattern, not when they just restate the rule.
- Prefer companion reference files when the main skill starts becoming long and hard to follow.

## Working In This Repo

When you add or substantially change a skill, keep the authoring loop simple:

1. write or revise the skill
2. sync the generated repo metadata
3. run validation

For a new skill, the preferred contributor flow is:

1. check `docs/skills.md` and `plugins/<plugin>/skills/` for overlap
2. decide whether this belongs in an existing skill, a new domain skill, or a
   new tool skill
3. scaffold the new skill only if the boundary is clearly justified
4. write the skill body and only the companion files it really needs
5. sync generated metadata
6. run validation

If you have access to a skill-authoring helper in your host tool, use it before step 1 or during revision, then review the result against this file before committing.

When helping a user create or edit skills in this repo, do not ordinarily
suggest or make changes to the shared scaffolding in the repo root such as task
wrappers, generated-manifest sync logic, install docs, or other packaging and
harness-support files. Treat those as stable repo infrastructure and only touch
them in exceptional circumstances.

If the scaffolding appears repeatedly broken, surprising, or inconsistent with
the documented workflow, say so plainly and suggest that the user file an issue
in the repo rather than silently broadening the task into a scaffolding
refactor.

The exact commands and file map are documented elsewhere in this repo. This file is intentionally focused on writing better skills, not on repeating procedural details.
