---
name: konnect-portal-branding
description: Replicate a brand or existing website's design on a Kong Konnect Dev Portal page. Use to match colors, fonts, imagery, and spacing within an individual MDC page through components and page-level styling for visual parity.
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

Reproduce a brand or an existing website's look on a single Dev Portal MDC page.
Own the page's visual identity: colors, fonts, imagery, and spacing, expressed
through MDC components and page-level styling.

Keep every task inside one MDC page. Author and edit pages locally or in a
dedicated repository. Do not push destructive changes to a live portal through
the Konnect API unless the user explicitly asks.

## Tool Selection

- Use the shared `kong-konnect` MCP server for MDC component metadata and to
  generate a page preview URL. If it is not connected, say so and continue from
  local files.
- Use Playwright to screenshot the source site and the page preview for
  comparison. Fall back to manual visual comparison when it is unavailable.
- Use the VS Code Konnect Dev Portal Toolkit for live local preview while
  editing.
- Preserve the repo's toolchain when pages are managed as code: `kongctl`
  (`portals[].pages`) or Terraform (`konnect_portal_page`).

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

- Keep styling within the page. Global portal styling is discouraged.
- Dev Portal does not offer asset management. Hotlink image URLs where possible,
  and embed SVGs inline.
- Prefer `--kui-*` design tokens so the page stays consistent with the portal it
  lives in.
- The portal's internal class names are not a stable contract. Do not depend on
  them; use component props and inline styles.
- Preview can show stale content from browser cache. A refresh usually clears
  it.

## Validation Checklist

Before answering, verify that you can state:

- the source and the target page
- which colors, fonts, imagery, and spacing you applied, and how
- that images are hotlinked or embedded SVGs, not uploaded assets
- that text contrast is acceptable against every background
- how parity was confirmed, including a preview screenshot comparison
- that the work stayed inside the MDC page
- which elements could not be matched, and the alternatives offered

## Handoffs

- Use `konnect-portal-page-design` for page structure and component choice.
- Use `technical-writing` for the wording of the page.
- Use `terraform-konnect` or `kongctl-declarative` to encode pages as code.
- Use `konnect-api-publish` or `konnect-app-auth` when the real issue is API
  visibility, publication, or developer application auth.
