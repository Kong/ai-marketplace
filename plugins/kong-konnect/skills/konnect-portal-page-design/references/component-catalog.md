# Component Catalog

Load this when choosing components. Treat prop and slot lists as a scaffold that
may be partial. Confirm the exact props against live MDC metadata
(`kong-konnect` MCP) or `portaldocs.konghq.com` before relying on them.

Many components share styling props (`display`, `margin`, `padding`, `border`,
`border-radius`, `background-color`, `gap`) that default to `--kui-*` tokens.

## Layout and structure

- `::page-hero`: the masthead. Composed from a title, a description, and an
  actions area of `::button`s. Props: `full-width`, `background` /
  `background-image`, `padding`, alignment.
- `::container`: a flexbox wrapper. Props: `display`, `flex-direction`, `gap`,
  and the shared styling props. Slot: `#default`.
- `::grid` and `::grid-item`: a CSS-grid container and its children. `::grid`
  takes `grid-columns-breakpoints` and `gap`; `::grid-item` takes `grid-column`
  (for example `"1/4"`) and responsive `*-breakpoints` variants.

## Content blocks

- `::card`: a content or link card. Props include the shared styling props and
  `card-attribute-keys`. Slots: `#title` (often an `::a`) and `#default`.
- `::alert`: a callout. Props: `appearance` (`success`, `info`, `warning`),
  `title`, `message`, `show-icon`. Use `#default` for rich content.
- `::button`: an action. Props: `appearance`, `size`, `to`, `display`.
- `::a`: an anchor wrapper. Props: `href`, `target`, `rel`.
- `::image`: an image. Props: `src`, `alt`, `width`, `height`, plus styling.
- `::iframe`: embeds an external page. Takes native `<iframe>` attributes except
  `srcdoc`.
- `::accordion`: collapsible sections. Confirm props against live metadata.

## API-aware

- `::apis-list`: a paginated list of published APIs. Props: `attributes`
  (pre-filter), `card-attribute-keys`, `show-filter` / `enable-search`,
  `grid-columns-breakpoints`, `card-snippet-name`.

## Unconfirmed

`tabs`, `badge`, and a dedicated code-block component appear in prose but were
not confirmed as tags. Standard fenced code blocks work. Verify before using
`::tabs`, `::badge`, or `::code-block`.

## Choosing well

Pick the component that names the section's job. Keep the set small per page;
repetition of a few components reads as consistency, many one-off components as
clutter. Put actions in `::button`s, not scattered inline.
