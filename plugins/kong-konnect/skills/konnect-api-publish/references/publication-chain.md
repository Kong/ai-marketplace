# Publication Chain

Use this file when the operator says "the API is not published" but the missing
stage is unclear.

## Core Rule

Do not treat publication as one step. Separate:

1. managed API existence
2. version/spec readiness
3. catalog or package readiness
4. portal publication association
5. consumer-facing access

## Questions To Answer

Answer these in order before proposing a fix:

1. Which managed API and version are supposed to be published?
2. Which portal and audience are supposed to receive it?
3. Is the complaint about absence, discoverability, or post-discovery use?

## Stage Map

| Stage | What must exist |
|---|---|
| Managed API | API object and intended identity exist |
| Version/spec | version objects and usable spec/metadata exist |
| Catalog readiness | asset is complete enough for catalog/governance workflows |
| Portal publication | the API is associated to the intended portal audience |
| Consumer use | developers can discover, register, authenticate, and call it |

## Stop Conditions

- If the managed API or version is missing, stop there and hand off upstream.
- If the API asset exists but is not ready for Catalog use, keep the diagnosis
  on Catalog readiness rather than Portal behavior.
- If publication exists but the wrong portal or audience is targeted, return a
  scoping error instead of a generic publication failure.
- If publication and visibility are both proven, stop publication debugging and
  hand off to app auth or access ownership.

## Common Misclassifications

| What operator says | What it often means |
|---|---|
| "Portal bug" | managed API/version/spec is incomplete upstream |
| "Not published" | publication exists, but visibility or access is wrong |
| "Catalog is stale" | wrong version/spec or metadata source |
| "It works internally" | runtime presence without managed/categorized publication state |

## Return Shape

Return:

- the first broken stage in the chain
- the evidence that ruled out earlier stages
- the neighboring skill or tool that owns the next action, if this skill does
  not

Do not mix multiple speculative stages into one diagnosis.
