# Entity Patterns

Use this file when the hard part is how Gateway entities should fit the current
Terraform layout.

## Core Rule

Match the repo's existing ownership pattern before adding new HCL. The entity
model is not separate from the module boundary.

## Boundary Questions

- are services/routes/plugins grouped together or split by domain
- do certificates or consumers live in separate modules
- does the repo already separate infrastructure from Gateway entities
- is the existing split imperfect but still the accepted contract

## What To Return

Return:

- which file or module should own the change
- whether the change is narrow or would trigger a bigger refactor
- whether `decK` would be a better fit for the user’s stated intent
