# Provider and Import

Use this file when the main question is how the self-managed Gateway provider
and import path should be handled.

## Core Rule

Prefer importing live Gateway resources over recreating them. State continuity
matters more than fast greenfield-looking HCL.

## Questions To Clarify

- which Admin API endpoint is actually in scope
- whether auth is already supplied correctly
- whether the resource already exists live
- whether the repo already tracks it under another address or module

## Common Patterns

| Situation | Preferred default |
|---|---|
| Existing live service/route/plugin | import first |
| New narrow entity | add HCL in the existing module layout |
| User really wants export/diff-style GitOps | consider `deck-gateway` instead |

## What To Return

Return:

- whether import is required
- whether provider/auth assumptions are already satisfied
- whether Terraform is still the right tool after that check
