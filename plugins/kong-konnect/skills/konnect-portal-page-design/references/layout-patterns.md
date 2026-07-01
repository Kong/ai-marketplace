# Layout patterns

Composition judgment only. Get the exact, current syntax for any shape from
`mdc_get_component_examples` and confirm props with `mdc_get_component_metadata`.
Do not hardcode component names here; they change, and the tools stay current.

## Shapes

- **Hero.** Open with `page-hero`: a title, a short value line, one or two
  actions. Check its slots with metadata before writing (it has named slots for
  tagline, title, description, actions, and image, not a default slot).
- **Feature columns.** Use the responsive column container for parallel items
  (cards, entry points). Set per-breakpoint column counts.
- **Feature row.** Alternate text and media by pairing containers with a gap.
- **Doc page.** Sections in reading order on one page: hero, getting started,
  auth, request/response, troubleshooting. Prose comes from `technical-writing`.

## Consistency

Reuse the same hero and card patterns across pages, group related actions into
buttons, extract repeated blocks into snippets, prefer `--kui-*` tokens, and
confirm the result on mobile.
