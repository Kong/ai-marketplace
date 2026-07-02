# Layout patterns

Composition judgment only. For the exact, current syntax, props, and slots of
any component named below, use the MCP server's component examples and metadata.
Treat the component names here as a starting point, not a fixed list.

## Shapes

- **Hero.** Open with a hero component: a title, a short value line, one or two
  actions. Confirm its slots against the server's metadata before writing it
  (a hero typically has named slots for tagline, title, description, actions,
  and image rather than a default slot).
- **Feature columns.** Use the responsive column container for parallel items
  (cards, entry points). Set per-breakpoint column counts.
- **Feature row.** Alternate text and media by pairing containers with a gap.
- **Doc page.** Sections in reading order on one page: hero, getting started,
  auth, request/response, troubleshooting. Prose comes from `technical-writing`.

## Consistency

Reuse the same hero and card patterns across pages, group related actions into
buttons, extract repeated blocks into snippets, prefer `--kui-*` tokens, and
confirm the result on mobile.
