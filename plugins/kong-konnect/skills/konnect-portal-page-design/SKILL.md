---
name: konnect-portal-page-design
description: Structure and compose Kong Konnect Dev Portal pages with MDC components like heroes, cards, columns, tabbed panels, callouts, and expandable sections. Use for page layout, section design, and component choice. Not for documentation writing or editing.
license: MIT
metadata:
  product: konnect
  category: dev-portal-design
  tags:
    - kong
    - konnect
    - dev-portal
    - mdc
    - markdown-components
    - page-design
---

# Konnect Dev Portal page design

## Goal

Turn a page intent into a well-structured Dev Portal page built from MDC
(Markdown Components). Own the layout: which sections the page needs, which
components express them, and how they compose into a consistent, responsive
result. The `kong-konnect` MCP server owns the facts, component names, props,
slots, syntax, tokens, examples, and preview. Your job is to choose well and
sequence the work; never invent a component or prop from memory.

## Clarify First

Batch two or three high-impact questions with a sensible default to confirm:

- the page's primary goal and audience
- which sections are wanted (hero, feature columns, doc sections, API list)
- whether it should match the structure of an existing page

## Tool Selection

The `kong-konnect` MCP server owns the MDC facts. Use its tools rather than
restating their output from memory, and discover the exact tool names from the
server rather than assuming them. The working order is:

1. Load the server's authoritative MDC syntax guide once at session start. It
   covers syntax, nesting, slots, and YAML props.
2. Discover which components exist from the server's component list.
3. For any component you will use, read its definitive props and slots from the
   server's component metadata before writing it. Metadata returns prop names in
   camelCase; write them kebab-case in MDC (`fullWidth` becomes `full-width`).
4. Copy idiomatic usage from the server's component examples.
5. Pull `--kui-*` values for color, spacing, and type from the server's design
   tokens.
6. Format, then validate, the MDC through the server before previewing.
7. Look up the target portal's origin (its canonical or default domain) and
   generate a preview through the server, then open it with a browser tool and
   screenshot desktop and mobile.

Preview URLs are single-use and time-limited. Regenerate one per view; once a
page is loaded, resize the browser in place to test widths rather than
regenerating per width.

Pages and snippets can be read and written directly through the server. Read
current state before an update, which overwrites content. Do not write to a live
portal unless the user explicitly asks; author locally or in a repo otherwise,
and preserve an existing `kongctl` or Terraform toolchain when one is in use.

## References To Load

- `references/layout-patterns.md`
  - Composition judgment (what shape a section wants). Get the exact syntax for
    each shape from the server's component examples.

There is no hand-maintained syntax or component reference. Those come from the
MCP server, which stays current as components change.

## Workflow

1. Name the page type and its ordered sections before writing MDC.
2. Map each section to the component whose job it names, then confirm that
   component against the server's metadata and examples before writing it. Keep
   the component set small; repetition reads as consistency.
3. Compose by nesting section, container, and column components around content,
   not one monolithic block.
4. Style with `--kui-*` tokens from the server's design tokens; use responsive
   breakpoint props for columns.
5. Format and validate the MDC through the server.
6. Preview and screenshot at desktop and mobile; iterate.

## MDC Gotchas

- This is the current v3 Konnect portal MDC system. Do not use legacy Gateway
  Enterprise portal templates; they are a different, incompatible model.
- Never invent component or prop names. If the server's metadata does not list
  it, it does not exist. Prop names are kebab-case in MDC even though metadata
  shows camelCase.
- Snippets are a flat namespace and render only when a page references them.
  Pages support nested slugs; snippets do not.
- Frontmatter in page content wins over separately supplied title and
  description.
- Reserved root paths (`/login`, `/register`, `/account`) cannot be page slugs.

## Validation Checklist

Before finishing, confirm:

- the page type and its ordered sections are named
- every component and prop used was confirmed against the server's metadata
- layout uses the server's design tokens and responsive breakpoints
- repeated blocks are snippets, not copied markup
- every image has alt text and heading levels are sequential
- content passed the server's validator and previewed cleanly on desktop and
  mobile

## Handoffs

- Use `konnect-portal-branding` for colors, fonts, imagery, and brand parity.
- Use `technical-writing` for the wording inside the components.
- Use `terraform-konnect` or `kongctl-declarative` to encode pages as code.
- Use `konnect-api-publish` when the goal is getting an API into the portal.
