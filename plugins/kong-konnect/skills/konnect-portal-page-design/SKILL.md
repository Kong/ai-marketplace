---
name: konnect-portal-page-design
description: Structure and compose Kong Konnect Dev Portal pages with MDC components like heroes, cards, grids, callouts, tabs, and code blocks. Use for page layout, section design, and component choice. Not for documentation writing or editing.
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
result.

Keep every task inside one MDC page. Author and edit pages locally or in a
dedicated repository. Do not push destructive changes to a live portal through
the Konnect API unless the user explicitly asks.

## Tool Selection

- Use the shared `kong-konnect` MCP server for MDC component metadata, to
  validate and format MDC, and to generate a page preview URL. Verify each
  component's real props and slots against that metadata; if MCP is not
  connected, treat the reference details as a scaffold to confirm against
  `portaldocs.konghq.com`.
- Use the VS Code Konnect Dev Portal Toolkit for live preview, and Playwright to
  screenshot the preview at desktop and mobile widths.
- Preserve the repo's toolchain when pages are managed as code: `kongctl`
  (`portals[].pages`, `portals[].snippets`) or Terraform
  (`konnect_portal_page`, `konnect_portal_snippet`).

## References To Load

Load only the file that matches the active step:

- `references/mdc-syntax.md`
  - Load when writing MDC: block and inline components, props, slots, binding,
    nesting, span attributes, frontmatter, and snippet reuse.
- `references/component-catalog.md`
  - Load when choosing components, for the common palette and its typical props.
- `references/layout-patterns.md`
  - Load when composing sections: hero, card grid, feature row, and a doc-page
    skeleton.

## Workflow

1. Name the page type and its ordered sections before writing MDC. Keep the
   list short and purposeful.
2. Map each section to the component that names its job: `::page-hero` for the
   masthead, `::grid`/`::grid-item` or `::card` groups for parallel items,
   `::alert` for callouts, `::button` and `::a` for actions, `::image` and
   `::iframe` for media, `::apis-list` for APIs, `::accordion` for detail. Load
   `references/component-catalog.md` to confirm props.
3. Compose by nesting `::container` and `::grid` around content components
   rather than one monolithic block. Load `references/layout-patterns.md`.
4. Write valid MDC: block syntax with props and named slots, `:` for non-string
   props, and snippets for repeated blocks. Load `references/mdc-syntax.md`.
5. Keep it consistent and responsive: `--kui-*` tokens for spacing, color, and
   radius, responsive columns through breakpoint props, and reused hero and card
   patterns across pages.
6. Validate the MDC, generate a preview URL, and screenshot it at desktop and
   mobile before calling it done.

## MDC Gotchas

- This is the v3 Konnect portal MDC system (Vue and Nuxt). Do not use the legacy
  Gateway Enterprise portal templates; they are a different, incompatible model.
- Component props and slots can change and some are undocumented. Verify against
  live MCP metadata or `portaldocs.konghq.com` rather than trusting memory.
- Snippets are a flat namespace and only render when a page references them.
  Pages support nested slugs; snippets do not.
- Frontmatter inside page content wins over separately supplied title and
  description fields.
- Reserved root paths such as `/login`, `/register`, and `/account` cannot be
  used as page slugs.

## Validation Checklist

Before answering, verify that you can state:

- the page type and its ordered sections
- which component expresses each section and why
- that props and slots were confirmed against live metadata
- that layout uses `--kui-*` tokens and responsive breakpoint props
- that repeated blocks are snippets, not copied markup
- that the MDC validates and previews cleanly on desktop and mobile

## Handoffs

- Use `konnect-portal-branding` for the page's colors, fonts, and styling.
- Use `technical-writing` for the wording that fills these components.
- Use `terraform-konnect` or `kongctl-declarative` to encode pages as code.
- Use `konnect-api-publish` when the goal is getting an API to appear in the
  portal rather than laying out a page.
