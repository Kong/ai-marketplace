---
name: technical-writing
description: Write task-oriented developer documentation and Dev Portal page copy in plain, active-voice prose with scannable structure and no em-dashes or AI tells. Use when authoring or editing technical docs, API guides, and page content. Not for layout or theming.
license: MIT
metadata:
  product: konnect
  category: documentation
  tags:
    - kong
    - konnect
    - dev-portal
    - documentation
    - writing
---

# Technical documentation writing

## Goal

Write and edit developer-facing documentation that is easy to consume: plain,
task-oriented, active-voice prose with scannable structure and clean
punctuation. Own the words and their organization within a page.

This skill is not Dev Portal specific, but it is built to work with the portal
skills. It pairs with `konnect-portal-page-design` for the components and layout
that hold the prose, and with `konnect-portal-branding` for appearance. Use it
whenever the deliverable is documentation, an API guide, or page copy, whether
or not it ships through a portal.

## Tool Selection

- When the content documents Konnect resources, use the `kong-konnect` MCP
  server to pull real details (control planes, services, routes, specs) rather
  than inventing example values.
- When the content is a portal page, hand structure and components to
  `konnect-portal-page-design` and keep this skill on the prose. Use callouts,
  tabs, and code blocks through MDC, and verify each component's props against
  live metadata.
- Follow Kong's documentation style guide for terminology and capitalization
  when writing Kong content, and default to the Google and Microsoft developer
  style guides for anything it does not cover.

## References To Load

Load only the file that matches the active step:

- `references/style-rules.md`
  - Load when deciding voice, tense, person, headings, lists, code samples, and
    Kong terminology and capitalization.
- `references/avoid-llm-tells.md`
  - Load when editing for punctuation and word choice: em-dashes, banned words,
    hollow phrases, and machine-sounding constructions to remove.
- `references/doc-structures.md`
  - Load when structuring a page: hero, getting started, authentication,
    request and response samples, and troubleshooting or FAQ.

## Workflow

### 1. Fix the reader and the task

Before writing, name who reads this and what they are trying to do. Documentation
serves a task. Lead with what the reader does, not with background.

### 2. Choose the structure first

Pick the page shape from the reader's task, then write into it. Keep everything
for one use case on one page so the reader is not bounced between concept and
configuration. Load `references/doc-structures.md` for the common shapes.

### 3. Write in the house voice

- Second person, active voice, present tense.
- Plain language: the shortest correct word, short sentences, no filler.
- Front-load: put the answer or goal first, context after.
- Scannable: descriptive sentence-case headings, short paragraphs, lists for
  steps or options, tables for comparisons.
- "We recommend" a choice, and always give the reason.

Load `references/style-rules.md` for the specifics, including Kong terminology.

### 4. Make it correct and self-contained

- Pull real values from MCP or the user's config instead of guessing.
- Use placeholders for anything the reader must supply: `ALL_CAPS_WITH_UNDERSCORES`
  for generic values, `{curlyBraces}` for spec parameters, `example.com` for
  illustrative hosts, `localhost` for runnable ones. Never embed real secrets.
- One command per code block, commands and output in separate blocks, each block
  language-tagged. End a how-to with a step that verifies it worked.

### 5. Edit out the tells

Reread and cut the machine-sounding layer. No em-dashes or en-dashes. No banned
filler words. No "it's not just X, it's Y." No hollow intensifiers or template
openers. Load `references/avoid-llm-tells.md` and apply it as a final pass.

### 6. Match the density

Aim for enough to be self-contained and no more. Not so terse that the reader
must guess, not so verbose that they skim past the point. Cut a sentence if it
repeats the one before it.

## Writing Gotchas

- Em-dashes and en-dashes are the clearest AI tell. Target zero. Replace with a
  comma, colon, parentheses, or two sentences. Do not use `--` as a substitute.
- Generic headings such as "Overview" or "Details" waste the most scannable line
  on the page. Say what the section covers.
- Passive voice hides who acts. Name the actor.
- Latin abbreviations (`e.g.`, `i.e.`) read as stiff. Use "for example" and
  "that is."
- "Click here" and "read more" are dead link text. Describe the destination.
- Synonym-cycling for variety confuses readers. Repeat the clearest term.

## Validation Checklist

Before answering, verify that you can state:

- who the reader is and the task the page serves
- that the page leads with the task and stays on one page per use case
- that prose is second person, active voice, present tense, and plain
- that headings are descriptive and sentence case, and content is scannable
- that samples use placeholders, are language-tagged, and a how-to ends in a
  verification step
- that the text contains no em-dashes, banned filler, or template openers
- that real values came from MCP or the user, not invention

## Handoffs

- Use `konnect-portal-page-design` for the components and layout that present
  this content on a portal page.
- Use `konnect-portal-branding` when the request is about appearance rather than
  wording.
- Use `konnect-api-publish` or `konnect-api-catalog` when the real gap is that
  an API is not published or modeled, not that its docs need writing.
