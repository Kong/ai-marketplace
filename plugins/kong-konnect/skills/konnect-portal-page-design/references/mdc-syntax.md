# MDC Syntax

Load this when writing MDC. These rules are the stable part of the system;
follow them exactly. Component names and props can drift, so verify those
against live metadata.

MDC (Markdown Components) extends Markdown with rich components that take slots
and props. Pages and snippets are both authored in MDC (`.md` / `.mdc`).

## Block components and props

Use the `::` identifier. Pass props inline in braces, or as a YAML block between
`---` fences for anything longer.

```mdc
::alert{ appearance="success" title="Done" }

::alert
---
appearance: "success"
message: "Plain text in a prop. Use the default slot for Markdown."
---
::
```

## Binding non-string props

Prefix a prop with `:` to bind a frontmatter value or force a boolean, number,
or JSON value. Keep prop name and reference in the same case.

```mdc
::apis-list
---
:show-filter: true
:card-attribute-keys: '["version", "labels"]'
---
::
```

## Slots

The main content is `#default`. Named slots use `#slotname`, commonly `#title`.

```mdc
::card
#title
::a{ href="/getting-started" } Getting started ::
#default
Everything you need to make your first call.
::
```

## Nesting and inline

Indent nested components and add extra colons on outer ones (`::::`) so depth
stays clear. A slotless block can be used inline with a single `:`. Style inline
text with `[]{}`, which takes classes, IDs, attributes, and `style`.

```mdc
Check out our [brand new]{ .highlight style="padding:2px 4px;" } portal!
```

## Frontmatter and binding

YAML frontmatter sets metadata and variables. Confirmed fields include `title`,
`description`, `slug`, `visibility`, `status`, and `image`. Frontmatter here
wins over separately supplied title and description. Bind values in the body
with `{{ $doc.variable || 'default' }}`.

## Snippets

Store repeated content once as a snippet and reference it from pages. Snippets
are a flat namespace and only appear when a page uses them. Confirm the exact
snippet-embed tag against live metadata or `portaldocs.konghq.com`.
