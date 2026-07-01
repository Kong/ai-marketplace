# Brand Extraction

Load this when capturing a brand from a source site or brand kit. The goal is a
small, concrete set of values you can map onto the portal, not a pile of
screenshots.

## What to capture

Pull these from the source, in priority order:

1. Brand or accent color. The dominant non-neutral color used for primary
   buttons, links, and active states.
2. Base mode. Whether the page reads as light (dark text on light background) or
   dark. This drives `theme.mode`.
3. Typography. The heading font family, the body font family, and the monospace
   font used for code. Capture weights actually used.
4. Logo and favicon. The header logo (and a dark-mode variant if one exists) and
   the browser favicon.
5. Shape and spacing feel. Corner radius, border presence, and whether the
   layout is dense or airy.

You do not need every value. Color, mode, fonts, and logo carry most of the
perceived brand.

## Pulling computed styles with Playwright

Read the rendered values rather than guessing from a screenshot. Navigate to the
source URL, then evaluate computed styles on representative elements.

```js
// Body typography and background
const base = await page.evaluate(() => {
  const s = getComputedStyle(document.body);
  return { font: s.fontFamily, color: s.color, background: s.backgroundColor };
});

// Primary color: sample the most prominent call-to-action or link
const accent = await page.evaluate(() => {
  const el = document.querySelector('a, button, [class*="btn"], [class*="primary"]');
  return el ? getComputedStyle(el).backgroundColor || getComputedStyle(el).color : null;
});

// Heading font
const heading = await page.evaluate(() => {
  const h = document.querySelector('h1, h2');
  return h ? getComputedStyle(h).fontFamily : null;
});
```

Convert sampled `rgb()` values to hex for the portal. When several candidates
compete, prefer the color used on the primary call to action.

## Resolving the single brand color

The portal accepts one structured color (`theme.colors.primary`). Choose the
color a visitor would name as "the brand color," usually the primary button or
link color. Keep secondary and accent colors for the `css` layer.

If the source uses a very light or very dark brand color that would fail
contrast as an accent, keep the true brand color for large brand surfaces in
CSS and pick a contrast-safe variant for `primary`. Note the tradeoff to the
user.

## Fonts

Record the exact family names and whether they are web fonts. You will load them
in CSS later:

- a hosted stylesheet link (for example a font CDN), or
- self-hosted files referenced with `@font-face`

Note the fallback stack so text stays sensible before the web font loads.

## Assets

- Download the logo at the highest available resolution. Prefer SVG when
  offered, then high-resolution PNG.
- Grab the favicon from the site's declared icon link or `/favicon.ico`.
- Both will be encoded as base64 data URLs when applied. See
  `customization-and-css.md`.

## When there is no source

If the user only says "match our brand" or "make it look like Kong" with no
URL, do not stall. Use the Kong design-token palette and fonts in
`customization-and-css.md` as the default, and confirm the choice with the user.
