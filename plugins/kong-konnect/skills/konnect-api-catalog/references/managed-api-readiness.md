# Managed API Readiness

Use this file when the operator says an API is missing or incomplete in Catalog
and the main question is which upstream object is actually missing.

## Core Rule

Do not treat Catalog readiness as one object. Separate API identity, versions,
specs, docs, implementations, and packages.

## Inspection Order

Work from the first missing upstream object, not from the most visible
downstream symptom.

| Stage | Inspect first | Stop and classify here when... |
|---|---|---|
| API identity | API object, name, slug, owning team/system | the API does not exist or its identity is wrong |
| Version | intended current version and lifecycle boundary | the right version is absent or modeled on the wrong API |
| Spec and docs | spec presence, version alignment, generated docs inputs | docs or publication assumptions depend on bad source material |
| Implementation | service or control-plane-backed implementation linkage | the API exists but is not consumable or maps to the wrong runtime surface |
| Package | whether grouping is required at all | packaging is being used to paper over a weak API or implementation model |

## Return Shape

Return:

- the first incomplete stage
- the exact object or linkage that is missing or malformed
- whether the next owner is still Catalog, or a handoff to Portal/app auth is
  now appropriate
