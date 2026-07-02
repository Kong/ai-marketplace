# MDC essentials

A reduced fallback for when the Konnect MCP server is not available. With the
server connected, take syntax, components, props, slots, and tokens from it
instead; this file cannot replace live metadata, so anything here is a
general-knowledge starting point, not verified truth.

## Syntax

- Write components as `::component-name` on its own line, content or slots
  below, and close with `::`. Never use HTML tags, a raw `<div>`, or Vue
  `<Component>` syntax.
- Put props in a YAML block between `---` fences, with kebab-case names
  (`background-color`, `show-icon`, `columns-breakpoints`). Quote string values.
- Name slots with `#slot-name`. Leave a blank line between one slot's content
  and the next slot marker. The main content is the default slot.
- Nest a child component by indenting it one level under its parent.

## Choosing components and styling

- Reuse common components by role: a hero for the masthead, sections and
  containers for structure, a responsive column component for parallel items,
  and cards, buttons, alerts, and images for content. You cannot confirm exact
  props or slots without the server, so keep to common ones and tell the user
  they are unverified.
- Prefer `--kui-*` design tokens for color, spacing, and type. The primary token
  family reflects the portal's configured brand color.
- Apply the same design requirements as with the server: dedicated props over a
  catch-all styles prop, WCAG AA contrast, at least 12px between adjacent
  elements, a hero that always has a title, and columns that wrap on mobile.

## Preview

Without the server you cannot generate a preview URL. Ask the user to preview in
the Portal Editor, and check the structure by eye against these rules before
handing it back.
