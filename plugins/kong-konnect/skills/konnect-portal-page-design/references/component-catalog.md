# Component Catalog

Load this when choosing components. These are the built-in MDC components. Their
exact props can change, so confirm props and slots against live MDC metadata
(`kong-konnect` MCP) before relying on them.

Many components share styling props (`display`, `margin`, `padding`, `border`,
`border-radius`, `background-color`, `gap`) that default to `--kui-*` tokens.

## Layout and sections

- `::page-hero`: the masthead. A title, a description, and an actions area of
  `::button`s. Props: `full-width`, `background` / `background-image`,
  `padding`, alignment.
- `::page-section`: a full content section, with an optional background, holding
  nested containers and components.
- `::container`: a flex wrapper. Props: `display`, `flex-direction`, `gap`, and
  the shared styling props. Slot: `#default`.
- `::grid` and `::grid-item`: a grid container and its children. `::grid` takes
  `grid-columns-breakpoints` and `gap`; `::grid-item` takes `grid-column` (for
  example `"1/4"`) and responsive `*-breakpoints` variants.

## Content

- `::card`: a content or link card. Slots: `#title` (often an `::a`) and
  `#default`. Can surface an API's attributes through `card-attribute-keys`.
- `::tabs`: tabbed content panels for grouping alternatives such as per-language
  samples.
- `::accordion`: collapsible sections for optional or secondary detail.
- `::alert`: a callout. Props: `appearance` (`success`, `info`, `warning`),
  `title`, `message`, `show-icon`. Use `#default` for rich content.
- `::button`: an action. Props: `appearance`, `size`, `to`, `display`.
- `::a`: an anchor wrapper. Props: `href`, `target`, `rel`.
- `::image`: an image. Props: `src`, `alt`, `width`, `height`, plus styling.
- `::iframe`: embeds an external page. Takes native `<iframe>` attributes except
  `srcdoc`.

## API-aware

- `::apis-list`: a paginated list of published APIs. Props: `attributes`
  (pre-filter), `card-attribute-keys`, `show-filter` / `enable-search`,
  `grid-columns-breakpoints`, `card-snippet-name`.

## Code

Use standard fenced code blocks with a language tag for code samples. Keep one
command per block and put output in a separate block.

## Choosing well

Pick the component that names the section's job. Keep the set small per page;
repetition of a few components reads as consistency, many one-off components as
clutter. Put actions in `::button`s, not scattered inline.
