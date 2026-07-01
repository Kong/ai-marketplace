# MDC Syntax

Load this when writing MDC. These rules are the most stable part of the system;
follow them exactly. Component names and props can drift, so verify those
against live metadata.

MDC (Markdown Components) supercharges Markdown so it renders Vue components with
slots and props. Pages and snippets are both authored in MDC (`.md` / `.mdc`).

## Block components

Use the `::` identifier. The block accepts Markdown or nested components as its
content.

```mdc
::component-name
Content goes here, including Markdown or other components.
::
```

## Props

Two forms. Prefer the YAML block for anything beyond one or two short props.

Inline braces:

```mdc
::alert{ appearance="success" title="Done" }
```

YAML block, one prop per line, between `---` fences inside the component:

```mdc
::alert
---
appearance: "success"
title: "Done"
message: "Plain text in a prop. Use the default slot for Markdown or rich content."
---
::
```

## Binding and non-string props

Prefix a prop name with `:` to bind it to a frontmatter value or to force
non-string interpretation (boolean, number). Keep the prop name and its
reference in the same case (kebab-case or camelCase).

To pass an array or object, provide a JSON string and prefix the key with `:` so
it is decoded:

```mdc
::apis-list
---
:card-attribute-keys: '["version", "labels"]'
:show-filter: true
---
::
```

## Slots

The main content is the `#default` slot. Named slots use `#slotname`. Components
document which slots they expose, commonly `#title` and `#default`.

```mdc
::card
#title
::a{ href="/getting-started" } Getting started ::
#default
Everything you need to make your first call.
::
```

## Nesting

Indent nested block components. Add extra colons on outer components (`::::`,
`::::::`) so the nesting depth stays visually clear.

```mdc
::::container{ display="flex" flex-direction="column" gap="var(--kui-space-100)" }
::card
Inner content.
::
::::
```

## Inline components and span attributes

A block component with no slots can be used inline with a single `:`. Style or
annotate inline text with `[]{}`, which accepts classes (`.name`), IDs
(`#name`), attributes, and inline `style`:

```mdc
Check out our [brand new]{ .highlight style="padding:2px 4px;" } portal!
```

## Frontmatter and data binding

YAML frontmatter at the top of the page sets metadata and arbitrary variables:

```mdc
---
title: "Getting started"
description: "Make your first API call."
customVariable: "Custom value"
---
```

Bind frontmatter values in the body with Vue interpolation:

```mdc
{{ $doc.customVariable || 'default value' }}
```

Confirmed page frontmatter fields include `title`, `description`, `slug`,
`visibility` (`public` or private), `status` (for example `published`), and
`image` for the Open Graph override. Frontmatter here wins over any separately
supplied title and description.

## Snippets

Store repeated content once as a snippet and reference it from pages rather than
copying markup. Snippets are a flat namespace and only appear when a page uses
them. Confirm the exact snippet-embed tag against live metadata or
`portaldocs.konghq.com`, since it is not fully captured here.

## Verify before relying

The Portal Editor provides syntax generators for the more complex components.
When exact props or the snippet-embed syntax matter, read live MDC metadata
through the `kong-konnect` MCP server or check `portaldocs.konghq.com` rather
than assuming.
