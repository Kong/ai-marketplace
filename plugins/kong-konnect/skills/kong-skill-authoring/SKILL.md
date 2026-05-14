---
name: kong-skill-authoring
description: Create or refactor a skill in this repo. Use when deciding extend-versus-create, classifying domain/tool/router ownership, tightening a description, or reviewing a skill package against repo policy. Not for the product workflow itself.
license: MIT
metadata:
  product: repo
  internal: true
  category: skill-authoring
  tags:
    - kong
    - skills
    - authoring
    - review
    - workflow
---

# Kong skill authoring

## Goal

Help contributors create or revise high-signal skills for this repository
without creating overlap, generic filler, root bloat, or tool-boundary
confusion.

Treat `AGENTS.md` as the canonical authoring policy. Use this skill as the
decision layer for what the skill should own, how it should be structured, and
what should stay out of it.

## Tool Selection

- Use the host environment's built-in generic skill-authoring helper first when
  it materially improves structure, then apply this repo's rules as the final
  authority.
- Use this skill for authoring decisions and review workflow, not for the
  Konnect or Gateway task that the target skill will later handle.
- When the user is asking for product execution, diagnosis, or declarative
  implementation rather than skill authoring, hand off to the relevant domain,
  router, or tool skill instead of keeping the work here.

## References To Load

- Load `AGENTS.md` first for authoring policy, section conventions, layered
  skill design, and plugin-aware repo boundaries.
- Load `docs/skills.md` and inspect `plugins/*/skills/*/SKILL.md` when checking
  for overlap, adjacent trigger surfaces, or handoff targets.

## Workflow

1. State the target skill's job in one sentence.
   - If the request is really about doing Konnect or Gateway work rather than
     authoring the skill, stop and hand off.
2. Check overlap before drafting.
   - Inspect `docs/skills.md` and the existing `plugins/<plugin>/skills/`
     trees.
   - Extend an existing skill when the trigger class, ownership boundary, and
     operating procedure are substantially the same.
   - Create a new skill only when the workflow, owner, or trigger surface is
     materially different.
3. Classify the skill boundary.
   - Use a domain skill when the hard part is Kong-specific diagnosis,
     inspection order, or operator workflow.
   - Use a tool skill when the hard part is `decK`, `kongctl`, Terraform,
     import/adopt behavior, or file-shape ownership.
   - Use a router skill only when the main problem is broad classification
     across existing specialist skills.
   - If both domain and tool concerns appear, keep diagnosis in the domain
     skill and hand off implementation to the tool skill.
4. Define the trigger surface before writing body text.
   - Write down what a user would actually ask.
   - Name the nearby requests that should not activate the skill.
   - Keep the `description` activation-grade: front-loaded, explicit, and
     usually under roughly 260 characters.
   - Tighten the boundary instead of adding long example lists.
5. Keep `SKILL.md` as the decision layer.
   - Root content should cover ownership, workflow or inspection order,
     defaults, validation, and handoffs.
   - Do not turn the root into a command catalog, product guide, schema dump,
     or copy of repo policy that already lives in `AGENTS.md`.
   - Prefer subtraction before rewriting. Delete detail that does not change
     agent behavior.
6. Place detail in the cheapest useful layer.
   - Keep branch-specific depth in `references/` with an explicit load
     condition.
   - Make each reference file support one branch, failure domain, or execution
     mode. Split files that carry multiple unrelated jobs.
   - Add a `scripts/` helper only when deterministic validation or
     transformation is materially safer than prompt text.
   - Do not create companion files just to relocate generic filler.
7. Run the review tests before you finalize structure.
   - Overfitting test: remove assumptions about one repo layout, starter
     bundle, exact command path, exact auth check, current UI behavior, or one
     canonical naming scheme unless that specificity is safety-critical.
   - Minutiae test: trim long field lists, dense flag catalogs, or examples
     that the model would copy more readily than reason from.
   - Progressive-disclosure test: move detail down a layer when metadata, root,
     references, or scripts can hold it more cheaply without harming behavior.
   - If the root still reads like a condensed runbook or partial manual, cut or
     relocate content before polishing wording.
8. Apply the repo's section conventions.
   - Domain skills should use `Goal`, `Tool Selection`, `References To Load`,
     `Workflow` or `Inspection Order`, an explicit gotchas section,
     `Validation Checklist`, and `Handoffs`.
   - Tool skills should use `Goal`, `Tool Positioning`, `References To Load`,
     `Validation Contract`, `Operating Rules`, `Workflow`,
     `Validation Checklist`, and `Handoffs`.
   - Router skills should use `Goal`, `Shared Operating Defaults`,
     `Classification Order`, `Routing Rules`, `Validation Checklist`, and
     `Output Style`.
   - Do not introduce cosmetic heading drift for equivalent concepts.
9. Preserve Kong-specific boundaries.
   - For Konnect work, prefer the shared `kong-konnect` MCP server for live
     inspection when available, but keep fallback paths through `kongctl`,
     declarative config, logs, or user-provided artifacts.
   - Preserve the repository's existing toolchain instead of forcing migration
     between `decK`, `kongctl`, and Terraform.
   - Keep domain skills focused on reasoning quality and handoffs instead of
     absorbing full tool-execution playbooks.
10. Produce the smallest useful authoring output.
   - State whether to extend an existing skill or create a new one.
   - Name the owning plugin path.
   - Provide the exact `description` trigger surface.
   - List the minimum root sections and any justified companion files with
     exact load conditions.
   - When reviewing an existing skill, lead with the highest-risk finding and
     the smallest corrective move.
   - Before stopping, name the main pass/fail call for trigger quality,
     boundary discipline, reasoning quality, root bloat, reference discipline,
     and reference bloat.

## Validation Checklist

- The edit stays within the owning skill directory unless the task explicitly
  broadens scope.
- Overlap was checked against `docs/skills.md` and the existing
  `plugins/<plugin>/skills/` trees.
- The skill boundary is explicit: existing-skill revision, domain, tool, or
  router.
- The `description` activates on the right requests and excludes nearby ones.
- `SKILL.md` stays focused on trigger boundary, ownership boundary, workflow or
  inspection order, defaults, validation, and handoffs.
- The root teaches workflow, defaults, validation, and handoffs rather than
  reciting commands or product facts.
- Any reference file has a narrow load condition and does not carry core
  defaults that the root needs.
- Any reference file supports one branch, failure domain, or execution mode
  instead of acting like a second root skill.
- Any script has a deterministic job and a clear run condition.
- Konnect MCP guidance is a preferred live-inspection path, not a hard
  dependency.
- The skill preserves the user's existing declarative toolchain unless the user
  asked to change it.
- The revision does not silently pull in shared scaffolding, generated
  manifests, or unrelated skills.
- If the task is a review, the main issue is identified before line editing:
  boundary drift, root bloat, reference bloat, drift risk, weak validation, or
  poor handoffs.
- The overfitting, minutiae, and progressive-disclosure tests were run before
  calling the skill done.

## Handoffs

- Hand off broad Konnect request classification to `konnect-platform-router`
  when the authoring question is really "which existing skill should own this?"
- Hand off product diagnosis or implementation details to the relevant domain
  or tool skill once the authoring boundary is settled.
- Use existing skills as boundary examples, not as templates to copy verbatim.
