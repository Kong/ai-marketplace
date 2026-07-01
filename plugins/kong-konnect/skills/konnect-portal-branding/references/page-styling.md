# Page Styling

Load this when applying brand cues on the page. Everything here stays inside the
MDC page. Keep styling scoped to components and inline text.

## Colors, spacing, and shape

Set these through component style and appearance props and through inline span
styles, not through global configuration.

- Use component props such as `background-color`, `padding`, `border`, and
  `border-radius` to place brand colors and spacing.
- Use span attributes for inline accents: `[text]{ style="color:#6f28ff;" }`.
- Prefer `--kui-*` design tokens (for example `var(--kui-space-80)`) so the page
  stays consistent with the portal it lives in, and use explicit hex only where
  the source brand requires it.

## Fonts

Set fonts at the page level with `font-family` on component style props. Provide
a sensible fallback stack so text stays readable before any web font loads. Do
not rely on global font configuration.

## Images

Dev Portal does not offer asset management.

- Hotlink image URLs where possible with `::image{ src="https://..." }`.
- Embed SVGs inline when you need the markup on the page.
- Do not base64-encode or upload logo and favicon assets from this skill.

## Keep it minimal

Style only what the brand needs. Do not depend on the portal's internal class
names, which are not a stable contract. Reproduce the source's look with the
smallest set of component and inline styles that gets there.
