# Layout Patterns

Load this when composing full sections and pages. Each pattern is a starting
shape to adapt. Verify component props against live metadata, and prefer
`--kui-*` tokens over hardcoded values so pages stay consistent with the theme.

## Masthead / hero

Open a landing or product page with a hero that states value and offers one or
two clear actions.

```mdc
::page-hero
---
full-width: true
padding: "clamp(60px, 8vw, 120px)"
---
#title
Build with the Example API
#default
Ship your first integration in minutes.

::button{ to="/getting-started" size="large" } Get started ::
::button{ to="/apis" appearance="secondary" size="large" } Browse APIs ::
::
```

Keep the hero to one headline, one supporting line, and at most two actions.

## Feature or value grid

Use a responsive grid of cards for parallel features or entry points.

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
::a{ href="/guides" } Guides ::
#default
Task-based walkthroughs for common workflows.
::

::card
#title
::a{ href="/reference" } API reference ::
#default
Every endpoint, parameter, and response.
::
::
```

Larger breakpoints inherit smaller values when unset. Confirm the exact
breakpoint prop shape against live metadata.

## Feature row (media beside text)

Alternate text and media across rows for a marketing-style section.

```mdc
::::container{ display="flex" gap="var(--kui-space-100)" }
::container
#default
## Fast to integrate
Clear, task-oriented docs and copy-paste samples.
::button{ to="/getting-started" } Start now ::
::
::image{ src="/images/integrate.svg" alt="Integration diagram" }
::::
```

## APIs list page

For a catalog page, pair a short hero with an APIs list.

```mdc
::page-hero
#title
APIs
#default
Explore and start building.
::

::apis-list
---
:show-filter: true
:card-attribute-keys: '["version"]'
---
::
```

## Documentation page skeleton

Structure a doc page as sections in reading order. Keep everything for one use
case on a single page. Fill the prose with `technical-writing`.

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
Prerequisites, then the shortest path to a first success.

## Authentication
How to obtain and send credentials. End with a verification step.

## Make a request
```bash
curl https://api.example.com/v1/payments \
  -H "Authorization: Bearer API_KEY"
```

::alert{ appearance="info" title="Tip" }
Use a test key first.
::

## Troubleshooting
Common errors phrased as the reader's question, with cause and fix.
```

Load `technical-writing` for how to write each section, and
`konnect-portal-branding` for theme and color.

## Consistency rules

- Reuse the same hero and card patterns across pages.
- Group related actions; do not scatter buttons.
- Extract any block repeated across pages into a snippet.
- Confirm the result on mobile, not just desktop.
