# Documentation Page Structures

Load this when structuring a page. Pick the shape from the reader's task, then
write each section in the house voice. On a Dev Portal, hand the components and
layout to `konnect-portal-page-design`; this file is about what each section
says and in what order.

## Page types

- Landing page: signposts the reader to the right next page. One or two lines of
  value, then clear links. Do not try to teach here.
- How-to: an end-to-end task with a validation step at the end.
- Reference: concepts plus tables, schemas, and diagrams. Keep everything for one
  use case together.

## API or product documentation page

A dependable order for a product or API page:

### Hero

State what the product does and who it is for in one or two lines. Offer the
primary next step. Front-load value; do not open with history.

### Getting started

The shortest path to a first success.

- List every prerequisite up front. Do not assume tools are already installed.
- Give copy-paste steps in order.
- End with a step that proves it worked.

### Authentication

Put this early and keep it self-contained.

- Show how to obtain credentials and how to send them.
- Use placeholders (`API_KEY`, ALL_CAPS) and `example.com` for illustration,
  `localhost` or environment variables for runnable examples.
- Never show a real secret.

### Request and response samples

- One command per block, request and response in separate blocks.
- Language-tag every block for highlighting.
- No shell prompt markers. Wrap long commands with `\`.
- Annotate with brief comments where a value needs explaining.

```bash
curl https://api.example.com/v1/orders \
  -H "Authorization: Bearer API_KEY" \
  -H "Content-Type: application/json"
```

```json
{ "id": "order_123", "status": "created" }
```

### Troubleshooting or FAQ

- Phrase headings as the reader's actual question or symptom, not a generic
  label.
- Give the cause and the fix, in that order.

## Pull real values

When the page documents Konnect resources, pull real control planes, services,
routes, and spec details through the `kong-konnect` MCP server or from the
user's config. Concrete, correct examples beat invented ones. Keep secrets out.

## Density

Each section should be self-contained and no longer than it needs to be. If a
sentence repeats the previous one or states the obvious, cut it. If a reader
would have to guess a step, add it. That balance, not length, is the target.
