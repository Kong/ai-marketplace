# Parity Loop

Close the gap between the page and the source, then decide when to stop.

## The loop

1. Format and validate the MDC, then look up the target portal's origin (its
   canonical or default domain) and generate a preview through the MCP server.
   This needs a real portal and a configured token. Without them there is no
   rendered preview and no parity loop, so say so and stop rather than pretending
   the loop runs.
2. Set the viewport before opening the URL, wait for full hydration (network
   idle, no pending animations), then screenshot the preview and the source at
   the same widths (mobile, tablet, and desktop).
3. Compare in order: base tone, brand colors, fonts, spacing and shape, then
   fine detail.
4. Fix the largest visible gap first, then repeat. Drive changes from the
   screenshots, not from assumptions about the styles.

When editing an existing page rather than building fresh, first screenshot the
live page as a "before" at each width, then compare it against the preview
"after."

Preview URLs are single-use and time-limited. Regenerate one per view only when
the MDC changes; once a page is loaded, resize the browser in place to test
widths rather than regenerating per width.

The preview uses the target portal's theme, so `--kui-*-primary` surfaces show
that portal's brand color, not the source's. To judge brand parity, either set
the portal's primary brand color in the theme first, or use explicit hex on
brand-critical surfaces so the preview is theme-independent.

## Contrast

Confirm brand color against its background on buttons and links, and body text
against its background. Meet WCAG AA: at least 4.5:1 for normal text and 3:1 for
large text. If the true brand color fails, use it for large surfaces and pick a
contrast-safe variant for text.

## When an element cannot be matched

Some source elements have no page equivalent. Do not drop them silently. Offer
the closest achievable approximation, or state plainly that the page cannot
express the effect.

## Stopping rule

Stop when tone, colors, fonts, and imagery match and the remaining differences
are cosmetic and below the user's fidelity bar. Report the residual differences
rather than chasing pixels that do not change the impression.
