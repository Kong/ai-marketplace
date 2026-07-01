# Customization Schema, CSS, and Kong Tokens

Load this when mapping an extracted brand onto the portal's real configuration.
The structured surface is intentionally small. Custom CSS carries the rest.

## The customization object

Branding is written through the Portal Management v3 customization object
(`update-portal-customization` or `replace-portal-customization`). The
branding-relevant fields:

```jsonc
{
  "theme": {
    "name": "string",                 // theme identifier
    "mode": "light",                  // "light" | "dark" | "system"
    "colors": { "primary": "#0044F4" } // the ONLY structured color
  },
  "layout": "string",                 // template selector, rarely changed
  "css": "…global custom CSS…",       // the main branding lever, nullable
  "menu": { "main": [], "footer_sections": [], "footer_bottom": [] }
}
```

Logo and favicon are separate resources, not fields on this object.

Declarative equivalents use the same shape. Preserve whichever the repo uses:

- `kongctl` YAML: `portals[].customization.theme|css|menu` and
  `portals[].assets.logo|favicon`.
- Terraform (`Kong/konnect`): `konnect_portal_customization`,
  `konnect_portal_logo`, `konnect_portal_favicon`.

Verify field and enum names against live MCP schema (`get_schema`) or the
current provider docs before writing. Do not trust remembered field names for a
resource you have not inspected this session.

## Logo and favicon assets

Both must be base64 data URLs. Supported types: png, jpeg, gif, ico, svg.

```
data:image/svg+xml;base64,<BASE64_DATA>
data:image/png;base64,<BASE64_DATA>
```

The logo is placed automatically in the header and footer. Provide a variant
that reads well against the chosen `theme.mode` background.

## CSS recipes

Everything the structured fields cannot express goes in `css`. Keep it scoped
and minimal.

Fonts (there is no font field):

```css
@font-face {
  font-family: "BrandSans";
  src: url("https://cdn.example.com/brandsans.woff2") format("woff2");
  font-weight: 400 700;
  font-display: swap;
}
:root {
  --brand-font: "BrandSans", Inter, Roboto, Helvetica, sans-serif;
  --brand-accent: #6f28ff; /* secondary/accent the structured theme cannot hold */
}
body { font-family: var(--brand-font); }
```

Secondary and accent colors, backgrounds, and radius:

```css
:root { --brand-surface: #f7f8fa; --brand-radius: 8px; }
```

Selector-level overrides: the portal's internal class names are not a stable
published contract. Inspect the live rendered DOM to find the real selector
before overriding a specific component, and keep such overrides few.

## Kong design-token palette (default brand)

Use these when the brand is Kong or unspecified. Konnect's system is blue-led,
not green. Reference `--kui-*` tokens in CSS when available rather than
hardcoding, so the portal stays aligned if Kong updates values.

Core semantic mapping:

- brand / primary action: `#0044F4` (blue 60)
- body text: `#000933` (blue 100, dark navy)
- default background: `#FFFFFF`; inverse background: `#000933`
- default border: `#E0E4EA` (gray 20)

Blue scale (10 lightest to 100 darkest): `#EEFAFF`, `#BEE2FF`, `#8FC1FF`,
`#5F9AFF`, `#306FFF`, `#0044F4`, `#0030CC`, `#002099`, `#001466`, `#000933`.

Gray scale: `#F9FAFB`, `#E0E4EA`, `#C7CED8`, `#AFB7C5`, `#828A9E`, `#6C7489`,
`#52596E`, `#3A3F51`, `#232633`, `#0D0E14`.

Semantic accents: info uses blue, success uses green (`#00A17B` at 50),
warning uses yellow (`#FFC400` at 40), danger uses red (`#F50045` at 50).
Decorative accents: purple (`#6F28FF`), aqua (`#00C8F4`), pink (`#F4007A`).

Typography:

- UI and prose, headings included: `Inter, Roboto, Helvetica, sans-serif`
- code and inline code: `JetBrains Mono, Consolas, monospace`
- weights: regular 400, medium 500, semibold 600, bold 700

## Do not

- Do not add structured color roles beyond `primary`. They do not exist.
- Do not embed real secrets in CSS or config.
- Do not restyle reserved auth or account pages beyond what the portal exposes.
