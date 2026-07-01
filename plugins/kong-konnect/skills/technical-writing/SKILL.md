---
name: technical-writing
description: Write task-oriented developer documentation and Dev Portal page copy in plain, active-voice prose with clear, scannable structure. Use when authoring or editing technical docs, API guides, and page content.
license: MIT
metadata:
  product: konnect
  category: documentation
  tags:
    - kong
    - konnect
    - dev-portal
    - documentation
    - api-documentation
    - writing
---

# Technical documentation writing

## Goal

Write and edit developer-facing documentation that is easy to consume: plain,
task-oriented, active-voice prose with scannable structure and clean
punctuation. Own the words and their organization within a page.

This skill is not Dev Portal specific, but it pairs with the portal skills. It
works alongside `konnect-portal-page-design` for the components that hold the
prose and `konnect-portal-branding` for appearance. Work in page content files,
edit them locally or in a dedicated repository, and do not push destructive
changes to a live portal unless the user explicitly asks.

## Clarify First

Ask a few high-impact questions before you write, and offer a sensible default
so the user can simply confirm. Keep it to two or three questions. For this
skill, clarify:

- the reader and the task the page serves
- the source of truth for the technical details
- an existing page to match in tone and structure, if any
- the depth expected, from a quickstart to a full reference

## Tool Selection

- When the content documents Konnect resources, pull real details (control
  planes, services, routes, specs) through the `kong-konnect` MCP OpenAPI tools
  (`search` then `get_schema` then `execute`) instead of inventing values.
- When the content is a portal page, hand structure and components to
  `konnect-portal-page-design` and keep this skill on the prose.
- Follow Kong's documentation style guide for terminology and capitalization on
  Kong content, and default to the Google and Microsoft developer style guides
  otherwise.
- When unsure of Kong terminology or how Kong documents a concept, check
  `KnowledgeBaseSearch` rather than inventing it.

## References To Load

Load only the file that matches the active step:

- `references/style-rules.md`
  - Load when deciding voice, tense, person, headings, lists, code samples, and
    Kong terminology.
- `references/avoid-llm-tells.md`
  - Load when editing punctuation and word choice: em-dashes, banned words, and
    machine-sounding constructions to remove.
- `references/doc-structures.md`
  - Load when structuring a page: hero, getting started, authentication,
    request and response samples, and troubleshooting.

## Workflow

1. Name the reader and the task, and lead with what the reader does.
2. Choose the structure from that task and keep one use case on one page. Load
   `references/doc-structures.md`.
3. Write in the house voice: second person, active voice, present tense, plain,
   front-loaded, and scannable. Recommend choices with a reason. Load
   `references/style-rules.md`.
4. Make it self-contained: real values from MCP or the user, placeholders for
   reader-supplied values, one command per block, and a verification step to
   close a how-to.
5. Edit out the tells as a final pass. Load `references/avoid-llm-tells.md`.
6. Match the density. Cut a sentence that repeats the previous one; add one the
   reader would otherwise have to guess.

## Writing Gotchas

- Em-dashes and en-dashes are the clearest tell. Target zero, and do not use
  `--` instead.
- Generic headings such as "Overview" waste the most scannable line on the page.
- Passive voice hides who acts. Name the actor.

## Validation Checklist

Before finishing, confirm:

- who the reader is and the task the page serves
- that the page leads with the task and stays on one page per use case
- that prose is second person, active voice, present tense, and scannable
- that samples use placeholders and a how-to ends in a verification step
- that the text has no em-dashes, banned filler, or template openers
- that real values came from MCP or the user, not invention

## Handoffs

- Use `konnect-portal-page-design` for the components and layout that present
  this content.
- Use `konnect-portal-branding` when the request is about appearance rather than
  wording.
- Use `konnect-api-publish` or `konnect-api-catalog` when the real gap is that
  an API is not published or modeled, not that its docs need writing.
