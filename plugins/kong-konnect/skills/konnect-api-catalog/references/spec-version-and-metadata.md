# Spec, Version, and Metadata

Use this file when the hard part is versioning style, spec quality, or metadata
alignment.

## Core Rule

Treat specs and version metadata as the governing input for Catalog quality,
not as optional decoration.

## Decision Rules

| Question | Default guidance |
|---|---|
| No version style chosen | semantic versioning is the safest default |
| Major lifecycle split unclear | separate APIs per major version when the lifecycle boundary is real |
| Docs look wrong downstream | check spec and metadata before blaming publication |

Apply those defaults with these checks:

- Keep one API with multiple versions when the lifecycle, audience, and
  implementation surface are still shared.
- Split into distinct APIs when a major version changes ownership, audience,
  registration path, or long-lived support expectations.
- Treat slug, displayed version, and attached spec version as separate fields
  that all need to agree with the intended catalog story.

## What To Inspect

- whether a spec exists for the version that should be documented
- whether the version marked current is the one the operator expects users to
  find first
- whether documentation pages and metadata derive from the intended version
- whether validation warnings point to a bad source artifact rather than a
  Portal rendering problem

## What To Return

Return:

- whether the versioning model itself is sound
- whether the spec/docs inputs are good enough
- whether metadata drift is the real issue
