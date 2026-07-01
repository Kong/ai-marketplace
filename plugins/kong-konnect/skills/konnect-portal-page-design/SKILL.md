---
name: konnect-portal-page-design
description: Structure and compose Kong Konnect Dev Portal pages with MDC components like heroes, cards, grids, callouts, tabs, and code blocks. Use for page layout, section design, and component choice. Not for theme, branding, or documentation wording.
license: MIT
metadata:
  product: konnect
  category: dev-portal-design
  tags:
    - kong
    - konnect
    - dev-portal
    - mdc
    - page-design
---

# Konnect Dev Portal page design

## Goal

Turn a page intent into a well-structured Konnect Dev Portal page built from MDC
(Markdown Components). Own the layout: which sections a page needs, which
components express them, and how they compose into a visually consistent,
responsive result.

This skill owns structure and component choice. It does not own the portal's
theme and colors, the wording of the content, or publication. Hand those to
`konnect-portal-branding`, `technical-writing`, and the publication owners.

## Tool Selection

- Use the shared `kong-konnect` MCP server first to read MDC component metadata,
  generate or edit pages, validate and format MDC, and produce a preview URL.
  Verify each component's real props and slots against that metadata before
  relying on them. If MCP is not connected, say so and treat the component
  details in the references as a starting scaffold to confirm against
  `portaldocs.konghq.com`.
- Use the VS Code Konnect Dev Portal Toolkit for live side-by-side preview of
  `.md` and `.mdc` files while editing.
- Use Playwright to screenshot the preview at desktop and mobile widths when
  visual confirmation matters.
- Preserve the repo's toolchain when pages are managed as code. Stay in
  `kongctl` (`portals[].pages`, `portals[].snippets`) or Terraform
  (`konnect_portal_page`, `konnect_portal_snippet`) if one is already in use.

## References To Load

Load only the file that matches the active step:

- `references/mdc-syntax.md`
  - Load when writing MDC: block and inline components, props, slots, binding,
    nesting, span attributes, frontmatter, and snippet reuse.
- `references/component-catalog.md`
  - Load when choosing components. Lists the common palette with purpose and
    typical props and slots, and the rule to verify against live metadata.
- `references/layout-patterns.md`
  - Load when composing full sections and pages: masthead or hero, card grids,
    feature rows, responsive grids, and a documentation page skeleton.

## Workflow

### 1. Decide the page's job and sections

Name the page type and its sections before writing any MDC:

- landing or product page: hero, value or feature grid, calls to action
- documentation page: hero or title block, getting started, reference, samples,
  troubleshooting
- API listing or catalog page: hero plus an APIs list

Keep the section list short and purposeful. A page that tries to do everything
reads as noise.

### 2. Map sections to components

Choose components by the job of each section, not by copying an example:

- masthead or top of page: `::page-hero`
- grouped choices or features: `::grid` with `::grid-item`, or `::card` groups
- a single emphasized message: `::alert`
- actions: `::button`, links with `::a`
- media: `::image`, `::iframe`
- published APIs: `::apis-list`
- collapsible detail: `::accordion`

Load `references/component-catalog.md` to confirm the component and its props.

### 3. Compose with layout primitives, not one giant component

Build sections by nesting `::container` and `::grid` around content components.
Prefer several small, composable blocks over one monolithic component. Load
`references/layout-patterns.md` for reusable section shapes.

### 4. Write valid MDC

- Use block syntax (`::name` ... `::`) with props as inline braces or a YAML
  block, and named slots with `#slot`.
- Bind non-string props (booleans, numbers, arrays, objects) with the `:`
  prefix.
- Reuse repeated blocks as snippets rather than copying markup.

Load `references/mdc-syntax.md` for the exact rules.

### 5. Keep it consistent and responsive

- Prefer Kong `--kui-*` design tokens for spacing, color, and radius over
  hardcoded values, so pages match the portal theme and each other.
- Set responsive columns through the breakpoint props. The ladder is mobile
  640, phablet 768, tablet 1024, laptop 1280, desktop 1536; larger breakpoints
  inherit smaller values when unset.
- Reuse the same hero and card patterns across pages so the portal feels like
  one product.

### 6. Validate and preview

Validate and format the MDC through MCP, generate a preview URL, then screenshot
it at desktop and mobile to confirm it renders cleanly before calling it done.

## MDC Gotchas

- This is the v3 Konnect portal MDC system (Vue and Nuxt based). Do not use the
  legacy Kong Gateway Enterprise portal templates or `kong-portal-templates`;
  they are a different, incompatible model.
- Component props and slots can change and some are not fully documented. Verify
  against live MCP metadata or `portaldocs.konghq.com` instead of trusting
  remembered prop names.
- Snippets are a flat namespace and only render when a page references them.
  Pages support nested slugs; snippets do not.
- Frontmatter inside page content wins over separately supplied title and
  description fields.
- Reserved root paths such as `/login`, `/register`, `/account`, and
  `/_preview-mode` cannot be used as custom page slugs.
- Match prop name casing between the prop and any bound reference (kebab-case or
  camelCase), and add extra colons on outer components when nesting so depth
  stays readable.

## Validation Checklist

Before answering, verify that you can state:

- the page type and its ordered sections
- which component expresses each section and why
- that component props and slots were confirmed against live metadata
- that layout uses `--kui-*` tokens and responsive breakpoint props
- that repeated blocks are snippets, not copied markup
- that the MDC validates and the preview renders cleanly on desktop and mobile
- which toolchain owns the page if it is managed as code

## Handoffs

- Use `konnect-portal-branding` when the request is about theme, brand color,
  fonts, or CSS rather than page structure.
- Use `technical-writing` for the wording, tone, and structure of the prose that
  fills these components.
- Use `terraform-konnect` or `kongctl-declarative` to encode pages and snippets
  in an existing declarative repo.
- Use `konnect-api-publish` when the goal is getting an API to appear in the
  portal rather than laying out a page.
