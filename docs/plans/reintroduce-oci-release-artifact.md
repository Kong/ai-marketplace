# Reintroduce OCI Release Artifact Publishing

## Goal

Restore OCI artifact publishing for releases after repository owners decide the
repo should again ship the checked-in skills as a Docker-built image. The
reintroduction must restore the full workflow slice: local validation,
release-time build and publish automation, and contributor docs that describe
the artifact path and when to verify it.

## Current State

OCI artifact publishing was intentionally removed. The current repo still has a
GitHub release flow for versioning, but it no longer:

- builds a Docker image during CI or release
- validates a local OCI packaging path
- ships `Dockerfile.skills` or `.dockerignore`
- publishes an image reference alongside GitHub releases
- documents Docker or OCI artifact checks as part of contributor workflows

Do not assume restoring OCI means redesigning the existing tag-and-release
path. The current release workflow is still the source of truth for versioned
GitHub releases and should be extended rather than replaced.

## Preconditions

Before restoring anything, confirm:

1. Shipping the skills as an OCI artifact is again a supported distribution
   path.
2. The desired artifact shape is still a minimal image that packages the
   checked-in `plugins/kong-konnect/skills/` tree.
3. The target registry, auth model, and security requirements are still known
   and approved.
4. Docker-based validation is acceptable again in local contributor guidance
   and CI/release runners.

If any of those changed, update the implementation instead of recreating the
old flow verbatim.

## Files To Restore Or Update

### OCI Packaging Files

Restore:

- `Dockerfile.skills`
- `.dockerignore`
- `scripts/check_oci_artifact.py`

Expected responsibilities:

- `Dockerfile.skills` builds the artifact image from the checked-in skill tree
- `.dockerignore` narrows the build context to the intended payload
- `scripts/check_oci_artifact.py` validates image labels, extracted layout, and
  byte-for-byte parity with `plugins/kong-konnect/skills/`

### Task And Preflight Automation

Restore OCI handling in:

- `mise.toml`
- `scripts/preflight.py`

Required implementation details:

1. `mise.toml`
   - restore `artifact:check`
   - keep the task description explicit that it builds and validates the local
     OCI artifact image

2. `scripts/preflight.py`
   - restore the `artifact` profile
   - require `docker` for that profile
   - add `artifact` back to the accepted profile list
   - make `all` include the `artifact` profile again

### GitHub Actions Workflows

Restore OCI handling in:

- `.github/workflows/validate.yml`
- `.github/workflows/release.yml`

Required implementation details:

1. `.github/workflows/validate.yml`
   - restore the OCI packaging validation step
   - keep repo validation and OCI validation as separate steps so failures are
     easy to distinguish

2. `.github/workflows/release.yml`
   - restore the OCI validation step in the release preflight stage
   - restore a dedicated publish job between validation and tag/release
   - keep tag creation and GitHub release creation gated on successful artifact
     publication
   - include the published image reference in release notes only if that
     remains part of the supported release contract

If the repo needs a different workflow filename again, update the docs and repo
validators alongside it rather than reintroducing stale names.

### Repo Validation And Docs

Restore or update these files:

- `scripts/check_repo.py`
- `README.md`
- `docs/release.md`
- `docs/testing.md`
- `docs/developer.md`
- `docs/structure.md`

Required doc and validation content:

1. `scripts/check_repo.py`
   - require `.dockerignore` again if it is part of the shipped packaging path
   - restore text-file assertions that mention the OCI validation workflow and
     release flow accurately

2. `docs/release.md`
   - restore OCI validation as part of release-candidate preparation
   - document the publish stage and any release-note artifact reference
   - point at the correct workflow filename

3. `docs/testing.md`
   - restore the `artifact` preflight profile
   - restore the `OCI Artifact` section
   - explain when `artifact:check` is required versus when `mise run ci` is
     enough

4. `docs/developer.md`
   - restore Docker as an optional contributor prerequisite
   - restore OCI-related guidance in the typical loops only where it is truly
     needed
   - keep the release-prep loop aligned with the actual workflow

5. `docs/structure.md`
   - restore the OCI packaging files only if they are again part of the
     checked-in repo contract

6. `README.md`
   - restore any OCI-distribution wording only if the repo is again meant to
     advertise that install or packaging surface publicly

## Suggested Artifact Shape

Unless the release contract has changed, restore the previous minimal pattern:

- a `scratch` image
- labels for version, revision, source, and title
- payload copied from `plugins/kong-konnect/skills/` to the image root
- local validation that compares the extracted payload against the checked-in
  files

Treat that as a starting point only. Revalidate the registry and metadata
requirements before committing.

## Implementation Sequence

1. Confirm OCI distribution is approved again and the registry target is still
   correct.
2. Restore `Dockerfile.skills`, `.dockerignore`, and the local OCI validator
   script.
3. Restore the `artifact:check` task and Docker preflight profile.
4. Restore OCI validation in CI and the publish stage in the release workflow.
5. Update repo validation and contributor docs so they match the restored flow.
6. Run validation.
7. If registry publication is part of the reintroduction scope, run the release
   workflow in a safe environment and verify the pushed artifact and release
   notes.

## Validation Checklist

Run:

```bash
mise run preflight -- artifact
mise run deps
mise run gen
mise run lint
mise run artifact:check
```

If the change is release-oriented, also run:

```bash
gh skill publish --dry-run
mise run release:prepare -- 1.0.1
```

Then verify:

- `scripts/check_oci_artifact.py` passes locally with Docker access
- `mise run ci` and `.github/workflows/validate.yml` both exercise the OCI path
- the release workflow blocks tag/release creation if artifact publication
  fails
- release notes include the artifact reference only when publication succeeds
- docs reference the correct workflow file, packaging files, and validation
  commands

## Non-Goals

Do not broaden this task into:

- a redesign of shared skill installers
- a migration away from GitHub-tagged releases
- a repackaging of skills into a different artifact format unless that change
  is explicitly requested
- unrelated repo-wide documentation rewrites

## Handoff Notes For The Implementing Agent

- Preserve the current GitHub release flow as the versioning backbone. OCI
  publishing should extend it, not replace it.
- Keep the OCI path narrow and content-focused. If a future artifact adds more
  than the checked-in skills payload, update the validation contract
  explicitly.
- If registry auth, runner requirements, or scanning expectations changed since
  removal, document that clearly in the implementation and update this plan so
  it does not preserve stale assumptions.
