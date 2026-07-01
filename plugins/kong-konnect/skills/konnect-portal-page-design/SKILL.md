---
name: konnect-portal-page-design
description: Structure and compose Kong Konnect Dev Portal pages with MDC components like heroes, cards, columns, tabbed panels, callouts, and expandable sections. Use for page layout, section design, and component choice. Not for documentation writing or editing.
license: MIT
metadata:
  product: konnect
  category: dev-portal-design
  tags:
    - kong
    - konnect
    - dev-portal
    - mdc
    - markdown-components
    - page-design
---

# Konnect Dev Portal page design

## Goal

Turn a page intent into a well-structured Dev Portal page built from MDC
(Markdown Components). Own the layout: which sections the page needs, which
components express them, and how they compose into a consistent, responsive
result. The `kong-konnect` MCP server owns the facts, component names, props,
slots, syntax, tokens, examples, and preview. Your job is to choose well and
sequence the tools; never invent a component or prop from memory.

## Clarify First

Batch two or three high-impact questions with a sensible default to confirm:

- the page's primary goal and audience
- which sections are wanted (hero, feature columns, doc sections, API list)
- whether it should match the structure of an existing page

## Tool Selection

Use these `kong-konnect` MCP tools. Do not restate their output from memory.

1. `mdc_get_mdc_syntax_guide`: run **once at session start**. Authoritative
   syntax, nesting (2-space indent, matched colon counts), slots, YAML props.
2. `mdc_list_components`: discover what components exist.
3. `mdc_get_component_metadata` (`componentName`): the definitive props and
   slots for a component. Metadata returns prop names in **camelCase**; write
   them **kebab-case** in MDC (`fullWidth` becomes `full-width`). Read before
   you use.
4. `mdc_get_component_examples` (`componentName`): idiomatic usage to copy.
5. `mdc_get_design_tokens`: `--kui-*` values for color, spacing, type.
6. `mdc_format_mdc` then `mdc_validate_mdc_syntax`: clean and check content.
7. `list_portals` (read `canonical_domain`, else `default_domain`) then
   `mdc_get_mdc_preview_url` (needs `portal_origin`) then open with a browser
   tool and screenshot desktop and mobile.

Preview URLs are single-use and time-limited. Regenerate one per view; once a
page is loaded, resize the browser in place to test widths rather than
regenerating per width.

Pages and snippets can be read and written directly through the MCP
(`list_portal_pages`, `get_portal_page`, `create_portal_page`,
`update_portal_page`, and the `*_portal_snippet` tools). Read current state with
`get_portal_page` or `list_portal_pages` before an `update_portal_page`, which
overwrites content. Do not write to a live portal unless the user explicitly
asks; author locally or in a repo otherwise, and preserve an existing `kongctl`
or Terraform toolchain when one is in use.

## References To Load

- `references/layout-patterns.md`
  - Composition judgment (what shape a section wants). Get the exact syntax for
    each shape from `mdc_get_component_examples`.

There is no hand-maintained syntax or component reference. Those come from the
MCP tools above, which stay current as components change.

## Workflow

1. Name the page type and its ordered sections before writing MDC.
2. Map each section to the component whose job it names, then confirm that
   component with `mdc_get_component_metadata` and `mdc_get_component_examples`
   before writing it. Keep the component set small; repetition reads as
   consistency.
3. Compose by nesting `page-section`, `container`, and `multi-column` around
   content, not one monolithic block.
4. Style with `--kui-*` tokens from `mdc_get_design_tokens`; use responsive
   breakpoint props for columns.
5. `mdc_format_mdc` then `mdc_validate_mdc_syntax`.
6. Preview and screenshot at desktop and mobile; iterate.

## MDC Gotchas

- This is the current v3 Konnect portal MDC system. Do not use legacy Gateway
  Enterprise portal templates; they are a different, incompatible model.
- Never invent component or prop names. If metadata does not list it, it does
  not exist. Prop names are kebab-case in MDC even though metadata shows
  camelCase.
- Snippets are a flat namespace and render only when a page references them
  (`::snippet{ name="…" }`). Pages support nested slugs; snippets do not.
- Frontmatter in page content wins over separately supplied title and
  description.
- Reserved root paths (`/login`, `/register`, `/account`) cannot be page slugs.

## Validation Checklist

Before finishing, confirm:

- the page type and its ordered sections are named
- every component and prop used was confirmed against `mdc_get_component_metadata`
- layout uses tokens from `mdc_get_design_tokens` and responsive breakpoints
- repeated blocks are snippets, not copied markup
- every `::image` has alt text and heading levels are sequential
- content passed `mdc_validate_mdc_syntax` and previewed cleanly on desktop and
  mobile

## Handoffs

- Use `konnect-portal-branding` for colors, fonts, imagery, and brand parity.
- Use `technical-writing` for the wording inside the components.
- Use `terraform-konnect` or `kongctl-declarative` to encode pages as code.
- Use `konnect-api-publish` when the goal is getting an API into the portal.
