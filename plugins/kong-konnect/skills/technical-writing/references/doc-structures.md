# Documentation Page Structures

Pick the shape from the reader's task, then write each section in the house
voice. On a Dev Portal, hand components and layout to
`konnect-portal-page-design`; this file is about what each section says and in
what order.

## Page types

- Landing page: signposts the reader to the right next page. State value in one
  or two lines, then link. Do not teach here.
- How-to: an end-to-end task that ends with a validation step.
- Reference: concepts plus tables and schemas, with everything for one use case
  kept together.

## API or product page

A dependable order:

- Hero: what the product does and who it is for, in one or two lines, plus the
  primary next step. Front-load value.
- Getting started: the shortest path to a first success. List every prerequisite
  up front, give copy-paste steps, and end with a step that proves it worked.
- Authentication: early and self-contained. Show how to obtain and send
  credentials with placeholders. Never show a real secret.
- Request and response samples: one command per block, request and response in
  separate language-tagged blocks, no prompt markers, long commands wrapped.

```bash
curl https://api.example.com/v1/orders \
  -H "Authorization: Bearer API_KEY"
```

```json
{ "id": "order_123", "status": "created" }
```

- Troubleshooting or FAQ: headings phrased as the reader's actual question, with
  the cause and the fix in that order.

## Pull real values

When documenting Konnect resources, pull real control planes, services, routes,
and spec details through the `kong-konnect` MCP server or the user's config.
Concrete examples beat invented ones. Keep secrets out.

## Density

Each section is self-contained and no longer than it needs to be. Cut a sentence
that repeats the previous one; add one if the reader would otherwise guess.
