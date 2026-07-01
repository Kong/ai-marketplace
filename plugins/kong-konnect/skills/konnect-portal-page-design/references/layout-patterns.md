# Layout Patterns

Load this when composing sections. Each pattern is a starting shape. Verify
props against live metadata and prefer `--kui-*` tokens over hardcoded values.

## Hero

Open with a hero that states value and offers one or two actions.

```mdc
::page-hero
#title
Build with the Example API
#default
Ship your first integration in minutes.

::button{ to="/getting-started" size="large" } Get started ::
::button{ to="/apis" appearance="secondary" size="large" } Browse APIs ::
::
```

## Card grid

Use a responsive grid of cards for parallel features or entry points. Larger
breakpoints inherit smaller values when unset.

```mdc
::grid
---
:grid-columns-breakpoints: '{"mobile":1,"tablet":2,"laptop":3}'
gap: "var(--kui-space-80)"
---
::card
#title
::a{ href="/quickstart" } Quickstart ::
#default
Make your first authenticated call.
::
::card
#title
::a{ href="/reference" } API reference ::
#default
Every endpoint and response.
::
::
```

## Feature row

Alternate text and media by pairing two `::container`s (or a container and an
`::image`) inside a flex `::::container` with a `gap`.

## Doc-page skeleton

Structure a doc page as sections in reading order, kept on one page. Fill the
prose with `technical-writing`.

```mdc
---
title: "Payments API"
description: "Authenticate, make your first call, and handle errors."
---

::page-hero
#title
Payments API
#default
Accept payments in a few requests.
::

## Getting started
## Authentication
## Make a request
## Troubleshooting
```

## Consistency rules

Reuse the same hero and card patterns across pages, group related actions,
extract repeated blocks into snippets, and confirm the result on mobile.
