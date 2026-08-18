---
name: technical-writing
description: Write task-oriented developer documentation and Dev Portal page copy in plain, active-voice prose with clear, scannable structure. Use when authoring or editing technical docs, API guides, and page content.
license: MIT
metadata:
  product: konnect
  category: documentation
  tags: kong,konnect,dev-portal,documentation,api-documentation,writing
---

# Technical documentation writing

## Goal

Write and edit developer-facing documentation that is easy to consume: plain,
task-oriented, active-voice prose with scannable structure and clean punctuation.
Own the words and their organization within a page.

Not Dev Portal specific, but it pairs with the portal skills: `portal-page-design`
for the components that hold the prose, `portal-branding` for appearance. Work in
page content files, locally or in a repo, and do not push destructive changes to a
live portal unless the user explicitly asks.

## Clarify First

Ask two or three high-impact questions, each with a default to confirm:

- the reader and the task the page serves
- the source of truth for the technical details
- an existing page to match in tone and structure, if any
- the depth expected, from quickstart to full reference

## Tool Selection

- Documenting Konnect resources: pull real details (control planes, services,
  routes, specs) from real entities through the `kong-konnect` MCP server instead
  of inventing values. If it is not connected, recommend installing it; otherwise
  ask the user for real values or mark them clearly as placeholders, not guesses.
- Portal-page content: hand structure and components to `portal-page-design` and
  keep this skill on the prose.
- Follow Kong's documentation style guide for terminology and capitalization on
  Kong content; default to the Google and Microsoft developer style guides
  otherwise.
- Unsure of Kong terminology or how Kong documents a concept: check the server's
  Kong documentation knowledge base. If unavailable, rely on the style guides and
  flag anything you cannot confirm.

## Workflow

1. Name the reader and the task; lead with what the reader does.
2. Choose the structure from that task and keep one use case on one page.
3. Write in the house voice: second person, active voice, present tense, plain,
   front-loaded, scannable. Recommend choices with a reason.
4. Make it self-contained: real values from MCP or the user, placeholders for
   reader-supplied values, one command per block, a verification step to close a
   how-to.
5. Edit out the tells as a final pass.
6. Match the density: cut a sentence that repeats the previous one; add one the
   reader would otherwise guess.

## Style rules

These combine Kong's documentation style guide with the Google and Microsoft
developer style guides, which agree on the core.

Voice and grammar:

- Second person, active voice, present tense. Passive voice hides who acts; name
  the actor.
- Plain verbs: "run" not "execute," "use" not "utilize," "to" not "in order to."
- Contractions are fine in prose; drop them in warnings for a serious tone.
- Name what a bare "this" points to. No Latin abbreviations (use "for example,"
  "that is"). Use allowlist and denylist, main branch, and neutral pronouns.
- Recommend with "we recommend" and always give the reason.

Headings, lists, tables:

- Headings: descriptive, not generic; sentence case; task headings can use a bare
  verb.
- Numbered lists for sequences, bulleted otherwise; parallel structure; end
  punctuation only for full sentences.
- Tables for parameter references, status codes, and comparisons.

Code samples:

- One command per block; commands and output in separate blocks; language-tag
  every block; no `$` prompt; wrap long commands with `\`.
- Placeholders: `ALL_CAPS_WITH_UNDERSCORES` for generic values, `{curlyBraces}`
  for spec parameters, `example.com` for illustration, `localhost` for runnable
  examples. Never embed real secrets.

Kong terminology:

- Capitalize Gateway entities: Certificate, Consumer, Plugin, Route, Service,
  Target, Upstream, Vault.
- Keep lowercase: control plane, data plane, application, developer, hybrid mode,
  service mesh.
- Plugin names: capitalize the name, not "plugin" ("Rate Limiting plugin"); use
  the lowercase slug in code (`rate-limiting`).
- American English. Refer to third-party UI by label only, not color or position.

Page tenets:

- Every page is page one: a reader answers their question on one page; do not split
  a concept from its configuration.
- A how-to has validation: the final step confirms the product works.

## Avoid LLM tells

These patterns make prose read as machine-generated. Remove them in a final
editing pass, in this order (em-dashes and en-dashes are the clearest tell, so
start there):

1. Delete every em-dash and en-dash, rewriting the sentence around it. The hard cap
   is zero, headings included. Replace with a comma, colon, parentheses, or two
   sentences, and do not use `--` as a substitute.
2. Replace always-replace words: delve to explore; leverage (verb) to use; robust
   to reliable; seamless to smooth; utilize to use; landscape (metaphor) to field.
   For tapestry, synergy, game-changer, cutting-edge, and embrace (metaphor), say
   the concrete thing.
3. Cut hedges, intensifiers, and template openers (see below).
4. Break up any run of three same-length sentences.

Constructions to avoid:

- "It's not just X, it's Y" and "not only X but Y." Rewrite as a direct statement,
  at most one per document.
- Hollow hedges and intensifiers: genuinely, truly, quite frankly, it's worth
  noting that, it's important to note, could potentially. Keep one hedge at most.
- Vague endorsements ("worth reading"), chatbot artifacts ("Great question!", "I
  hope this helps!"), and template openers ("In today's X," "When it comes to,"
  "Whether you're X or Y").
- Cutoff disclaimers and unfilled placeholders left in the text.

Flag-in-clusters words: any one may be fine, but if two or more cluster, rewrite
the paragraph plainly: harness, navigate, foster, elevate, unleash, streamline,
empower, bolster, resonate, revolutionize, facilitate, underpin, ecosystem,
myriad, plethora.

Rhythm: prefer plain copulas ("is," "has") over "serves as," "boasts," "features."
Do not synonym-cycle; repeat the clearest term. Vary sentence length; machine prose
is metronomic.

## Documentation structures

Pick the shape from the reader's task, then write each section in the house voice.
On a Dev Portal, hand components and layout to `portal-page-design`; this covers
what each section says and in what order.

Page types:

- Landing page: signpost the reader to the right next page. State value in one or
  two lines, then link. Do not teach here.
- How-to: an end-to-end task that ends with a validation step.
- Reference: concepts plus tables and schemas, with everything for one use case
  kept together.

API or product page, a dependable order:

- Hero: what the product does and who it is for, in one or two lines, plus the
  primary next step. Front-load value.
- Getting started: the shortest path to a first success. List every prerequisite
  up front, give copy-paste steps, and end with a step that proves it worked.
- Authentication: early and self-contained. Show how to obtain and send credentials
  with placeholders. Never show a real secret.
- Request and response samples: put request and response in separate,
  language-tagged blocks (formatting under Code samples).
- Troubleshooting or FAQ: headings phrased as the reader's actual question, with
  the cause and the fix in that order.

When documenting Konnect resources, pull real values from the `kong-konnect` MCP
server or the user's config; concrete examples beat invented ones, and keep secrets
out.

Keep each section self-contained and no longer than it needs to be.

## Validation Checklist

- reader and task identified
- leads with the task; one use case per page
- second person, active voice, present tense, scannable
- placeholders in samples; how-to ends with verification
- no em-dashes, banned filler, or template openers
- real values from MCP or the user, not invention

## Handoffs

- `portal-page-design` for the components and layout that present this content.
- `portal-branding` when the request is about appearance rather than wording.
- `konnect-api-publish` or `konnect-api-catalog` when the real gap is that an API is
  not published or modeled, not that its docs need writing.
