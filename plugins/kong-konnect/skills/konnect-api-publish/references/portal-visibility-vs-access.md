# Portal Visibility vs Access

Use this file when an API may already be published but still does not appear or
cannot be used by the intended audience.

## Core Rule

Separate three questions:

- is the API published to the portal
- should this viewer be able to see it
- can this consumer actually use it after discovery

Treat these as separate evidence checks, not a single Portal-state question.

## Fast Split

| Symptom | Likely branch |
|---|---|
| Portal admins can see it, developers cannot | visibility or audience issue |
| Page exists but signup/use fails | downstream app auth or registration issue |
| API shows in one portal but not another | wrong portal target or publication scope |
| Search/discovery misses it but direct link works | portal visibility/presentation issue, not publication absence |

## Evidence Order

Check in this order:

1. publication exists for the intended portal
2. the complaint is about the same portal and audience the publication targets
3. direct access and discovery both fail, or only one of them fails
4. registration and app-auth requirements begin only after visibility is proven

## Decision Rules

- If publication exists but only some audiences can see it, keep the diagnosis
  on visibility first.
- If the API is visible but registration or credentials fail, hand off toward
  app auth instead of continuing publication debugging.
- If the API is missing from the wrong portal, treat that as target/scope
  error, not global publication failure.

## What To Return

Return whether the problem is:

- missing publication
- wrong portal target or scope
- viewer visibility boundary
- consumer access after successful discovery

Include which viewer or audience boundary produced that conclusion.
