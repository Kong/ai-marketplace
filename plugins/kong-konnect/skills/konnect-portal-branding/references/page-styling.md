# Page Styling

Load this when applying brand cues. Choose the right lever: set brand color,
fonts, and layout portal-wide in `theme`, and use page-level styling for shades
and effects beyond the primary palette on a single page.

## Colors, spacing, and shape

- Portal-wide brand color, fonts, and layout belong in `theme` via
  `update_portal_customization`. The `primary` token family is generated from
  `theme.colors.primary`, so setting it once applies the brand consistently.
- For one page, use component style and appearance props (`background-color`,
  `padding`, `border`, `border-radius`) and inline span styles, for example
  `[text]{ style="color:#6f28ff;" }`.
- Pull `--kui-*` values from `mdc_get_design_tokens` (filterable, with defaults
  and categories) rather than from memory, and use explicit hex only for shades
  beyond the primary palette.

## Fonts

Set fonts portal-wide through `theme` so every page matches. For a one-page
exception, set `font-family` on component style props with a sensible fallback
stack.

## Images

- Logo and favicon upload via `replace_portal_asset_logo` and
  `replace_portal_asset_favicon`; API and API-package images via
  `upsert_api_image` and `upsert_api_package_image`.
- There is no general uploader for arbitrary inline content images. Hotlink
  those over HTTPS with `::image{ src="https://..." }`, or embed SVG markup
  inline.

## Keep it minimal

Style only what the brand needs. Do not depend on the portal's internal class
names, which are not a stable contract. Reproduce the source's look with the
smallest set of theme settings and component or inline styles that gets there.
