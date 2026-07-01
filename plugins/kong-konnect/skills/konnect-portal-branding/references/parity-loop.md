# Parity Loop

Load this when you have applied a first pass and need to close the gap with the
source, then decide when to stop.

## The loop

1. Apply the current theme, CSS, and assets to the portal.
2. Generate a preview URL through the `kong-konnect` MCP server.
3. Screenshot the preview and the source at the same viewport widths. Use at
   least one desktop width and one mobile width.
4. Compare deliberately, in this order: layout mode (light or dark), brand
   color on primary actions, heading and body fonts, spacing and radius, then
   fine detail.
5. Fix the largest visible gap, not the smallest. Reapply and repeat.

```js
// Screenshot both sides at matched widths
for (const width of [1440, 390]) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto(SOURCE_URL);
  await page.screenshot({ path: `source-${width}.png`, fullPage: true });
  await page.goto(PREVIEW_URL);
  await page.screenshot({ path: `portal-${width}.png`, fullPage: true });
}
```

Compare the pairs visually. Drive changes from what the screenshots show, not
from assumptions about what the CSS should do.

## Contrast check

The platform does not enforce contrast. Confirm it yourself:

- brand color against the mode background where it sits on buttons and links
- body text against background
- any custom background you introduce against text on it

Aim for a normal-text contrast ratio of at least 4.5:1 and large-text at least
3:1. If the true brand color fails, keep it for large brand surfaces and pick a
contrast-safe variant for interactive text or `primary`. Tell the user.

## Mobile

Check the mobile screenshot specifically. Confirm the logo scales, the hero and
nav do not overflow, and font sizes remain readable. Brand parity that only
holds on desktop is not done.

## When an element cannot be matched

Some source elements have no portal equivalent: reserved auth or account
regions, bespoke animations, or effects the portal layout cannot express. Do
not silently drop them. Offer a concrete alternative:

- the closest achievable CSS approximation
- moving the effect into a place the portal does allow, such as a page hero
- a plain statement that the region is reserved and why

## Stopping rule

Stop when the layout mode, brand color, fonts, and key assets match and the
remaining differences are cosmetic and below the user's fidelity bar. Report the
residual differences rather than iterating indefinitely on pixels that do not
change the brand impression.
