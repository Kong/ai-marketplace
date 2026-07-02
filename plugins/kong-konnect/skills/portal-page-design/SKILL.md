---
name: portal-page-design
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
result. Choose well and sequence the work; never invent a component or prop from
memory.

## Clarify First

Batch two or three high-impact questions with a sensible default to confirm:

- the page's primary goal and audience
- which sections are wanted (hero, feature columns, doc sections, API list)
- whether it should match the structure of an existing page

## Tool Selection

Prefer the Konnect MCP server. It is the authoritative, always-current source
for MDC facts: the syntax rules, the available components, their props and slots,
design tokens, usage examples, formatting, validation, and page preview. When it
is connected, take facts from the server rather than memory, in this order:

1. Read the server's MDC syntax guide once at the start of the session.
2. Discover the available components, then read each component's props, slots,
   and examples before you use it. Write all prop names in kebab-case, even if
   the metadata shows them in camelCase.
3. Pull color, spacing, and type values from the server's design tokens.
4. Format, then validate, the MDC through the server.
5. Generate a page preview through the server and screenshot it (see Preview and
   iterate).

If the server is not connected, recommend the user install and connect it, since
verified components, tokens, validation, and preview make the result much
better. If they cannot or prefer not to, continue with general MDC knowledge and
the user's existing portal files, load `references/mdc-essentials.md`, and say
plainly that you cannot verify components, props, or tokens against live metadata
and that the result will be less reliable.

Pages and snippets can be read and written directly through the server. Read
current state before an update, which overwrites content. Do not write to a live
portal unless the user explicitly asks; author locally or in a repo otherwise,
and preserve an existing `kongctl` or Terraform toolchain when one is in use.

## Preview and iterate

Previewing needs the target portal's origin, a valid token, and a browser tool.
Without them, ask the user to preview in the Portal Editor instead. Set the
viewport before opening the single-use preview URL, wait for full hydration
(network idle, no pending animations), then screenshot. Regenerate the URL only
when the MDC changes, not for each width.

- Build from a source design: screenshot the source, build the page, preview,
  screenshot at the source width, and compare layout, color, type, and spacing.
- Edit an existing page: screenshot the live page as a "before," make the
  change, preview, screenshot the "after" at the same width, and compare.
- Improve responsive behavior: screenshot at several widths (mobile, tablet,
  desktop), fix overflow and breakpoint issues, then re-check each width.

## Design Requirements

- Prefer a component's dedicated visual props (for background, padding, margin,
  radius, and type size) over a catch-all styles prop. Use a styles prop only
  for what dedicated props cannot express, such as a gradient background.
- Always give a hero a title and a description, plus actions when it needs
  buttons. Never ship a hero without a title.
- Lay parallel items out in the responsive column component so they wrap cleanly
  on mobile and tablet; cards must reflow, not overflow.
- Keep adjacent buttons, cards, and similar elements at least 12px apart.
- Meet WCAG AA contrast for all text on its background and for buttons.

## References To Load

- `references/layout-patterns.md`
  - Composition judgment (what shape a section wants). Get the exact syntax for
    each shape from the server's component examples.
- `references/mdc-essentials.md`
  - Load only when the Konnect MCP server is not available and you must rely on
    general MDC knowledge.

## Workflow

1. Name the page type and its ordered sections before writing MDC.
2. Map each section to the component whose job it names, then confirm that
   component's props and slots before writing it. Keep the component set small;
   repetition reads as consistency.
3. Compose by nesting section, container, and column components around content,
   not one monolithic block.
4. Style with design tokens; use the responsive column component and breakpoint
   props for parallel items.
5. Format and validate the MDC.
6. Preview and screenshot across widths, then iterate.

## MDC Gotchas

- This is the current v3 Konnect portal MDC system. Do not use legacy Gateway
  Enterprise portal templates; they are a different, incompatible model.
- Use MDC component syntax only. Never use HTML tags, a raw `<div>`, or Vue
  `<Component>` syntax in page content.
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
- every component and prop was confirmed against metadata, or clearly flagged as
  unverified when the server was unavailable
- layout uses design tokens and the responsive column component
- dedicated props were used instead of a catch-all styles prop where possible
- any hero has a title; adjacent elements are at least 12px apart; text and
  buttons meet WCAG AA contrast
- repeated blocks are snippets, not copied markup
- every image has alt text and heading levels are sequential
- the MDC validated and previewed cleanly (after hydration) on mobile, tablet,
  and desktop, or the user previewed it in the Portal Editor

## Handoffs

- Use `portal-branding` for colors, fonts, imagery, and brand parity.
- Use `technical-writing` for the wording inside the components.
- Use `terraform-konnect` or `kongctl-declarative` to encode pages as code.
- Use `konnect-api-publish` when the goal is getting an API into the portal.
