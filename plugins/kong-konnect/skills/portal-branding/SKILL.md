---
name: portal-branding
description: Replicate a brand or existing website's design on Kong Konnect Dev Portal pages. Use to match colors, fonts, imagery, and spacing through MDC components and page-level styling for visual parity.
license: MIT
metadata:
  product: konnect
  category: dev-portal-branding
  tags:
    - kong
    - konnect
    - dev-portal
    - branding
    - styling
---

# Konnect Dev Portal page branding

## Goal

Reproduce a brand or an existing website's look on Dev Portal MDC pages. Own
each page's visual identity: colors, fonts, imagery, and spacing, expressed
through MDC components and page-level styling.

Work in MDC page files, one or more as the task needs. Author and edit them
locally or in a dedicated repository, and do not push destructive changes to a
live portal through the Konnect API unless the user explicitly asks.

## Clarify First

Ask a few high-impact questions before you build, and offer a sensible default
so the user can simply confirm. Do not interrogate; batch two or three
questions. For this skill, clarify:

- the source to match, as a URL or a short brand description
- which page or pages are the target
- which details must be exact and which can be approximate
- whether the base should read light or dark

## Tool Selection

- Author, format, validate, and preview MDC with the toolchain in
  `portal-page-design`; this skill adds the brand-specific steps below.
- Capturing the source and comparing the result depend on a browser. If no
  browser automation such as Playwright or an agent browser is available,
  recommend the user install one before proceeding.
- If a local preview extension is available, use it for live local preview while
  editing.

## Two brand levers

- **Portal theme.** Anything that should be consistent portal-wide: brand
  color, fonts, layout, logo, and favicon. Change it only when the user asks.
- **Page-level styling.** One-page shades and effects beyond the primary
  palette, for example a `full-width` hero background.

See `references/page-styling.md` for which tools each lever uses.

## References To Load

Load only the file that matches the active step:

- `references/brand-extraction.md`
  - Load when capturing colors, fonts, imagery, and spacing from a source.
- `references/page-styling.md`
  - Load when applying them on the page with component props, inline styles,
    `--kui-*` tokens, and images.
- `references/parity-loop.md`
  - Load when previewing the page and comparing it to the source.

## Workflow

1. Fix the source and the target page. Confirm the source (a URL or brand cues)
   and which MDC page you are styling.
2. Capture the brand cues: brand and accent colors, heading and body fonts,
   imagery, and spacing feel. Load `references/brand-extraction.md`.
3. Build the page's look with components and page-level styling. Set colors,
   spacing, and fonts through component style props and inline styles, and place
   imagery. Load `references/page-styling.md`.
4. Preview the page and compare to the source at desktop and mobile widths.
   Iterate on color, type, and spacing. Load `references/parity-loop.md`.
5. Check contrast so text stays readable against every background you set.
6. Report what matched. For anything the page cannot express, offer a concrete
   alternative instead of a silent miss.

## Dev Portal Gotchas

- Logo, favicon, and API images have dedicated upload operations in the MCP
  server. There is no general uploader for arbitrary inline content images;
  hotlink those over HTTPS with an image component, or inline SVG markup.
- Prefer `--kui-*` tokens (from the server's design tokens) so the page stays
  consistent with the portal. Use explicit hex only where the brand needs a
  shade beyond the primary palette.
- The portal's internal class names are not a stable contract; use component
  props and inline styles.

## Validation Checklist

Before finishing, confirm:

- the source and the target pages
- which colors, fonts, imagery, and spacing you applied, and how
- that logo, favicon, and API images use the server's upload operations, and
  inline content images are hotlinked or embedded SVGs
- that text contrast is acceptable against every background
- how parity was confirmed, including a preview screenshot comparison
- that the work stayed in MDC page files
- which elements could not be matched, and the alternatives offered

## Handoffs

- Use `portal-page-design` for page structure and component choice.
- Use `technical-writing` for the wording of the page.
- Use `terraform-konnect` or `kongctl-declarative` to encode pages as code.
- For portal-wide customization (theme, navigation menus, custom domain, page
  visibility), use the MCP server's portal customization operations directly. No
  page-scoped skill here owns that workflow.
- Use `konnect-api-publish` or `konnect-app-auth` when the real issue is API
  visibility, publication, or developer application auth.
