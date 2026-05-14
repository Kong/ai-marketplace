# Visibility vs Permission

Use this file when the hard question is whether the resource exists, is
visible to this identity, or is only non-mutable.

## Core Rule

Separate these cases:

- resource truly absent
- resource exists but this user cannot see it
- resource exists and is readable but not writable

## Decision Rules

- First prove the resource with a broader-access operator, a live inventory
  source, or a trusted repo artifact before blaming the affected identity.
- If broader-access operators can see it, keep the diagnosis on visibility or
  permission.
- If nobody can see it, do not blame roles first.
- If the user can read but not edit, call that out as a narrower permission
  boundary than full inaccessibility.
- If the resource shows up under a different Konnect surface than the user
  expects, explain the surface mismatch instead of treating it as hidden.

## What To Return

Return one primary outcome:

- absent resource
- visibility-limited resource
- read-only access
- scope mismatch across product surfaces
