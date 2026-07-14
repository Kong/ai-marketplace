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

Turn a page intent into a well-structured Dev Portal page built from MDC (Markdown
Components). Own the layout: which sections the page needs, which components
express them, and how they compose into a consistent, responsive result. Never
invent a component or prop from memory.

## Clarify First

Ask two or three high-impact questions, each with a default to confirm:

- the page's primary goal and audience
- which sections are wanted (hero, feature columns, doc sections, API list)
- whether it should match an existing page's structure

## Tool Selection

Prefer the Konnect MCP server: the authoritative, always-current source for MDC
facts (syntax rules, available components, their props and slots, design tokens,
usage examples, formatting, validation, page preview). When connected, take facts
from it rather than memory, and read its MDC syntax guide once at the start of the
session; the Workflow below then draws components, tokens, validation, and preview
from the server in order.

If not connected, recommend connecting it, since verified components, tokens,
validation, and preview make the result much better. Otherwise work from general
MDC knowledge and the user's existing portal files (see MDC essentials), and say
plainly you cannot verify components, props, or tokens against live metadata and
the result is less reliable.

Read and write pages and snippets directly through the server. Read current state
before an update, which overwrites content. Do not write to a live portal unless
the user explicitly asks; otherwise author locally or in a repo, and preserve an
existing `kongctl` or Terraform toolchain when one is in use.

## Preview and iterate

Previewing needs the target portal's origin, a valid token, and a browser tool;
without them, ask the user to preview in the Portal Editor. Set the viewport
before opening the single-use preview URL, wait for full hydration (network idle,
no pending animations), then screenshot. Regenerate the URL only when the MDC
changes, not per width.

- Build from a source design: screenshot the source, build the page, preview,
  screenshot at the source width, compare layout, color, type, and spacing.
- Edit an existing page: screenshot the live page as a "before," make the change,
  preview, screenshot the "after" at the same width, compare.
- Responsive behavior: screenshot at several widths (mobile, tablet, desktop), fix
  overflow and breakpoint issues, re-check each width.

## Design Requirements

- Prefer a component's dedicated visual props (background, padding, margin, radius,
  type size) over a catch-all styles prop; use a styles prop only for what
  dedicated props cannot express (a gradient background).
- Always give a hero a title and description, plus actions when it needs buttons.
  Never ship a hero without a title.
- Lay parallel items out in the responsive column component so they wrap cleanly
  on mobile and tablet; cards must reflow, not overflow.
- Keep adjacent buttons, cards, and similar elements at least 12px apart.
- Meet WCAG AA contrast for all text on its background and for buttons.

## Layout patterns

Composition judgment only; get exact, current syntax, props, and slots from the
server's component examples and metadata, and treat these names as a starting
point, not a fixed list.

- Hero: a title, a short value line, one or two actions. Confirm its slots first
  (typically named slots for tagline, title, description, actions, and image
  rather than a default slot).
- Feature columns: the responsive column container for parallel items (cards,
  entry points); set per-breakpoint column counts.
- Feature row: alternate text and media by pairing containers with a gap.
- Doc page: sections in reading order on one page: hero, getting started, auth,
  request/response, troubleshooting. Prose comes from `technical-writing`.

Reuse the same hero and card patterns across pages, group related actions into
buttons, extract repeated blocks into snippets, and confirm on mobile.

## MDC essentials

Fallback for when the server is unavailable; everything here is a
general-knowledge starting point, not verified truth.

- Write a component as `::component-name` on its own line, content or slots below,
  closed with `::`.
- Put props in a YAML block between `---` fences, kebab-case names
  (`background-color`, `show-icon`, `columns-breakpoints`). Quote string values.
- Name slots with `#slot-name`, a blank line between one slot's content and the
  next marker. Main content is the default slot.
- Nest a child component by indenting it one level under its parent.
- Reuse common components by role: hero for the masthead, sections and containers
  for structure, a responsive column component for parallel items, and cards,
  buttons, alerts, and images for content. Keep to common ones and tell the user
  they are unverified.
- Prefer `--kui-*` design tokens for color, spacing, and type; the primary token
  family reflects the portal's configured brand color.
- Apply the Design Requirements above. Without the server you cannot generate a
  preview URL, so ask the user to preview in the Portal Editor, and check the
  structure by eye against these rules first.

## Workflow

1. Name the page type and its ordered sections before writing MDC.
2. Map each section to the right component from the server's available components;
   confirm its props, slots, and examples against the metadata before writing it.
   Keep the component set small; repetition reads as consistency.
3. Compose by nesting section, container, and column components around content,
   not one monolithic block.
4. Style with the server's design tokens for color, spacing, and type; use the
   responsive column component and breakpoint props for parallel items.
5. Format, then validate, the MDC through the server.
6. Generate a preview and screenshot across widths, then iterate (see Preview and
   iterate).

## MDC Gotchas

- This is the current v3 Konnect portal MDC system; do not use legacy Gateway
  Enterprise portal templates, a different and incompatible model.
- Use MDC component syntax only. Never use HTML tags, a raw `<div>`, or Vue
  `<Component>` syntax in page content.
- Never invent component or prop names: if the server's metadata does not list it,
  it does not exist. Prop names are kebab-case in MDC even though metadata shows
  camelCase.
- Snippets are a flat namespace and render only when a page references them. Pages
  support nested slugs; snippets do not.
- Frontmatter in page content wins over separately supplied title and description.
- Reserved root paths (`/login`, `/register`, `/account`) cannot be page slugs.

## Validation Checklist

- page type and ordered sections named
- components and props confirmed against metadata, or flagged unverified
- layout uses design tokens and the responsive column component
- dedicated props over a catch-all styles prop
- hero has a title; 12px minimum spacing; WCAG AA contrast
- repeated blocks are snippets, not copied markup
- images have alt text; heading levels sequential
- MDC validated and previewed on mobile, tablet, desktop (or in the Portal Editor)

## Handoffs

- `portal-branding` for colors, fonts, imagery, and brand parity.
- `technical-writing` for the wording inside components.
- `terraform-konnect` or `kongctl-declarative` to encode pages as code.
- `konnect-api-publish` when the goal is getting an API into the portal.
