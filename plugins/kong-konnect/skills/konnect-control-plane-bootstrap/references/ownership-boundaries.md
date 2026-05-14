# Ownership Boundaries

Use this file when naming, labels, region, repo ownership, or durable
management path are the real bootstrap questions.

## Core Rule

Bootstrap boundaries become long-lived operational boundaries. Treat them as
first-class decisions, not as afterthoughts.

## Boundary Questions

- which region should own this control plane
- how will names distinguish environment or purpose
- which labels or slices separate ownership
- which repo and automation path will manage the control plane
- which tool owns durable config: Terraform or `kongctl`

## Decision Rules

- Prefer names that encode environment or purpose clearly enough to avoid
  operators debugging the wrong control plane later.
- Prefer labels or slices that match the actual operating boundary, not just
  the bootstrap requestor.
- Choose the durable tool from existing repo ownership first. Do not introduce
  Terraform or `kongctl` as a new default during bootstrap unless the user asks
  for that migration.
- Treat region as an explicit design choice. If the region is ambiguous, do not
  paper over it with a generic "create first, fix later" answer.

## Common Risks

| Risk | Why it matters |
|---|---|
| Region chosen casually | later symptoms look like auth or drift issues |
| Similar control plane names | operators debug the wrong environment |
| No explicit owner | bootstrap succeeds but durable management is unclear |

## What To Check Before Moving On

- whether the control plane can still be identified unambiguously once several
  environments exist
- whether the repo or automation owner is named explicitly
- whether the recommended toolchain matches the files the team already keeps in
  version control
- whether the boundary decision resolves the user's real ambiguity instead of
  deferring it

## What To Return

Return:

- the intended ownership boundary
- the durable management path
- the specific naming, region, or ownership rule that should be kept stable
- the specific bootstrap decision that must be fixed before moving on
