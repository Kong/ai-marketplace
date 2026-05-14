# Package and Implementation Boundaries

Use this file when the operator is mixing packages, individual APIs, and
Gateway implementation linkage.

## Core Rule

Packages are grouping and presentation constructs. They should not hide a weak
API model or missing implementation linkage.

## Useful Distinctions

| Branch | Meaning |
|---|---|
| Individual API modeling | one API object and its versions/docs are the focus |
| Package modeling | grouping multiple operations/APIs for presentation and consumption |
| Implementation linkage | the API should map to a Gateway Service or control-plane-backed implementation |

## Decision Rules

- If the implementation story is unclear, do not call the API consumer-ready.
- If a package is used, explain whether it reflects a business boundary or only
  a technical convenience.
- If the issue is really publication after readiness, hand off to
  `konnect-api-publish`.

## What To Return

Return:

- whether the API model is sound before packaging
- whether implementation linkage exists and is the right one
- whether the package boundary is helping or obscuring the real issue
