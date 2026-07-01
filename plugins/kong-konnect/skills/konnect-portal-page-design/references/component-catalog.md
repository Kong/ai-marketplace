# Component Catalog

Load this when choosing components. Treat this as a starting palette. Prop and
slot lists here are a scaffold recovered from the docs and may be partial.
Confirm the exact props and slots against live MDC metadata (`kong-konnect` MCP)
or `portaldocs.konghq.com` before relying on them.

Components fall into building blocks (`/components/*`) and composed section
examples (`/sections/*`). Many share styling props such as `display`, `margin`,
`padding`, `border`, `border-radius`, `background-color`, and `gap`, which
default to Kong `--kui-*` design tokens.

## Layout and structure

- `::page-hero` (section): the masthead. Communicates product value and points
  developers to key actions. Composed from a title, a description, and an
  actions area holding `::button`s. Common props: `full-width`, `background` /
  `background-image` / `background-size`, `padding`, title and description font
  sizing, `color`, and vertical alignment. Variants: default, image-on-right,
  background-image.
- `::container`: a flexbox layout wrapper for grouping and spacing. Common
  props: `display` (for example `flex`), `flex-direction`, `gap`, `margin`,
  `padding`, `border-radius`, `background-color`, `background-image`. Slot:
  `#default`.
- `::grid`: a CSS-grid container. Props: `grid-columns-breakpoints` (columns per
  viewport) and `gap`. Pairs with `::grid-item`. Slot: `#default`.
- `::grid-item`: a grid child. Props: `grid-column` (for example `"1/4"` or
  `"4/ span 2"`), `grid-row`, and their responsive `*-breakpoints` variants.
  Slot: `#default`.

## Content blocks

- `::card`: a content or link card, also used for API cards. Props include
  `border-radius`, `background-color`, `border`, `padding`, and
  `card-attribute-keys`. Slots: `#title` (often an `::a`) and `#default`.
- `::alert`: a contextual callout for tips, info, or warnings. Props:
  `appearance` (for example `success`, `info`, `warning`), `title`, `message`
  (plain text), and `show-icon`. Use the `#default` slot for rich content.
- `::accordion`: collapsible sections. Confirm props against live metadata.
- `::button`: a call-to-action or navigation button. Props: `appearance` (for
  example `secondary`), `size` (for example `large`), `to` (route or URL),
  `display`, `border-radius`. Slot: the label.
- `::a`: an anchor link wrapper for consistent navigation, also used inside
  `#title` slots. Props: `href`, `target`, `rel` (defaults to
  `noopener noreferrer` for external links), `display`.
- `::image`: an image, standalone or nested. Props: `src`, `alt`, `width`,
  `height`, `border`, `border-radius`, `display`, `margin`, `padding`.
- `::iframe`: embeds an external page. Accepts native `<iframe>` attributes
  except `srcdoc`, plus sizing and border props.

## API-aware components

- `::apis-list`: a paginated list of published APIs, with optional pre-filter
  and end-user filtering. Props: `attributes` (pre-filter), `card-attribute-keys`
  (keys shown per card), `show-filter` or `enable-search`,
  `grid-columns-breakpoints`, and `card-snippet-name` to render cards via a
  custom snippet.

## Unconfirmed as discrete components

`tabs` and `badge` appear in prose but no standalone component page was
confirmed. Standard fenced code blocks (triple backticks with a language) work;
no special code-block component was confirmed. Verify these against live
metadata before using a `::tabs`, `::badge`, or `::code-block` tag.

## Choosing well

- Pick the component that names the section's job. A features section is a
  `::grid` of `::card`s, not one large custom block.
- Keep the component set small per page. Repetition of a few components reads as
  consistency; many one-off components read as clutter.
- Put actions in `::button`s inside the hero and section footers, not scattered
  inline.
