# OpenAPI Generation

Use this file when the user starts from an API spec and wants Gateway entities
derived from it.

## Core Rule

Use OpenAPI as the source document for Gateway-entity generation, but do not
assume the generated output matches the repository's layout or ownership
boundaries without cleanup.

## Questions To Clarify

- is the goal initial generation or updating an existing `decK` layout
- which Gateway entities should be derived versus authored manually
- does the repo already keep generated output separate from hand-edited state

## Decision Rules

- If the repo already has an established file split, fold generated entities
  into that shape rather than dropping in a monolith.
- If the spec is only a starting point, generate into a temporary file or
  isolated slice first, then merge only the owned entities into the curated
  state files.
- If the spec is incomplete for runtime behavior, call out what still needs
  explicit Gateway authoring.
- Do not treat OpenAPI-driven generation as a substitute for Konnect platform
  resources or non-Gateway workflows.

## What To Return

Return:

- what can be generated from the spec
- what still requires explicit `decK` authoring
- how the generated result should fit the repo's existing state layout
