---
name: portal-branding
description: Replicate a brand or existing website's design on Kong Konnect Dev Portal pages. Use to match colors, fonts, imagery, and spacing through MDC components and page-level styling for visual parity.
license: MIT
metadata:
  product: konnect
  category: dev-portal-branding
  tags: kong,konnect,dev-portal,branding,styling
---

# Konnect Dev Portal page branding

## Goal

Reproduce a brand or an existing website's look on Dev Portal MDC pages: colors,
fonts, imagery, and spacing, through MDC components and page-level styling. Work
in MDC page files, locally or in a repo. Do not push destructive changes to a
live portal through the Konnect API unless the user explicitly asks.

## Clarify First

Ask two or three high-impact questions, each with a default to confirm; do not
interrogate:

- source to match: a URL or short brand description
- target page or pages
- which details must be exact, which can be approximate
- light or dark base

## Tool Selection

- Author, format, validate, and preview MDC with the `portal-page-design`
  toolchain, which uses the Konnect MCP server for verified components, design
  tokens, validation, and preview. This skill adds the brand-specific steps below.
- If the MCP server is not connected, recommend connecting it. Without it there
  is no preview or parity loop: work from general MDC knowledge and the user's
  files, ask them to preview in the Portal Editor, and say plainly the result is
  less reliable.
- Capturing the source and comparing results need a browser. If no browser
  automation (Playwright or an agent browser) is available, have the user install
  one first.
- If a local preview extension is available, use it for live preview while
  editing.

## Workflow

1. Confirm the source (URL or brand cues) and target MDC page.
2. Capture the brand cues (see Capture the brand).
3. Build the look with components and page-level styling (see Apply the brand).
4. Preview and compare to the source across widths, then iterate (see Parity
   loop).
5. Check contrast against every background.
6. Report what matched; for anything the page cannot express, offer a concrete
   alternative, not a silent miss.

## Capture the brand

Aim for a small set of concrete cues, not a pile of screenshots:

1. Brand and accent colors: dominant non-neutral colors on primary buttons,
   links, and highlights. Record hex.
2. Base tone: light or dark.
3. Typography: heading, body, and monospace fonts, plus the weights used.
4. Imagery: logos, icons, and hero images with source URLs. Prefer SVG.
5. Spacing and shape: dense or airy, plus corner-radius and border feel.

Screenshot the source with Playwright at desktop and mobile widths and keep it
open beside your work. Match the given source; do not substitute a default brand.

## Apply the brand

Two levers:

- Portal theme: anything portal-wide (brand color, fonts, layout, logo, favicon),
  set through the MCP server's customization operations. The `primary` token
  family derives from the theme's primary color, so setting it once applies the
  brand consistently. Change the theme only when the user asks.
- Page-level styling: one-page shades and effects beyond the primary palette,
  such as a `full-width` hero background.

For one page, use a component's dedicated appearance props (`background-color`,
`padding`, `border`, `border-radius`) and inline span styles, for example
`[text]{ style="color:#6f28ff;" }`. Prefer dedicated props over the catch-all
styles prop, which is only for what props cannot express (a gradient background).

Set fonts portal-wide through the theme so every page matches; for a one-page
exception, set `font-family` on component style props with a fallback stack.

## Parity loop

Run this only with a real portal and a configured token; without them there is no
rendered preview and no parity loop, so say so and stop.

1. Format and validate the MDC, look up the target portal's origin (its canonical
   or default domain), and generate a preview through the MCP server.
2. Set the viewport before opening the URL, wait for full hydration (network idle,
   no pending animations), then screenshot the preview and source at the same
   widths (mobile, tablet, desktop).
3. Compare in order: base tone, brand colors, fonts, spacing and shape, then fine
   detail.
4. Fix the largest visible gap first, then repeat. Drive changes from the
   screenshots, not assumptions.

Editing an existing page: first screenshot the live page as a "before" at each
width, then compare against the "after."

Preview URLs are single-use and time-limited: regenerate only when the MDC
changes; once loaded, resize the browser in place to test widths.

The preview uses the target portal's theme, so `--kui-*-primary` surfaces show
that portal's brand color, not the source's. To judge brand parity, either set
the portal's primary color in the theme first, or use explicit hex on
brand-critical surfaces so the preview is theme-independent.

Contrast: check brand color against its background on buttons and links, and body
text against its background. Meet WCAG AA: 4.5:1 for normal text, 3:1 for large
text. If the true brand color fails, use it for large surfaces and pick a
contrast-safe variant for text.

When an element has no page equivalent, do not drop it silently: offer the
closest approximation, or state plainly that the page cannot express the effect.

Stop when tone, colors, fonts, and imagery match and the remaining differences
are cosmetic and below the user's fidelity bar. Report residual differences
rather than chasing pixels.

## Dev Portal Gotchas

- Pull `--kui-*` values from the server's design tokens, not memory; use explicit
  hex only for shades beyond the primary palette.
- Logo, favicon, and API images have dedicated MCP upload operations. There is no
  uploader for arbitrary inline content images; hotlink those over HTTPS with an
  image component, or embed SVG inline.
- The portal's internal class names are not a stable contract; use component props
  and inline styles.
- Style only what the brand needs, with the smallest set of theme settings and
  styles.

## Validation Checklist

- source and target pages named
- colors, fonts, imagery, and spacing applied
- images use the right upload path or hotlink/SVG
- WCAG AA contrast on every background
- parity confirmed via screenshot comparison
- work stayed in MDC page files
- unmatched elements and their alternatives noted

## Handoffs

- `portal-page-design` for page structure and component choice.
- `technical-writing` for page wording.
- `terraform-konnect` or `kongctl-declarative` to encode pages as code.
- Portal-wide customization (theme, navigation menus, custom domain, page
  visibility): use the MCP server's portal customization operations directly; no
  page-scoped skill here owns it.
- `konnect-api-publish` or `konnect-app-auth` when the real issue is API
  visibility, publication, or developer application auth.
