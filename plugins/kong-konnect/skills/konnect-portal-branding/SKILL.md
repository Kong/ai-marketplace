---
name: konnect-portal-branding
description: Replicate a brand or existing website design in a Kong Konnect Dev Portal. Use to extract colors, fonts, logo, and spacing and map them to portal theme, brand color, custom CSS, and assets for visual parity. Not for page layout or documentation copy.
license: MIT
metadata:
  product: konnect
  category: dev-portal-branding
  tags:
    - kong
    - konnect
    - dev-portal
    - branding
    - theming
---

# Konnect Dev Portal branding

## Goal

Turn a brand reference, usually an existing website, into a Konnect Dev Portal
that matches it. Own the portal's visual identity: theme mode, brand color,
global custom CSS, logo, and favicon, and the iterate-to-parity loop that proves
the result matches the source.

This skill owns look and feel, not the page structure, the words, or
publication. Hand off component layout to `konnect-portal-page-design`, page
copy to `technical-writing`, and API publication or app auth to their owners.

## Tool Selection

- Use the shared `kong-konnect` MCP server first to inspect the portal's current
  customization, apply changes, and generate a preview URL. If it is not
  connected, say so early and continue with the Portal Management v3 API or the
  repo's declarative artifacts.
- Use Playwright (or the user's browser automation) to capture the source site's
  computed styles and to screenshot the portal preview for comparison. Say so
  when neither is available and fall back to a manual visual comparison.
- Preserve the repository's existing toolchain when branding must be encoded as
  code. Stay in Terraform (`konnect_portal_customization`, `konnect_portal_logo`,
  `konnect_portal_favicon`) or `kongctl` (`portals[].customization` and
  `portals[].assets`) if the repo already uses one. Otherwise apply through the
  v3 API via MCP.
- The VS Code Konnect Dev Portal Toolkit gives live local preview while editing.
  Recommend it when the user is iterating on files, but do not require it.

## References To Load

Load only the file that matches the active step:

- `references/brand-extraction.md`
  - Load when capturing colors, typography, logo, and spacing from a source
    site or brand kit, including how to pick the single brand color.
- `references/customization-and-css.md`
  - Load when mapping the extracted brand onto the portal's real knobs: the
    `theme`, `css`, and asset fields, plus CSS recipes and the Kong design-token
    palette to use as a default.
- `references/parity-loop.md`
  - Load when previewing, comparing against the source, checking contrast, and
    deciding when to offer alternatives for elements that cannot be matched.

## Workflow

### 1. Establish the brand source and the target portal

Confirm what you are matching and where it goes:

- the source: a live URL, a brand kit, or an explicit color and font list
- the target portal, and whether other pages already exist to stay consistent
  with
- the fidelity bar: pixel parity with one page, or a general brand feel

If the request is "make it look like Kong" or gives no source, use the Kong
design-token palette in `references/customization-and-css.md` as the default.

### 2. Extract the brand

Capture the values that drive appearance, not a screenshot alone:

- brand or accent color, and whether the base is light or dark
- heading and body font families, and the monospace font for code
- logo and favicon assets
- spacing, corner radius, and border character

Load `references/brand-extraction.md` for how to pull computed styles with
Playwright and how to resolve the one brand color the portal accepts.

### 3. Map the brand to the portal's real knobs

The portal exposes a small structured surface and one large free-form lever.
Do not expect a full token system:

- structured: `theme.mode` (`light`, `dark`, or `system`), `theme.colors.primary`
  (a single hex), plus `logo` and `favicon` as separate base64 data-URL assets
- everything else, including fonts, secondary and accent colors, backgrounds,
  spacing, and component overrides, goes in the global `css` string

Load `references/customization-and-css.md` for exact field names, CSS recipes,
and the asset format.

### 4. Encode the CSS

- Load fonts with `@font-face` or a hosted stylesheet, then set `font-family`.
  There is no font field.
- Prefer Kong `--kui-*` design tokens when the brand is Kong or unspecified, and
  explicit values when matching a specific external brand.
- Keep CSS scoped and minimal. Do not hardcode the portal's internal class or
  variable names from memory. Inspect the live rendered DOM when you need a
  selector.

### 5. Preview, compare, and iterate

- Apply the change and generate a preview URL through MCP.
- Screenshot the preview at desktop and mobile widths and compare against the
  source. Iterate on color, type, and spacing until the gap is closed.
- Load `references/parity-loop.md` for the comparison loop and stopping rules.

### 6. Verify contrast and accessibility

The platform does not enforce contrast. This skill owns it. Confirm the brand
color and text meet a readable contrast ratio against both the chosen mode's
background and any custom backgrounds you set.

### 7. Report what matched and what could not

State the applied theme mode, brand color, fonts, and assets. For anything that
could not be matched exactly, such as reserved page regions or effects the
portal cannot express, offer concrete alternatives rather than a silent miss.

## Dev Portal Gotchas

- Only `theme.colors.primary` is a structured color. Secondary and accent colors
  live in `css`. Do not invent extra structured color roles.
- Logo and favicon are separate assets, not customization fields, and must be
  base64 data URLs (png, jpeg, gif, ico, or svg).
- `theme.mode` sets both background and text. Recheck contrast whenever you
  change it.
- Reserved paths and regions such as auth pages and account areas cannot be
  freely restyled. Confirm the target area is customizable before promising
  parity.
- The portal's internal CSS class and variable names are not a published,
  stable contract. Inspect the live DOM instead of guessing selectors.
- Open Graph images are generated from the brand color, mode, and page metadata,
  so setting the brand color also changes link previews.
- Custom domain SSL provisioning can take hours, and preview content can look
  stale from browser cache. A refresh usually resolves stale preview.

## Validation Checklist

Before answering, verify that you can state:

- the source brand and the target portal
- the resolved `theme.mode` and single `theme.colors.primary` value
- which brand details were pushed into `css` and why
- that logo and favicon are correctly formatted data URLs
- that brand color and text contrast are acceptable in the chosen mode
- how parity was confirmed, including a preview screenshot comparison
- which toolchain owns the change if it must be encoded as code
- which elements could not be matched, and the alternatives offered

## Handoffs

- Use `konnect-portal-page-design` when the request is really about page
  structure, sections, or component choice rather than theme and CSS.
- Use `technical-writing` when the request is about the wording of pages rather
  than their appearance.
- Use `terraform-konnect` or `kongctl-declarative` to encode customization,
  logo, and favicon changes in an existing declarative repo.
- Use `konnect-api-publish` or `konnect-app-auth` when the real issue is API
  visibility, publication, or developer application auth, not branding.
