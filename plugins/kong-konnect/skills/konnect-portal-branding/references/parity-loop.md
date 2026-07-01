# Parity Loop

Load this when closing the gap between the page and the source.

## The loop

1. Apply your page edits and generate a page preview URL through the
   `kong-konnect` MCP server.
2. Screenshot the preview and the source at the same widths, at least one
   desktop and one mobile.
3. Compare in order: base tone, brand colors, fonts, spacing and shape, then
   fine detail.
4. Fix the largest visible gap first, then repeat. Drive changes from the
   screenshots, not from assumptions about the styles.

```js
for (const width of [1440, 390]) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto(SOURCE_URL);
  await page.screenshot({ path: `source-${width}.png`, fullPage: true });
  await page.goto(PREVIEW_URL);
  await page.screenshot({ path: `page-${width}.png`, fullPage: true });
}
```

## Contrast

Confirm brand color against its background on buttons and links, and body text
against its background. Aim for at least 4.5:1 for normal text and 3:1 for large
text. If the true brand color fails, use it for large surfaces and pick a
contrast-safe variant for text.

## When an element cannot be matched

Some source elements have no page equivalent. Do not drop them silently. Offer
the closest achievable approximation, or state plainly that the page cannot
express the effect.

## Stopping rule

Stop when tone, colors, fonts, and imagery match and the remaining differences
are cosmetic and below the user's fidelity bar. Report the residual differences
rather than chasing pixels that do not change the impression.
